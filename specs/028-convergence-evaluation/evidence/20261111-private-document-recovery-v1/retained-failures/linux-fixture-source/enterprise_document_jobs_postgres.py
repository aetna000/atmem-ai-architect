"""Actual SQL/leases/process death; Google operations are explicit fixtures."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/azure-runtime-sdk'),str(ROOT/'tests/runtime')]
import psycopg
from psycopg.rows import dict_row
from enterprise_auth_store import EnterpriseAuthStore
from enterprise_configuration import session_domain
from enterprise_deployment_fixture import fresh_database,metadata
from enterprise_operator import activate
from enterprise_document_jobs import DocumentJobLedger,FileJobLease
from enterprise_google_jobs import GoogleBatchDocuments,GoogleDocumentApi
from enterprise_google_jobs_acceptance import config,NativeHttp
from enterprise_sources import SourceUnavailable,SourceDenied


class DurableDocumentJobs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.database=fresh_database()
    def setUp(self):
        self.account=uuid.uuid4().hex;self.owned=metadata(self.account)
        with psycopg.connect(self.database['owner'])as conn:activate(conn,self.owned)
        self.auth=EnterpriseAuthStore(lambda:psycopg.connect(self.database['worker']),self.database['key'],company_domain=session_domain(self.owned))
        self.http=NativeHttp();self.runner=GoogleBatchDocuments(config(),api=GoogleDocumentApi(session=self.http,credential=lambda:'SYNTHETIC-TOKEN'),poll_seconds=.01)
        self.runner.attach_runtime(self.auth,self.account);self.ledger=self.runner.ledger
    def rows(self):
        with psycopg.connect(self.database['owner'],row_factory=dict_row)as conn:
            return conn.execute('SELECT * FROM enterprise_document_jobs.jobs WHERE account_id=%s ORDER BY created_at',(self.account,)).fetchall()
    def due(self, *, expire=False):
        with psycopg.connect(self.database['owner'])as conn:
            conn.execute("UPDATE enterprise_document_jobs.jobs SET next_attempt_at=clock_timestamp()-interval '1 second'"+(",expires_at=clock_timestamp()-interval '1 second'"if expire else'')+' WHERE account_id=%s',(self.account,))

    def test_intent_commits_before_remote_creation_and_success_retires_metadata(self):
        original=self.http.request;observed=[]
        def request(method,url,**values):
            if method=='POST'and'upload/storage'in url:
                row=self.rows()[0];observed.append(row['phase']);self.assertEqual(row['state'],'active')
                self.assertNotIn('PRIVATE',json.dumps(row,default=str))
            return original(method,url,**values)
        self.http.request=request
        result=self.runner.from_source(b'PRIVATE approved policy.','text/plain',lambda:None)
        self.assertEqual(result['text'],'PRIVATE approved policy.');self.assertEqual(observed,['input_pending']);self.assertEqual(self.rows(),[])

    def test_abrupt_process_death_and_late_native_effect_are_recovered_after_restart(self):
        with tempfile.TemporaryDirectory(prefix='atmem-native-job-crash-')as folder:
            remote=Path(folder)/'owned-input-object'
            code="""import json,os,sys
from pathlib import Path
value=json.load(sys.stdin)
root=Path.cwd();sys.path[:0]=[value['runtime'],str(root/'.local/azure-runtime-sdk')]
import psycopg
from enterprise_auth_store import EnterpriseAuthStore
from enterprise_google_jobs import GoogleBatchDocuments
auth=EnterpriseAuthStore(lambda:psycopg.connect(value['database']),value['key'].encode(),company_domain=value['domain'])
class Crash:
 def json(self,method,url,**options):
  assert method=='POST'and '/upload/storage/'in url
  Path(value['remote']).write_bytes(options['data'])
  os._exit(17)
