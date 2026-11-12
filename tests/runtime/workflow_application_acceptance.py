"""Application assembly with real JWT crypto/local SQL/queue/TLS fixtures.

Native IdP keys, cloud credential APIs and managed databases are not contacted.
Internal connection injection is test/bootstrap-only, never a profile/HTTP feature.
"""
import asyncio
import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid
import httpx
import psycopg

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from workflow_payload_acceptance import definition
from durable_postgres_acceptance import DurableFixture,fixture_dsn
from durable_fixture_tasks import FIXTURE_CONTRACT
from durable_workflow import Principal
from invoice_identity_acceptance import identity_fixture
RUNTIME=Path(__import__('workflow_payload').__file__).resolve().parent
sys.path.insert(0,str(RUNTIME))
from workflow_application import ApplicationProfile,load_profile,create_native_api,create_native_worker,membership_key
from workflow_worker import producer_store
from workflow_contract import normalized_contract
from approved_http_destination import ApprovedHttpDestination
from workflow_tls_destination_fixture import TlsDestinationFixture
from workflow_errors import InvalidDispatch

ORIGIN='https://application.example'
SOURCE={'itemId':'microscope','memberId':'member-1'}
RESULT={'loanDays':7,'inspectionRequired':True}


def configuration(account=None,provider='aws'):
    return {'format':'approval-application-v1','provider':provider,'componentId':'reservation-α',
        'environment':'qualification','accountId':account or str(uuid.uuid4()),'publicOrigin':ORIGIN,
        'operationKind':'draft','identitySettings':identity_fixture(provider)[4],
        'payloadContract':definition(),'destinationContract':dict(FIXTURE_CONTRACT)}


