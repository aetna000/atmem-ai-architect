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
from workflow_worker import WorkflowRuntime,producer_store,_transient_database_error

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
    async def test_worker_supervisor_reopens_native_pool_after_interrupted_queue_transaction(self):
        from unittest.mock import patch
        processed=[];runtime=WorkflowRuntime(self.worker_dsn,lambda row:processed.append(str(row['id']))or{'supplier':'After queue reconnect'},lambda row,**kwargs:{'externalId':'unused'},destination_contract=FIXTURE_CONTRACT,namespace=self.namespace)
        api=producer_store(self.api_dsn,destination_contract=FIXTURE_CONTRACT,namespace=self.namespace)
        original=runtime.app.run_worker_async;calls=[]
        async def interrupted(*args,**kwargs):
            calls.append(True)
            if len(calls)==1:
                # Use a real SQL transaction whose own backend is terminated.
                # The queue supervisor must close this pool before reopening it.
                async with runtime.app.connector.pool.connection()as conn:
                    await conn.execute('SELECT pg_terminate_backend(pg_backend_pid())')
            return await original(*args,**kwargs)
        with patch.object(runtime.app,'run_worker_async',side_effect=interrupted),self.assertLogs('workflow_worker',level='WARNING')as logs:
            task=asyncio.create_task(runtime.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=2));self.tasks.append(task)
            operation=await asyncio.to_thread(api.submit,self.user,'document','queue-supervisor',{})
            deadline=time.monotonic()+12
            while time.monotonic()<deadline:
                if task.done():task.result();raise AssertionError('Worker stopped before recovery')
                if(await asyncio.to_thread(api.get,self.user,operation))['state']=='review':break
                await asyncio.sleep(.03)
            else:raise AssertionError('Worker did not reconnect')
            self.assertEqual(processed,[operation]);self.assertGreaterEqual(len(calls),2);self.assertEqual(len(logs.records),1);self.assertNotIn('pg_terminate_backend',logs.output[0]);task.cancel()
            try:await task
            except asyncio.CancelledError:pass

    async def test_worker_recovers_when_workload_credential_refresh_is_temporarily_unavailable(self):
        from unittest.mock import patch
        from workflow_connection import DatabaseCredentialUnavailable
        processed=[];runtime=WorkflowRuntime(self.worker_dsn,lambda row:processed.append(str(row['id']))or{'supplier':'After identity refresh'},lambda row,**kwargs:{'externalId':'unused'},destination_contract=FIXTURE_CONTRACT,namespace=self.namespace)
        original=runtime.recover_once;calls=[]
        async def interrupted():
            calls.append(True)
            if len(calls)==1:raise DatabaseCredentialUnavailable('PRIVATE_IDENTITY_DETAIL')
            return await original()
        api=producer_store(self.api_dsn,destination_contract=FIXTURE_CONTRACT,namespace=self.namespace)
        with patch.object(runtime,'recover_once',side_effect=interrupted),self.assertLogs('workflow_worker',level='WARNING')as logs:
            task=asyncio.create_task(runtime.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=2));self.tasks.append(task)
            # Wait for the interrupted recovery cycle before submitting work.
            deadline=time.monotonic()+12
            while len(calls)<2:
                if task.done():task.result();raise AssertionError('Worker stopped during credential refresh')
                if time.monotonic()>deadline:raise AssertionError('Worker did not retry identity refresh')
                await asyncio.sleep(.03)
            operation=await asyncio.to_thread(api.submit,self.user,'document','identity-supervisor',{})
            while time.monotonic()<deadline:
                if task.done():task.result();raise AssertionError('Worker stopped before processing')
                if(await asyncio.to_thread(api.get,self.user,operation))['state']=='review':break
                await asyncio.sleep(.03)
            else:raise AssertionError('Work did not complete after identity refresh')
            self.assertEqual(processed,[operation]);self.assertNotIn('PRIVATE_IDENTITY_DETAIL',str(logs.output));task.cancel()
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

class DatabaseReconnectClassificationTests(unittest.TestCase):
    def test_only_native_connection_failures_and_uniform_wrapped_groups_are_recoverable(self):
        from workflow_connection import DatabaseCredentialUnavailable
        self.assertTrue(_transient_database_error(DatabaseCredentialUnavailable('PRIVATE_IDENTITY_DETAIL')))
        self.assertTrue(_transient_database_error(psycopg.OperationalError('PRIVATE_TRANSPORT_DETAIL')))
        self.assertTrue(_transient_database_error(psycopg.errors.AdminShutdown('closed')))
        for error in [ValueError('bug'),psycopg.errors.InsufficientPrivilege('denied'),psycopg.errors.UndefinedTable('migration'),ExceptionGroup('mixed',[psycopg.OperationalError('closed'),ValueError('bug')])]:self.assertFalse(_transient_database_error(error))
        try:
            try:raise psycopg.OperationalError('PRIVATE_TRANSPORT_DETAIL')
            except psycopg.OperationalError as cause:raise RuntimeError('connector wrapper')from cause
        except RuntimeError as error:self.assertTrue(_transient_database_error(ExceptionGroup('tasks',[error])))
