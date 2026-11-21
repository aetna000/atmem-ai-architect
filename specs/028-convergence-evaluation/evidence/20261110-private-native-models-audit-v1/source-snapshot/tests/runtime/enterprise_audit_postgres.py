"""Real encrypted-question/append-only SQL audit, no native vendor/cloud calls."""
from pathlib import Path
import sys
import unittest
import uuid
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / '.local/azure-runtime-sdk'), str(ROOT / 'tests/runtime')]
import psycopg
from psycopg.conninfo import conninfo_to_dict
import enterprise_auth_postgres as fixture
from enterprise_audit import KnowledgeAudit, initialize_audit, grant_audit_writer
from enterprise_auth_store import EnterpriseAuthStore
from enterprise_identity import CompanyPrincipal
from enterprise_queries import producer_queries, initialize_query_store, grant_query_runtime
from enterprise_sessions import CompanySessions
from enterprise_sources import SourceUnavailable

ANSWER = {'event': 'knowledge.answer', 'outcome': 'answered', 'sources': 2, 'documents': 3}


class AuditTransactions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = fixture.EnterpriseCredentialTransactions
        parent.setUpClass()
        cls.owner_dsn, cls.app_dsn, cls.key = parent.owner_dsn, parent.app_dsn, parent.key
        with psycopg.connect(cls.owner_dsn) as conn:
            initialize_audit(conn)
            role = conninfo_to_dict(cls.app_dsn)['user']
            grant_audit_writer(conn, role)
            initialize_query_store(conn)
            grant_query_runtime(conn, role, worker=True)

    def setUp(self):
        fixture.EnterpriseCredentialTransactions.setUp(self)
        self.audit = KnowledgeAudit(self.store, self.account)

    def rows(self):
        with psycopg.connect(self.owner_dsn) as conn:
            return conn.execute('SELECT account_id,principal_key,trace_id,query_id,attempt,event,outcome,source_count,document_count FROM enterprise_audit.events WHERE account_id=%s ORDER BY id', (self.account,)).fetchall()

    def test_records_restart_visible_outcomes_without_private_content(self):
        record = self.audit.bind(self.principal)
        record(ANSWER)
        record({'event': 'knowledge.release', 'outcome': 'released', 'sources': 2, 'documents': 3})
        restarted = EnterpriseAuthStore(lambda: psycopg.connect(self.app_dsn), self.key)
        KnowledgeAudit(restarted, self.account).bind(self.principal)({'event': 'knowledge.answer', 'outcome': 'abstained', 'sources': 2, 'documents': 0})
        rows = self.rows(); self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0][2], rows[1][2]); self.assertNotEqual(rows[0][2], rows[2][2])
        self.assertNotIn(self.principal.subject, repr(rows)); self.assertEqual(rows[0][1], self.principal.key)

    def test_unknown_payload_fields_and_invalid_counts_never_persist(self):
        record = self.audit.bind(self.principal)
        invalid = [{**ANSWER, 'question': 'SYNTHETIC PRIVATE QUESTION'}, {**ANSWER, 'answer': 'SYNTHETIC PRIVATE ANSWER'},
                   {**ANSWER, 'sourceId': 'SYNTHETIC PRIVATE SOURCE'}, {**ANSWER, 'sources': True},
                   {**ANSWER, 'documents': True}, {**ANSWER, 'documents': 9}, {**ANSWER, 'outcome': 'released'},
                   {'event': 'knowledge.answer', 'outcome': 'answered', 'sources': 1}]
        for event in invalid:
            with self.assertRaises(ValueError): record(event)
        self.assertEqual(self.rows(), [])

    def test_runtime_cannot_read_rewrite_or_erase_history(self):
        self.audit.bind(self.principal)(ANSWER)
        for operation in ['SELECT * FROM enterprise_audit.events', 'UPDATE enterprise_audit.events SET outcome=\'withheld\'',
                          'DELETE FROM enterprise_audit.events', 'TRUNCATE enterprise_audit.events',
                          'ALTER TABLE enterprise_audit.events ADD COLUMN private_text text']:
            with psycopg.connect(self.app_dsn) as conn:
                with self.assertRaises(psycopg.errors.InsufficientPrivilege): conn.execute(operation)
        self.assertEqual(len(self.rows()), 1)

    def test_withheld_can_be_audited_after_local_membership_revocation(self):
        record = self.audit.bind(self.principal)
        with psycopg.connect(self.owner_dsn) as conn:
            conn.execute('UPDATE enterprise_auth.memberships SET active=false WHERE account_id=%s', (self.account,))
        record({'event': 'knowledge.answer', 'outcome': 'withheld', 'sources': 2})
        self.assertEqual(self.rows()[0][6], 'withheld')

    def query(self):
        session = CompanySessions(self.store).create(self.principal)
        sessions = CompanySessions(self.store)
        browser = sessions.authenticate(session.token)
        store = producer_queries(self.store, self.app_dsn, self.account)
        identity = store.submit(browser, 'SYNTHETIC PRIVATE QUESTION', str(uuid.uuid4()))
        lease = store.claim(identity)
        return store, lease

    def test_query_attempt_is_bound_and_expired_work_can_record_withheld(self):
        store, lease = self.query()
        record = self.audit.bind(self.principal, query_id=lease.id, attempt=lease.attempt)
        record(ANSWER)
        store.failed(lease, 'unavailable')
        record({'event': 'knowledge.answer', 'outcome': 'withheld', 'sources': 2})
        rows = self.rows(); self.assertEqual(len(rows), 2)
        self.assertEqual(str(rows[0][3]), lease.id); self.assertEqual(rows[0][4], 1)
        self.assertNotIn(lease.question, repr(rows))

    def test_unknown_other_principal_and_future_attempt_cannot_forge_query_audit(self):
        _, lease = self.query()
        for principal, identity, attempt in [(self.principal, str(uuid.uuid4()), 1),
                (self.other, lease.id, 1), (self.principal, lease.id, 2)]:
            with self.assertRaises(SourceUnavailable):
                self.audit.bind(principal, query_id=identity, attempt=attempt)(ANSWER)
        self.assertEqual(self.rows(), [])

    def test_other_company_and_noncanonical_attempt_bindings_are_rejected(self):
        other = CompanyPrincipal('different-company', self.principal.issuer, self.principal.subject, self.principal.expires_at)
        with self.assertRaises(ValueError): self.audit.bind(other)
        for identity, attempt in [(None, 1), (str(uuid.uuid4()), True), (str(uuid.uuid4()), 4), (uuid.uuid4().hex, 1)]:
            with self.assertRaises(ValueError): self.audit.bind(self.principal, query_id=identity, attempt=attempt)

    def test_database_outage_is_sanitized_and_no_audit_success_is_invented(self):
        class Unavailable:
            def transaction(self): raise RuntimeError('SYNTHETIC DATABASE SECRET')
        with self.assertRaises(SourceUnavailable) as error:
            KnowledgeAudit(Unavailable(), self.account).bind(self.principal)(ANSWER)
        self.assertEqual(str(error.exception), 'knowledge_audit_unavailable')

    def test_grant_rejects_inherited_history_and_authority_writes(self):
        role = conninfo_to_dict(self.app_dsn)['user']
        with psycopg.connect(self.owner_dsn) as conn:
            conn.execute('GRANT SELECT ON enterprise_audit.events TO ' + role)
            with self.assertRaises(ValueError): grant_audit_writer(conn, role)
            conn.execute('REVOKE SELECT ON enterprise_audit.events FROM ' + role)
            conn.execute('GRANT UPDATE ON enterprise_auth.memberships TO ' + role)
            with self.assertRaises(ValueError): grant_audit_writer(conn, role)
            conn.execute('REVOKE UPDATE ON enterprise_auth.memberships FROM ' + role)


if __name__ == '__main__': unittest.main()