class ProfileTests(unittest.TestCase):
    def test_deep_snapshot_alias_and_full_identity_are_retained(self):
        raw=configuration();profile=ApplicationProfile(raw);original=profile.namespace
        raw['componentId']='changed';raw['payloadContract']['result']['properties']['loanDays']['maximum']=99
        data=profile.data;data['componentId']='also changed'
        self.assertEqual(profile.data['componentId'],'reservation-α');self.assertEqual(profile.namespace,original)
        self.assertLessEqual(len(profile.namespace),20);self.assertTrue(profile.namespace.isalnum())
        self.assertEqual(len(profile.binding_sha256),64)
        with self.assertRaises(FrozenInstanceError):profile._encoded=b'{}'
    def test_account_component_environment_and_provider_define_distinct_queues(self):
        raw=configuration();base=ApplicationProfile(raw).namespace
        for key,value in [('provider','azure'),('componentId','another'),('accountId',str(uuid.uuid4())),('environment','staging')]:
            changed={**raw,key:value}
            if key=='provider':changed['identitySettings']=identity_fixture(value)[4]
            self.assertNotEqual(ApplicationProfile(changed).namespace,base)
        changed=copy.deepcopy(raw);changed['payloadContract']['result']['properties']['loanDays']['maximum']=20
        self.assertEqual(ApplicationProfile(changed).namespace,base) # Find/block old work; never hide it in a new queue.
    def test_identity_and_operation_policy_changes_bind_approvals_without_hiding_old_work(self):
        raw=configuration();first=ApplicationProfile(raw)
        for change in ['operation','identity']:
            changed=copy.deepcopy(raw)
            if change=='operation':changed['operationKind']='account_change'
            else:changed['identitySettings']['CLIENT_ID']='changedclient'
            second=ApplicationProfile(changed)
            self.assertEqual(first.namespace,second.namespace)
            self.assertNotEqual(first.destination,second.destination)
            self.assertEqual(second.destination['applicationContractSha256'],second.sha256)
    def test_native_membership_key_binds_entire_subject_and_identity_realm(self):
        data=configuration();profile=ApplicationProfile(data);subject='long-native-subject-'+'α'*1000
        key=membership_key(profile,subject);self.assertEqual(key,membership_key(ApplicationProfile(data),subject))
        self.assertNotEqual(key,membership_key(profile,subject+'x'))
        changed=copy.deepcopy(data);changed['identitySettings']['POOL_ID']='ap-southeast-2_Different'
        self.assertNotEqual(key,membership_key(ApplicationProfile(changed),subject))
        self.assertEqual(len(key),71)
    def test_client_scope_changes_preserve_person_identity_but_rebind_work(self):
        raw=configuration();first=ApplicationProfile(raw);key=membership_key(first,'complete-native-subject')
        for field,value in [('CLIENT_ID','changedclient'),('AUTH_SCOPE','changed/process')]:
            changed=copy.deepcopy(raw);changed['identitySettings'][field]=value;second=ApplicationProfile(changed)
            self.assertEqual(membership_key(second,'complete-native-subject'),key)
            self.assertNotEqual(second.destination,first.destination)
    def test_unknown_fields_oversize_identity_provider_fallback_and_secrets_are_rejected(self):
        for update in [{'provider':'other'},{'componentId':'界'*171},{'environment':'unknown'},{'connection':'postgres://secret'},
                       {'processor':'module:run'},{'credentialPath':'/private/key'},{'operationKind':'execute'}]:
            with self.subTest(update=update),self.assertRaises(ValueError):ApplicationProfile({**configuration(),**update})
    def test_file_loader_rejects_duplicate_and_oversize_bytes(self):
        with tempfile.TemporaryDirectory()as tmp:
            path=Path(tmp)/'profile.json';path.write_text(json.dumps(configuration()));profile=load_profile(path)
            self.assertEqual(profile.data['format'],'approval-application-v1')
            path.write_text('{"provider":"aws","provider":"ibm"}')
            with self.assertRaises(ValueError):load_profile(path)
            path.write_text('x'*64001)
            with self.assertRaises(ValueError):load_profile(path)
            with self.assertRaises(ValueError):load_profile('relative.json')
    def test_runtime_override_is_rejected_before_native_credentials(self):
        profile=ApplicationProfile(configuration())
        for key in ['PROVIDER','ACCOUNT_ID','ENVIRONMENT','WORKFLOW_NAMESPACE','PUBLIC_ORIGIN']:
            with self.subTest(key=key),patch('workflow_application.native_database')as native,self.assertRaises(ValueError):
                create_native_worker(profile,{key:'wrong'},lambda row:RESULT,lambda row,**kw:{})
            native.assert_not_called()
    def test_worker_import_never_loads_api_jwt_or_invoice_modules(self):
        code="import sys;sys.path.insert(0,sys.argv[1]);import workflow_application;from workflow_worker import WorkflowRuntime;assert not ({'jwt','fastapi','invoice_native','invoice_identity','workflow_identity','workflow_http'} & set(sys.modules))"
        result=subprocess.run([sys.executable,'-I','-c',code,str(RUNTIME)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


class AssemblyTests(DurableFixture,unittest.TestCase):
    def test_same_native_subject_from_changed_issuer_does_not_inherit_membership(self):
        from fastapi.testclient import TestClient
        identity,subject,token,claims,settings=identity_fixture('aws')
        data=configuration(self.account);first=ApplicationProfile(data)
        with self.store.connect()as conn:conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)',(self.account,membership_key(first,subject),['user']))
        app=create_native_api(first,{},connection=self.dsn,jwks=identity.verify.jwks)
        with TestClient(app,base_url=ORIGIN)as client:self.assertEqual(client.get('/api/session',headers={'Authorization':'Bearer '+token()}).status_code,200)
        changed=copy.deepcopy(data);changed['identitySettings']['POOL_ID']='ap-southeast-2_Different';second=ApplicationProfile(changed)
        app=create_native_api(second,{},connection=self.dsn,jwks=identity.verify.jwks)
        new_token=token({'iss':'https://cognito-idp.ap-southeast-2.amazonaws.com/ap-southeast-2_Different'})
        with TestClient(app,base_url=ORIGIN)as client:self.assertEqual(client.get('/api/session',headers={'Authorization':'Bearer '+new_token}).status_code,403)
    def test_wrong_kind_is_rejected_before_insert_and_before_claim_of_misrouted_work(self):
        profile=ApplicationProfile(configuration(self.account));worker=create_native_worker(profile,{},lambda row:RESULT,lambda row,**kw:{},connection=self.dsn)
        with self.assertRaises(ValueError):worker.store.submit(self.user,'account_change','wrong-kind',SOURCE)
        self.assertEqual(worker.store.list(self.user),[])
        other=producer_store(self.dsn,destination_contract=profile.destination,namespace=profile.namespace,payload_contract=profile.payload)
        operation=other.submit(self.user,'account_change','misrouted-kind',SOURCE)
        from durable_workflow import Conflict
        with self.assertRaises(Conflict):worker.store.claim_extract(operation)
        self.assertEqual(other.get(self.user,operation)['state'],'pending')
    def test_changed_operation_policy_cannot_approve_older_draft_work(self):
        data=configuration(self.account);first=ApplicationProfile(data)
        old=create_native_worker(first,{},lambda row:RESULT,lambda row,**kw:{},connection=self.dsn)
        operation=old.store.submit(self.user,'draft','policy-change',SOURCE)
        lease=old.store.claim_extract(operation);old.store.record_result(operation,str(lease['lease_token']),RESULT)
        changed=ApplicationProfile({**data,'operationKind':'account_change'})
        current=create_native_worker(changed,{},lambda row:RESULT,lambda row,**kw:{},connection=self.dsn)
        from durable_workflow import Conflict
        with self.assertRaises(Conflict):current.store.approve(self.reviewer,operation,1)
        self.assertNotEqual(first.destination,changed.destination)
    def test_each_provider_routes_api_and_worker_to_exact_native_database_role(self):
        for provider in ['aws','azure','gcp','ibm']:
            identity,subject,token,claims,settings=identity_fixture(provider)
            profile=ApplicationProfile(configuration(self.account,provider))
            with patch('workflow_application.native_database',return_value=self.dsn)as native:
                create_native_api(profile,settings,jwks=identity.verify.jwks)
                native.assert_called_once_with(provider,settings,'api')
            with patch('workflow_application.native_database',return_value=self.dsn)as native:
                worker=create_native_worker(profile,{},lambda row:RESULT,lambda row,**kw:{})
                native.assert_called_once_with(provider,{},'worker')
                self.assertEqual(worker.store.workflow_key,profile.namespace+'.extract')
    def test_stage_guards_deny_foreign_accounts_before_callbacks_and_preserve_deadlines(self):
        profile=ApplicationProfile(configuration(self.account));calls=[]
        class Stage:
            timeout_seconds=180
            def __call__(self,*args,**kwargs):calls.append(args);return RESULT
        worker=create_native_worker(profile,{},Stage(),lambda row,**kwargs:{},connection=self.dsn)
        self.assertEqual(worker.processor.timeout_seconds,180)
        for stage in [worker.processor,worker.deliver]:
            with self.assertRaises(InvalidDispatch):stage({'account_id':self.other})
        self.assertEqual(calls,[])
    def test_foreign_work_misrouted_to_same_queue_never_reaches_processor(self):
        profile=ApplicationProfile(configuration(self.account));calls=[]
        worker=create_native_worker(profile,{},lambda row:calls.append(row),lambda row,**kwargs:{},connection=self.dsn)
        operation=worker.store.submit(self.outsider,'draft','foreign',SOURCE)
        async def process():
            from workflow_errors import PermanentWork
            with self.assertRaises(PermanentWork):await worker._extract(operation)
        asyncio.run(process());self.assertEqual(calls,[])
        self.assertEqual(worker.store.get(self.outsider,operation)['state'],'dead')


class NativeAssemblyJourneyTests(unittest.IsolatedAsyncioTestCase):
    async def test_four_provider_identity_profiles_cross_real_http_queue_and_tls(self):
        from durable_privileges_acceptance import create_runtime_roles
        owner_dsn,api_role,worker_role,api_dsn,worker_dsn=create_runtime_roles()
        for provider in ['aws','azure','gcp','ibm']:
            identity,subject,token,claims,settings=identity_fixture(provider)
            account=str(uuid.uuid4());reviewer=str(uuid.uuid4());sink=TlsDestinationFixture()
            data=configuration(account,provider);data['destinationContract']=normalized_contract(sink.url,'synthetic-profile')
            profile=ApplicationProfile(data)
            deliver=ApprovedHttpDestination(sink.url,lambda:sink.token,destination_scope='synthetic-profile',tls_context=sink.context,allowed_kinds=('draft',),payload_contract=profile.payload,application_contract_sha256=profile.sha256)
            worker=create_native_worker(profile,{},lambda row:RESULT,deliver,connection=worker_dsn)
            with psycopg.connect(owner_dsn)as conn:
                conn.execute('INSERT INTO workflow.accounts(id) VALUES(%s)',(account,))
                for member,roles in [(subject,['user']),(reviewer,['reviewer'])]:conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)',(account,membership_key(profile,member),roles))
            app=create_native_api(profile,settings,connection=api_dsn,jwks=identity.verify.jwks)
            task=asyncio.create_task(worker.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=2))
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url=ORIGIN)as client:
                    header=identity.token_header or 'Authorization'
                    credential=lambda value:value if identity.token_header else 'Bearer '+value
                    headers={header:credential(token()),'Origin':ORIGIN,'Idempotency-Key':'stable-profile'}
                    response=await client.post('/api/operations',json={'source':SOURCE},headers=headers)
                    self.assertEqual(response.status_code,202,response.text);operation=response.json()['operation']['id']
                    async def until(state):
                        deadline=time.monotonic()+10
                        while time.monotonic()<deadline:
                            if task.done():task.result()
                            response=await client.get('/api/operations/'+operation,headers=headers)
                            self.assertEqual(response.status_code,200,response.text)
                            row=response.json()['operation']
                            if row['state']==state:return row
                            await asyncio.sleep(.03)
                        self.fail('Native-profile fixture did not reach '+state)
                    await until('review');self.assertEqual(sink.calls,[])
                    denied=await client.post('/api/operations/'+operation+'/approve',json={'revision':1},headers=headers)
                    self.assertEqual(denied.status_code,403) # Token role names never replace current SQL membership.
                    reviewer_token=token({'sub':reviewer,'oid':reviewer})
                    approved=await client.post('/api/operations/'+operation+'/approve',json={'revision':1},headers={**headers,header:credential(reviewer_token)})
                    self.assertEqual(approved.status_code,200,approved.text)
                    sent=await until('sent');self.assertEqual(sent['receipt']['operationId'],operation);self.assertEqual(len(sink.effects),1)
                    forged=await client.get('/api/operations/'+operation,headers={**headers,header:credential(token({'iss':'https://foreign.invalid'}))})
                    self.assertEqual(forged.status_code,403)
                    self.assertEqual(worker.store.get(Principal(account,membership_key(profile,subject)),operation)['destination_contract'],profile.destination)
            finally:
                task.cancel()
                try:await task
                except asyncio.CancelledError:pass
                await asyncio.to_thread(sink.close)


if __name__=='__main__':unittest.main(verbosity=2)
