"""Actual SQL/restart/process death; ECS/S3 remain explicit owned fixtures."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'tests/runtime'),str(ROOT/'.local/aws-web-runtime-sdk')]
import psycopg
from psycopg.rows import dict_row
from enterprise_auth_store import EnterpriseAuthStore
from enterprise_configuration import session_domain
from enterprise_deployment_fixture import fresh_database,metadata
from enterprise_operator import activate
from enterprise_aws_jobs import EcsDocuments
from enterprise_aws_execution_contract import Ecs,Objects,verified_hosts
from enterprise_aws_jobs_contract import config,AwsDocumentTaskContract
from enterprise_sources import SourceUnavailable


class DurableAwsDocuments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database=fresh_database();AwsDocumentTaskContract.setUpClass();cls.model=AwsDocumentTaskContract.model
    def setUp(self):
        self.account=uuid.uuid4().hex;self.owned=metadata(self.account,'aws')
        with psycopg.connect(self.database['owner'])as conn:activate(conn,self.owned)
        self.auth=EnterpriseAuthStore(lambda:psycopg.connect(self.database['worker']),self.database['key'],company_domain=session_domain(self.owned))
        self.api=Ecs(self.model);self.objects=Objects();self.runner=self.adapter()
    def adapter(self):
        runner=EcsDocuments(config(),api=self.api,objects=self.objects,host_check=verified_hosts,poll_seconds=.01)
        runner.attach_runtime(self.auth,self.account);return runner
    def rows(self):
        with psycopg.connect(self.database['owner'],row_factory=dict_row)as conn:return conn.execute('SELECT * FROM enterprise_document_jobs.jobs WHERE account_id=%s',(self.account,)).fetchall()
    def due(self):
        with psycopg.connect(self.database['owner'])as conn:conn.execute("UPDATE enterprise_document_jobs.jobs SET expires_at=clock_timestamp()-interval '1 second',next_attempt_at=clock_timestamp()-interval '1 second'WHERE account_id=%s",(self.account,))
    def test_intent_is_committed_before_s3_and_success_retires_its_metadata(self):
        original=self.objects.put;seen=[]
        def put(*args):
            row=self.rows()[0];seen.append((row['phase'],row['state']));return original(*args)
        self.objects.put=put
        self.assertEqual(self.runner.from_source(b'policy','text/plain',lambda:None)['text'],'policy')
        self.assertEqual(seen,[('input_pending','active')]);self.assertEqual(self.rows(),[])
    def test_cleanup_failure_is_retried_after_adapter_restart_without_rerunning_task(self):
        self.objects.delete_failure=True
        with self.assertRaises(SourceUnavailable):self.runner.from_source(b'policy','text/plain',lambda:None)
        self.assertEqual((self.rows()[0]['phase'],self.rows()[0]['state']),('succeeded','pending'))
        launches=sum(op=='run_task'for op,_ in self.api.calls);self.objects.delete_failure=False;self.due()
        self.assertEqual(self.adapter().reconcile(limit=1),{'claimed':1,'retired':1,'settling':0,'failed':0})
        self.assertEqual(self.rows(),[]);self.assertEqual(sum(op=='run_task'for op,_ in self.api.calls),launches)
    def test_actual_process_death_after_native_start_is_recovered_without_create_ack(self):
        with tempfile.TemporaryDirectory(prefix='atmem-aws-document-crash-')as folder:
            root=Path(folder);remote=root/'owned-input';state=root/'owned-task-metadata.json'
            code="""import json,os,sys
from pathlib import Path
value=json.load(sys.stdin);sys.path[:0]=[value['runtime'],value['tests'],str(Path.cwd()/'.local/aws-web-runtime-sdk')]
import psycopg
from enterprise_auth_store import EnterpriseAuthStore
from enterprise_aws_jobs import EcsDocuments
from enterprise_aws_execution_contract import Ecs,Objects,verified_hosts
from enterprise_aws_jobs_contract import config,AwsDocumentTaskContract
AwsDocumentTaskContract.setUpClass()
class Crash(Ecs):
 def call(self,operation,**values):
  result=super().call(operation,**values)
  if operation=='run_task':
   Path(value['state']).write_text(json.dumps({'task':self.task,'definition':self.definition}))
   os._exit(17)
  return result
class Remote(Objects):
 def put(self,*args):
  result=super().put(*args);Path(value['remote']).write_bytes(args[2]);return result
auth=EnterpriseAuthStore(lambda:psycopg.connect(value['database']),value['key'].encode(),company_domain=value['domain'])
runner=EcsDocuments(config(),api=Crash(AwsDocumentTaskContract.model),objects=Remote(),host_check=verified_hosts)
runner.attach_runtime(auth,value['account']);runner.from_source(b'OWNED SYNTHETIC INPUT','text/plain',lambda:None)
"""
            private={'runtime':str(Path(sys.modules['enterprise_aws_jobs'].__file__).parent),'tests':str(Path(__file__).parent),
                     'database':self.database['worker'],'key':self.database['key'].decode(),'domain':session_domain(self.owned),
                     'account':self.account,'remote':str(remote),'state':str(state)}
            child=subprocess.run([sys.executable,'-I','-c',code],cwd=ROOT,input=json.dumps(private).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
            self.assertEqual(child.returncode,17,child.stderr.decode());self.assertEqual(child.stdout,b'');self.assertTrue(remote.exists())
            self.assertEqual((self.rows()[0]['phase'],self.rows()[0]['state']),('job_pending','active'))
            saved=json.loads(state.read_text());self.api.task=saved['task'];self.api.definition=saved['definition'];self.api.running=True
            original=self.objects.delete
            def remove(*args):remote.unlink(missing_ok=True);return original(*args)
            self.objects.delete=remove;self.due()
            self.assertEqual(self.adapter().reconcile(limit=1),{'claimed':1,'retired':0,'settling':1,'failed':0})
            self.assertFalse(remote.exists());self.assertFalse(self.api.running)
            self.assertIn('stop_task',[op for op,_ in self.api.calls]);self.assertNotIn('run_task',[op for op,_ in self.api.calls])


if __name__=='__main__':unittest.main(verbosity=2)
