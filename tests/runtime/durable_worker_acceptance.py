"""Actual Procrastinate worker execution against the owned PostgreSQL fixture.

Processors/destinations are explicit synthetic callbacks here. Native cloud/model,
PDF and HTTP destination adapters are separate integration acceptance work.
"""
import asyncio
from pathlib import Path
import sys
import time
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from durable_workflow import Principal
from durable_fixture_tasks import FIXTURE_CONTRACT
from workflow_worker import WorkflowRuntime,TemporaryWork,ExternalOutcomeUnknown
from durable_postgres_acceptance import fixture_dsn

class DurableWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.dsn=fixture_dsn();self.account=str(uuid.uuid4());self.user=Principal(self.account,'worker-fixture-staff');self.reviewer=Principal(self.account,'worker-fixture-reviewer');self.tasks=[]
    async def start(self,processor,deliver,*,idempotent=False):
        runtime=WorkflowRuntime(self.dsn,processor,deliver,destination_contract=FIXTURE_CONTRACT,idempotent_destination=idempotent,namespace='q'+uuid.uuid4().hex[:12],retry_wait=0,lease_seconds=10)
        with runtime.store.connect()as conn:
            conn.execute('INSERT INTO workflow.accounts(id) VALUES(%s)',(self.account,))
            for actor,roles in [(self.user,['user']),(self.reviewer,['reviewer'])]:conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)',(actor.account_id,actor.subject,roles))
        task=asyncio.create_task(runtime.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=2));self.tasks.append(task);return runtime,task
    async def asyncTearDown(self):
        for task in self.tasks:task.cancel()
        for task in self.tasks:
            try:await task
            except asyncio.CancelledError:pass
    async def until_state(self,runtime,operation,state,*,timeout=10):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            for task in self.tasks:
                if task.done()and not task.cancelled():task.result()
            row=await asyncio.to_thread(runtime.store.get,self.user,operation)
            if row['state']==state:return row
            await asyncio.sleep(.03)
        raise AssertionError('Workflow did not reach '+state+'; last state '+row['state'])
    async def test_real_worker_stops_for_human_approval_then_dispatches_once(self):
        processed=[];delivered=[]
        def processor(row):processed.append(str(row['id']));return {'supplier':'Synthetic supplier','invoice_date':'2026-11-10','total':'42.50','currency':'AUD'}
        def deliver(row,**identity):delivered.append(identity);return {'externalId':'synthetic-accepted'}
        runtime,_=await self.start(processor,deliver);operation=await asyncio.to_thread(runtime.store.submit,self.user,'document','native-worker-document',{'sha256':'a'*64})
        await self.until_state(runtime,operation,'review');self.assertEqual(processed,[operation]);self.assertEqual(delivered,[])
        await asyncio.to_thread(runtime.store.approve,self.reviewer,operation,1);row=await self.until_state(runtime,operation,'sent');self.assertEqual(len(delivered),1);self.assertEqual(delivered[0]['idempotency_key'],operation);self.assertEqual(delivered[0]['payload_sha256'],row['approved_hash'])
        events=await asyncio.to_thread(runtime.store.events,self.user,operation);self.assertEqual([e['event']for e in events],['submitted','claimed','result_ready','approved','dispatch_claimed','sent'])
    async def test_native_bounded_retry_recovers_a_temporary_processor_failure(self):
        attempts=[]
        def processor(row):
            attempts.append(str(row['id']))
            if len(attempts)==1:raise TemporaryWork('PRIVATE_PROCESSOR_PAYLOAD_MUST_NOT_ESCAPE')
            return {'supplier':'Recovered result'}
        runtime,_=await self.start(processor,lambda row,**identity:{'externalId':'unused'});operation=await asyncio.to_thread(runtime.store.submit,self.user,'document','temporary',{})
        await self.until_state(runtime,operation,'review');self.assertEqual(attempts,[operation,operation]);events=await asyncio.to_thread(runtime.store.events,self.user,operation);self.assertIn('retry_pending',[e['event']for e in events]);self.assertNotIn('PRIVATE_PROCESSOR_PAYLOAD_MUST_NOT_ESCAPE',str(events))
    async def test_real_worker_does_not_retry_an_uncertain_nonidempotent_external_action(self):
        deliveries=[]
        def deliver(row,**identity):deliveries.append(identity);raise ExternalOutcomeUnknown('Synthetic lost acknowledgement')
        runtime,_=await self.start(lambda row:{'supplier':'Synthetic'},deliver);operation=await asyncio.to_thread(runtime.store.submit,self.user,'document','uncertain',{})
        await self.until_state(runtime,operation,'review');await asyncio.to_thread(runtime.store.approve,self.reviewer,operation,1);await self.until_state(runtime,operation,'unknown');await asyncio.sleep(.2);self.assertEqual(len(deliveries),1)
    async def test_verified_idempotent_destination_reuses_the_same_key_after_lost_ack(self):
        calls=[];accepted={}
        def deliver(row,**identity):
            calls.append(identity)
            accepted.setdefault(identity['idempotency_key'],identity['payload_sha256'])
            self.assertEqual(accepted[identity['idempotency_key']],identity['payload_sha256'])
            if len(calls)==1:raise ExternalOutcomeUnknown('Synthetic accepted but acknowledgement lost')
            return {'externalId':'same-synthetic-action'}
        runtime,_=await self.start(lambda row:{'supplier':'Synthetic'},deliver,idempotent=True);operation=await asyncio.to_thread(runtime.store.submit,self.user,'document','idempotent',{})
        await self.until_state(runtime,operation,'review');await asyncio.to_thread(runtime.store.approve,self.reviewer,operation,1);await self.until_state(runtime,operation,'sent');self.assertEqual(len(calls),2);self.assertEqual(len(accepted),1);self.assertEqual(calls[0],calls[1])

if __name__=='__main__':unittest.main(verbosity=2)
