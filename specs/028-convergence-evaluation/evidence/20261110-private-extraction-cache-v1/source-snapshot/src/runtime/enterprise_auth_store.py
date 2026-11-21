"""Transactional, encrypted per-person source credentials and one-use OAuth state.

DB transport and the encryption key are injected by an owned native deployment.
No cloud key is generated or persisted here. API credentials are never logged.
"""
from contextlib import contextmanager
from dataclasses import dataclass,field
import hashlib
import base64
import hmac
import json
from pathlib import Path
import re
import secrets
import uuid
from cryptography.fernet import Fernet,InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from psycopg.rows import dict_row
from enterprise_identity import CompanyPrincipal
from enterprise_sources import SourceDenied,SourceUnavailable,DelegatedAccess


def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def opaque(value):
    if not isinstance(value,str)or not 1<=len(value)<=160 or any(ord(c)<33 for c in value):raise SourceDenied('invalid_source_binding')
    return value


def secret_binding(value):
    if not isinstance(value,str)or not re.fullmatch(r'[A-Za-z0-9_-]{32,160}',value):raise SourceDenied('invalid_oauth_browser_binding')
    return value


class CredentialBox:
    def __init__(self,key):
        self.box=Fernet(key)
        self._fingerprint_key=HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=b'atmem-enterprise-private-fingerprint-v1').derive(base64.urlsafe_b64decode(key))
    def fingerprint(self,context,value):
        raw=json.dumps({'context':context,'value':value},sort_keys=True,separators=(',',':')).encode()
        if len(raw)>2000000:raise SourceUnavailable('credential_material_too_large')
        return hmac.new(self._fingerprint_key,raw,hashlib.sha256).hexdigest()
    def seal(self,context,value):
        raw=json.dumps({'context':context,'value':value},sort_keys=True,separators=(',',':')).encode()
        if len(raw)>2000000:raise SourceUnavailable('credential_material_too_large')
        return self.box.encrypt(raw).decode()
    def open(self,context,ciphertext):
        try:
            raw=self.box.decrypt(ciphertext.encode());value=json.loads(raw)
            if value['context']!=context or not isinstance(value['value'],dict):raise ValueError('Invalid context')
            return value['value']
        except (InvalidToken,ValueError,KeyError,TypeError,AttributeError):raise SourceDenied('credential_binding_invalid')from None


@dataclass(frozen=True)
class SourceMapping:
    source_id: str
    source_subject: str
    version: int
    attempt_sha256: str|None = field(default=None,repr=False,compare=False)


@dataclass(frozen=True)
class SourceWitness:
    source_id: str
    source_subject: str = field(repr=False)
    mapping_version: int
    consent_id: str = field(repr=False)


