"""Typed ASGI intake, real local SQL/queue and synthetic TLS destination.

Identity and business processors are fixtures. No cloud, browser, managed
database, domain implementation or deployment is qualified by these checks.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
import unittest
import uuid
import httpx
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from durable_workflow import WorkflowStore,Principal
from durable_postgres_acceptance import DurableFixture,fixture_dsn
from durable_fixture_tasks import FIXTURE_CONTRACT
from workflow_payload_acceptance import definition
RUNTIME=Path(__import__('workflow_payload').__file__).resolve().parent
sys.path.insert(0,str(RUNTIME))
from workflow_payload import PayloadContract
from workflow_http import create_app
from workflow_worker import WorkflowRuntime,producer_store
from approved_http_destination import ApprovedHttpDestination
from workflow_tls_destination_fixture import TlsDestinationFixture

ORIGIN='https://application.example'
SOURCE={'itemId':'microscope','memberId':'member-1'}
RESULT={'loanDays':7,'inspectionRequired':True}


class WorkflowHttpTests(DurableFixture,unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.store=WorkflowStore(self.dsn,self.extract,self.dispatch,destination_contract=FIXTURE_CONTRACT,payload_contract=PayloadContract(definition()))
        def verify(token):
            if token not in {'staff','reviewer','supervisor','outsider'}:raise ValueError('PRIVATE_IDENTITY_DETAIL')
            return token
        self.verify=verify
        self.app=create_app(verify,self.store,account_id=self.account,public_origin=ORIGIN)
        self.client=TestClient(self.app,base_url=ORIGIN);self.addCleanup(self.client.close)
        self.headers={'Authorization':'Bearer staff','Origin':ORIGIN,'Idempotency-Key':'stable'}
    def post(self,path='/api/operations',value=None,headers=None):
        return self.client.post(path,json=value if value is not None else {'source':SOURCE},headers=headers or self.headers)
    def pending(self):
        response=self.post();self.assertEqual(response.status_code,202,response.text)
        return response.json()['operation']['id']
    def reviewed(self):
        operation=self.pending();row=self.store.claim_extract(operation)
        self.store.record_result(operation,str(row['lease_token']),RESULT)
        return operation
    def test_selected_runtime_modules_are_used(self):
        for name in ['workflow_http','workflow_worker','durable_workflow','workflow_payload']:
            self.assertEqual(Path(sys.modules[name].__file__).resolve().parent,RUNTIME)
    def test_enqueue_reply_replay_list_and_exact_source_conflict(self):
        operation=self.pending();again=self.post()
        self.assertEqual(again.status_code,202);self.assertEqual(again.json()['operation']['id'],operation)
        self.assertEqual(self.queue_count(self.extract,operation),1)
        self.assertEqual(again.json()['operation']['state'],'pending')
        self.assertEqual(set(again.json()['operation']),{'id','state','revision','result','receipt','createdAt','updatedAt'})
        listing=self.client.get('/api/operations',headers=self.headers)
        self.assertEqual(listing.json()['operations'][0]['id'],operation)
        self.assertEqual(self.post(value={'source':{**SOURCE,'itemId':'changed'}}).status_code,409)
        self.assertEqual(self.store.get(self.user,operation)['source_ref'],SOURCE)
    def test_concurrent_http_duplicates_insert_one_operation_and_job(self):
        with ThreadPoolExecutor(max_workers=8)as executor:
            responses=list(executor.map(lambda _:self.post(),range(20)))
        self.assertTrue(all(r.status_code==202 for r in responses))
        ids={r.json()['operation']['id']for r in responses};self.assertEqual(len(ids),1)
        operation=ids.pop();self.assertEqual(self.queue_count(self.extract,operation),1)
        self.assertEqual([e['event']for e in self.store.events(self.user,operation)],['submitted'])
    def test_client_cannot_override_tenant_kind_contract_or_roles(self):
        for field,value in [('accountId',self.other),('kind','account_change'),('roles',['owner']),('destination',{}),('payloadContract',{})]:
            with self.subTest(field=field):self.assertEqual(self.post(value={'source':SOURCE,field:value}).status_code,400)
        response=self.post(value={'source':{**SOURCE,'role':'owner'}});self.assertEqual(response.status_code,400)
        self.assertEqual(self.store.list(self.user),[])
    def test_duplicate_nested_json_nonfinite_and_noninteger_revision_are_rejected(self):
        for raw in [b'{"source":{"itemId":"a","itemId":"b","memberId":"x"}}',b'{"source":{},"source":{}}',b'{"source":{"itemId":NaN,"memberId":"x"}}']:
            response=self.client.post('/api/operations',content=raw,headers={**self.headers,'Content-Type':'application/json'})
            self.assertEqual(response.status_code,400)
        operation=self.reviewed()
        for revision in [True,'1',1.0]:
            response=self.post('/api/operations/'+operation+'/approve',{'revision':revision},headers={**self.headers,'Authorization':'Bearer reviewer'})
            self.assertEqual(response.status_code,400)
        self.assertEqual(self.queue_count(self.dispatch,operation),0)
    def test_missing_wrong_or_duplicated_origin_or_authorization_is_denied(self):
        for headers in [{k:v for k,v in self.headers.items()if k!='Origin'},{**self.headers,'Origin':'https://foreign.example'},
                        {**self.headers,'Authorization':'Bearer owner'},{k:v for k,v in self.headers.items()if k!='Authorization'}]:
            self.assertEqual(self.post(headers=headers).status_code,403)
        duplicated=[('Origin',ORIGIN),('Origin',ORIGIN),('Authorization','Bearer staff'),('Idempotency-Key','stable')]
        self.assertEqual(self.client.post('/api/operations',json={'source':SOURCE},headers=duplicated).status_code,403)
        duplicated=[('Origin',ORIGIN),('Authorization','Bearer staff'),('Authorization','Bearer reviewer'),('Idempotency-Key','stable')]
        self.assertEqual(self.client.post('/api/operations',json={'source':SOURCE},headers=duplicated).status_code,403)
        self.assertEqual(self.store.list(self.user),[])
    def test_body_limits_content_type_and_missing_key_fail_without_persistence(self):
        self.assertEqual(self.client.post('/api/operations',content=b'x'*66001,headers={**self.headers,'Content-Type':'application/json'}).status_code,413)
        self.assertEqual(self.client.post('/api/operations',content=b'{}',headers=self.headers).status_code,415)
        self.assertEqual(self.post(headers={k:v for k,v in self.headers.items()if k!='Idempotency-Key'}).status_code,400)
        self.assertEqual(self.post(headers={**self.headers,'Idempotency-Key':'a'*201}).status_code,400)
        self.assertEqual(self.store.list(self.user),[])
    def test_reviewer_edit_requires_current_revision_and_live_membership(self):
        operation=self.reviewed();path='/api/operations/'+operation+'/review'
        self.assertEqual(self.post(path,{'revision':1,'result':RESULT}).status_code,403)
        headers={**self.headers,'Authorization':'Bearer reviewer'}
        self.assertEqual(self.post(path,{'revision':1,'result':{**RESULT,'loanDays':31}},headers=headers).status_code,400)
        changed={**RESULT,'loanDays':10}
        self.assertEqual(self.post(path,{'revision':1,'result':changed},headers=headers).json()['operation']['revision'],2)
        self.assertEqual(self.post(path,{'revision':1,'result':changed},headers=headers).status_code,409)
        self.assertEqual(self.post('/api/operations/'+operation+'/approve',{'revision':1},headers=headers).status_code,409)
        with self.store.connect()as conn:conn.execute('UPDATE workflow.memberships SET active=false WHERE account_id=%s AND subject=%s',(self.account,'reviewer'))
        self.assertEqual(self.post('/api/operations/'+operation+'/approve',{'revision':2},headers=headers).status_code,403)
        self.assertEqual(self.queue_count(self.dispatch,operation),0)
    def test_foreign_operation_ids_queries_and_tokens_do_not_cross_accounts(self):
        operation=self.store.submit(self.outsider,'draft','foreign',SOURCE)
        self.assertEqual(self.client.get('/api/operations/'+operation,headers=self.headers).status_code,404)
        self.assertEqual(self.post('/api/operations/'+operation+'/approve',{'revision':1},headers={**self.headers,'Authorization':'Bearer reviewer'}).status_code,404)
        self.assertEqual(self.client.get('/api/operations',headers={**self.headers,'Authorization':'Bearer outsider'}).status_code,403)
        for path in ['/api/session?accountId=other','/api/operations?accountId=other','/api/operations?before=a&before=b']:
            self.assertEqual(self.client.get(path,headers=self.headers).status_code,400)
    def test_response_security_headers_and_identity_errors_do_not_expose_details(self):
        response=self.post(headers={**self.headers,'Authorization':'Bearer invalid'})
        self.assertEqual(response.json(),{'error':{'code':'access_denied'}})
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertEqual(response.headers['x-content-type-options'],'nosniff')
        self.assertNotIn('PRIVATE_IDENTITY_DETAIL',response.text)
    def test_bootstrap_requires_typed_store_fixed_origin_and_native_transport(self):
        for options in [{'public_origin':'http://public.example'},{'public_origin':ORIGIN+'/'},{'token_header':'cookie'},{'operation_kind':'execute'}]:
            with self.assertRaises(ValueError):create_app(self.verify,self.store,account_id=self.account,**{'public_origin':ORIGIN,**options})
        with self.assertRaises(ValueError):create_app(self.verify,WorkflowStore(self.dsn,self.extract,self.dispatch,destination_contract=FIXTURE_CONTRACT),account_id=self.account,public_origin=ORIGIN)
    def test_native_signed_header_is_explicit_and_does_not_fall_back_to_bearer(self):
        app=create_app(self.verify,self.store,account_id=self.account,public_origin=ORIGIN,token_header='x-goog-iap-jwt-assertion')
        with TestClient(app,base_url=ORIGIN)as client:
            self.assertEqual(client.post('/api/operations',json={'source':SOURCE},headers=self.headers).status_code,403)
            response=client.post('/api/operations',json={'source':SOURCE},headers={**self.headers,'x-goog-iap-jwt-assertion':'staff'})
            self.assertEqual(response.status_code,202)
    def test_account_change_keeps_supervisor_policy_despite_reviewer_token(self):
        app=create_app(self.verify,self.store,account_id=self.account,public_origin=ORIGIN,operation_kind='account_change')
        with TestClient(app,base_url=ORIGIN)as client:
            response=client.post('/api/operations',json={'source':SOURCE},headers=self.headers);operation=response.json()['operation']['id']
            row=self.store.claim_extract(operation);self.store.record_result(operation,str(row['lease_token']),RESULT)
            for role,status in [('reviewer',403),('supervisor',200)]:
                response=client.post('/api/operations/'+operation+'/approve',json={'revision':1},headers={**self.headers,'Authorization':'Bearer '+role})
                self.assertEqual(response.status_code,status,response.text)


class StreamBoundaryTests(DurableFixture,unittest.IsolatedAsyncioTestCase):
    async def request(self,stream):
        store=WorkflowStore(self.dsn,self.extract,self.dispatch,destination_contract=FIXTURE_CONTRACT,payload_contract=PayloadContract(definition()))
        def verify(token):
            if token!='staff':raise ValueError('Unverified identity')
            return token
        app=create_app(verify,store,account_id=self.account,public_origin=ORIGIN)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url=ORIGIN)as client:
            response=await client.post('/api/operations',content=stream,headers={'Authorization':'Bearer staff','Origin':ORIGIN,'Idempotency-Key':'stable','Content-Type':'application/json'})
        with store.connect()as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM workflow.operations WHERE account_id=%s',(self.account,)).fetchone()['n'],0)
        return response
    async def test_membership_revoked_during_stream_prevents_enqueue(self):
        raw=json.dumps({'source':SOURCE}).encode()
        async def stream():
            yield raw[:10]
            with self.store.connect()as conn:conn.execute('UPDATE workflow.memberships SET active=false WHERE account_id=%s AND subject=%s',(self.account,'staff'))
            yield raw[10:]
        self.assertEqual((await self.request(stream())).status_code,403)
    async def test_actual_body_deadline_stops_a_stalled_stream(self):
        async def stream():
            yield b'{"source":'
            await asyncio.sleep(6)
            yield b'{}}'
        started=time.monotonic();response=await self.request(stream())
        self.assertEqual(response.status_code,408,response.text)
        self.assertLess(time.monotonic()-started,5.8)


class ConnectedHttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_domains_complete_http_queue_review_and_tls_without_scope_override(self):
        dsn=fixture_dsn()
        for domain,source,result in [('equipment-reservation',SOURCE,RESULT),('editorial-publication',{'articleId':'news','revision':4},{'title':'Community news','channels':['web']})]:
            contract=PayloadContract(definition(domain));namespace='q'+uuid.uuid4().hex[:12];sink=TlsDestinationFixture()
            deliver=ApprovedHttpDestination(sink.url,lambda:sink.token,destination_scope='synthetic-http',tls_context=sink.context,allowed_kinds=('draft',),payload_contract=contract)
            runtime=WorkflowRuntime(dsn,lambda row:result,deliver,payload_contract=contract,namespace=namespace,lease_seconds=10,retry_wait=0)
            store=producer_store(dsn,destination_contract=deliver.contract,payload_contract=contract,namespace=namespace)
            account=str(uuid.uuid4())
            with store.connect()as conn:
                conn.execute('INSERT INTO workflow.accounts(id) VALUES(%s)',(account,))
                for subject,roles in [('member',['user']),('reviewer',['reviewer'])]:conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)',(account,subject,roles))
            def verify(token):
                if token not in {'member','reviewer'}:raise ValueError('Unverified identity')
                return token
            app=create_app(verify,store,account_id=account,public_origin=ORIGIN)
            task=asyncio.create_task(runtime.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=2))
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url=ORIGIN)as client:
                    headers={'Authorization':'Bearer member','Origin':ORIGIN,'Idempotency-Key':'same-operation'}
                    submitted=await client.post('/api/operations',json={'source':source},headers=headers)
                    self.assertEqual(submitted.status_code,202,submitted.text);operation=submitted.json()['operation']['id']
                    async def until(state):
                        deadline=time.monotonic()+10
                        while time.monotonic()<deadline:
                            if task.done():task.result()
                            response=await client.get('/api/operations/'+operation,headers=headers)
                            self.assertEqual(response.status_code,200,response.text)
                            row=response.json()['operation']
                            if row['state']==state:return row
                            await asyncio.sleep(.03)
                        self.fail('HTTP operation did not reach '+state)
                    reviewed=await until('review');self.assertEqual(reviewed['result'],result);self.assertEqual(sink.calls,[])
                    denied=await client.post('/api/operations/'+operation+'/approve',json={'revision':1},headers=headers);self.assertEqual(denied.status_code,403)
                    approved=await client.post('/api/operations/'+operation+'/approve',json={'revision':1},headers={**headers,'Authorization':'Bearer reviewer'});self.assertEqual(approved.status_code,200,approved.text)
                    sent=await until('sent');self.assertEqual(len(sink.effects),1);self.assertEqual(len(sink.calls),1)
                    self.assertEqual(sink.calls[0]['body']['result'],result)
                    self.assertEqual(sent['receipt']['operationId'],operation)
                    replay=await client.post('/api/operations',json={'source':source},headers=headers)
                    self.assertEqual(replay.json()['operation']['id'],operation);self.assertEqual(len(sink.calls),1)
            finally:
                task.cancel()
                try:await task
                except asyncio.CancelledError:pass
                await asyncio.to_thread(sink.close)


if __name__=='__main__':unittest.main(verbosity=2)
