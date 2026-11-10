"""Actual ASGI/auth/SQL/outbox/worker composition; explicit vendor/model fixtures."""
import asyncio
from contextlib import suppress
from pathlib import Path
import sys
import threading
import unittest
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/azure-runtime-sdk'),str(ROOT/'tests/runtime')]
import psycopg
from psycopg.conninfo import conninfo_to_dict
import enterprise_http_postgres as fixture
from enterprise_http import create_app
from enterprise_queries import producer_queries,initialize_query_store,grant_query_runtime
from enterprise_query_service import EnterpriseAnswers,EnterpriseQueryWorker
from enterprise_sources import SourceUnavailable


class QueuedHttp(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixture.CompanyHttpIntegration.setUpClass()
        parent=fixture.CompanyHttpIntegration
        with psycopg.connect(parent.owner_dsn)as conn:
            initialize_query_store(conn);grant_query_runtime(conn,conninfo_to_dict(parent.app_dsn)['user'],worker=True)

    async def asyncSetUp(self):
        self.f=fixture.CompanyHttpIntegration();await self.f.asyncSetUp()
        self.store=producer_queries(self.f.store,self.f.app_dsn,self.f.account)
        self.answers=EnterpriseAnswers(self.store,self.f.connections,self.f.engine_factory)
        self.f.app=create_app(self.f.identity,self.f.sessions,self.f.connections,self.f.engine_factory,public_origin=fixture.ORIGIN,answers=self.answers)
        await self.f.client.aclose();self.f.client=self.f.new_client();self.f.clients=[self.f.client]
        await self.f.login();await self.f.connect_all()

    async def asyncTearDown(self):await self.f.asyncTearDown()
    async def submit(self,request=None):
        response=await self.f.client.post('/api/queries',json={'question':'What does our retention policy require?','requestId':request or str(uuid.uuid4())},headers=self.f.headers())
        self.assertEqual(response.status_code,202,response.text);return response.json()['id']
    async def status(self,identity,client=None):return await(client or self.f.client).get('/api/queries/'+identity,headers={'X-Workspace-Request':'session'})
    def browser(self):return self.f.sessions.authenticate(self.f.client.cookies.get(fixture.COOKIE))

    async def test_submit_returns_before_model_and_real_queue_worker_completes(self):
        identity=await self.submit();self.assertEqual(self.f.model_calls,[])
        self.assertEqual((await self.status(identity)).json()['status'],'queued')
        worker=EnterpriseQueryWorker(self.f.app_dsn,self.answers)
        await worker.run(wait=False,concurrency=1,install_signal_handlers=False,listen_notify=False,fetch_job_polling_interval=.01)
        response=await self.status(identity);self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['status'],'ready');self.assertIn('ninety days',response.json()['result']['answer'])
        self.assertEqual(len(self.f.model_calls),1)
        with psycopg.connect(self.f.owner_dsn)as conn:
            self.assertEqual(conn.execute("SELECT status::text FROM enterprise_queries.procrastinate_jobs WHERE args->>'query_id'=%s",(identity,)).fetchone()[0],'succeeded')

    async def test_http_idempotency_and_caller_fields_cannot_select_authority(self):
        request=str(uuid.uuid4());identity=await self.submit(request);self.assertEqual(await self.submit(request),identity)
        response=await self.f.client.post('/api/queries',json={'question':'different','requestId':request},headers=self.f.headers());self.assertEqual(response.status_code,409)
        response=await self.f.client.post('/api/queries',json={'question':'policy','requestId':str(uuid.uuid4()),'accountId':'other'},headers=self.f.headers());self.assertEqual(response.status_code,400)
        response=await self.f.client.post('/api/queries',json={'question':'policy','requestId':str(uuid.uuid4())},headers={'Origin':fixture.ORIGIN});self.assertEqual(response.status_code,403)

    async def test_signed_out_or_other_browser_cannot_read_or_cancel(self):
        identity=await self.submit();other=self.f.new_client();self.f.clients.append(other)
        self.assertEqual((await self.status(identity,other)).status_code,401)
        await self.f.login(other,'bob')
        response=await self.status(identity,other);self.assertEqual(response.status_code,404)
        self.assertNotIn('retention',response.text)

    async def test_cancel_before_work_prevents_model_generation(self):
        identity=await self.submit()
        response=await self.f.client.delete('/api/queries/'+identity,headers=self.f.headers());self.assertEqual(response.status_code,204)
        await asyncio.to_thread(self.answers.execute,identity)
        self.assertEqual(self.f.model_calls,[]);self.assertEqual((await self.status(identity)).json()['status'],'cancelled')

    async def test_current_edit_requeues_and_automatically_generates_fresh_answer(self):
        identity=await self.submit();await asyncio.to_thread(self.answers.execute,identity)
        self.f.source_version='v2';response=await self.status(identity)
        self.assertEqual(response.json(),{'id':identity,'status':'queued'})
        await asyncio.to_thread(self.answers.execute,identity)
        response=await self.status(identity);self.assertEqual(response.json()['status'],'ready');self.assertEqual(len(self.f.model_calls),2)

    async def test_membership_revoked_after_generation_never_releases_saved_answer(self):
        identity=await self.submit();await asyncio.to_thread(self.answers.execute,identity)
        with psycopg.connect(self.f.owner_dsn)as conn:conn.execute('UPDATE enterprise_auth.memberships SET active=false WHERE account_id=%s AND principal_key=%s',(self.f.account,self.f.principal.key))
        response=await self.status(identity);self.assertEqual(response.status_code,403);self.assertNotIn('ninety',response.text)

    async def test_cancellation_during_release_fences_late_answer(self):
        identity=await self.submit();await asyncio.to_thread(self.answers.execute,identity)
        entered=threading.Event();release=threading.Event();original=self.answers.make_engine
        def factory(*args):
            engine=original(*args);verify=engine.release
            def delayed(*a):entered.set();release.wait(5);return verify(*a)
            engine.release=delayed;return engine
        self.answers.make_engine=factory
        pending=asyncio.create_task(self.status(identity))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait,3))
            await self.f.client.delete('/api/queries/'+identity,headers=self.f.headers())
        finally:release.set()
        response=await pending;self.assertNotIn('ninety',response.text);self.assertEqual(response.json()['status'],'cancelled')

    async def test_heartbeat_renews_during_long_model_work(self):
        self.store.lease_seconds=15
        identity=await self.submit();entered=threading.Event();release=threading.Event();original=self.answers.make_engine
        def factory(*args):
            engine=original(*args);generate=engine.generate
            def delayed(*a):entered.set();release.wait(12);return generate(*a)
            engine.generate=delayed;return engine
        self.answers.make_engine=factory
        pending=asyncio.create_task(asyncio.to_thread(self.answers.execute,identity))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait,3));await asyncio.sleep(5.5)
            with psycopg.connect(self.f.owner_dsn)as conn:
                remaining=conn.execute('SELECT extract(epoch FROM lease_until-clock_timestamp())FROM enterprise_queries.requests WHERE id=%s',(identity,)).fetchone()[0]
                self.assertGreater(remaining,10)
        finally:release.set();await pending
        self.assertEqual((await self.status(identity)).json()['status'],'ready')

    async def test_real_worker_retries_a_temporary_failure_with_a_fresh_attempt(self):
        identity=await self.submit();original=self.answers.make_engine;calls=[]
        def factory(*args):
            calls.append(True)
            if len(calls)==1:raise SourceUnavailable('source_request_failed')
            return original(*args)
        self.answers.make_engine=factory;worker=EnterpriseQueryWorker(self.f.app_dsn,self.answers)
        pending=asyncio.create_task(worker.run(concurrency=1,install_signal_handlers=False,listen_notify=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=1))
        try:
            deadline=asyncio.get_running_loop().time()+12
            while True:
                row=await asyncio.to_thread(self.store.get,self.browser(),identity)
                if row['state']=='ready':break
                if asyncio.get_running_loop().time()>deadline:self.fail('Native queue retry did not complete')
                await asyncio.sleep(.1)
            self.assertEqual(row['attempt'],2);self.assertEqual(len(self.f.model_calls),1)
            self.assertEqual((await self.status(identity)).json()['status'],'ready')
        finally:
            pending.cancel()
            with suppress(asyncio.CancelledError):await pending

    async def test_ready_answer_is_not_an_outage_fallback(self):
        identity=await self.submit();await asyncio.to_thread(self.answers.execute,identity);original=self.answers.make_engine
        def outage(*args):raise SourceUnavailable('source_request_failed')
        self.answers.make_engine=outage
        response=await self.status(identity);self.assertEqual(response.status_code,503);self.assertNotIn('ninety',response.text)
        self.answers.make_engine=original
        response=await self.status(identity);self.assertEqual(response.json()['status'],'ready');self.assertEqual(len(self.f.model_calls),1)


if __name__=='__main__':unittest.main(verbosity=2)
