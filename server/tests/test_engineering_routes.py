import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from server.app import app, TOKEN
from server import engineering_routes as routes
from server.engineering_sessions import ProjectScope, SessionError


class EngineeringRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/'projects').mkdir()
        self.project = 'client-project-123'
        self.session = '00000000-0000-0000-0000-000000000001'
        (self.root/'projects'/f'{self.project}.atforma.json').write_text(json.dumps({'format':'atmem.ai-architect.project'}))
        self.home = patch.object(routes,'home',return_value=self.root)
        self.settings = patch.object(routes,'setting',side_effect=lambda name:'1' if name=='ENABLE_ENGINEERING' else None)
        self.home.start();self.settings.start()
        self.client = TestClient(app)
        self.headers = {'Authorization':f'Bearer {TOKEN}'}
        self.payload = {'projectId':self.project,'sessionId':self.session}

    def tearDown(self):
        self.home.stop();self.settings.stop();self.temp.cleanup()

    def test_every_native_endpoint_requires_local_token(self):
        for endpoint in ['create','list','state','events','start','recover','steer','interrupt','capture','download',
                         'artifacts','finalizations','recheck','validators','validation/start','validation/list','validation/plan','validation/get','validation/recover']:
            self.assertEqual(self.client.post('/api/engineering/'+endpoint,json={}).status_code,401)

    def test_recheck_is_project_bound_with_exact_run_and_artifact_only(self):
        run='00000000-0000-0000-0000-000000000002';artifact='00000000-0000-0000-0000-000000000003'
        with patch.object(routes,'service') as service:
            service.return_value.finalization.recheck=AsyncMock(return_value={'state':'checking'})
            payload={**self.payload,'runId':run,'artifactId':artifact}
            result=self.client.post('/api/engineering/recheck',json=payload,headers=self.headers)
            self.assertEqual(result.status_code,200)
            service.return_value.finalization.recheck.assert_awaited_once_with(ProjectScope('local-owner',self.project),self.session,run,artifact)
            for extra in ['command','run_id','maxRepairs','retry','tenant']:
                self.assertEqual(self.client.post('/api/engineering/recheck',json={**payload,extra:'untrusted'},headers=self.headers).status_code,422)

    def test_cross_origin_and_rebinding_denied(self):
        for header in [{'Origin':'https://evil.example'},{'Host':'evil.example'}]:
            self.assertEqual(self.client.post('/api/engineering/list',json={'projectId':self.project},headers={**self.headers,**header}).status_code,403)

    def test_browser_cannot_select_tenant_workspace_native_handle_or_commands(self):
        for field in ['tenant','workspace','handle','command','readRoots']:
            payload = {**self.payload,field:'/private/secret'}
            self.assertEqual(self.client.post('/api/engineering/state',json=payload,headers=self.headers).status_code,422)

    def test_saved_project_resolves_scope_and_exact_selection(self):
        with patch.object(routes,'service') as service:
            service.return_value.create = AsyncMock(return_value={'id':self.session,'model':'exact-model','effort':'high'})
            result = self.client.post('/api/engineering/create',json={'projectId':self.project,'model':'exact-model','effort':'high'},headers=self.headers)
            self.assertEqual(result.status_code,200)
            scope, path, selection = service.return_value.create.call_args.args
            self.assertEqual(scope,ProjectScope('local-owner',self.project))
            self.assertEqual(path,self.root/'projects'/f'{self.project}.atforma.json')
            self.assertEqual((selection.model,selection.effort),('exact-model','high'))

    def test_missing_and_binned_projects_cannot_open_or_read_jobs(self):
        with patch.object(routes,'service') as service:
            for project in ['missing-project','../private','client-project-123/other']:
                result = self.client.post('/api/engineering/state',json={**self.payload,'projectId':project},headers=self.headers)
                self.assertIn(result.status_code,[404,422])
            service.assert_not_called()

    def test_disabled_worker_and_invalid_effort_do_not_start_a_model(self):
        with patch.object(routes,'setting',return_value=None),patch.object(routes,'service') as service:
            self.assertEqual(self.client.post('/api/engineering/list',json={'projectId':self.project},headers=self.headers).status_code,409)
            service.assert_not_called()
        with patch.object(routes,'service') as service:
            self.assertEqual(self.client.post('/api/engineering/create',json={'projectId':self.project,'model':'exact-model','effort':'guess'},headers=self.headers).status_code,422)
            service.return_value.create.assert_not_called()

    def test_native_diagnostics_not_exposed_and_oversized_intent_not_truncated(self):
        with patch.object(routes,'service') as service:
            service.return_value.jobs.start = AsyncMock(side_effect=RuntimeError('/private/secret native-handle'))
            response = self.client.post('/api/engineering/start',json={**self.payload,'text':'Build it.'},headers=self.headers)
            self.assertEqual(response.status_code,409)
            self.assertNotIn('/private',response.text)
            service.return_value.jobs.start.reset_mock()
            self.assertEqual(self.client.post('/api/engineering/start',json={**self.payload,'text':'x'*80001},headers=self.headers).status_code,422)
            service.return_value.jobs.start.assert_not_awaited()

    def test_artifact_download_is_project_bound_and_returns_digest(self):
        with patch.object(routes,'service') as service:
            service.return_value.artifacts.get.return_value = ({'id':self.session,'sha256':'abc123'},b'ZIP')
            response = self.client.post('/api/engineering/download',json={**self.payload,'artifactId':self.session},headers=self.headers)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.content,b'ZIP')
            self.assertEqual(response.headers['x-artifact-sha256'],'abc123')
            self.assertEqual(response.headers['cache-control'],'no-store')
            service.return_value.artifacts.get.side_effect = SessionError('Artifact is unavailable for this project and session')
            self.assertEqual(self.client.post('/api/engineering/download',json={**self.payload,'artifactId':self.session},headers=self.headers).status_code,409)

    def test_validation_accepts_only_registered_id_and_scoped_artifact(self):
        payload={**self.payload,'artifactId':self.session,'validatorId':'python-tests'}
        with patch.object(routes,'service') as service:
            checks=service.return_value.validation_service.return_value
            checks.start=AsyncMock(return_value={'id':self.session,'state':'queued'})
            response=self.client.post('/api/engineering/validation/start',json=payload,headers=self.headers)
            self.assertEqual(response.status_code,200)
            checks.start.assert_awaited_once_with(ProjectScope('local-owner',self.project),self.session,self.session,'python-tests',retry=False)
            checks.start.reset_mock()
            for extra in [{'command':['sh','-c','anything']},{'image':'python:latest'},{'endpoint':'tcp://host:2375'},{'retry':'true'}]:
                self.assertEqual(self.client.post('/api/engineering/validation/start',json={**payload,**extra},headers=self.headers).status_code,422)
            checks.start.assert_not_awaited()

    def test_check_selection_and_finalization_are_scoped_read_only_views(self):
        with patch.object(routes,'service') as service:
            checks=service.return_value.validation_service.return_value
            checks.plan.return_value={'artifactSha256':'bound','acceptance':'not_established_by_file_applicability'}
            response=self.client.post('/api/engineering/validation/plan',json={**self.payload,'artifactId':self.session},headers=self.headers)
            self.assertEqual(response.status_code,200)
            checks.plan.assert_called_once_with(ProjectScope('local-owner',self.project),self.session,self.session)
            checks.start.assert_not_called()
            service.return_value.finalization.list.return_value=[]
            response=self.client.post('/api/engineering/finalizations',json=self.payload,headers=self.headers)
            self.assertEqual(response.json(),{'finalizations':[]})
            service.return_value.finalization.list.assert_called_once_with(ProjectScope('local-owner',self.project),self.session)

    def test_validation_scope_and_worker_errors_never_fall_back_or_leak(self):
        with patch.object(routes,'service') as service:
            service.return_value.store.get.side_effect=SessionError('Unavailable for this project')
            response=self.client.post('/api/engineering/validators',json=self.payload,headers=self.headers)
            self.assertEqual(response.status_code,409);service.return_value.validation_service.assert_not_called()
            service.return_value.store.get.side_effect=None
            checks=service.return_value.validation_service.return_value
            checks.start=AsyncMock(side_effect=RuntimeError('/private/daemon/credential'))
            response=self.client.post('/api/engineering/validation/start',json={**self.payload,'artifactId':self.session,'validatorId':'python-tests'},headers=self.headers)
            self.assertEqual(response.status_code,409);self.assertNotIn('/private',response.text)
