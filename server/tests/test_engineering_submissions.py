import asyncio
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from pydantic import ValidationError
from server.engineering_contexts import EngineeringContexts
from server.engineering_jobs import EngineeringJobs
from server.engineering_routes import StartRequest,IntentRequest
from server.engineering_sessions import BackendEvent,EngineeringSessions,ModelSelection,ProjectScope,RecoveredStart,SessionError,SqliteSessionStore
from server.tests.test_engineering_sessions import Backend


class SubmissionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'control.sqlite'
        self.store=SqliteSessionStore(self.path);self.backend=Backend()
        async def close():pass
        self.backend.close=close
        self.scope=ProjectScope('tenant-submission','project-library')
        self.sessions=EngineeringSessions(self.store,self.backend);self.jobs=EngineeringJobs(self.sessions)
        self.ident=(await self.sessions.create(self.scope,'library-workspace',ModelSelection('selected','medium')))['id']
        self.request=str(uuid.uuid4());self.text='Build only the library loans block.\nPreserve patrons, original scope and Unicode 📚.'

    async def asyncTearDown(self):
        await self.jobs.close();self.store.close();self.temp.cleanup()

    async def settle(self):
        for _ in range(20):await asyncio.sleep(0)

    async def test_parallel_retries_share_one_reserved_native_turn_and_one_intent(self):
        results=await asyncio.gather(*[self.jobs.start(self.scope,self.ident,self.text,request_id=self.request)for _ in range(8)])
        self.assertEqual(self.backend.request_ids,[self.request]);self.assertEqual(sum(not row['replayed']for row in results),1)
        self.assertTrue(all(row['acceptedRunId']==self.request for row in results))
        accepted=[row for row in self.jobs.journal.read(self.scope,self.ident)if row['kind']=='accepted']
        self.assertEqual(len(accepted),1);self.assertEqual(accepted[0]['text'],self.text)

    async def test_context_binding_survives_later_saved_changes_without_repinning_or_inference(self):
        contexts=EngineeringContexts(self.store)
        current={'bytes':json.dumps({'format':'atmem.ai-architect.project','meta':{'id':self.scope.project},'requirements':['Preserve local library loans']}).encode()}
        sha=hashlib.sha256(current['bytes']).hexdigest()
        self.jobs.context_provider=lambda scope,session,request,expected:contexts.attach(scope,session,request,current['bytes'],expected_sha256=expected)
        self.jobs.context_lookup=contexts.for_request
        original=self.backend.start
        async def with_context(*args,context=None,**kwargs):return await original(*args,**kwargs)
        self.backend.start=with_context
        await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request,context_sha256=sha)
        current['bytes']=json.dumps({'format':'atmem.ai-architect.project','meta':{'id':self.scope.project},'requirements':['New independent owner demand']}).encode()
        replay=await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request,context_sha256=sha)
        self.assertTrue(replay['replayed']);self.assertEqual(len(self.backend.request_ids),1)
        self.assertEqual(contexts.for_request(self.scope,self.ident,self.request)['sha256'],sha)
        with self.assertRaisesRegex(SessionError,'original intent or saved context'):
            await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request,context_sha256=hashlib.sha256(current['bytes']).hexdigest())
        with self.assertRaisesRegex(SessionError,'original intent or saved context'):
            await self.jobs.start(self.scope,self.ident,'Replace the library with another product.',request_id=self.request,context_sha256=sha)
        self.assertEqual(len(self.backend.request_ids),1)

    async def test_lost_acceptance_ack_returns_uncertainty_and_never_starts_again(self):
        self.backend.fail_start=True
        with self.assertRaises(TimeoutError):await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request)
        result=await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request)
        self.assertEqual(result['requestStatus'],'starting');self.assertEqual(result['state'],'starting');self.assertTrue(result['replayed'])
        self.assertEqual(self.backend.request_ids,[self.request])
        self.backend.recovered_start=RecoveredStart(self.request,'native-recovered','completed')
        result=await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request)
        self.assertEqual(result['requestStatus'],'completed');self.assertEqual(len(self.backend.request_ids),1)
        accepted=[row for row in self.jobs.journal.read(self.scope,self.ident)if row['kind']=='accepted']
        self.assertEqual(len(accepted),1);self.assertEqual(accepted[0]['origin'],'recovered_client_request')

    async def test_identity_survives_controller_and_store_restart(self):
        await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request)
        await self.jobs.close();self.store.close()
        self.store=SqliteSessionStore(self.path);self.sessions.store=self.store;self.jobs=EngineeringJobs(self.sessions)
        result=await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request)
        self.assertEqual(result['acceptedRunId'],self.request);self.assertEqual(len(self.backend.request_ids),1)
        self.assertEqual(len([row for row in self.jobs.journal.read(self.scope,self.ident)if row['kind']=='accepted']),1)

    async def test_replaying_an_older_turn_does_not_start_or_interrupt_newer_work(self):
        original=self.backend.start
        async def unique(*args,**kwargs):await original(*args,**kwargs);return 'native-turn-'+str(len(self.backend.request_ids))
        self.backend.start=unique
        await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request)
        await self.backend.events.put(BackendEvent('native-turn-1','completed'));await self.settle()
        newer=str(uuid.uuid4());await self.jobs.start(self.scope,self.ident,'Add the library returns flow.',request_id=newer)
        calls=list(self.backend.calls)
        result=await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request)
        self.assertEqual(result['run'],newer);self.assertEqual(result['acceptedRunId'],self.request);self.assertEqual(result['requestStatus'],'completed')
        self.assertEqual(self.backend.calls,calls);self.assertEqual(len(self.backend.request_ids),2)

    async def test_failed_or_interrupted_requests_are_not_implicitly_reexecuted(self):
        for status in ['failed','interrupted']:
            if status=='interrupted':
                self.ident=(await self.sessions.create(self.scope,'returns-workspace',ModelSelection('selected','medium')))['id'];self.request=str(uuid.uuid4())
            await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request)
            await self.backend.events.put(BackendEvent('native-turn-1',status));await self.settle()
            count=len(self.backend.request_ids);result=await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request)
            self.assertEqual(result['requestStatus'],status);self.assertEqual(len(self.backend.request_ids),count)

    async def test_cross_scope_and_other_session_identity_cannot_expose_or_reserve_work(self):
        await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request)
        for scope in [ProjectScope('other-tenant','project-library'),ProjectScope('tenant-submission','other-project')]:
            with self.assertRaises(SessionError):await self.jobs.start(scope,self.ident,self.text,request_id=self.request)
        other=(await self.sessions.create(self.scope,'other-workspace',ModelSelection('selected','medium')))['id']
        with self.assertRaisesRegex(SessionError,'identity is unavailable'):await self.jobs.start(self.scope,other,'Unrelated work',request_id=self.request)
        self.assertEqual(self.jobs.state(self.scope,other)['state'],'idle');self.assertEqual(len(self.backend.request_ids),1)
        self.assertIsNone(self.store.get_run(self.scope,other,self.request))

    async def test_bad_identity_and_missing_context_lookup_fail_before_native_calls(self):
        before=list(self.backend.calls)
        for request in ['bad-identity',self.request.upper()]:
            with self.assertRaises(ValueError):await self.jobs.start(self.scope,self.ident,self.text,request_id=request)
        with self.assertRaises(ValueError):await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request,run_id=str(uuid.uuid4()))
        self.jobs.context_provider=lambda *args:None
        with self.assertRaisesRegex(SessionError,'immutable context lookup'):await self.jobs.start(self.scope,self.ident,self.text,request_id=self.request)
        self.assertEqual(self.backend.calls,before)

    def test_http_start_identity_requires_exact_context_and_is_not_accepted_on_steer(self):
        body={'projectId':'project-library','sessionId':str(uuid.uuid4()),'text':self.text,'requestId':self.request,'contextSha256':'a'*64}
        self.assertEqual(StartRequest(**body).requestId,self.request)
        with self.assertRaises(ValidationError):StartRequest(**{**body,'contextSha256':None})
        with self.assertRaises(ValidationError):StartRequest(**{**body,'requestId':'invalid'})
        with self.assertRaises(ValidationError):IntentRequest(**body)
        legacy={k:v for k,v in body.items()if k!='requestId'};self.assertIsNone(StartRequest(**legacy).requestId)
