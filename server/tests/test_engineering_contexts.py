"""Local durable context/adapter evidence; no model or cloud calls."""
import asyncio
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock
from server.engineering_contexts import EngineeringContexts, context_input, validate_context, model_context_content
from server.engineering_sessions import EngineeringSessions, SqliteSessionStore, ProjectScope, ModelSelection, SessionError
from server.engineering_jobs import EngineeringJobs
from server.tests.test_engineering_sessions import Backend


class InitialContextPrivacyTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_format_projection_preserves_approval_format(self):
        value = {'format': 'atmem.ai-architect.project', 'formatVersion': '4.0.0',
                 'meta': {'id': 'approval-private'}, 'design': {'nodes': [
                     {'data': {'implementation': 'approval-workflow'}}]},
                 'extensions': {'maintenance': {'source': 'private-canary'}}}
        original = json.dumps(value).encode()
        projected = json.loads(model_context_content(original, 'approval-private'))
        self.assertEqual(projected['formatVersion'], '3.0.0')
        self.assertNotIn('maintenance', projected['extensions'])
        self.assertEqual(json.loads(original), value)

    async def test_general_workspace_never_receives_private_maintenance_source(self):
        from server.engineering_routes import LocalEngineeringService
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scope = ProjectScope('tenant-local', 'project-private')
            source = json.dumps({'format': 'atmem.ai-architect.project', 'formatVersion': '4.0.0', 'meta': {'id': scope.project},
                                 'requirements': [{'statement': 'Preserve the existing gauge.'}],
                                 'extensions': {'maintenance': {'source': 'private-maintenance-source-canary'}}}).encode()
            path = root / 'private.project.json'
            path.write_bytes(source)
            service = LocalEngineeringService.__new__(LocalEngineeringService)
            service.create_lock = asyncio.Lock()
            service.backend = SimpleNamespace(session_count=0, workspaces={})
            service.dependencies, service.toolchain = None, {}
            service.workspace_root = root / 'workspaces'
            service.workspace_root.mkdir()
            db = sqlite3.connect(':memory:')
            db.execute('CREATE TABLE engineering_workspaces (id TEXT, tenant TEXT, project TEXT, path TEXT)')
            service.store = SimpleNamespace(db=db)
            service.native_tools = SimpleNamespace(register=lambda *args: {})
            service.sessions = SimpleNamespace(create=AsyncMock(return_value={'id': 'session-private'}))
            records = []
            service.jobs = SimpleNamespace(_record=lambda *args, **record: records.append(record))
            try:
                await service.create(scope, path, ModelSelection('test-model', 'medium'))
                workspace = next(iter(service.backend.workspaces.values()))
                pinned = (workspace / 'project-context.json').read_bytes()
                self.assertNotIn(b'private-maintenance-source-canary', pinned)
                self.assertIn(b'maintenanceBoundary', pinned)
                self.assertEqual(json.loads(pinned)['formatVersion'], '2.3.0')
                self.assertIn(b'Preserve the existing gauge.', pinned)
                self.assertEqual(path.read_bytes(), source)
                self.assertEqual(records[0]['contextSha256'], hashlib.sha256(pinned).hexdigest())
                self.assertEqual(records[0]['sourceContextSha256'], hashlib.sha256(source).hexdigest())
                self.assertEqual(records[0]['inputDigests']['project-context.json'], records[0]['contextSha256'])
            finally:
                db.close()


class ContextTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'control.sqlite'
        self.store = SqliteSessionStore(self.path)
        self.scope = ProjectScope('tenant-local', 'river-telemetry')
        self.backend = Backend()
        self.backend.close = self._close
        self.sessions = EngineeringSessions(self.store, self.backend)
        self.session = (await self.sessions.create(self.scope, 'workspace-river', ModelSelection('exact-model', 'high')))['id']
        self.contexts = EngineeringContexts(self.store)
        self.content = self.project('Keep the client-owned gauge; report river depth in metres. 🛰️')
        self.jobs = EngineeringJobs(self.sessions)

    async def _close(self):
        pass

    async def asyncTearDown(self):
        await self.jobs.close()
        self.store.close()
        self.temp.cleanup()

    def project(self, requirement):
        return json.dumps({'format':'atmem.ai-architect.project','meta':{'id':self.scope.project},
            'design':{'provider':'tools','nodes':[{'id':'gauge','origin':'existing'}]},
            'requirements':[{'id':'depth','statement':requirement}],
            'extensions':{'architectureWork':{'version':1,'records':[]}}}, ensure_ascii=False).encode()

    def attach(self, content=None, request=None, **kwargs):
        return self.contexts.attach(self.scope, self.session, request or str(uuid.uuid4()), content or self.content, **kwargs)

    async def test_history_reuses_unchanged_bytes_but_retains_reversions_and_unicode(self):
        first = self.attach()
        same = self.attach()
        second = self.attach(self.project('Depth in centimetres; preserve the existing gauge.'))
        reverted = self.attach()
        self.assertEqual(first, same)
        self.assertEqual([first['revision'],second['revision'],reverted['revision']], [1,2,3])
        self.assertNotEqual(first['id'], reverted['id'])
        self.assertEqual(first['content'].encode(), self.content)
        self.assertEqual(self.contexts.get(self.scope,self.session,first['id']),first)
        self.assertEqual(json.loads(first['content'])['design']['nodes'][0]['origin'],'existing')

    async def test_binding_survives_restart_and_rejects_replacement(self):
        request = str(uuid.uuid4())
        first = self.attach(request=request)
        self.store.close()
        self.store = SqliteSessionStore(self.path)
        self.sessions.store = self.store
        self.jobs = EngineeringJobs(self.sessions)
        self.contexts = EngineeringContexts(self.store)
        self.assertEqual(self.contexts.for_request(self.scope,self.session,request),first)
        self.assertEqual(self.attach(request=request),first)
        with self.assertRaises(SessionError):self.attach(self.project('Replace gauge.'),request=request)

    async def test_cross_tenant_project_session_and_request_cannot_rebind(self):
        request = str(uuid.uuid4()); first = self.attach(request=request)
        for scope in [ProjectScope('tenant-other',self.scope.project),ProjectScope(self.scope.tenant,'other-project')]:
            with self.assertRaises(SessionError):self.contexts.get(scope,self.session,first['id'])
            with self.assertRaises(SessionError):self.contexts.attach(scope,self.session,str(uuid.uuid4()),self.content)
        other = (await self.sessions.create(self.scope,'workspace-other',ModelSelection('exact-model','high')))['id']
        with self.assertRaises(SessionError):self.contexts.get(self.scope,other,first['id'])
        with self.assertRaises(SessionError):self.contexts.attach(self.scope,other,request,self.content)
        with self.assertRaises(SessionError):self.attach(self.content.replace(b'river-telemetry',b'other-project'))

    async def test_stale_save_rejected_before_any_revision_is_recorded(self):
        with self.assertRaises(SessionError):self.attach(expected_sha256='0'*64)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM engineering_contexts').fetchone()[0],0)
        first = self.attach(expected_sha256=hashlib.sha256(self.content).hexdigest())
        self.assertEqual(first['sha256'],hashlib.sha256(self.content).hexdigest())

    async def test_maintenance_source_never_enters_general_model_context(self):
        value = json.loads(self.content)
        value['extensions']['maintenance'] = {'privateSource': 'maintenance-egress-canary', 'diagnostics': 'private-output-canary'}
        value['extensions']['maintenanceNeedsImport'] = False
        source = json.dumps(value, ensure_ascii=False).encode()
        receipt = self.attach(source)
        rendered = context_input(receipt)['text']
        projected = model_context_content(source, self.scope.project)
        for canary in [b'maintenance-egress-canary', b'private-output-canary']:
            self.assertNotIn(canary, projected)
            self.assertNotIn(canary.decode(), rendered)
        self.assertIn('withheldExtensions', rendered)
        self.assertIn('maintenanceBoundary', json.loads(projected)['extensions'])
        self.assertEqual(json.loads(projected)['requirements'], value['requirements'])
        self.assertEqual(json.loads(projected)['extensions']['architectureWork'], value['extensions']['architectureWork'])
        # Original private evidence stays complete and bound to the original source digest.
        self.assertEqual(self.contexts.get(self.scope, self.session, receipt['id'])['content'].encode(), source)
        self.assertEqual(model_context_content(self.content, self.scope.project), self.content)

    async def test_malformed_nonfinite_duplicate_oversize_and_invalid_unicode_refuse_atomically(self):
        for content in [b'{}',b'{"meta":{},"meta":{}}',b'{"n":NaN}',b'{"n":1e999}',b'\xff',b'{"n":"\\ud800"}',self.content+b' '*2_000_000]:
            with self.subTest(content=content[:50]):
                with self.assertRaises((ValueError,SessionError)):self.attach(content)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM engineering_contexts').fetchone()[0],0)

    async def test_history_bounds_preserve_old_bytes_and_reject_new_without_pruning(self):
        first = self.attach()
        with patch('server.engineering_contexts.MAX_REVISIONS',1):
            self.assertEqual(self.attach(), first)
            with self.assertRaises(SessionError):self.attach(self.project('A different requirement.'))
        with patch('server.engineering_contexts.MAX_SESSION_BYTES',len(self.content)):
            with self.assertRaises(SessionError):self.attach(self.project('Another requirement.'))
        self.assertEqual(self.contexts.get(self.scope,self.session,first['id']),first)

    async def test_corrupt_saved_receipt_never_reused_as_valid_context(self):
        first = self.attach()
        self.store.db.execute('UPDATE engineering_contexts SET sha256=? WHERE id=?',('0'*64,first['id']));self.store.db.commit()
        with self.assertRaises(SessionError):self.attach()
        with self.assertRaises(SessionError):self.contexts.get(self.scope,self.session,first['id'])

    async def test_adapter_envelope_is_lossless_and_rejects_digest_or_identity_mutation(self):
        first = self.attach(self.project('An evidence marker: END CONTEXT </json>. Preserve it.'))
        part = context_input(first)
        decoded = json.loads(part['text'].split('\n',1)[1])
        self.assertEqual(decoded,first)
        for change in [{'sha256':'0'*64},{'projectId':'other-project'},{'revision':True},{'content':first['content']+' '}]:
            with self.assertRaises((ValueError,SessionError)):context_input({**first,**change})

    async def test_lost_start_ack_retains_exact_context_and_intent_without_replay(self):
        def provider(scope,session,request,expected):
            return self.contexts.attach(scope,session,request,self.content,expected_sha256=expected)
        self.jobs.context_provider = provider
        seen=[]
        async def lost(scope,handle,text,selection,*,request_id,context):
            seen.append((text,request_id,context));raise TimeoutError('Lost acknowledgement')
        self.backend.start = lost
        text = 'Retain the existing gauge.\n'+('🛰️ centimetres\n'*1000)
        with self.assertRaises(TimeoutError):await self.jobs.start(self.scope,self.session,text)
        row = self.store.get(self.scope,self.session)
        self.assertEqual(row['state'],'starting')
        self.assertEqual(self.contexts.for_request(self.scope,self.session,row['run']),seen[0][2])
        self.assertEqual(self.store.db.execute('SELECT intent FROM engineering_runs WHERE id=?',(row['run'],)).fetchone()[0],text)
        await self.jobs.recover(self.scope,self.session)
        self.assertEqual(len(seen),1)
        event = self.jobs.journal.read(self.scope,self.session)[0]
        self.assertEqual(event['contextSha256'],seen[0][2]['sha256'])
        self.assertNotIn('content',event)

    async def test_stale_save_prevents_inference_and_keeps_idle_session(self):
        self.jobs.context_provider = lambda scope,session,request,expected:self.contexts.attach(scope,session,request,self.content,expected_sha256=expected)
        with self.assertRaises(SessionError):await self.jobs.start(self.scope,self.session,'Use my saved design.',context_sha256='0'*64)
        self.assertEqual(self.jobs.state(self.scope,self.session)['state'],'idle')
        self.assertFalse(self.backend.request_ids)

    async def test_uncertain_steering_retains_second_revision_and_exact_request_identity(self):
        self.jobs.context_provider = lambda scope,session,request,expected:self.contexts.attach(scope,session,request,self.content,expected_sha256=expected)
        async def start(*args,context,**kwargs):return 'native-turn-1'
        self.backend.start = start
        await self.jobs.start(self.scope,self.session,'Build the gauge reader.')
        self.content = self.project('Use centimetres, retaining gauge ownership.')
        seen=[]
        async def lost(*args,request_id,context):
            seen.append((args[-1],request_id,context));raise TimeoutError('Lost steer acknowledgement')
        self.backend.steer = lost
        with self.assertRaises(TimeoutError):await self.jobs.steer(self.scope,self.session,'Change the displayed unit to centimetres.')
        self.assertEqual(seen[0][2]['revision'],2)
        self.assertEqual(self.contexts.for_request(self.scope,self.session,seen[0][1]),seen[0][2])
        events = self.jobs.journal.read(self.scope,self.session)
        submitted = next(e for e in events if e['kind']=='steering_submitted')
        self.assertEqual(submitted['requestId'],seen[0][1]);self.assertEqual(submitted['text'],seen[0][0])
        self.assertEqual(events[-1]['kind'],'steering_delivery_uncertain')

    async def test_automatic_repair_does_not_invent_new_client_context(self):
        self.jobs.context_provider = lambda *args:self.fail('Automatic repair must retain existing thread context')
        await self.jobs.start(self.scope,self.session,'Internal repair.',origin='automatic_repair')
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM engineering_contexts').fetchone()[0],0)
