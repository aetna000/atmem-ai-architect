import asyncio
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch
from server.engineering_handoff_capsules import HandoffCapsules,render,encode,digest,validate
from server.engineering_contexts import EngineeringContexts
from server.engineering_jobs import EngineeringJobs
from server.engineering_work_orders import EngineeringWorkOrders
from server.engineering_artifacts import EngineeringArtifacts
from server.engineering_tools import EngineeringTools
from server.engineering_sessions import EngineeringSessions,ModelSelection,ProjectScope,SessionError,BackendEvent,SqliteSessionStore
from server.tests.test_engineering_sessions import Backend


def design(project):
    spec={'behavior':'Own immutable loan receipts.','inputs':'Scoped operation ID.','outputs':'Durable receipt.','failures':'Reconcile uncertain outcomes.','implementation':'Transactional fenced writer.','infrastructure':'Qualified local durable store.','operations':'Restore with a fresh writer.','tests':'Race duplicates and recover safely.','scenarios':[{'name':'Issue','steps':[{'sender':'Clerk','receiver':'Loans','action':'Commit receipt'}]}]}
    node=lambda id,parent=None:{'id':id,'type':'resource','position':{'x':0,'y':0},'data':{'kind':'resource','provider':'tools','origin':'proposed','label':id,'buildSpec':spec,**({'parentBlockId':parent}if parent else{})}}
    value={'format':'atmem.ai-architect.project','formatVersion':'2.3.0','meta':{'id':project,'name':'Library','revision':1,'createdAt':'2026-11-19T00:00:00Z'},'design':{'provider':'tools','nodes':[node('library'),node('loans','library'),node('archive','library')],'edges':[{'id':'receipt','source':'loans','target':'archive','label':'Accepted receipt','interfaceSpec':{'transport':'versioned event','input':'Loan ID and version','output':'Consumer checkpoint','authorization':'Scoped archival role','failure':'Same-ID replay','verification':'Duplicate and denied caller tests'}}]},'requirements':[{'id':'once','statement':'Preserve one result per operation.','acceptance':'Two equal operations return one durable receipt.','kind':'functional','priority':'must','source':'user','status':'open','links':['loans']}],'extensions':{}}
    return json.dumps(value).encode()


class HandoffCapsuleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.workspace=self.root/'owned';self.workspace.mkdir()
        self.store=SqliteSessionStore(self.root/'control.sqlite');self.scope=ProjectScope('tenant-capsule','project-library');self.backend=Backend()
        async def close():pass
        self.backend.close=close;self.sessions=EngineeringSessions(self.store,self.backend);self.jobs=EngineeringJobs(self.sessions)
        self.session=(await self.sessions.create(self.scope,'owned',ModelSelection('selected','medium')))['id']
        self.content=design(self.scope.project);self.sha=digest(self.content);self.contexts=EngineeringContexts(self.store)
        self.jobs.context_provider=lambda scope,session,request,expected:self.contexts.attach(scope,session,request,self.content,expected_sha256=expected)
        self.jobs.context_lookup=self.contexts.for_request
        self.render_count=0
        def compiler(content,project,block):self.render_count+=1;return render(content,project,block)
        self.capsules=HandoffCapsules(self.store,lambda scope,session:self.workspace,renderer=compiler)
        self.orders=EngineeringWorkOrders(self.jobs,handoffs=self.capsules);self.jobs.before_start=self.capsules.materialize
        original=self.backend.start
        async def start(*args,context=None,**kwargs):
            request=kwargs['request_id'];assert (self.workspace/f'.atmem-handoffs/{request}/READ_ME_FIRST.md').is_file()
            return await original(*args,**kwargs)
        self.backend.start=start;self.request=str(uuid.uuid4())
    async def asyncTearDown(self):
        await self.capsules.close();await self.jobs.close();self.store.close();self.temp.cleanup()
    async def submit(self,block='loans'):
        return await self.orders.start_block(self.scope,self.session,self.request,block,self.sha,lambda:self.content)
    async def settle(self):
        await self.backend.events.put(BackendEvent('native-turn-1','completed'))
        for _ in range(50):
            await asyncio.sleep(0)
            if self.jobs.state(self.scope,self.session)['state']=='idle':return
        self.fail('Synthetic native turn did not settle')
    async def test_real_compiler_materializes_exact_scoped_kit_before_native_start(self):
        result=await self.submit();descriptor=result['workOrder']['handoff'];row,value=self.capsules.get(self.scope,self.session,self.request)
        self.assertEqual(value['blockIds'],['loans']);self.assertEqual(value['files']['source-context.json'].encode(),self.content)
        self.assertFalse(any(name.startswith('spec-kit/blocks/block-61726368697665/')for name in value['files']))
        prefix=self.workspace/descriptor['root']
        for name,text in value['files'].items():self.assertEqual((prefix/name).read_text(),text)
        self.assertEqual(digest((prefix/'CAPSULE.json').read_bytes()),descriptor['manifestSha256'])
        self.assertEqual(digest(encode(value)),descriptor['sha256']);self.assertIn(descriptor['sha256'],self.store.get_run(self.scope,self.session,self.request)['intent'])
        tasks=json.loads(value['files']['spec-kit/tasks.json'])['tasks'];contract=next(t for t in tasks if t['phase']=='Contracts')
        self.assertTrue(any('Same-ID replay'in step for step in contract['steps']));self.assertEqual(self.backend.request_ids,[self.request])
    async def test_concurrent_retry_uses_one_compiler_one_capsule_one_native_call(self):
        results=await asyncio.gather(*[self.submit()for _ in range(5)])
        self.assertEqual(self.render_count,1);self.assertEqual(self.backend.request_ids,[self.request]);self.assertEqual(len({r['workOrder']['handoff']['sha256']for r in results}),1)
        self.content=design(self.scope.project)+b' '
        replay=await self.submit();self.assertTrue(replay['replayed']);self.assertEqual(self.render_count,1)
    async def test_capture_retains_and_checks_handoff_inputs_and_rejects_tampering(self):
        await self.submit();await self.settle();artifacts=EngineeringArtifacts(self.store);pins=self.capsules.pins(self.scope,self.session)
        captured=artifacts.capture(self.scope,self.session,self.workspace,expected_inputs=pins)
        self.assertTrue(any(file['path'].endswith('/source-context.json')for file in captured['files']))
        target=self.workspace/f'.atmem-handoffs/{self.request}/READ_ME_FIRST.md';target.chmod(0o600);target.write_text('Changed after submission')
        with self.assertRaises(SessionError):artifacts.capture(self.scope,self.session,self.workspace,expected_inputs=pins)
    async def test_compiler_error_or_bad_generated_paths_start_no_native_work(self):
        def broken(*args):raise SessionError('Compiler failed')
        self.capsules.renderer=broken
        with self.assertRaises(SessionError):await self.submit()
        self.assertEqual(self.backend.request_ids,[]);self.assertEqual(self.store.db.execute('SELECT count(*) FROM engineering_work_orders').fetchone()[0],0)
        value=render(self.content,self.scope.project,'loans');value['files']['../../outside']='bad'
        with self.assertRaises(SessionError):validate(value,self.scope.project,'loans',self.sha)
        value['files'].pop('../../outside');value['blockIds'].append('archive')
        with self.assertRaises(SessionError):validate(value,self.scope.project,'loans',self.sha)
    async def test_symlink_and_existing_foreign_bytes_are_not_followed_or_repaired(self):
        outside=self.root/'outside';outside.mkdir();(self.workspace/'.atmem-handoffs').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(SessionError):await self.submit()
        self.assertEqual(list(outside.iterdir()),[]);self.assertEqual(self.backend.request_ids,[])
    async def test_parent_order_includes_descendant_kits_without_changing_source(self):
        result=await self.submit('library');row,value=self.capsules.get(self.scope,self.session,self.request)
        self.assertEqual(set(value['blockIds']),{'library','loans','archive'})
        for block in value['blockIds']:self.assertIn(f'spec-kit/blocks/block-{block.encode().hex()}/WORK_ORDER.md',value['files'])
        self.assertEqual(value['sourceSha256'],self.sha)
    async def test_scoped_paged_tool_reads_are_audited_and_do_not_imply_quality(self):
        await self.submit();tools=EngineeringTools(self.store,EngineeringArtifacts(self.store),lambda:None,handoff_read=self.capsules.read)
        entry=self.capsules.get(self.scope,self.session,self.request)[1]['entryPoint'].replace('WORK_ORDER.md','tasks.json')
        offset=0;sha=None;count=0
        while True:
            args={'path':entry,'offset':offset,**({'sha256':sha}if sha else{})};count+=1
            result=await tools.invoke(self.scope,'owned','native-turn-1','page-'+str(count),'atmem_work_order_read',args)
            self.assertTrue(result['success']);value=json.loads(result['contentItems'][0]['text']);sha=value['sha256'];offset=value['page']['nextOffset']
            if offset is None:break
        self.assertFalse((await tools.invoke(self.scope,'owned','native-turn-1','bad-path','atmem_work_order_read',{'path':'../../outside'}))['success'])
        self.assertFalse((await tools.invoke(self.scope,'owned','native-turn-1','bad-sha','atmem_work_order_read',{'path':entry,'offset':1,'sha256':'0'*64}))['success'])
        self.assertGreater(count,1);self.assertEqual(self.capsules.evidence(self.scope,self.session,self.request)['completeRequiredFiles'],0)
        await self.settle();evidence=self.capsules.evidence(self.scope,self.session,self.request)
        self.assertEqual(evidence['completeRequiredFiles'],1);self.assertEqual(evidence['requiredFileCount'],8);self.assertIn('not interpretation',evidence['boundary'])
        with self.assertRaises(SessionError):await tools.invoke(self.scope,'owned','native-turn-1','after','atmem_work_order_read',{})
    async def test_restart_retains_original_package_instead_of_recompiling(self):
        result=await self.submit();self.capsules=HandoffCapsules(self.store,lambda scope,session:self.workspace,renderer=lambda *args:self.fail('Recompiled accepted handoff'))
        self.orders=EngineeringWorkOrders(self.jobs,handoffs=self.capsules)
        self.assertEqual((await self.submit())['workOrder']['handoff'],result['workOrder']['handoff'])
    async def test_handoff_history_bound_fails_closed_without_removing_prior_evidence(self):
        with patch('server.engineering_handoff_capsules.MAX_BYTES',1):
            with self.assertRaises(SessionError):await self.submit()
        self.assertEqual(self.backend.request_ids,[])

    async def test_interrupted_unaccepted_copy_resumes_only_its_exact_retained_prefix(self):
        def interrupted(scope,session,request,context,intent):
            value=self.capsules.get(scope,session,request)[1];target=self.workspace/f'.atmem-handoffs/{request}/READ_ME_FIRST.md';target.parent.mkdir(parents=True);target.write_bytes(value['files']['READ_ME_FIRST.md'].encode()[:31]);target.chmod(0o400)
            raise SessionError('Simulated server interruption before native reservation')
        self.jobs.before_start=interrupted
        with self.assertRaises(SessionError):await self.submit()
        self.assertEqual(self.backend.request_ids,[]);self.assertIsNone(self.store.get_run(self.scope,self.session,self.request))
        observed=[]
        def resume(*args):observed.append(self.capsules.materialize(*args))
        self.jobs.before_start=resume;await self.submit()
        self.assertEqual(self.render_count,1);self.assertTrue(observed[0]['recoveredPartialPreparation']);self.assertEqual(self.backend.request_ids,[self.request])
        value=self.capsules.get(self.scope,self.session,self.request)[1]
        self.assertEqual((self.workspace/f'.atmem-handoffs/{self.request}/READ_ME_FIRST.md').read_text(),value['files']['READ_ME_FIRST.md'])

    async def test_prepared_order_cannot_be_rebound_through_untyped_start(self):
        def reject(*args):raise SessionError('Retain prepared work before inference')
        self.jobs.before_start=reject
        with self.assertRaises(SessionError):await self.submit()
        self.jobs.before_start=self.capsules.materialize
        with self.assertRaisesRegex(SessionError,'reserved work order'):
            await self.jobs.start(self.scope,self.session,'Change this block to another system',request_id=self.request,context_sha256=self.sha)
        self.assertEqual(self.backend.request_ids,[])
        await self.submit();self.assertEqual(self.backend.request_ids,[self.request])

    async def test_partial_read_cannot_claim_complete_required_file(self):
        # Pagination must be exercised by explicit content, not JSON indentation.
        source=json.loads(self.content)
        source['design']['nodes'][1]['data']['buildSpec']['behavior']='Preserve the original receipt and reconcile each duplicate. '*50
        self.content=json.dumps(source).encode();self.sha=digest(self.content)
        await self.submit();tools=EngineeringTools(self.store,EngineeringArtifacts(self.store),lambda:None,handoff_read=self.capsules.read)
        name=self.capsules.get(self.scope,self.session,self.request)[1]['entryPoint'].replace('WORK_ORDER.md','tasks.json')
        first=await tools.invoke(self.scope,'owned','native-turn-1','first','atmem_work_order_read',{'path':name});page=json.loads(first['contentItems'][0]['text'])
        self.assertGreater(page['page']['totalCharacters'],8000)
        await tools.invoke(self.scope,'owned','native-turn-1','last','atmem_work_order_read',{'path':name,'offset':page['page']['totalCharacters']-10,'sha256':page['sha256']})
        await self.settle();self.assertEqual(self.capsules.evidence(self.scope,self.session,self.request)['completeRequiredFiles'],0)

    async def test_lost_native_ack_keeps_one_exact_compiled_package(self):
        self.backend.fail_start=True
        with self.assertRaises(TimeoutError):await self.submit()
        initial=self.capsules.get(self.scope,self.session,self.request)[0]['sha256']
        result=await self.submit();self.assertTrue(result['replayed']);self.assertEqual(self.render_count,1)
        self.assertEqual(result['workOrder']['handoff']['sha256'],initial);self.assertEqual(self.backend.request_ids,[self.request])

    async def test_canceled_http_wait_does_not_bypass_compiler_admission_bound(self):
        import threading
        value=render(self.content,self.scope.project,'loans');entered=threading.Event();release=threading.Event()
        def blocked(*args):entered.set();release.wait(3);return value
        capsules=HandoffCapsules(self.store,lambda scope,session:self.workspace,renderer=blocked,max_pending=1)
        task=asyncio.create_task(capsules.prepare(self.scope,self.session,self.request,self.content,'loans'))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait,2));task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
            with self.assertRaisesRegex(SessionError,'queue'):
                await capsules.prepare(self.scope,self.session,str(uuid.uuid4()),self.content,'loans')
            self.assertEqual(self.backend.request_ids,[])
        finally:release.set();await capsules.close()
