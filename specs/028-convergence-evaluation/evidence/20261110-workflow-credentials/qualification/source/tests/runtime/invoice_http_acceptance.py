"""Real PostgreSQL + ASGI upload/review boundary; identity/storage are fixtures."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import threading
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent),str(ROOT/'.local/azure-runtime-sdk')]
import httpx
import psycopg
from durable_postgres_acceptance import DurableFixture
from durable_workflow import Denied,Principal
from durable_fixture_tasks import FIXTURE_CONTRACT
from durable_privileges_acceptance import create_runtime_roles
from workflow_worker import producer_store,WorkflowRuntime
from invoice_http import create_app
from invoice_object_store import object_key

class OwnedObjectsFixture:
    def __init__(self):self.rows={};self.lock=threading.Lock();self.puts=0;self.on_read=None
    def put(self,account_id,raw):
        digest=hashlib.sha256(raw).hexdigest();key=object_key(account_id,digest)
        with self.lock:self.rows.setdefault(key,raw);self.puts+=1
        return {'provider':'explicit-local-fixture','region':'loopback','bucket':'synthetic-private','key':key,'version':'fixture-version-1','sha256':digest}
    def load(self,account_id,ref):
        if ref['key']!=object_key(account_id,ref['sha256']):raise PermissionError('Wrong fixture account')
        with self.lock:raw=self.rows[ref['key']]
        if self.on_read:self.on_read()
        return raw

class InvoiceHttpTests(DurableFixture,unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass();cls.owner_dsn,_,_,cls.api_dsn,cls.worker_dsn=create_runtime_roles()
    async def asyncSetUp(self):
        self.namespace='q'+uuid.uuid4().hex[:12];self.objects=OwnedObjectsFixture();self.tasks=[]
        self.store=producer_store(self.api_dsn,destination_contract=FIXTURE_CONTRACT,namespace=self.namespace)
        self.worker=producer_store(self.worker_dsn,destination_contract=FIXTURE_CONTRACT,namespace=self.namespace)
        self.raw=(ROOT/'benchmarks/convergence/fixtures/invoices/invoice-text.pdf').read_bytes()
        self.tokens={'staff':self.user.subject,'reviewer':self.reviewer.subject,'supervisor':self.supervisor.subject,'outsider':self.outsider.subject}
        def verify(token):
            if token not in self.tokens:raise Denied('Unknown signed-in fixture identity')
            return self.tokens[token]
        self.verify=verify;self.app=self.application();self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='https://invoices.example.test')
    def application(self):return create_app(self.verify,self.store,self.objects,account_id=self.account,public_origin='https://invoices.example.test')
    def headers(self,token='staff',**extra):return {'Authorization':'Bearer '+token,'Origin':'https://invoices.example.test',**extra}
    async def upload(self,*,client=None):return await(client or self.client).post('/api/invoices',content=self.raw,headers=self.headers(**{'Content-Type':'application/pdf'}))
    async def reviewed(self,result=None):
        response=await self.upload();self.assertEqual(response.status_code,202,response.text);operation=response.json()['invoice']['id'];lease=self.worker.claim_extract(operation)
        self.worker.record_result(operation,str(lease['lease_token']),result or {'supplier':'Southern Horizon Test Supplies','invoice_date':'2026-11-10','total':'42.50','currency':'AUD','requiresHumanReview':True})
        return operation
    async def asyncTearDown(self):
        for task in self.tasks:task.cancel()
        for task in self.tasks:
            try:await task
            except asyncio.CancelledError:pass
        await self.client.aclose()
    async def test_unknown_or_nonmember_identity_cannot_upload_or_read_private_results(self):
        for token in ['unknown','outsider','']:
            response=await self.client.post('/api/invoices',content=self.raw,headers=self.headers(token,**{'Content-Type':'application/pdf'}));self.assertEqual(response.status_code,403);self.assertNotIn('invoice',response.json())
        self.assertEqual(self.objects.puts,0)
    async def test_twenty_repeated_uploads_create_one_persistent_invoice_and_one_queue_row(self):
        replies=await asyncio.gather(*[self.upload()for _ in range(20)]);self.assertEqual({response.status_code for response in replies},{202});ids={response.json()['invoice']['id']for response in replies};self.assertEqual(len(ids),1);operation=next(iter(ids));self.assertEqual(self.worker.get(self.user,operation)['state'],'pending')
        with psycopg.connect(self.owner_dsn)as conn:count=conn.execute("SELECT count(*)FROM workflow.procrastinate_jobs WHERE task_name=%s AND args->>'operation_id'=%s",(self.namespace+'.extract',operation)).fetchone()[0]
        self.assertEqual(count,1);self.assertEqual(len(self.objects.rows),1)
    async def test_ordinary_uploader_cannot_edit_or_approve_even_with_forged_action_fields(self):
        operation=await self.reviewed();response=await self.client.post('/api/invoices/'+operation+'/approve',json={'revision':1},headers=self.headers());self.assertEqual(response.status_code,403)
        response=await self.client.post('/api/invoices/'+operation+'/review',json={'revision':1,'fields':{'supplier':'Forged','invoice_date':'2026-11-10','total':'42.50','currency':'AUD'},'notes':''},headers=self.headers());self.assertEqual(response.status_code,403)
        response=await self.client.post('/api/invoices/'+operation+'/approve',json={'revision':1,'role':'owner','state':'approved'},headers=self.headers('reviewer'));self.assertEqual(response.status_code,400);self.assertEqual(self.worker.get(self.user,operation)['state'],'review')
    async def test_reviewer_correction_is_revision_checked_and_keeps_original_extraction_history(self):
        operation=await self.reviewed();fields={'supplier':'Reviewer corrected supplier','invoice_date':'2026-11-10','total':'42.50','currency':'AUD'}
        response=await self.client.post('/api/invoices/'+operation+'/review',json={'revision':1,'fields':fields,'notes':'Corrected from the original PDF.'},headers=self.headers('reviewer'));self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['invoice']['revision'],2)
        stale=await self.client.post('/api/invoices/'+operation+'/approve',json={'revision':1},headers=self.headers('reviewer'));self.assertEqual(stale.status_code,409)
        history=await self.client.get('/api/invoices/'+operation+'/history',headers=self.headers());self.assertEqual(history.status_code,200);rows=history.json()['revisions'];self.assertEqual([row['revision']for row in rows],[1,2]);self.assertEqual(rows[0]['result']['supplier'],'Southern Horizon Test Supplies');self.assertEqual(rows[1]['result']['supplier'],fields['supplier']);self.assertEqual(rows[1]['actor'],self.reviewer.subject)
        approved=await self.client.post('/api/invoices/'+operation+'/approve',json={'revision':2},headers=self.headers('reviewer'));self.assertEqual(approved.status_code,200);self.assertEqual(approved.json()['invoice']['state'],'approved')
    async def test_incomplete_suggestion_cannot_be_approved_until_required_fields_are_reviewed(self):
        operation=await self.reviewed({'supplier':'Uncertain','invoice_date':'','total':'','currency':'AUD','uncertain':True})
        response=await self.client.post('/api/invoices/'+operation+'/approve',json={'revision':1},headers=self.headers('reviewer'));self.assertEqual(response.status_code,400);self.assertEqual(self.worker.get(self.user,operation)['state'],'review')
    async def test_original_download_checks_live_membership_again_after_storage_returns(self):
        operation=await self.reviewed();path='/api/invoices/'+operation+'/original';response=await self.client.get(path,headers=self.headers());self.assertEqual(response.content,self.raw);self.assertEqual(response.headers['cache-control'],'no-store')
        def revoke():
            with psycopg.connect(self.owner_dsn)as conn:conn.execute('UPDATE workflow.memberships SET active=false WHERE account_id=%s AND subject=%s',(self.account,self.user.subject))
        self.objects.on_read=revoke;denied=await self.client.get(path,headers=self.headers());self.assertEqual(denied.status_code,403);self.assertNotIn(b'%PDF-',denied.content)
    async def test_account_and_cursor_substitution_cannot_leak_private_invoices(self):
        operation=self.worker.submit(self.outsider,'document','other-account',{})
        for path in ['/api/invoices/'+operation,'/api/invoices/'+operation+'/history','/api/invoices?before='+operation]:
            response=await self.client.get(path,headers=self.headers());self.assertEqual(response.status_code,404);self.assertNotIn('result',response.json())
        response=await self.client.get('/api/invoices?account_id='+self.other,headers=self.headers());self.assertEqual(response.json()['invoices'],[])
    async def test_replacement_application_reads_persisted_review_without_session_memory(self):
        operation=await self.reviewed()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.application()),base_url='https://invoices.example.test')as replacement:
            response=await replacement.get('/api/invoices/'+operation,headers=self.headers());self.assertEqual(response.json()['invoice']['state'],'review');self.assertEqual(response.json()['invoice']['result']['total'],'42.50')
    async def test_oversize_and_wrong_origin_never_reach_storage(self):
        response=await self.client.post('/api/invoices',content=b'%PDF-'+b'x'*10000000,headers=self.headers(**{'Content-Type':'application/pdf'}));self.assertEqual(response.status_code,413)
        response=await self.client.post('/api/invoices',content=self.raw,headers=self.headers(**{'Content-Type':'application/pdf','Origin':'https://attacker.example.test'}));self.assertEqual(response.status_code,403);self.assertEqual(self.objects.puts,0)

if __name__=='__main__':unittest.main(verbosity=2)
