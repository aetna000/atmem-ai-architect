"""Adapter contract tests; these doubles do not qualify native sandbox enforcement."""
import asyncio
import copy
from pathlib import Path
import tempfile
import unittest

from server.codex_engineering_backend import CodexEngineeringBackend
from server.engineering_sessions import ModelSelection, ProjectScope, SessionError


class Client:
    def __init__(self, root):
        self.root = root
        self.requests = []
        self.events = asyncio.Queue()
        self.closed = False
        self.mutate = lambda result: None
        self.history = []

    async def start(self):
        pass

    async def request(self, method, params):
        self.requests.append((method, copy.deepcopy(params)))
        if method in {'thread/start', 'thread/resume'}:
            result = {'cwd': str(self.root), 'model': 'selected-model',
                      'reasoningEffort': 'high', 'approvalPolicy': 'never',
                      'sandbox': CodexEngineeringBackend._policy(self.root),
                      'thread': {'id': params.get('threadId', 'native-thread')}}
            if params.get('permissions'):
                result.update(activePermissionProfile={'id':params['permissions']},runtimeWorkspaceRoots=[str(self.root)])
                result['sandbox']['networkAccess']=True
            self.mutate(result)
            return result
        if method == 'turn/start':
            return {'turn': {'id': 'native-turn', 'status': 'inProgress'}}
        if method == 'thread/turns/list':
            return self.history.pop(0)
        return {}

    async def notification(self):
        return await self.events.get()

    async def close(self):
        self.closed = True

    async def verify_worker_tools(self,expected_profile):
        self.verified_profile=expected_profile


class CodexBackendTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.scope = ProjectScope('tenant-one', 'project-one')
        self.selection = ModelSelection('selected-model', 'high')
        self.clients = []

        def factory(root):
            client = Client(root)
            self.clients.append(client)
            return client

        self.backend = CodexEngineeringBackend(
            {(self.scope, 'workspace-one'): self.root}, client_factory=factory)

    async def asyncTearDown(self):
        await self.backend.close()
        self.temp.cleanup()

    async def create(self):
        return await self.backend.create(self.scope, 'workspace-one', self.selection)

    async def test_scope_is_checked_before_starting_any_process(self):
        other = ProjectScope('tenant-two', 'project-one')
        for scope, workspace in [(other, 'workspace-one'), (self.scope, '/tmp')]:
            with self.assertRaises(SessionError):
                await self.backend.create(scope, workspace, self.selection)
        self.assertFalse(self.clients)

    async def test_native_response_must_confirm_model_effort_and_write_boundary(self):
        mutations = [
            lambda r: r.update(model='cheaper-model'),
            lambda r: r.update(reasoningEffort='low'),
            lambda r: r.update(cwd='/other-project'),
            lambda r: r.update(approvalPolicy='on-request'),
            lambda r: r['sandbox'].update(type='dangerFullAccess'),
            lambda r: r['sandbox'].update(networkAccess=True),
            lambda r: r['sandbox'].update(excludeSlashTmp=False),
            lambda r: r['sandbox'].update(excludeTmpdirEnvVar=False),
            lambda r: r['sandbox'].update(writableRoots=[str(self.root), '/other-project']),
            lambda r: r.update(thread={'id': ''}),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                def factory(root):
                    client = Client(root)
                    client.mutate = mutate
                    self.clients.append(client)
                    return client
                self.backend.client_factory = factory
                with self.assertRaises(SessionError):
                    await self.create()
                self.assertTrue(self.clients[-1].closed)
                self.assertFalse(self.backend.clients)

    async def test_turn_preserves_complete_intent_and_selected_policy(self):
        handle = await self.create()
        text = 'Preserve the existing website.\n' + 'Requirement. ' * 1000
        turn = await self.backend.start(self.scope, handle, text, self.selection)
        self.assertEqual(turn, 'native-turn')
        method, params = self.clients[0].requests[-1]
        self.assertEqual(method, 'turn/start')
        self.assertEqual(params['input'], [{'type': 'text', 'text': text}])
        self.assertEqual(params['effort'], 'high')
        self.assertEqual(params['model'], self.selection.model)
        self.assertEqual(params['sandboxPolicy'], self.backend._policy(self.root))

    async def test_foreign_scope_and_changed_model_cannot_access_live_thread(self):
        handle = await self.create()
        before = len(self.clients[0].requests)
        for scope, selection in [
            (ProjectScope('tenant-two', 'project-one'), self.selection),
            (self.scope, ModelSelection('different-model', 'high')),
        ]:
            with self.assertRaises(SessionError):
                await self.backend.start(scope, handle, 'Build', selection)
        self.assertEqual(len(self.clients[0].requests), before)

    async def test_worker_restart_reasserts_exact_selection_and_policy(self):
        handle = await self.create()
        await self.backend.close()
        await self.backend.resume(self.scope, handle, 'workspace-one', self.selection)
        method, params = self.clients[-1].requests[-1]
        self.assertEqual(method, 'thread/resume')
        self.assertEqual(params['threadId'], handle)
        self.assertTrue(params['excludeTurns'])
        self.assertEqual(params['config']['model_reasoning_effort'], 'high')
        self.assertFalse(params['config']['sandbox_workspace_write.network_access'])
        self.assertTrue(params['config']['sandbox_workspace_write.exclude_slash_tmp'])
        self.assertTrue(params['config']['sandbox_workspace_write.exclude_tmpdir_env_var'])

    async def test_resuming_a_different_thread_fails_and_closes_the_client(self):
        def factory(root):
            client = Client(root)
            client.mutate = lambda r: r.update(thread={'id': 'another-thread'})
            self.clients.append(client)
            return client
        self.backend.client_factory = factory
        with self.assertRaises(SessionError):
            await self.backend.resume(self.scope, 'native-thread', 'workspace-one', self.selection)
        self.assertTrue(self.clients[0].closed)
        self.assertFalse(self.backend.clients)

    async def test_terminal_events_require_matching_thread_and_known_status(self):
        handle = await self.create()
        for params in [
            {'threadId': 'foreign-thread', 'turn': {'id': 'turn', 'status': 'completed'}},
            {'threadId': handle, 'turn': {'id': 'turn', 'status': 'unknown'}},
        ]:
            await self.clients[0].events.put({'method': 'turn/completed', 'params': params})
            with self.assertRaises(SessionError):
                await self.backend.next_event(self.scope, handle)

    async def test_message_and_tool_events_are_progress_not_validation(self):
        handle = await self.create()
        messages = [
            ('item/agentMessage/delta', {'turnId': 'turn', 'delta': 'All tests passed'}, 'message'),
            ('item/completed', {'turnId': 'turn', 'item': {'type': 'commandExecution'}}, 'progress'),
            ('turn/completed', {'turn': {'id': 'turn', 'status': 'completed'}}, 'completed'),
        ]
        for method, params, expected in messages:
            await self.clients[0].events.put({'method': method, 'params': {'threadId': handle, **params}})
            event = await self.backend.next_event(self.scope, handle)
            self.assertEqual(event.kind, expected)
            self.assertFalse(hasattr(event, 'validation'))

    async def test_steering_and_interrupt_use_the_confirmed_turn(self):
        handle = await self.create()
        await self.backend.steer(self.scope, handle, 'active-turn', 'Keep the data in Australia')
        await self.backend.interrupt(self.scope, handle, 'active-turn')
        steer, interrupt = self.clients[0].requests[-2:]
        self.assertEqual(steer[1]['expectedTurnId'], 'active-turn')
        self.assertEqual(interrupt[1]['turnId'], 'active-turn')
        self.assertEqual(steer[1]['input'][0]['text'], 'Keep the data in Australia')

    async def test_recovery_pages_to_exact_turn_without_loading_source_content(self):
        handle = await self.create()
        self.clients[0].history = [
            {'data': [{'id': 'different-turn', 'status': 'completed'}], 'nextCursor': 'older'},
            {'data': [{'id': 'owned-turn', 'status': 'interrupted'}], 'nextCursor': None},
        ]
        event = await self.backend.observe(self.scope, handle, 'owned-turn')
        self.assertEqual(event.turn, 'owned-turn')
        self.assertEqual(event.kind, 'interrupted')
        params = self.clients[0].requests[-1][1]
        self.assertEqual(params['cursor'], 'older')
        self.assertEqual(params['itemsView'], 'notLoaded')

    async def test_live_recovered_turn_remains_active(self):
        handle = await self.create()
        self.clients[0].history = [{'data': [{'id': 'owned-turn', 'status': 'inProgress'}]}]
        self.assertIsNone(await self.backend.observe(self.scope, handle, 'owned-turn'))

    async def test_start_request_identity_is_sent_unchanged_for_recovery(self):
        handle = await self.create()
        request_id = '019c1122-3344-7555-8666-778899001122'
        await self.backend.start(self.scope,handle,'Implement',self.selection,request_id=request_id)
        self.assertEqual(self.clients[0].requests[-1][1]['clientUserMessageId'],request_id)

    async def test_named_worker_policy_is_not_mixed_with_legacy_permissions(self):
        self.backend.permission_profile='qualified-worker'
        handle=await self.create()
        params=self.clients[0].requests[0][1]
        self.assertEqual(params['permissions'],'qualified-worker');self.assertNotIn('sandbox',params)
        self.assertEqual(params['config'],{'model_reasoning_effort':'high'})
        self.assertEqual(self.clients[0].verified_profile,'qualified-worker')
        await self.backend.start(self.scope,handle,'Implement',self.selection)
        self.assertEqual(self.clients[0].requests[-1][1]['permissions'],'qualified-worker')
        self.assertNotIn('sandboxPolicy',self.clients[0].requests[-1][1])

    async def test_named_worker_policy_rejects_unconfirmed_profile_or_extra_runtime_roots(self):
        self.backend.permission_profile='qualified-worker'
        for mutate in [lambda r:r.update(activePermissionProfile={'id':'broad-default'}),lambda r:r.update(runtimeWorkspaceRoots=[str(self.root),'/other-project'])]:
            def factory(root):
                client=Client(root);client.mutate=mutate;self.clients.append(client);return client
            self.backend.client_factory=factory
            with self.assertRaises(SessionError):await self.create()
            self.assertTrue(self.clients[-1].closed)

    async def test_lost_start_is_matched_by_client_identity_not_similar_content(self):
        handle = await self.create()
        self.clients[0].history = [{'data': [
            {'id':'other-turn','status':'completed','items':[{'type':'userMessage','clientId':'other-request','content':[{'type':'text','text':'Same intent'}]}]},
            {'id':'owned-turn','status':'completed','items':[{'type':'userMessage','clientId':'our-request','content':[]}]},
        ]}]
        recovered=await self.backend.recover_start(self.scope,handle,'our-request')
        self.assertEqual(recovered.turn,'owned-turn');self.assertEqual(recovered.status,'completed')
        self.assertEqual(self.clients[0].requests[-1][1]['itemsView'],'summary')

    async def test_ambiguous_start_identity_is_not_recovered(self):
        handle = await self.create()
        self.clients[0].history = [{'data': [
            {'id':turn,'status':'completed','items':[{'type':'userMessage','clientId':'our-request'}]}
            for turn in ['first','duplicate']]}]
        with self.assertRaises(SessionError):await self.backend.recover_start(self.scope,handle,'our-request')

    async def test_absent_client_identity_does_not_authorize_replay(self):
        handle = await self.create()
        self.clients[0].history = [{'data': [{'id':'old-turn','status':'completed','items':[{'type':'userMessage','content':[]}]}]}]
        self.assertIsNone(await self.backend.recover_start(self.scope,handle,'our-request'))

    async def test_missing_malformed_or_cyclic_history_is_uncertain(self):
        handle = await self.create()
        for history in [
            [{'data': []}],
            [{'data': 'invalid'}],
            [{'data': [{'id': 'owned-turn', 'status': 'unknown'}]}],
            [{'data': [], 'nextCursor': 'same'}, {'data': [], 'nextCursor': 'same'}],
        ]:
            self.clients[0].history = history
            with self.assertRaises(SessionError):
                await self.backend.observe(self.scope, handle, 'owned-turn')