class EnterpriseAuthStore:
    def __init__(self,connect,key):self.connect=connect;self.box=CredentialBox(key)

    @contextmanager
    def transaction(self):
        with self.connect()as conn:
            if conn.autocommit:raise ValueError('Credential operations require a transaction')
            with conn.cursor(row_factory=dict_row)as cur:
                cur.execute("SET LOCAL search_path=pg_catalog,enterprise_auth,pg_temp");cur.execute("SET LOCAL lock_timeout='3s'");cur.execute("SET LOCAL statement_timeout='10s'")
                yield cur

    def _authorize(self,cur,principal,source_id=None):
        if not isinstance(principal,CompanyPrincipal):raise SourceDenied('company_identity_required')
        principal.require()
        membership=cur.execute('SELECT issuer,subject,active FROM enterprise_auth.memberships WHERE account_id=%s AND principal_key=%s',(principal.account_id,principal.key)).fetchone()
        if not membership or not membership['active']or membership['issuer']!=principal.issuer or membership['subject']!=principal.subject:raise SourceDenied('company_membership_required')
        if source_id is None:return None
        opaque(source_id)
        row=cur.execute('SELECT source_subject,version,active FROM enterprise_auth.source_mappings WHERE account_id=%s AND principal_key=%s AND source_id=%s',(principal.account_id,principal.key,source_id)).fetchone()
        if not row or not row['active']:raise SourceDenied('source_mapping_required')
        return SourceMapping(source_id,row['source_subject'],row['version'])

    def authorize(self,principal):
        with self.transaction()as cur:self._authorize(cur,principal)

    def source_witness(self,principal,source_id):
        with self.transaction()as cur:
            mapping=self._authorize(cur,principal,source_id)
            row=cur.execute('SELECT mapping_version,consent_id,status FROM enterprise_auth.connections WHERE account_id=%s AND principal_key=%s AND source_id=%s',(principal.account_id,principal.key,source_id)).fetchone()
            # Refresh can rotate credential material without changing consent.
            # Native adapters independently check the access token's lifetime and
            # current source permissions; failed/uncertain reconnection is denied.
            if not row or row['status']not in {'connected','refreshing'}or row['mapping_version']!=mapping.version:raise SourceDenied('source_consent_required')
            return SourceWitness(source_id,mapping.source_subject,mapping.version,str(row['consent_id']))

    def check_source_witness(self,principal,witness):
        if not isinstance(witness,SourceWitness)or self.source_witness(principal,witness.source_id)!=witness:raise SourceDenied('source_connection_changed')

    def context(self,principal,mapping,kind):return [kind,principal.account_id,principal.key,mapping.source_id,mapping.version]
    def event(self,cur,principal,source_id,event):cur.execute('INSERT INTO enterprise_auth.events(account_id,principal_key,source_id,event)VALUES(%s,%s,%s,%s)',(principal.account_id,principal.key,source_id,event))

    def begin(self,principal,source_id,browser_nonce,flow,state=None):
        secret_binding(browser_nonce)
        if not isinstance(flow,dict):raise ValueError('Supply a native OAuth flow object')
        state=state or secrets.token_urlsafe(32);secret_binding(state)
        with self.transaction()as cur:
            mapping=self._authorize(cur,principal,source_id)
            cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('enterprise-oauth-start:'+principal.account_id+':'+principal.key,))
            # Bound abandoned attempts without deleting another person's state.
            cur.execute("DELETE FROM enterprise_auth.attempts WHERE account_id=%s AND principal_key=%s AND expires_at<clock_timestamp()AND(consumed_at IS NULL OR consumed_at<clock_timestamp()-interval '1 minute')",(principal.account_id,principal.key))
            count=cur.execute('SELECT count(*) AS n FROM enterprise_auth.attempts WHERE account_id=%s AND principal_key=%s AND consumed_at IS NULL',(principal.account_id,principal.key)).fetchone()['n']
            if count>=5:raise SourceUnavailable('oauth_attempt_limit')
            encrypted=self.box.seal(self.context(principal,mapping,'flow')+[digest(state)],flow)
            cur.execute("INSERT INTO enterprise_auth.attempts(state_sha256,account_id,principal_key,source_id,mapping_version,browser_sha256,flow_ciphertext,expires_at)VALUES(%s,%s,%s,%s,%s,%s,%s,clock_timestamp()+interval '5 minutes')",(digest(state),principal.account_id,principal.key,source_id,mapping.version,digest(browser_nonce),encrypted))
            self.event(cur,principal,source_id,'connect_started')
        return state

    def consume(self,principal,source_id,browser_nonce,state):
        secret_binding(browser_nonce);secret_binding(state)
        with self.transaction()as cur:
            mapping=self._authorize(cur,principal,source_id)
            row=cur.execute('UPDATE enterprise_auth.attempts SET consumed_at=clock_timestamp()WHERE state_sha256=%s AND account_id=%s AND principal_key=%s AND source_id=%s AND mapping_version=%s AND browser_sha256=%s AND consumed_at IS NULL AND expires_at>clock_timestamp() RETURNING flow_ciphertext',(digest(state),principal.account_id,principal.key,source_id,mapping.version,digest(browser_nonce))).fetchone()
            if not row:raise SourceDenied('oauth_state_unavailable')
            flow=self.box.open(self.context(principal,mapping,'flow')+[digest(state)],row['flow_ciphertext'])
        # Commit consumption before any network exchange: uncertain code redemption
        # requires a fresh consent flow, never a blind authorization-code replay.
        return SourceMapping(mapping.source_id,mapping.source_subject,mapping.version,digest(state)),flow

    def save(self,principal,mapping,material):
        if not isinstance(material,dict):raise ValueError('Supply verified native credential material')
        with self.transaction()as cur:
            current=self._authorize(cur,principal,mapping.source_id)
            if current!=mapping:raise SourceDenied('source_mapping_changed')
            if not isinstance(mapping.attempt_sha256,str)or not re.fullmatch('[0-9a-f]{64}',mapping.attempt_sha256):raise SourceDenied('source_consent_unavailable')
            self._connection_lock(cur,principal,mapping.source_id)
            receipt=cur.execute("SELECT state_sha256 FROM enterprise_auth.attempts WHERE state_sha256=%s AND account_id=%s AND principal_key=%s AND source_id=%s AND mapping_version=%s AND consumed_at IS NOT NULL AND consumed_at>clock_timestamp()-interval '1 minute'AND completed_at IS NULL FOR UPDATE",(mapping.attempt_sha256,principal.account_id,principal.key,mapping.source_id,mapping.version)).fetchone()
            if not receipt:raise SourceDenied('source_connection_changed')
            consent_id=str(uuid.uuid4())
            encrypted=self.box.seal(self.context(principal,mapping,'credential')+[consent_id],material)
            cur.execute("INSERT INTO enterprise_auth.connections(account_id,principal_key,source_id,mapping_version,consent_id,revision,credential_ciphertext,status)VALUES(%s,%s,%s,%s,%s,1,%s,'connected')ON CONFLICT(account_id,principal_key,source_id)DO UPDATE SET mapping_version=EXCLUDED.mapping_version,consent_id=EXCLUDED.consent_id,revision=enterprise_auth.connections.revision+1,credential_ciphertext=EXCLUDED.credential_ciphertext,status='connected',updated_at=clock_timestamp()",(principal.account_id,principal.key,mapping.source_id,mapping.version,consent_id,encrypted))
            cur.execute('UPDATE enterprise_auth.attempts SET completed_at=clock_timestamp()WHERE state_sha256=%s',(mapping.attempt_sha256,))
            self.event(cur,principal,mapping.source_id,'connect_completed')

    def _abandon(self,principal,source_id,revision):
        with self.transaction()as cur:
            row=cur.execute("UPDATE enterprise_auth.connections SET credential_ciphertext=NULL,status='needs_reconnect',updated_at=clock_timestamp()WHERE account_id=%s AND principal_key=%s AND source_id=%s AND revision=%s AND status='refreshing'RETURNING revision",(principal.account_id,principal.key,source_id,revision)).fetchone()
            if row:self.event(cur,principal,source_id,'needs_reconnect')

    def credentials(self,principal,source_id,refresh):
        # Persist the refresh intent BEFORE HTTP. A crash leaves a durable fence,
        # not an old token that another replica can silently reuse. No DB lock is
        # held across the source request; revocation/disconnection can proceed.
        stale=False
        with self.transaction()as cur:
            mapping=self._authorize(cur,principal,source_id)
            row=cur.execute("SELECT mapping_version,consent_id,revision,credential_ciphertext,status,updated_at<clock_timestamp()-interval '1 minute' AS stale FROM enterprise_auth.connections WHERE account_id=%s AND principal_key=%s AND source_id=%s FOR UPDATE",(principal.account_id,principal.key,source_id)).fetchone()
            if not row or row['mapping_version']!=mapping.version or row['status']not in {'connected','refreshing'}:raise SourceDenied('source_reconnection_required')
            if row['status']=='refreshing':
                if not row['stale']:raise SourceUnavailable('source_refresh_in_progress')
                cur.execute("UPDATE enterprise_auth.connections SET credential_ciphertext=NULL,status='needs_reconnect',updated_at=clock_timestamp()WHERE account_id=%s AND principal_key=%s AND source_id=%s",(principal.account_id,principal.key,source_id))
                self.event(cur,principal,source_id,'needs_reconnect');stale=True
            else:
                context=self.context(principal,mapping,'credential')+[str(row['consent_id'])];material=self.box.open(context,row['credential_ciphertext']);revision=row['revision']+1
                cur.execute("UPDATE enterprise_auth.connections SET status='refreshing',revision=%s,updated_at=clock_timestamp()WHERE account_id=%s AND principal_key=%s AND source_id=%s",(revision,principal.account_id,principal.key,source_id))
        if stale:raise SourceDenied('source_reconnection_required')
        try:
            updated,access=refresh(mapping,material)
            if not isinstance(updated,dict)or not isinstance(access,DelegatedAccess)or access.source_subject!=mapping.source_subject:raise SourceDenied('source_refresh_identity_mismatch')
            access.require(principal.key)
            with self.transaction()as cur:
                if self._authorize(cur,principal,source_id)!=mapping:raise SourceDenied('source_mapping_changed')
                changed=cur.execute("UPDATE enterprise_auth.connections SET credential_ciphertext=%s,status='connected',revision=revision+1,updated_at=clock_timestamp()WHERE account_id=%s AND principal_key=%s AND source_id=%s AND revision=%s AND status='refreshing'RETURNING revision",(self.box.seal(context,updated),principal.account_id,principal.key,source_id,revision)).fetchone()
                if not changed:raise SourceDenied('source_connection_changed')
                self.event(cur,principal,source_id,'refresh_completed')
        except Exception:
            try:self._abandon(principal,source_id,revision)
            except Exception:pass  # Durable refreshing fence already committed.
            raise SourceDenied('source_reconnection_required')from None
        return access

    def connection_status(self,principal,source_id):
        with self.transaction()as cur:
            self._authorize(cur,principal)
            mapping=cur.execute('SELECT version,active FROM enterprise_auth.source_mappings WHERE account_id=%s AND principal_key=%s AND source_id=%s',(principal.account_id,principal.key,source_id)).fetchone()
            if not mapping or not mapping['active']:return 'needs_setup'
            row=cur.execute('SELECT mapping_version,status FROM enterprise_auth.connections WHERE account_id=%s AND principal_key=%s AND source_id=%s',(principal.account_id,principal.key,source_id)).fetchone()
            if not row or row['mapping_version']!=mapping['version']:return 'needs_reconnect'
            return row['status']

    def _connection_lock(self,cur,principal,source_id):
        cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('enterprise-connection:'+principal.account_id+':'+principal.key+':'+source_id,))

    def disconnect(self,principal,source_id):
        with self.transaction()as cur:
            self._authorize(cur,principal,source_id)
            self._connection_lock(cur,principal,source_id)
            cur.execute("UPDATE enterprise_auth.connections SET credential_ciphertext=NULL,status='revoked',revision=revision+1,updated_at=clock_timestamp()WHERE account_id=%s AND principal_key=%s AND source_id=%s",(principal.account_id,principal.key,source_id))
            cur.execute('DELETE FROM enterprise_auth.attempts WHERE account_id=%s AND principal_key=%s AND source_id=%s',(principal.account_id,principal.key,source_id))
            self.event(cur,principal,source_id,'disconnected')