runner=GoogleBatchDocuments(value['config'],api=Crash());runner.attach_runtime(auth,value['account'])
runner.from_source(b'OWNED SYNTHETIC CRASH INPUT','text/plain',lambda:None)
"""
            private={'database':self.database['worker'],'key':self.database['key'].decode(),'domain':session_domain(self.owned),'account':self.account,'config':config(),'remote':str(remote),'runtime':str(Path(sys.modules['enterprise_document_jobs'].__file__).parent)}
            child=subprocess.run([sys.executable,'-I','-c',code],cwd=ROOT,input=json.dumps(private).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
            self.assertEqual(child.returncode,17,child.stderr.decode());self.assertEqual(child.stdout,b'');self.assertTrue(remote.exists())
            row=self.rows()[0];self.assertEqual((row['phase'],row['state']),('input_pending','active'))
            original=self.http.request
            def delete(method,url,**values):
                if method=='DELETE'and'storage.googleapis.com'in url:remote.unlink(missing_ok=True)
                return original(method,url,**values)
            self.http.request=delete
            restarted=GoogleBatchDocuments(config(),api=GoogleDocumentApi(session=self.http,credential=lambda:'SYNTHETIC-TOKEN'),poll_seconds=.01);restarted.attach_runtime(self.auth,self.account)
            self.due(expire=True);counts=restarted.reconcile(limit=1)
            self.assertEqual(counts,{'claimed':1,'retired':0,'settling':1,'failed':0});self.assertFalse(remote.exists())
            with self.assertRaises(SourceUnavailable):self.ledger.guard(FileJobLease(row['request_id'],str(row['owner_token'])))
            remote.write_bytes(b'OWNED SIMULATED LATE CLOUD COMMIT');self.due()
            self.assertEqual(restarted.reconcile(limit=1)['settling'],1);self.assertFalse(remote.exists())
            with psycopg.connect(self.database['owner'])as conn:conn.execute("UPDATE enterprise_document_jobs.jobs SET settle_until=clock_timestamp()-interval '1 second',next_attempt_at=clock_timestamp()-interval '1 second'WHERE account_id=%s",(self.account,))
            self.assertEqual(restarted.reconcile(limit=1)['retired'],1);self.assertEqual(self.rows(),[])

    def test_two_reconcilers_cannot_claim_one_live_cleanup_lease(self):
        self.ledger.allocate('a'*64);self.due(expire=True)
        with ThreadPoolExecutor(max_workers=2)as pool:values=list(pool.map(lambda _:self.ledger.claim_due(),range(2)))
        self.assertEqual(sum(value is not None for value in values),1)

    def test_expired_cleanup_token_cannot_remove_or_modify_a_new_owner(self):
        active=self.ledger.allocate('a'*64);old=self.ledger.claim_owner(active)
        with psycopg.connect(self.database['owner'])as conn:conn.execute("UPDATE enterprise_document_jobs.jobs SET cleanup_until=clock_timestamp()-interval '1 second'WHERE account_id=%s",(self.account,))
        current=self.ledger.claim_due();self.assertNotEqual(old.token,current.token)
        for action in [self.ledger.completed,self.ledger.failed]:
            with self.assertRaises(SourceUnavailable):action(old)
        self.assertEqual(self.rows()[0]['state'],'cleaning');self.assertFalse(self.ledger.completed(current))

    def test_target_and_company_scopes_do_not_adopt_other_cleanup_records(self):
        other_target=DocumentJobLedger(self.auth,self.account,'b'*64);other_target.allocate('a'*64)
        account=uuid.uuid4().hex;owned=metadata(account)
        with psycopg.connect(self.database['owner'])as conn:activate(conn,owned)
        auth=EnterpriseAuthStore(lambda:psycopg.connect(self.database['worker']),self.database['key'],company_domain=session_domain(owned))
        DocumentJobLedger(auth,account,self.runner.target).allocate('b'*64)
        with psycopg.connect(self.database['owner'])as conn:conn.execute("UPDATE enterprise_document_jobs.jobs SET expires_at=clock_timestamp()-interval '1 second'")
        self.assertIsNone(self.ledger.claim_due())
        self.assertIsNotNone(other_target.claim_due())

    def test_cleanup_failure_is_durable_and_new_adapter_retries_without_recreating_work(self):
        self.http.cleanup_error=True
        with self.assertRaisesRegex(SourceUnavailable,'cleanup_unavailable'):self.runner.from_source(b'PRIVATE approved policy.','text/plain',lambda:None)
        row=self.rows()[0];self.assertEqual((row['state'],row['phase'],row['failures']),('pending','succeeded',1))
        post_count=sum(method=='POST'for method,_,_ in self.http.calls)
        self.http.cleanup_error=False;self.due()
        other=GoogleBatchDocuments(config(),api=GoogleDocumentApi(session=self.http,credential=lambda:'SYNTHETIC-TOKEN'),poll_seconds=.01);other.attach_runtime(self.auth,self.account)
        self.assertEqual(other.reconcile(limit=1)['retired'],1);self.assertEqual(self.rows(),[])
        self.assertEqual(sum(method=='POST'for method,_,_ in self.http.calls),post_count)

    def test_phase_rewind_expiration_and_duplicate_identity_fail_closed(self):
        lease=self.ledger.allocate('a'*64)
        with self.assertRaises(SourceUnavailable):self.ledger.allocate('a'*64)
        with self.assertRaises(SourceUnavailable):self.ledger.advance(lease,'succeeded')
        self.ledger.advance(lease,'job_pending');self.ledger.advance(lease,'job_running')
        with self.assertRaises(SourceUnavailable):self.ledger.advance(lease,'job_pending')
        self.due(expire=True)
        with self.assertRaises(SourceUnavailable):self.ledger.guard(lease)

    def test_api_cannot_read_or_write_job_metadata_and_worker_cannot_administer_schema(self):
        for dsn,statement in [(self.database['api'],'SELECT * FROM enterprise_document_jobs.jobs'),(self.database['api'],'DELETE FROM enterprise_document_jobs.jobs'),(self.database['worker'],'TRUNCATE enterprise_document_jobs.jobs'),(self.database['worker'],'CREATE TABLE enterprise_document_jobs.unowned(value text)')]:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with psycopg.connect(dsn)as conn:conn.execute(statement)

    def test_stale_schema_is_not_adopted_by_a_new_ledger(self):
        try:
            with psycopg.connect(self.database['owner'])as conn:conn.execute("UPDATE enterprise_document_jobs.schema_version SET source_sha256='stale'")
            with self.assertRaisesRegex(SourceUnavailable,'schema_changed'):DocumentJobLedger(self.auth,self.account,self.runner.target)
        finally:
            import hashlib
            expected=hashlib.sha256((ROOT/'src/runtime/enterprise_document_jobs_schema.sql').read_bytes()).hexdigest()
            with psycopg.connect(self.database['owner'])as conn:conn.execute('UPDATE enterprise_document_jobs.schema_version SET source_sha256=%s',(expected,))

    def test_cleanup_still_owed_after_company_registration_changes(self):
        self.ledger.allocate('a'*64);self.due(expire=True)
        changed=metadata(self.account);changed['company']['web']['clientId']='changed-approved-registration'
        with psycopg.connect(self.database['owner'])as conn:activate(conn,changed)
        self.assertIsNotNone(self.ledger.claim_due())
        with self.assertRaises(SourceDenied):self.ledger.allocate('b'*64)


if __name__=='__main__':unittest.main(verbosity=2)
