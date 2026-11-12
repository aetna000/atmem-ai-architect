"""Encrypted immutable-byte extraction reuse, never cached source authorization.

Only a native source adapter can invoke ``from_source`` with its live version/access
check. Every hit still requires newly authorized source bytes. Native source and
company/job checks surround reads, extraction, publication and return. No source
URL, private title, user identity or credential is stored in the cache.
"""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import re
import time
import uuid
from psycopg import sql
from enterprise_document import MAX_INPUT, MAX_TEXT, media_type
from enterprise_sources import SourceUnavailable


class ExtractionLeaseLost(SourceUnavailable):
    pass


def checked_text(value):
    if not isinstance(value, str) or not value.strip() or '\x00' in value:
        raise SourceUnavailable('document_extraction_unavailable')
    try:
        if len(value.encode('utf-8')) > MAX_TEXT:
            raise ValueError()
    except (ValueError, UnicodeError):
        raise SourceUnavailable('document_extraction_unavailable') from None
    return value


class ExtractionCache:
    def __init__(self, auth, account_id, parser_revision, *, ttl_seconds=900, lease_seconds=150, wait_seconds=160):
        if not isinstance(account_id, str) or not re.fullmatch('[A-Za-z0-9_-]{1,128}', account_id):
            raise ValueError('Supply the owned company account')
        if not isinstance(parser_revision, str) or not re.fullmatch('[0-9a-f]{64}', parser_revision):
            raise ValueError('Supply the reviewed complete parser artifact revision')
        if (type(ttl_seconds) is not int or not 60 <= ttl_seconds <= 3600
            or type(lease_seconds) is not int or not 15 <= lease_seconds <= 300
            or type(wait_seconds) is not int or not 1 <= wait_seconds <= 600):
            raise ValueError('Use bounded owned cache deadlines')
        self.auth, self.account_id, self.parser_revision = auth, account_id, parser_revision
        self.ttl_seconds, self.lease_seconds, self.wait_seconds = ttl_seconds, lease_seconds, wait_seconds

    @contextmanager
    def transaction(self):
        with self.auth.transaction() as cur:
            cur.execute('SET LOCAL search_path=pg_catalog,enterprise_extractions,pg_temp')
            yield cur

    def identity(self, raw, declared):
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_INPUT:
            raise SourceUnavailable('source_document_unsupported')
        try:
            mime = media_type(declared)
        except Exception:
            raise SourceUnavailable('source_document_unsupported') from None
        digest = hashlib.sha256(raw).hexdigest()
        key = self.auth.box.fingerprint(['document-extraction-cache', self.account_id, self.parser_revision, mime], digest)
        return key, digest, mime

    def context(self, key):
        return ['document-extraction-cache', self.account_id, self.parser_revision, key]

    def claim(self, key):
        """Brief transaction only; parser/network work never holds SQL row locks."""
        with self.transaction() as cur:
            token = str(uuid.uuid4())
            cur.execute("INSERT INTO enterprise_extractions.documents(account_id,parser_revision,content_key,state,lease_token,lease_until,expires_at)VALUES(%s,%s,%s,'building',%s,clock_timestamp()+make_interval(secs=>%s),clock_timestamp()+make_interval(secs=>%s))ON CONFLICT DO NOTHING",
                (self.account_id, self.parser_revision, key, token, self.lease_seconds, self.lease_seconds))
            row = cur.execute('SELECT *,expires_at>clock_timestamp()AS current,lease_until>clock_timestamp()AS leased FROM enterprise_extractions.documents WHERE account_id=%s AND parser_revision=%s AND content_key=%s FOR UPDATE',
                (self.account_id, self.parser_revision, key)).fetchone()
            if row['state'] == 'ready' and row['current']:
                return 'ready', row['value_ciphertext']
            if row['state'] == 'building' and row['leased']:
                return ('claimed', token) if str(row['lease_token']) == token else ('waiting', None)
            cur.execute("UPDATE enterprise_extractions.documents SET state='building',value_ciphertext=NULL,lease_token=%s,lease_until=clock_timestamp()+make_interval(secs=>%s),expires_at=clock_timestamp()+make_interval(secs=>%s)WHERE account_id=%s AND parser_revision=%s AND content_key=%s",
                (token, self.lease_seconds, self.lease_seconds, self.account_id, self.parser_revision, key))
            return 'claimed', token

    def publish(self, key, token, value):
        cipher = self.auth.box.seal(self.context(key), value)
        with self.transaction() as cur:
            row = cur.execute("UPDATE enterprise_extractions.documents SET state='ready',lease_token=NULL,lease_until=NULL,value_ciphertext=%s,expires_at=clock_timestamp()+make_interval(secs=>%s)WHERE account_id=%s AND parser_revision=%s AND content_key=%s AND state='building'AND lease_token=%s AND lease_until>clock_timestamp()RETURNING content_key",
                (cipher, self.ttl_seconds, self.account_id, self.parser_revision, key, token)).fetchone()
            if not row:
                raise ExtractionLeaseLost('document_extraction_lease_changed')

    def abandon(self, key, token):
        with self.transaction() as cur:
            cur.execute("DELETE FROM enterprise_extractions.documents WHERE account_id=%s AND parser_revision=%s AND content_key=%s AND state='building'AND lease_token=%s",
                (self.account_id, self.parser_revision, key, token))

    def open(self, key, digest, mime, cipher):
        value = self.auth.box.open(self.context(key), cipher)
        if set(value) != {'sha256', 'mediaType', 'text'} or value['sha256'] != digest or value['mediaType'] != mime:
            raise SourceUnavailable('document_extraction_binding_invalid')
        return checked_text(value['text'])

    def wrap(self, extract, authorize):
        if not callable(extract) or not callable(authorize):
            raise ValueError('Supply owned extraction and live company/job authority')
        return CachedDecoder(self, extract, authorize)

    def purge(self, limit=1000):
        if type(limit) is not int or not 1 <= limit <= 5000:
            raise ValueError('Use a bounded expiration batch')
        with self.transaction() as cur:
            rows = cur.execute('DELETE FROM enterprise_extractions.documents WHERE(account_id,parser_revision,content_key)IN(SELECT account_id,parser_revision,content_key FROM enterprise_extractions.documents WHERE account_id=%s AND expires_at<clock_timestamp()ORDER BY expires_at FOR UPDATE SKIP LOCKED LIMIT %s)RETURNING content_key',
                (self.account_id, limit)).fetchall()
            return len(rows)


