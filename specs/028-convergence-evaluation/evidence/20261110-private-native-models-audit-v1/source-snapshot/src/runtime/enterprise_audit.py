"""Append-only private audit: owned identity/trace plus bounded outcome counts.

Never store questions, titles, source/document IDs, snippets, answers or secrets.
Withheld events must remain recordable after consent/session expiry or withdrawal;
this writer is not an authorization grant. SQL failure prevents answer release.
"""
import hashlib
from pathlib import Path
import re
import uuid
from psycopg import sql
from enterprise_identity import CompanyPrincipal
from enterprise_sources import SourceUnavailable


class KnowledgeAudit:
    def __init__(self, auth, account_id):
        if not isinstance(account_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', account_id):
            raise ValueError('Supply the owned company audit domain')
        self.auth, self.account_id = auth, account_id

    def bind(self, principal, *, query_id=None, attempt=None):
        if not isinstance(principal, CompanyPrincipal) or principal.account_id != self.account_id:
            raise ValueError('Audit identity must belong to the owned company')
        if query_id is not None:
            if (not isinstance(query_id, str) or str(uuid.UUID(query_id)) != query_id
                or type(attempt) is not int or not 1 <= attempt <= 3):
                raise ValueError('Supply the owned canonical question attempt')
        elif attempt is not None:
            raise ValueError('Audit attempt requires its question identity')
        trace = str(uuid.uuid4())

        def record(event):
            if (not isinstance(event, dict) or set(event) not in (
                    {'event', 'outcome', 'sources'}, {'event', 'outcome', 'sources', 'documents'})
                or event['event'] not in {'knowledge.answer', 'knowledge.release'}
                or event['outcome'] not in ({'answered', 'abstained', 'withheld'} if event['event'] == 'knowledge.answer' else {'released', 'withheld'})
                or type(event['sources']) is not int or not 1 <= event['sources'] <= 20):
                raise ValueError('Invalid owned audit event')
            documents = event.get('documents')
            if ((documents is not None and (type(documents) is not int or not 0 <= documents <= event['sources'] * 4))
                or (event['outcome'] != 'withheld' and documents is None)):
                raise ValueError('Invalid owned audit counts')
            values = (self.account_id, principal.key, trace, query_id, attempt,
                      event['event'], event['outcome'], event['sources'], documents)
            try:
                with self.auth.transaction() as cursor:
                    statement = '''INSERT INTO enterprise_audit.events
                        (account_id,principal_key,trace_id,query_id,attempt,event,outcome,source_count,document_count)
                        SELECT %s,%s,%s,%s,%s,%s,%s,%s,%s'''
                    if query_id is not None:
                        # The trace comes from a known owned question/attempt, not
                        # an arbitrary event dictionary or model-provided identity.
                        statement += ''' WHERE EXISTS(SELECT 1 FROM enterprise_queries.requests
                            WHERE id=%s AND account_id=%s AND principal_key=%s AND attempt>=%s)'''
                        values += (query_id, self.account_id, principal.key, attempt)
                    cursor.execute(statement, values)
                    if cursor.rowcount != 1:
                        raise ValueError('Audit question binding is no longer available')
            except Exception:
                raise SourceUnavailable('knowledge_audit_unavailable') from None
        return record


def initialize_audit(conn):
    if conn.autocommit:
        raise ValueError('Use an operator transaction for a fresh audit schema')
    body = Path(__file__).with_name('enterprise_audit_schema.sql').read_bytes()
    conn.execute(body.decode())
    conn.execute('INSERT INTO enterprise_audit.schema_version VALUES(1,%s)', (hashlib.sha256(body).hexdigest(),))


def grant_audit_writer(conn, role):
    if conn.autocommit or not isinstance(role, str) or not re.fullmatch(r'[A-Za-z0-9_.@-]{1,63}', role):
        raise ValueError('Use an owned nonadministrative role and operator transaction')
    expected = hashlib.sha256(Path(__file__).with_name('enterprise_audit_schema.sql').read_bytes()).hexdigest()
    if conn.execute('SELECT version,source_sha256 FROM enterprise_audit.schema_version').fetchone() != (1, expected):
        raise ValueError('Review the exact fresh audit schema before granting access')
    flags = conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname=%s', (role,)).fetchone()
    if not flags or any(flags[:5]) or not flags[5] or conn.execute("SELECT has_schema_privilege(%s,'enterprise_audit','CREATE')", (role,)).fetchone()[0]:
        raise ValueError('Use a nonadministrative role that does not own the audit schema')
    for table in ['memberships', 'source_mappings', 'schema_version']:
        if conn.execute('SELECT has_table_privilege(%s,%s,%s)', (role, 'enterprise_auth.' + table, 'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES')).fetchone()[0]:
            raise ValueError('Audit runtime must not inherit authority-table write privileges')
    if conn.execute("SELECT has_table_privilege(%s,'enterprise_audit.events','SELECT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES')", (role,)).fetchone()[0]:
        raise ValueError('Audit writer must not inherit history read/change permissions')
    target = sql.Identifier(role)
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA enterprise_audit TO {}').format(target))
    conn.execute(sql.SQL('GRANT INSERT ON enterprise_audit.events TO {}').format(target))
    conn.execute(sql.SQL('GRANT USAGE ON SEQUENCE enterprise_audit.events_id_seq TO {}').format(target))
