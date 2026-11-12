"""Real DB credential rotation and pool reconnection, not cloud IAM emulation."""
import asyncio
from pathlib import Path
import secrets
import sys
import time
import unittest
import uuid
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict,make_conninfo

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from durable_privileges_acceptance import create_runtime_roles
from durable_workflow import Principal
from durable_fixture_tasks import FIXTURE_CONTRACT
from workflow_worker import WorkflowRuntime,producer_store

class RefreshedDatabaseCredentialTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.owner,_,self.worker_role,self.api_dsn,self.worker_dsn=create_runtime_roles();self.account=str(uuid.uuid4());self.user=Principal(self.account,'credential-staff');self.namespace='q'+uuid.uuid4().hex[:12];self.tasks=[]
        with psycopg.connect(self.owner)as conn:
            conn.execute('INSERT INTO workflow.accounts(id)VALUES(%s)',(self.account,));conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles)VALUES(%s,%s,%s)',(self.account,self.user.subject,['user']))
    async def asyncTearDown(self):
        for task in self.tasks:task.cancel()
        for task in self.tasks:
            try:await task
            except asyncio.CancelledError:pass
    async def test_each_domain_connection_obtains_a_fresh_credential_and_does_not_reuse_a_revoked_password(self):
        values={'dsn':self.api_dsn,'calls':0}
        def credential():values['calls']+=1;return values['dsn']
        api=producer_store(credential,destination_contract=FIXTURE_CONTRACT,namespace=self.namespace)
        operation=api.submit(self.user,'document','first',{});before=values['calls'];role=conninfo_to_dict(self.api_dsn)['user'];password=secrets.token_urlsafe(32)
        with psycopg.connect(self.owner)as conn:conn.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
        values['dsn']=make_conninfo(**{**conninfo_to_dict(self.api_dsn),'password':password})
        self.assertEqual(api.get(self.user,operation)['state'],'pending');self.assertGreater(values['calls'],before)
        with self.assertRaises(psycopg.OperationalError):
            with psycopg.connect(self.api_dsn):pass
    async def test_native_async_queue_pool_and_domain_claims_reconnect_with_rotated_worker_credentials(self):
        values={'dsn':self.worker_dsn,'calls':0};processed=[]
        def credential():values['calls']+=1;return values['dsn']
        def processor(row):processed.append(str(row['id']));return{'supplier':'Credential refresh fixture'}
        runtime=WorkflowRuntime(credential,processor,lambda row,**kwargs:{'externalId':'unused'},destination_contract=FIXTURE_CONTRACT,namespace=self.namespace)
        api=producer_store(self.api_dsn,destination_contract=FIXTURE_CONTRACT,namespace=self.namespace)
        task=asyncio.create_task(runtime.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=2));self.tasks.append(task)
        async def wait(operation):
            end=time.monotonic()+15
            while time.monotonic()<end:
                if task.done():task.result();raise AssertionError('Worker exited during credential refresh')
                row=await asyncio.to_thread(api.get,self.user,operation)
                if row['state']=='review':return
                await asyncio.sleep(.03)
            raise AssertionError('Credential-refresh job did not finish')
        first=await asyncio.to_thread(api.submit,self.user,'document','before-rotation',{});await wait(first);before=values['calls'];password=secrets.token_urlsafe(32)
        with psycopg.connect(self.owner)as conn:
            conn.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(sql.Identifier(self.worker_role),sql.Literal(password)))
            values['dsn']=make_conninfo(**{**conninfo_to_dict(self.worker_dsn),'password':password})
            # Terminate only this fresh fixture role's idle native sessions. Other
            # tests, users and the owned administrator are outside this predicate.
            conn.execute('SELECT pg_terminate_backend(pid)FROM pg_stat_activity WHERE usename=%s AND datname=current_database()AND pid<>pg_backend_pid()',(self.worker_role,))
        second=await asyncio.to_thread(api.submit,self.user,'document','after-rotation',{});await wait(second)
        self.assertGreater(values['calls'],before);self.assertEqual(processed,[first,second])

if __name__=='__main__':unittest.main(verbosity=2)