def initialize_auth_store(conn):
    source=Path(__file__).with_name('enterprise_auth_schema.sql').read_bytes()
    conn.execute(source.decode());conn.execute('INSERT INTO enterprise_auth.schema_version VALUES(1,%s)',(hashlib.sha256(source).hexdigest(),))


def grant_auth_runtime(conn,role):
    from psycopg import sql
    if conn.autocommit or not isinstance(role,str)or not re.fullmatch(r'[A-Za-z0-9_.@-]{1,63}',role):raise ValueError('Use an owned nonadministrative broker role and transaction')
    expected=hashlib.sha256(Path(__file__).with_name('enterprise_auth_schema.sql').read_bytes()).hexdigest()
    if conn.execute('SELECT version,source_sha256 FROM enterprise_auth.schema_version').fetchone()!=(1,expected):raise ValueError('Review the owned exact schema before grants')
    flags=conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname=%s',(role,)).fetchone()
    if not flags or any(flags[:5])or not flags[5]:raise ValueError('Use an existing nonadministrative broker login')
    if conn.execute('SELECT has_schema_privilege(%s,%s,%s)',(role,'enterprise_auth','CREATE')).fetchone()[0]:raise ValueError('Broker must not own or create authentication schema objects')
    for table in ['memberships','source_mappings','schema_version']:
        if conn.execute('SELECT has_table_privilege(%s,%s,%s)',(role,'enterprise_auth.'+table,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES')).fetchone()[0]:raise ValueError('Broker must not inherit authority-table write privileges')
    name=sql.Identifier(role)
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA enterprise_auth TO {}').format(name))
    conn.execute(sql.SQL('GRANT SELECT ON enterprise_auth.schema_version,enterprise_auth.memberships,enterprise_auth.source_mappings TO {}').format(name))
    conn.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON enterprise_auth.attempts,enterprise_auth.sessions TO {}').format(name))
    conn.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE ON enterprise_auth.connections TO {}').format(name))
    conn.execute(sql.SQL('GRANT INSERT ON enterprise_auth.events TO {}').format(name))
    conn.execute(sql.SQL('GRANT USAGE ON ALL SEQUENCES IN SCHEMA enterprise_auth TO {}').format(name))
