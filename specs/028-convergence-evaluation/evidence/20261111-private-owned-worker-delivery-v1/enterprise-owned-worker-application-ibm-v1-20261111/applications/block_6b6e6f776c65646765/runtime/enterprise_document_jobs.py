"""Durable per-file cleanup intents, fencing and uncertain-creation settlement.

No source payload, title, identity, question, credential, endpoint or error body is
stored. Cleanup targets are derived by the owned adapter, never interpreted from
database text. All transactions end before native API work begins.
"""
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import re
import uuid
from psycopg import sql
from enterprise_sources import SourceUnavailable


@dataclass(frozen=True)
class FileJobLease:
    request_id: str
    token: str = field(repr=False)


class DocumentJobLedger:
    def __init__(self, auth, account_id, target_sha256):
        if not isinstance(account_id, str) or not re.fullmatch('[A-Za-z0-9_-]{1,128}', account_id): raise ValueError('Use the owned company account')
        if not isinstance(target_sha256, str) or not re.fullmatch('[0-9a-f]{64}', target_sha256): raise ValueError('Use the owned immutable cleanup target')
        self.auth, self.account_id, self.target = auth, account_id, target_sha256
        with auth.transaction() as cursor:
            expected=hashlib.sha256(Path(__file__).with_name('enterprise_document_jobs_schema.sql').read_bytes()).hexdigest()
            if cursor.execute('SELECT version,source_sha256 FROM enterprise_document_jobs.schema_version').fetchone()!={'version':1,'source_sha256':expected}:
                raise SourceUnavailable('document_job_schema_changed')

    def parameters(self, identifier):
        if not isinstance(identifier, str) or not re.fullmatch('[0-9a-f]{64}', identifier): raise ValueError('Use the owned per-file request')
        return self.account_id, self.target, identifier

    def allocate(self, identifier, *, ttl_seconds=240):
        if type(ttl_seconds) is not int or not 180 <= ttl_seconds <= 600: raise ValueError('Use a bounded active execution deadline')
        token = str(uuid.uuid4()); values = self.parameters(identifier)
        with self.auth.transaction() as cursor:
            self.auth.require_company(cursor, self.account_id)
            row = cursor.execute("INSERT INTO enterprise_document_jobs.jobs(account_id,target_sha256,request_id,owner_token,phase,state,expires_at,next_attempt_at)VALUES(%s,%s,%s,%s,'input_pending','active',clock_timestamp()+make_interval(secs=>%s),clock_timestamp())ON CONFLICT DO NOTHING RETURNING request_id", (*values, token, ttl_seconds)).fetchone()
            if not row: raise SourceUnavailable('document_execution_identity_conflict')
        return FileJobLease(identifier, token)

    def active(self, cursor, lease, *, lock=False):
        row = cursor.execute("SELECT *,expires_at>clock_timestamp()AS current FROM enterprise_document_jobs.jobs WHERE account_id=%s AND target_sha256=%s AND request_id=%s" + (' FOR UPDATE' if lock else ''), self.parameters(lease.request_id)).fetchone()
        if not row or row['state'] != 'active' or str(row['owner_token']) != lease.token or not row['current']:
            raise SourceUnavailable('document_execution_lease_changed')
        return row

    def guard(self, lease):
        with self.auth.transaction() as cursor: self.active(cursor, lease)

    def advance(self, lease, phase):
        previous = {'job_pending': 'input_pending', 'job_running': 'job_pending', 'succeeded': 'job_running'}
        if phase not in previous: raise ValueError('Use the owned monotonic execution phases')
        with self.auth.transaction() as cursor:
            row = self.active(cursor, lease, lock=True)
            if row['phase'] not in {previous[phase], phase}: raise SourceUnavailable('document_execution_phase_changed')
            cursor.execute('UPDATE enterprise_document_jobs.jobs SET phase=%s,updated_at=clock_timestamp()WHERE account_id=%s AND target_sha256=%s AND request_id=%s', (phase, *self.parameters(lease.request_id)))

    def mark_cleaning(self, cursor, identifier):
        token = str(uuid.uuid4())
        cursor.execute("UPDATE enterprise_document_jobs.jobs SET state='cleaning',cleanup_token=%s,cleanup_until=clock_timestamp()+interval '180 seconds',updated_at=clock_timestamp()WHERE account_id=%s AND target_sha256=%s AND request_id=%s", (token, *self.parameters(identifier)))
        return FileJobLease(identifier, token)

    def claim_owner(self, lease):
        with self.auth.transaction() as cursor:
            row = cursor.execute('SELECT *,cleanup_until>clock_timestamp()AS leased FROM enterprise_document_jobs.jobs WHERE account_id=%s AND target_sha256=%s AND request_id=%s FOR UPDATE', self.parameters(lease.request_id)).fetchone()
            if not row or str(row['owner_token']) != lease.token or row['state'] != 'active': raise SourceUnavailable('document_execution_lease_changed')
            return self.mark_cleaning(cursor, lease.request_id)

    def claim_due(self):
        with self.auth.transaction() as cursor:
            row = cursor.execute("SELECT request_id FROM enterprise_document_jobs.jobs WHERE account_id=%s AND target_sha256=%s AND((state='active'AND expires_at<clock_timestamp())OR(state IN('pending','settling')AND next_attempt_at<=clock_timestamp())OR(state='cleaning'AND cleanup_until<clock_timestamp()))ORDER BY updated_at FOR UPDATE SKIP LOCKED LIMIT 1", (self.account_id, self.target)).fetchone()
            return self.mark_cleaning(cursor, row['request_id']) if row else None

    def cleanup_row(self, cursor, lease):
        row = cursor.execute('SELECT *,cleanup_until>clock_timestamp()AS leased FROM enterprise_document_jobs.jobs WHERE account_id=%s AND target_sha256=%s AND request_id=%s FOR UPDATE', self.parameters(lease.request_id)).fetchone()
        if not row or row['state'] != 'cleaning' or str(row['cleanup_token']) != lease.token or not row['leased']:
            raise SourceUnavailable('document_cleanup_lease_changed')
        return row

    def completed(self, lease):
        with self.auth.transaction() as cursor:
            row = self.cleanup_row(cursor, lease)
            final = row['phase'] == 'succeeded' or (row['settle_until'] is not None and cursor.execute('SELECT %s<=clock_timestamp()AS done', (row['settle_until'],)).fetchone()['done'])
            if final:
                cursor.execute('DELETE FROM enterprise_document_jobs.jobs WHERE account_id=%s AND target_sha256=%s AND request_id=%s', self.parameters(lease.request_id))
                return True
            # Retain incomplete/uncertain creations for delayed cleanup probes.
            # These are scheduling bounds, not a provider deletion/retention SLA.
            delay = [60, 300, 1800, 86400][min(row['settle_round'], 3)]
            cursor.execute("UPDATE enterprise_document_jobs.jobs SET state='settling',cleanup_token=NULL,cleanup_until=NULL,settle_until=coalesce(settle_until,clock_timestamp()+interval '24 hours'),settle_round=least(settle_round+1,4),next_attempt_at=least(clock_timestamp()+make_interval(secs=>%s),coalesce(settle_until,clock_timestamp()+interval '24 hours')),updated_at=clock_timestamp()WHERE account_id=%s AND target_sha256=%s AND request_id=%s", (delay, *self.parameters(lease.request_id)))
            return False

    def failed(self, lease):
        with self.auth.transaction() as cursor:
            row = self.cleanup_row(cursor, lease)
            delay = min(600, 30 * 2 ** min(row['failures'], 5))
            cursor.execute("UPDATE enterprise_document_jobs.jobs SET state='pending',cleanup_token=NULL,cleanup_until=NULL,failures=least(failures+1,1000000),next_attempt_at=clock_timestamp()+make_interval(secs=>%s),updated_at=clock_timestamp()WHERE account_id=%s AND target_sha256=%s AND request_id=%s", (delay, *self.parameters(lease.request_id)))


