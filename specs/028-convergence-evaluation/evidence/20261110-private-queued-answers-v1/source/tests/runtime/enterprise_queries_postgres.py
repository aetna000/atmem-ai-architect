"""Real restricted SQL, crypto and transactional Procrastinate outbox checks."""
from concurrent.futures import ThreadPoolExecutor
import json
import hashlib
from pathlib import Path
import sys
import unittest
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/azure-runtime-sdk'),str(ROOT/'tests/runtime')]
import psycopg
import enterprise_auth_postgres as auth_fixture
from enterprise_sessions import CompanySessions
from enterprise_queries import producer_queries,initialize_query_store,grant_query_runtime,QueryMissing,QueryConflict,QueryLeaseLost
from enterprise_sources import SourceDenied


class DurableQuestions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture=auth_fixture.EnterpriseCredentialTransactions;fixture.setUpClass()
        cls.owner_dsn,cls.app_dsn,cls.key=fixture.owner_dsn,fixture.app_dsn,fixture.key
        from psycopg.conninfo import conninfo_to_dict
        role=conninfo_to_dict(cls.app_dsn)['user']
        with psycopg.connect(cls.owner_dsn)as conn:initialize_query_store(conn);grant_query_runtime(conn,role,worker=True)

    def setUp(self):
        auth_fixture.EnterpriseCredentialTransactions.setUp(self)
        self.sessions=CompanySessions(self.store);self.browser=self.sessions.create(self.principal)
        self.session=self.sessions.authenticate(self.browser.token)
        self.queries=producer_queries(self.store,self.app_dsn,self.account)
        self.question='SYNTHETIC PRIVATE QUESTION: what is the retention policy?'
        self.request=str(uuid.uuid4())

    def submit(self):return self.queries.submit(self.session,self.question,self.request)
    def receipt(self):return {'format':'enterprise-answer-receipt-v1','question':self.question,'answer':{'answer':'SYNTHETIC PRIVATE ANSWER','citations':[],'abstained':True},'selections':[],'documents':[]}
    def row(self,identity):
        with psycopg.connect(self.owner_dsn,row_factory=psycopg.rows.dict_row)as conn:return conn.execute('SELECT * FROM enterprise_queries.requests WHERE id=%s',(identity,)).fetchone()
    def expire_lease(self,identity):
        with psycopg.connect(self.owner_dsn)as conn:conn.execute("UPDATE enterprise_queries.requests SET lease_until=clock_timestamp()-interval '1 second'WHERE id=%s",(identity,))

    def test_encrypted_submission_and_atomic_identity_only_queue(self):
        identity=self.submit();row=self.row(identity)
        self.assertNotIn(self.question,row['question_ciphertext'])
        with psycopg.connect(self.owner_dsn)as conn:
            args=conn.execute("SELECT args FROM enterprise_queries.procrastinate_jobs WHERE args->>'query_id'=%s",(identity,)).fetchall()
            self.assertEqual(args,[({'query_id':identity},)])
            self.assertNotIn(self.question,json.dumps(args))
        self.assertEqual(self.queries.claim(identity).question,self.question)

    def test_idempotent_retries_and_changed_question_conflict(self):
        identity=self.submit();self.assertEqual(self.submit(),identity)
        with self.assertRaises(QueryConflict):self.queries.submit(self.session,'another question',self.request)
        with psycopg.connect(self.owner_dsn)as conn:self.assertEqual(conn.execute("SELECT count(*)FROM enterprise_queries.procrastinate_jobs WHERE args->>'query_id'=%s",(identity,)).fetchone()[0],1)

    def test_other_user_or_browser_cannot_observe_or_cancel(self):
        identity=self.submit();other=self.sessions.authenticate(self.sessions.create(self.other).token)
        same_user=self.sessions.authenticate(self.sessions.create(self.principal).token)
        for session in [other,same_user]:
            with self.assertRaises(QueryMissing):self.queries.get(session,identity)
            with self.assertRaises(QueryMissing):self.queries.cancel(session,identity)

    def test_duplicate_claims_have_one_live_owner(self):
        identity=self.submit()
        with ThreadPoolExecutor(max_workers=2)as pool:claims=list(pool.map(lambda _:self.queries.claim(identity),range(2)))
        self.assertEqual(sum(value is not None for value in claims),1)
        self.assertEqual(self.row(identity)['attempt'],1)

    def test_ready_result_is_encrypted_and_ciphertext_context_bound(self):
        identity=self.submit();lease=self.queries.claim(identity);self.queries.complete(lease,self.receipt())
        row=self.queries.get(self.session,identity);self.assertNotIn('PRIVATE ANSWER',row['result_ciphertext'])
        self.assertEqual(self.queries.open_result(row),self.receipt())
        with self.assertRaises(SourceDenied):self.queries.open_result({**row,'id':str(uuid.uuid4())})

    def test_cancel_during_work_erases_input_and_fences_late_result(self):
        identity=self.submit();lease=self.queries.claim(identity);self.queries.cancel(self.session,identity)
        with self.assertRaises(QueryLeaseLost):self.queries.complete(lease,self.receipt())
        row=self.row(identity);self.assertEqual(row['state'],'cancelled');self.assertIsNone(row['question_ciphertext']);self.assertIsNone(row['result_ciphertext'])

    def test_expired_lease_recovery_fences_prior_worker(self):
        identity=self.submit();old=self.queries.claim(identity);self.expire_lease(identity)
        self.assertGreaterEqual(self.queries.recover(),1)
        new=self.queries.claim(identity);self.assertNotEqual(old.token,new.token)
        with self.assertRaises(QueryLeaseLost):self.queries.complete(old,self.receipt())
        self.queries.complete(new,self.receipt());self.assertEqual(self.row(identity)['state'],'ready')

    def test_logout_or_membership_revocation_prevents_model_and_result_work(self):
        identity=self.submit();lease=self.queries.claim(identity);self.sessions.revoke(self.session)
        with self.assertRaises(SourceDenied):self.queries.guard(lease)
        with self.assertRaises(SourceDenied):self.queries.complete(lease,self.receipt())
        self.expire_lease(identity);self.assertIsNone(self.queries.claim(identity));self.assertEqual(self.row(identity)['state'],'cancelled')

    def test_membership_changes_apply_to_a_queued_question(self):
        identity=self.submit()
        with psycopg.connect(self.owner_dsn)as conn:conn.execute('UPDATE enterprise_auth.memberships SET active=false WHERE account_id=%s AND principal_key=%s',(self.account,self.principal.key))
        self.assertIsNone(self.queries.claim(identity));self.assertEqual(self.row(identity)['state'],'cancelled')

    def test_worker_retries_are_bounded_and_do_not_store_exception_bodies(self):
        identity=self.submit()
        for _ in range(3):
            lease=self.queries.claim(identity);self.queries.failed(lease,'unavailable',retry=True)
        self.assertIsNone(self.queries.claim(identity));row=self.row(identity);self.assertEqual(row['state'],'failed');self.assertIsNone(row['question_ciphertext'])
        self.assertEqual(row['error_code'],'unavailable')

    def test_changed_source_requeues_ready_result_and_clears_stale_ciphertext(self):
        identity=self.submit();lease=self.queries.claim(identity);self.queries.complete(lease,self.receipt())
        self.queries.requeue(self.session,identity,lease.attempt);row=self.row(identity)
        self.assertEqual(row['state'],'queued');self.assertIsNone(row['result_ciphertext']);self.assertEqual(self.queries.claim(identity).attempt,2)

    def test_expired_ready_result_is_scrubbed_without_a_browser_poll(self):
        identity=self.submit();lease=self.queries.claim(identity);self.queries.complete(lease,self.receipt())
        with psycopg.connect(self.owner_dsn)as conn:conn.execute("UPDATE enterprise_queries.requests SET expires_at=clock_timestamp()-interval '1 second'WHERE id=%s",(identity,))
        self.queries.recover();row=self.row(identity);self.assertEqual(row['state'],'expired');self.assertIsNone(row['question_ciphertext']);self.assertIsNone(row['result_ciphertext'])

    def test_question_identity_mac_is_not_a_guessable_plaintext_digest(self):
        identity=self.submit();row=self.row(identity)
        self.assertNotEqual(row['question_mac'],hashlib.sha256(self.question.encode()).hexdigest())
        another=self.queries.submit(self.session,self.question,str(uuid.uuid4()))
        self.assertNotEqual(self.row(another)['question_mac'],row['question_mac'])

    def test_another_company_worker_cannot_claim_or_recover_this_job(self):
        identity=self.submit();foreign=producer_queries(self.store,self.app_dsn,'other-company')
        self.assertIsNone(foreign.claim(identity));self.assertEqual(foreign.recover(),0)
        self.assertEqual(self.row(identity)['state'],'queued')
        self.assertNotEqual(foreign.task.queue,self.queries.task.queue)

    def test_active_capacity_is_bounded_per_person_not_other_users(self):
        for _ in range(3):self.queries.submit(self.session,self.question,str(uuid.uuid4()))
        from enterprise_sources import SourceUnavailable
        with self.assertRaisesRegex(SourceUnavailable,'query_capacity_reached'):self.queries.submit(self.session,self.question,str(uuid.uuid4()))
        other=self.sessions.authenticate(self.sessions.create(self.other).token)
        self.assertIsInstance(self.queries.submit(other,self.question,str(uuid.uuid4())),str)

    def test_failed_queue_notification_is_reconciled_with_its_domain_request(self):
        identity=self.submit()
        with psycopg.connect(self.owner_dsn)as conn:
            conn.execute('SET LOCAL search_path=pg_catalog,enterprise_queries,pg_temp')
            conn.execute("UPDATE enterprise_queries.procrastinate_jobs SET status='failed'WHERE args->>'query_id'=%s",(identity,))
        self.assertEqual(self.queries.recover(),1)
        with psycopg.connect(self.owner_dsn)as conn:self.assertEqual(conn.execute("SELECT count(*)FROM enterprise_queries.procrastinate_jobs WHERE args->>'query_id'=%s AND status='todo'",(identity,)).fetchone()[0],1)

    def test_old_answer_ciphertext_cannot_be_replayed_into_a_later_attempt(self):
        identity=self.submit();first=self.queries.claim(identity);self.queries.complete(first,self.receipt());old=self.queries.get(self.session,identity)['result_ciphertext']
        self.queries.requeue(self.session,identity,first.attempt);second=self.queries.claim(identity);self.queries.complete(second,self.receipt())
        current=self.queries.get(self.session,identity)
        with self.assertRaises(SourceDenied):self.queries.open_result({**current,'result_ciphertext':old})


if __name__=='__main__':unittest.main(verbosity=2)
