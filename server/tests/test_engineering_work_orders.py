import asyncio
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch
from server.engineering_contexts import EngineeringContexts
from server.engineering_jobs import EngineeringJobs
from server.engineering_sessions import EngineeringSessions,ModelSelection,ProjectScope,SessionError,SqliteSessionStore
from server.engineering_work_orders import EngineeringWorkOrders,compile_block_order
from server.tests.test_engineering_sessions import Backend


def design(project,block='loans',label='Library loans'):
    return json.dumps({'format':'atmem.ai-architect.project','meta':{'id':project},'design':{'nodes':[
        {'id':block,'data':{'label':label,'kind':'resource','buildSpec':{'behavior':'Preserve durable ownership','tests':'Race duplicate operations'}}},
        {'id':'existing-identity','data':{'kind':'resource','origin':'existing'}}]},
        'requirements':[{'id':'preserve-identity','statement':'Preserve existing identity authority'}]},ensure_ascii=False).encode()


class WorkOrderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=SqliteSessionStore(Path(self.temp.name)/'control.sqlite');self.backend=Backend()
        async def close():pass
        self.backend.close=close;self.scope=ProjectScope('tenant-orders','project-library')
        sessions=EngineeringSessions(self.store,self.backend);self.jobs=EngineeringJobs(sessions)
        self.session=(await sessions.create(self.scope,'owned',ModelSelection('chosen','medium')))['id']
        self.contexts=EngineeringContexts(self.store);self.content=design(self.scope.project)
        self.jobs.context_provider=lambda scope,session,request,expected:self.contexts.attach(scope,session,request,self.content,expected_sha256=expected)
        self.jobs.context_lookup=self.contexts.for_request
        original=self.backend.start
        async def start(*args,context=None,**kwargs):return await original(*args,**kwargs)
        self.backend.start=start;self.orders=EngineeringWorkOrders(self.jobs);self.request=str(uuid.uuid4())
        self.sha=hashlib.sha256(self.content).hexdigest()
    async def asyncTearDown(self):
        await self.jobs.close();self.store.close();self.temp.cleanup()
    async def submit(self,**kwargs):
        return await self.orders.start_block(self.scope,self.session,kwargs.get('request',self.request),kwargs.get('block','loans'),kwargs.get('sha',self.sha),lambda:self.content)
    async def test_concurrent_controls_pin_context_and_launch_one_native_turn(self):
        results=await asyncio.gather(*[self.submit()for _ in range(6)])
        self.assertEqual(self.backend.request_ids,[self.request]);self.assertEqual(sum(not result['replayed']for result in results),1)
        events=self.jobs.journal.read(self.scope,self.session)
        prepared=[e for e in events if e['kind']=='work_order_prepared'];self.assertEqual(len(prepared),1)
        self.assertEqual(prepared[0]['workOrder'],{'version':1,'kind':'build_block','blockId':'loans','contextSha256':self.sha})
        self.assertEqual(self.contexts.for_request(self.scope,self.session,self.request)['content'].encode(),self.content)
    async def test_replay_keeps_original_basis_when_saved_project_changes(self):
        await self.submit();self.content=design(self.scope.project,'awards','Procurement awards')
        result=await self.submit();self.assertTrue(result['replayed']);self.assertEqual(len(self.backend.request_ids),1)
        with self.assertRaises(SessionError):await self.submit(block='awards')
        with self.assertRaises(SessionError):await self.submit(sha=hashlib.sha256(self.content).hexdigest())
    async def test_stale_or_missing_spec_controls_do_not_reserve_or_start(self):
        with self.assertRaises(SessionError):await self.submit(sha='0'*64)
        with self.assertRaises(SessionError):await self.submit(block='existing-identity')
        with self.assertRaises(SessionError):await self.submit(block='missing')
        self.assertEqual(self.backend.request_ids,[])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM engineering_work_orders').fetchone()[0],0)
    async def test_changed_save_during_submission_fails_closed_without_inference(self):
        self.jobs.context_provider=lambda scope,session,request,expected:self.contexts.attach(scope,session,request,design(scope.project,'awards'),expected_sha256=expected)
        with self.assertRaises(SessionError):await self.submit()
        self.assertEqual(self.backend.request_ids,[])
    async def test_other_owned_session_cannot_reuse_an_order_identity(self):
        await self.submit();other=(await self.jobs.sessions.create(self.scope,'other',ModelSelection('chosen','medium')))['id']
        with self.assertRaises(SessionError):await self.orders.start_block(self.scope,other,self.request,'loans',self.sha,lambda:self.content)
        self.assertEqual(len(self.backend.request_ids),1)
    async def test_process_reconstruction_preserves_typed_scope(self):
        await self.submit();self.orders=EngineeringWorkOrders(self.jobs)
        self.assertTrue((await self.submit())['replayed']);self.assertEqual(len(self.backend.request_ids),1)
    async def test_compile_transfers_to_new_domain_without_dispatching_on_labels(self):
        other=design(self.scope.project,'award-审查','Procurement award review')
        order,intent=compile_block_order(other,self.scope.project,'award-审查')
        self.assertEqual(order['blockId'],'award-审查');self.assertIn('award-审查',intent);self.assertNotIn('Library',intent)
        self.assertIn('No cloud or site access',intent)
        with self.assertRaises(SessionError):compile_block_order(other,'other-project','award-审查')

    async def test_lost_native_ack_keeps_typed_order_and_does_not_replay_inference(self):
        self.backend.fail_start=True
        with self.assertRaises(TimeoutError):await self.submit()
        self.content=design(self.scope.project,'other-block')
        result=await self.submit()
        self.assertTrue(result['replayed']);self.assertEqual(result['state'],'starting')
        self.assertEqual(self.backend.request_ids,[self.request])
        self.assertEqual(len([e for e in self.jobs.journal.read(self.scope,self.session)if e['kind']=='work_order_prepared']),1)

    async def test_work_order_history_limit_preserves_prior_orders_and_denies_new_inference(self):
        with patch('server.engineering_work_orders.MAX_SESSION_BYTES',1):
            with self.assertRaisesRegex(SessionError,'storage bound'):await self.submit()
        self.assertEqual(self.backend.request_ids,[])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM engineering_work_orders').fetchone()[0],0)
        await self.submit()
        with patch('server.engineering_work_orders.MAX_REVISIONS',0):
            self.assertTrue((await self.submit())['replayed'])
        self.assertEqual(self.backend.request_ids,[self.request])

    async def test_cross_tenant_order_cannot_read_project_or_native_state(self):
        with self.assertRaises(SessionError):
            await self.orders.start_block(ProjectScope('different-tenant',self.scope.project),self.session,self.request,'loans',self.sha,lambda:self.fail('Unauthorized saved-file read'))
        self.assertEqual(self.backend.request_ids,[])

    async def test_invalid_graph_and_duplicate_block_identity_fail_closed(self):
        value=json.loads(self.content);value['design']['nodes'].append(value['design']['nodes'][0])
        with self.assertRaises(SessionError):compile_block_order(json.dumps(value).encode(),self.scope.project,'loans')
        value['design']['nodes']=['not-a-block']
        with self.assertRaises(ValueError):compile_block_order(json.dumps(value).encode(),self.scope.project,'loans')