def initialize_document_jobs(conn):
    if conn.autocommit: raise ValueError('Use an owned operator transaction')
    raw = Path(__file__).with_name('enterprise_document_jobs_schema.sql').read_bytes()
    conn.execute(raw.decode()); conn.execute('INSERT INTO enterprise_document_jobs.schema_version VALUES(1,%s)', (hashlib.sha256(raw).hexdigest(),))


def grant_document_jobs_runtime(conn, role):
    if conn.autocommit or not isinstance(role, str) or not re.fullmatch('[A-Za-z0-9_.@-]{1,63}', role): raise ValueError('Use an owned worker identity and operator transaction')
    expected = hashlib.sha256(Path(__file__).with_name('enterprise_document_jobs_schema.sql').read_bytes()).hexdigest()
    if conn.execute('SELECT version,source_sha256 FROM enterprise_document_jobs.schema_version').fetchone() != (1, expected): raise ValueError('Review the exact fresh document-job schema')
    flags = conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname=%s', (role,)).fetchone()
    if not flags or any(flags[:5]) or not flags[5] or conn.execute("SELECT has_schema_privilege(%s,'enterprise_document_jobs','CREATE')", (role,)).fetchone()[0]: raise ValueError('Use a nonadministrative worker identity')
    for table in ['memberships', 'source_mappings', 'company_bindings', 'schema_version']:
        if conn.execute('SELECT has_table_privilege(%s,%s,%s)', (role, 'enterprise_auth.' + table, 'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES')).fetchone()[0]: raise ValueError('Document worker must not inherit company authority writes')
    if conn.execute("SELECT has_table_privilege(%s,'enterprise_document_jobs.jobs','TRUNCATE,TRIGGER,REFERENCES')", (role,)).fetchone()[0]: raise ValueError('Document worker must not inherit administrative cleanup privileges')
    target = sql.Identifier(role)
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA enterprise_document_jobs TO {}').format(target))
    conn.execute(sql.SQL('GRANT SELECT ON enterprise_document_jobs.schema_version TO {}').format(target))
    conn.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON enterprise_document_jobs.jobs TO {}').format(target))
