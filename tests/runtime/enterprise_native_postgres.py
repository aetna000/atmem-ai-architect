"""Assembled native factories, actual separate SQL roles/queue, scripted vendors.

The fixture decoder is explicitly synthetic; native cloud per-file jobs, real
company/source/model accounts and deployment are not claimed by these tests.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import secrets
import sys
import unittest
from unittest.mock import patch
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/azure-runtime-sdk'),str(ROOT/'tests/runtime')]
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict,make_conninfo
import enterprise_http_postgres as fixture
from enterprise_audit import initialize_audit,grant_audit_writer
from enterprise_auth_store import grant_auth_runtime
from enterprise_configuration import deployment
from enterprise_extraction_cache import initialize_extraction_cache,grant_extraction_runtime
from enterprise_native import NativeRuntime,DocumentExecutor
from enterprise_queries import initialize_query_store,grant_query_runtime
from enterprise_models_acceptance import environment as model_environment
from enterprise_secrets_acceptance import environment as secret_environment

from enterprise_deployment_fixture import metadata,REVISION,fresh_database
from enterprise_operator import activate


class NativeFactories(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        from cryptography.hazmat.primitives.asymmetric import rsa
        database=fresh_database();cls.owner_dsn=database['owner'];cls.app_dsn=database['api'];cls.worker_dsn=database['worker'];cls.key=database['key']
        cls.signing=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        for name in ['owner_dsn','app_dsn','key','signing']:setattr(fixture.CompanyHttpIntegration,name,getattr(cls,name))

    async def asyncSetUp(self):
        self.f=fixture.CompanyHttpIntegration();await self.f.asyncSetUp()
        with psycopg.connect(self.owner_dsn)as conn:activate(conn,metadata(self.f.account))
        self.runtimes=[];self.model_factories=[];self.extracts=[]

    async def asyncTearDown(self):
        for runtime in self.runtimes:runtime.close()
        await self.f.asyncTearDown()

    def make(self,provider,role,**changes):
        configured=changes.pop('configured_worker',False)
        values={**secret_environment(provider),**model_environment(provider),'ENTERPRISE_ENCRYPTION_KEY':self.f.key.decode(),
            'SHAREPOINT_CLIENT_SECRET':'SYNTHETIC-CLIENT-SECRET','CONFLUENCE_CLIENT_SECRET':'SYNTHETIC-CLIENT-SECRET'}
        values.update(changes.pop('environment_updates',{}))
        options={'database':lambda:self.worker_dsn if role=='worker'else self.app_dsn,'identity':self.f.identity,
            'token_http':{'sharepoint':self.f.graph_http,'confluence':self.f.confluence_http},'profile_http':self.f.profiles,'document_http':self.f.document_http}
        def execute(raw,mime):
            self.extracts.append((len(raw),mime))
            return {'format':'enterprise-document-v1','sha256':hashlib.sha256(raw).hexdigest(),'mediaType':mime,'text':raw.decode()}
        def model(selected,environment):
            self.model_factories.append(selected)
            def generate(payload,schema,instruction):
                self.f.model_calls.append(True)
                if self.f.revoke_during_model:
                    with psycopg.connect(self.owner_dsn)as conn:conn.execute('UPDATE enterprise_auth.memberships SET active=false WHERE account_id=%s',(self.f.account,))
                article=json.loads(payload)['articles'][0]
                return json.dumps({'answer':'Private policy requires ninety days.','abstained':False,'citations':[{'id':article['id'],'quote':'Private policy requires ninety days.'}]})
            return generate
        if role=='worker':
            options.update(model_factory=model)
            if not configured:options['executor']=DocumentExecutor(REVISION,execute)
        options.update(changes)
        owned=options.pop('metadata_override',None)or metadata(self.f.account,provider)
        if configured:
            if role!='worker':raise ValueError('Configured native executor belongs only to the worker')
            from enterprise_worker import worker_runtime
            runtime=worker_runtime(owned,values,**options)
        else:runtime=NativeRuntime(owned,values,role,**options)
        self.runtimes.append(runtime);return runtime

    async def browser(self,runtime):
        await self.f.client.aclose();self.f.app=runtime.api();self.f.client=self.f.new_client();self.f.clients.append(self.f.client)
        await self.f.login();await self.f.connect_all()

    async def submit(self):
        response=await self.f.client.post('/api/queries',headers=self.f.headers(),json={'question':'What is our retention policy?','requestId':str(uuid.uuid4())})
        self.assertEqual(response.status_code,202,response.text);return response.json()['id']

    async def status(self,identity):return await self.f.client.get('/api/queries/'+identity,headers={'X-Workspace-Request':'session'})

    async def test_all_four_factories_queue_execute_and_release_with_distinct_native_sql_roles(self):
        for provider in ['aws','azure','gcp','ibm']:
            with self.subTest(provider=provider):
                with psycopg.connect(self.owner_dsn)as conn:activate(conn,metadata(self.f.account,provider))
                api=self.make(provider,'api');worker=self.make(provider,'worker');await self.browser(api)
                identity=await self.submit();self.assertEqual((await self.status(identity)).json()['status'],'queued')
                await worker.worker().run(wait=False,concurrency=1,install_signal_handlers=False,listen_notify=False,fetch_job_polling_interval=.01)
                response=await self.status(identity);self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['result']['citations'][0]['quote'],'Private policy requires ninety days.')
                self.assertIsNone(api.answers.extraction_cache);self.assertIsNotNone(worker.answers.extraction_cache)
                with psycopg.connect(self.owner_dsn)as conn:
                    audit=conn.execute('SELECT event,outcome,attempt FROM enterprise_audit.events WHERE query_id=%s ORDER BY id',(identity,)).fetchall()
                self.assertEqual(audit,[('knowledge.answer','answered',1),('knowledge.release','released',1)])
        self.assertEqual(self.model_factories,['aws','azure','gcp','ibm']);self.assertEqual(len(self.extracts),1)

    async def test_google_controller_binds_owned_target_and_completes_native_factory_question(self):
        from enterprise_google_jobs import GoogleBatchDocuments, GoogleDocumentApi
        from enterprise_google_jobs_acceptance import NativeHttp, config
        http=NativeHttp();http.extracted_text='Private policy requires ninety days.'
        owned=config();runner=GoogleBatchDocuments(owned,api=GoogleDocumentApi(session=http,credential=lambda:'SYNTHETIC-NATIVE-TOKEN'),poll_seconds=.01)
        executor=DocumentExecutor(REVISION,runner)
        with self.assertRaisesRegex(ValueError,'selected provider'):self.make('aws','worker',executor=executor)
        with self.assertRaisesRegex(ValueError,'selected provider'):self.make('gcp','worker',executor=executor,environment_updates={'DATABASE_SERVICE_ACCOUNT':owned['vmServiceAccount']})
        self.assertEqual(http.calls,[])
        api=self.make('gcp','api');await self.browser(api)
        worker=self.make('gcp','worker',executor=executor,environment_updates={'DATABASE_SERVICE_ACCOUNT':owned['workerServiceAccount']})
        identity=await self.submit();await asyncio.to_thread(worker.answers.execute,identity)
        response=await self.status(identity);self.assertEqual(response.json()['status'],'ready',response.text)
        self.assertEqual(response.json()['result']['citations'][0]['quote'],'Private policy requires ninety days.')
        self.assertEqual(http.operation_polls,1);self.assertEqual(sum(method=='DELETE'for method,_,_ in http.calls),3)

    async def test_serialized_aws_worker_configuration_runs_queue_with_owned_cleanup(self):
        from enterprise_aws_jobs import EcsDocuments
        from enterprise_aws_execution_contract import Ecs,Objects,verified_hosts
        from enterprise_aws_jobs_contract import config,AwsDocumentTaskContract
        AwsDocumentTaskContract.setUpClass();owned=config();objects=Objects();api=Ecs(AwsDocumentTaskContract.model)
        runner=EcsDocuments(owned,api=api,objects=objects,host_check=verified_hosts,poll_seconds=.01)
        with psycopg.connect(self.owner_dsn)as conn:activate(conn,metadata(self.f.account,'aws'))
        await self.browser(self.make('aws','api'))
        encoded=json.dumps({'format':'enterprise-document-executor-v1','provider':'aws','parserRevision':REVISION,'configuration':owned})
        with patch('enterprise_aws_jobs.EcsDocuments',return_value=runner):
            worker=self.make('aws','worker',configured_worker=True,environment_updates={'ENTERPRISE_DOCUMENT_EXECUTOR_JSON':encoded,'AWS_ACCOUNT_ID':owned['accountId'],'WORKER_ROLE_ARN':owned['workerRoleArn']})
        identity=await self.submit()
        await worker.worker().run(wait=False,concurrency=1,install_signal_handlers=False,listen_notify=False,fetch_job_polling_interval=.01)
        response=await self.status(identity);self.assertEqual(response.json()['status'],'ready',response.text)
        self.assertEqual(response.json()['result']['citations'][0]['quote'],'Private policy requires ninety days.')
        self.assertEqual(sum(op=='run_task'for op,_ in api.calls),1)
        self.assertEqual([side for op,_,side in objects.calls if op=='delete'],['input','result'])
        with psycopg.connect(self.owner_dsn)as conn:self.assertEqual(conn.execute('SELECT count(*)FROM enterprise_document_jobs.jobs WHERE account_id=%s',(self.f.account,)).fetchone()[0],0)

    async def test_serialized_google_worker_configuration_runs_queue_with_owned_cleanup(self):
        from enterprise_google_jobs import GoogleBatchDocuments,GoogleDocumentApi
        from enterprise_google_jobs_acceptance import NativeHttp,config
        http=NativeHttp();http.extracted_text='Private policy requires ninety days.';owned=config()
        runner=GoogleBatchDocuments(owned,api=GoogleDocumentApi(session=http,credential=lambda:'SYNTHETIC-NATIVE-TOKEN'),poll_seconds=.01)
        await self.browser(self.make('gcp','api'))
        encoded=json.dumps({'format':'enterprise-document-executor-v1','provider':'gcp','parserRevision':REVISION,'configuration':owned})
        with patch('enterprise_google_jobs.GoogleBatchDocuments',return_value=runner):
            worker=self.make('gcp','worker',configured_worker=True,environment_updates={'ENTERPRISE_DOCUMENT_EXECUTOR_JSON':encoded,'DATABASE_SERVICE_ACCOUNT':owned['workerServiceAccount']})
        identity=await self.submit()
        await worker.worker().run(wait=False,concurrency=1,install_signal_handlers=False,listen_notify=False,fetch_job_polling_interval=.01)
        response=await self.status(identity);self.assertEqual(response.json()['status'],'ready',response.text)
        self.assertEqual(sum(method=='DELETE'for method,_,_ in http.calls),3)

    async def test_question_worker_runs_document_recovery_as_an_independent_background_task(self):
        from enterprise_google_jobs import GoogleBatchDocuments,GoogleDocumentApi
        from enterprise_google_jobs_acceptance import NativeHttp,config
        http=NativeHttp();http.extracted_text='Private policy requires ninety days.'
        owned=config();runner=GoogleBatchDocuments(owned,api=GoogleDocumentApi(session=http,credential=lambda:'SYNTHETIC-NATIVE-TOKEN'),poll_seconds=.01)
        api=self.make('gcp','api');await self.browser(api)
        worker=self.make('gcp','worker',executor=DocumentExecutor(REVISION,runner),environment_updates={'DATABASE_SERVICE_ACCOUNT':owned['workerServiceAccount']})
        runner.ledger.allocate('a'*64)
        with psycopg.connect(self.owner_dsn)as conn:conn.execute("UPDATE enterprise_document_jobs.jobs SET expires_at=clock_timestamp()-interval '1 second'WHERE account_id=%s AND request_id=%s",(self.f.account,'a'*64))
        identity=await self.submit()
        await worker.worker().run(wait=False,concurrency=1,install_signal_handlers=False,listen_notify=False,fetch_job_polling_interval=.01)
        self.assertEqual((await self.status(identity)).json()['status'],'ready')
        for _ in range(100):
            with psycopg.connect(self.owner_dsn)as conn:state=conn.execute('SELECT state FROM enterprise_document_jobs.jobs WHERE account_id=%s AND request_id=%s',(self.f.account,'a'*64)).fetchone()[0]
            if state=='settling':break
            await asyncio.sleep(.05)
        self.assertEqual(state,'settling');self.assertGreaterEqual(http.operation_polls,2)

    async def test_api_has_no_sync_inference_route_and_cannot_start_worker_or_receive_adapters(self):
        api=self.make('gcp','api');await self.browser(api)
        response=await self.f.client.post('/api/ask',headers=self.f.headers(),json={'question':'What is our retention policy?'})
        self.assertEqual(response.status_code,410);self.assertEqual(self.f.model_calls,[]);self.assertEqual(self.extracts,[])
        with self.assertRaises(ValueError):api.worker()
        with self.assertRaises(ValueError):self.make('gcp','api',model_factory=lambda *args:None)
        with self.assertRaises(ValueError):self.make('gcp','worker').api()

    async def test_unreviewed_worker_config_fails_before_claiming_questions_without_breaking_api(self):
        for provider in ['gcp','ibm']:
            with self.subTest(provider=provider):
                with psycopg.connect(self.owner_dsn)as conn:activate(conn,metadata(self.f.account,provider))
                with self.assertRaisesRegex(ValueError,'model retention review'):
                    self.make(provider,'worker',environment_updates={'POLICY_REVIEW_BASE64':''})
                self.make(provider,'api',environment_updates={'POLICY_REVIEW_BASE64':''})
        self.assertEqual(self.model_factories,[]);self.assertEqual(self.f.model_calls,[])

    async def test_api_startup_rejects_worker_database_and_inherited_authority_or_history_writes(self):
        with self.assertRaises(ValueError):self.make('gcp','api',database=lambda:self.worker_dsn)
        role=conninfo_to_dict(self.app_dsn)['user']
        for table,privilege in [('enterprise_auth.memberships','UPDATE'),('enterprise_audit.events','SELECT'),('enterprise_document_jobs.jobs','SELECT')]:
            try:
                with psycopg.connect(self.owner_dsn)as conn:conn.execute(sql.SQL('GRANT '+privilege+' ON '+table+' TO {}').format(sql.Identifier(role)))
                with self.assertRaises(ValueError):self.make('gcp','api')
            finally:
                with psycopg.connect(self.owner_dsn)as conn:conn.execute(sql.SQL('REVOKE '+privilege+' ON '+table+' FROM {}').format(sql.Identifier(role)))

    async def test_factory_never_migrates_or_adopts_a_stale_schema(self):
        try:
            with psycopg.connect(self.owner_dsn)as conn:conn.execute("UPDATE enterprise_audit.schema_version SET source_sha256='stale'")
            with self.assertRaises(ValueError):self.make('gcp','api')
            with psycopg.connect(self.owner_dsn)as conn:self.assertEqual(conn.execute('SELECT source_sha256 FROM enterprise_audit.schema_version').fetchone()[0],'stale')
        finally:
            expected=hashlib.sha256((ROOT/'src/runtime/enterprise_audit_schema.sql').read_bytes()).hexdigest()
            with psycopg.connect(self.owner_dsn)as conn:conn.execute('UPDATE enterprise_audit.schema_version SET source_sha256=%s',(expected,))

    async def test_revocation_between_worker_result_and_api_release_is_not_bypassed_by_factory(self):
        api=self.make('gcp','api');worker=self.make('gcp','worker');await self.browser(api)
        identity=await self.submit();await asyncio.to_thread(worker.answers.execute,identity)
        await self.f.client.delete('/api/sources/sharepoint',headers=self.f.headers())
        result=await self.status(identity);self.assertNotIn('ninety',result.text);self.assertNotIn('result',result.json())

    async def test_worker_requires_matching_byte_bound_executor_before_question_admission(self):
        with self.assertRaises(ValueError):self.make('gcp','worker',executor=lambda raw,mime:raw.decode())
        with self.assertRaises(ValueError):self.make('gcp','worker',executor=DocumentExecutor('b'*64,lambda raw,mime:{}))
        api=self.make('gcp','api');await self.browser(api)
        worker=self.make('gcp','worker',executor=DocumentExecutor(REVISION,lambda raw,mime:{'format':'enterprise-document-v1','sha256':'0'*64,'mediaType':mime,'text':'FORGED PRIVATE TEXT'}))
        identity=await self.submit();await asyncio.to_thread(worker.answers.execute,identity)
        self.assertEqual(self.f.model_calls,[]);self.assertNotIn('result',(await self.status(identity)).json())

    async def test_api_can_restart_without_regenerating_keys_or_losing_durable_question(self):
        first=self.make('gcp','api');await self.browser(first);identity=await self.submit()
        first.close();second=self.make('gcp','api');self.f.app=second.api();old=self.f.client
        client=self.f.new_client();client.cookies.update(old.cookies);self.f.clients.append(client);self.f.client=client
        self.assertEqual((await self.status(identity)).json()['status'],'queued')
        worker=self.make('gcp','worker');await asyncio.to_thread(worker.answers.execute,identity)
        self.assertIn('result',(await self.status(identity)).json())

    async def test_company_registration_change_invalidates_cookie_and_old_queued_work(self):
        api=self.make('gcp','api');await self.browser(api);identity=await self.submit()
        changed=metadata(self.f.account);changed['company']['web']['clientId']='new-reviewed-company-registration'
        with self.assertRaisesRegex(ValueError,'Activate'):self.make('gcp','api',metadata_override=changed)
        with psycopg.connect(self.owner_dsn)as conn:activate(conn,changed)
        with self.assertRaises(fixture.SourceDenied):api.auth.authorize(self.f.principal)
        replacement=self.make('gcp','api',metadata_override=changed)
        self.f.app=replacement.api();old=self.f.client;client=self.f.new_client();client.cookies.update(old.cookies);self.f.clients.append(client);self.f.client=client
        self.assertEqual((await self.status(identity)).status_code,401)
        worker=self.make('gcp','worker',metadata_override=changed);await asyncio.to_thread(worker.answers.execute,identity)
        self.assertEqual(self.f.model_calls,[])
        with psycopg.connect(self.owner_dsn)as conn:self.assertEqual(conn.execute('SELECT state FROM enterprise_queries.requests WHERE id=%s',(identity,)).fetchone()[0],'cancelled')
        # A newly verified company login can rotate the stale cookie and resume
        # ordinary work. It cannot inherit the old browser nonce or old jobs.
        await self.f.login();fresh=await self.submit();await asyncio.to_thread(worker.answers.execute,fresh)
        self.assertIn('result',(await self.status(fresh)).json())


if __name__=='__main__':unittest.main()
