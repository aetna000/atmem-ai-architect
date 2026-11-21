"""Real SIGKILL/replacement and TLS action recovery with explicit fixture aging.

Only the killed worker's PostgreSQL heartbeat/lease are aged after SIGKILL to avoid
waiting production recovery intervals. This is not a measured production RTO.
"""
import asyncio
import json
import os
from pathlib import Path
import signal
import ssl
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from durable_postgres_acceptance import fixture_dsn
from durable_workflow import Principal
from workflow_worker import WorkflowRuntime
from approved_http_destination import ApprovedHttpDestination
from workflow_tls_destination_fixture import TlsDestinationFixture

class DurableCrashTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder=tempfile.TemporaryDirectory(prefix='durable-worker-',dir=ROOT/'.local');self.root=Path(self.folder.name);self.sink=TlsDestinationFixture();self.children=[];self.tasks=[]
        self.account=str(uuid.uuid4());self.namespace='q'+uuid.uuid4().hex[:12];self.user=Principal(self.account,'crash-staff');self.reviewer=Principal(self.account,'crash-reviewer')
    async def prepare(self,*,idempotent):
        destination=ApprovedHttpDestination(self.sink.url,lambda:self.sink.token,destination_scope='synthetic-account',idempotency_verified=idempotent,tls_context=self.sink.context)
        self.runtime=WorkflowRuntime(fixture_dsn(),lambda row:{'supplier':'Replacement worker'},destination,idempotent_destination=idempotent,namespace=self.namespace,lease_seconds=10,retry_wait=0)
        with self.runtime.store.connect()as conn:
            conn.execute('INSERT INTO workflow.accounts(id) VALUES(%s)',(self.account,))
            for actor,roles in [(self.user,['user']),(self.reviewer,['reviewer'])]:conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)',(actor.account_id,actor.subject,roles))
        return await asyncio.to_thread(self.runtime.store.submit,self.user,'document','crash-document',{'sha256':'a'*64})
    def child(self,mode,*,idempotent):
        marker=self.root/'held.json';config=self.root/'child.json';config.write_text(json.dumps({'mode':mode,'marker':str(marker),'namespace':self.namespace,'destination':self.sink.url,'caFile':str(self.sink.ca_file),'idempotent':idempotent}));config.chmod(0o600)
        child_env={'PATH':os.getenv('PATH',''),'HOME':str(self.root),'PYTHONDONTWRITEBYTECODE':'1','ATMEM_WORKFLOW_TEST_CONFIG':os.environ.get('ATMEM_WORKFLOW_TEST_CONFIG',str(ROOT/'.local/durable-postgres/fixture.json'))}
        log=(self.root/'child.log').open('ab');process=subprocess.Popen([sys.executable,'-I',str(ROOT/'tests/runtime/durable_worker_process.py'),str(config)],cwd=ROOT,env=child_env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);log.close();self.children.append(process);return process,marker
    async def until(self,predicate,description):
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            for task in self.tasks:
                if task.done()and not task.cancelled():task.result()
            if await asyncio.to_thread(predicate):return
            await asyncio.sleep(.03)
        raise AssertionError(description)
    def kill_and_age(self,process,operation):
        os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
        with self.runtime.store.connect()as conn:
            rows=conn.execute("SELECT worker_id FROM workflow.procrastinate_jobs WHERE args->>'operation_id'=%s AND status='doing'",(operation,)).fetchall();self.assertTrue(rows)
            for row in rows:conn.execute("UPDATE workflow.procrastinate_workers SET last_heartbeat=clock_timestamp()-interval '120 seconds' WHERE id=%s",(row['worker_id'],))
            conn.execute("UPDATE workflow.operations SET lease_until=clock_timestamp()-interval '1 second' WHERE id=%s AND account_id=%s",(operation,self.account))
    def start_replacement(self):
        self.tasks.append(asyncio.create_task(self.runtime.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=2,recovery_interval=5)))
    async def asyncTearDown(self):
        for process in self.children:
            if process.poll()is None:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
        for task in self.tasks:task.cancel()
        for task in self.tasks:
            try:await task
            except asyncio.CancelledError:pass
        self.sink.close();self.folder.cleanup()
    async def test_killed_extractor_is_replaced_without_duplicate_result_or_business_record(self):
        operation=await self.prepare(idempotent=True);process,marker=self.child('hold-extract',idempotent=True)
        await self.until(marker.exists,'Extractor never reached the held stage');await asyncio.to_thread(self.kill_and_age,process,operation);self.start_replacement()
        await self.until(lambda:self.runtime.store.get(self.user,operation)['state']=='review','Replacement did not recover the killed extraction')
        events=self.runtime.store.events(self.user,operation);self.assertEqual(sum(e['event']=='result_ready'for e in events),1);self.assertEqual(self.sink.effects,{})
    async def dispatch_crash(self,*,idempotent):
        operation=await self.prepare(idempotent=idempotent);process,marker=self.child('hold-dispatch',idempotent=idempotent)
        await self.until(lambda:self.runtime.store.get(self.user,operation)['state']=='review','Process did not produce a review result');await asyncio.to_thread(self.runtime.store.approve,self.reviewer,operation,1)
        await self.until(marker.exists,'Destination was not accepted before the held receipt commit');self.assertEqual(len(self.sink.effects),1);await asyncio.to_thread(self.kill_and_age,process,operation);self.start_replacement();return operation
    async def test_kill_after_real_tls_acceptance_replays_one_durable_operation_identity(self):
        operation=await self.dispatch_crash(idempotent=True)
        await self.until(lambda:self.runtime.store.get(self.user,operation)['state']=='sent','Accepted action did not reconcile after worker replacement')
        self.assertEqual(len(self.sink.effects),1);self.assertEqual(len(self.sink.calls),2);self.assertEqual(self.sink.calls[0],self.sink.calls[1]);self.assertEqual(self.runtime.store.get(self.user,operation)['receipt']['operationId'],operation)
    async def test_kill_after_acceptance_without_verified_contract_requires_reconciliation(self):
        operation=await self.dispatch_crash(idempotent=False)
        await self.until(lambda:self.runtime.store.get(self.user,operation)['state']=='unknown','An uncertain unverified action was not held for reconciliation');await asyncio.sleep(.2);self.assertEqual(len(self.sink.calls),1);self.assertEqual(len(self.sink.effects),1)

if __name__=='__main__':unittest.main(verbosity=2)