class CachedDecoder:
    def __init__(self, cache, extract, authorize):
        self.cache, self.extract, self.authorize = cache, extract, authorize

    def __call__(self, raw, declared):
        # A plain callback does not prove the surrounding native source has a live
        # authorization/version check. Unreviewed adapters must not bypass it.
        raise SourceUnavailable('source_validation_required')

    def from_source(self, raw, declared, revalidate):
        if not callable(revalidate):
            raise ValueError('Supply the native live source check')
        key, digest, mime = self.cache.identity(raw, declared)
        deadline = time.monotonic() + self.cache.wait_seconds
        def guard():
            self.authorize()
            revalidate()
        guard()
        while True:
            self.authorize()
            state, material = self.cache.claim(key)
            if state == 'ready':
                guard()
                text = self.cache.open(key, digest, mime, material)
                guard()
                return text
            if state == 'claimed':
                try:
                    guard()
                    text = checked_text(self.extract(raw, mime))
                    guard()
                    self.cache.publish(key, material, {'sha256': digest, 'mediaType': mime, 'text': text})
                    guard()
                    return text
                except BaseException:
                    # A failed/denied/stale extractor never replaces a newer row.
                    self.cache.abandon(key, material)
                    raise
            if time.monotonic() >= deadline:
                raise SourceUnavailable('document_extraction_busy')
            time.sleep(min(.2, max(0, deadline - time.monotonic())))


def initialize_extraction_cache(conn):
    if conn.autocommit:
        raise ValueError('Use an owned operator transaction')
    source = Path(__file__).with_name('enterprise_extraction_schema.sql').read_bytes()
    conn.execute(source.decode())
    conn.execute('INSERT INTO enterprise_extractions.schema_version VALUES(1,%s)', (hashlib.sha256(source).hexdigest(),))


def grant_extraction_runtime(conn, role):
    if conn.autocommit or not isinstance(role, str) or not re.fullmatch('[A-Za-z0-9_.@-]{1,63}', role):
        raise ValueError('Use an owned nonadministrative runtime role and operator transaction')
    expected = hashlib.sha256(Path(__file__).with_name('enterprise_extraction_schema.sql').read_bytes()).hexdigest()
    if conn.execute('SELECT version,source_sha256 FROM enterprise_extractions.schema_version').fetchone() != (1, expected):
        raise ValueError('Review the exact fresh cache schema before granting access')
    flags = conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname=%s', (role,)).fetchone()
    if not flags or any(flags[:5]) or not flags[5] or conn.execute("SELECT has_schema_privilege(%s,'enterprise_extractions','CREATE')", (role,)).fetchone()[0]:
        raise ValueError('Use a nonadministrative role that does not own the cache schema')
    for table in ['memberships', 'source_mappings', 'schema_version']:
        if conn.execute('SELECT has_table_privilege(%s,%s,%s)', (role, 'enterprise_auth.' + table, 'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES')).fetchone()[0]:
            raise ValueError('Cache runtime must not inherit authority-table write privileges')
    target = sql.Identifier(role)
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA enterprise_extractions TO {}').format(target))
    conn.execute(sql.SQL('GRANT SELECT ON enterprise_extractions.schema_version TO {}').format(target))
    conn.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON enterprise_extractions.documents TO {}').format(target))
