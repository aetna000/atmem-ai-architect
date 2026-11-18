from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from server.app import app, TOKEN
from server import maintenance_routes as routes

ROOT = Path(__file__).resolve().parents[2]


class MaintenanceRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = patch.object(routes, 'home', return_value=Path(self.temp.name))
        self.setting = patch.object(routes, 'setting', return_value=None)
        self.home.start()
        self.setting.start()
        self.addCleanup(self.home.stop)
        self.addCleanup(self.setting.stop)
        self.addCleanup(routes.close)
        self.client = TestClient(app)
        self.headers = {'Authorization': f'Bearer {TOKEN}'}
        self.source = (ROOT / 'tests/maintenance/fixtures/baseline/main.tf').read_text()
        self.payload = {'projectId': 'project-001', 'name': 'Migration', 'files': {'main.tf': self.source}}

    def test_authentication_origin_and_arbitrary_host_paths_denied(self):
        self.assertEqual(self.client.post('/api/maintenance/projects', json=self.payload).status_code, 401)
        for extra in [{'root': '/private'}, {'tenantId': 'other-tenant'}, {'command': 'terraform apply'}]:
            self.assertEqual(self.client.post('/api/maintenance/projects', json={**self.payload, **extra}, headers=self.headers).status_code, 422)
        self.assertEqual(self.client.post('/api/maintenance/projects', json=self.payload, headers={**self.headers, 'Origin': 'https://evil.invalid'}).status_code, 403)

    def test_inventory_export_and_import_are_permission_free(self):
        created = self.client.post('/api/maintenance/projects', json=self.payload, headers=self.headers)
        self.assertEqual(created.status_code, 200, created.text)
        inventory = self.client.post('/api/maintenance/projects/project-001/inventory', json={'expectedProjectRevision': 0}, headers=self.headers)
        self.assertEqual(inventory.status_code, 200, inventory.text)
        self.assertEqual(inventory.json()['inventory']['resources'][0]['type'], 'aws_batch_job_queue')
        exported = self.client.get('/api/maintenance/projects/project-001/export').json()
        imported = self.client.post('/api/maintenance/projects/import', json={'projectId': 'project-002', 'section': exported}, headers=self.headers)
        self.assertEqual(imported.status_code, 200, imported.text)
        self.assertTrue(imported.json()['aggregate']['imported'])
        self.assertEqual(imported.json()['aggregate']['tenantId'], 'local-owner')
        self.assertEqual(self.client.get('/api/maintenance/projects/missing-001').status_code, 404)

    def test_missing_worker_fails_closed_instead_of_host_subprocess(self):
        created = self.client.post('/api/maintenance/projects', json=self.payload, headers=self.headers).json()
        value = {'expectedProjectRevision': 0, 'sourceDigest': created['aggregate']['snapshots'][0]['treeDigest'],
                 'recipeDigest': created['recipeDigest'], 'computeConfirmed': True}
        result = self.client.post('/api/maintenance/projects/project-001/prepare', json=value,
                                  headers={**self.headers, 'Idempotency-Key': 'request-001'})
        self.assertEqual(result.status_code, 503)
        self.assertEqual(self.client.get('/api/maintenance/capabilities').json()['status'], 'setup_required')

    def test_large_source_crosses_old_250kb_limit_without_truncation(self):
        payload = {**self.payload, 'files': {'main.tf': self.source + '\n#' + 'a' * 260_000}}
        result = self.client.post('/api/maintenance/projects', json=payload, headers=self.headers)
        self.assertEqual(result.status_code, 200, result.text[:200])
        self.assertEqual(result.json()['aggregate']['snapshots'][0]['files'][0]['text'], payload['files']['main.tf'])
