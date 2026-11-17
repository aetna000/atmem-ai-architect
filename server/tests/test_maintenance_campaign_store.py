"""Campaign ownership, CAS, fencing, historical portability and API boundary tests."""
import copy
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from server.app import app, TOKEN
from server.maintenance.campaigns import CampaignService
from server.maintenance.store import Store, Conflict
from server.tests.test_maintenance_graph import frozen_campaign
from server import maintenance_routes as local, maintenance_campaign_routes as routes


class CampaignStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'maintenance.sqlite')
        self.service = CampaignService(self.store, None)
        self.addCleanup(self.service.close)
        self.snapshots, self.roots, self.bindings = frozen_campaign()
        self.value = self.service.create('tenant-one', 'project-one', 'actor-one', self.snapshots, self.roots, [])

    def test_binding_cas_cross_tenant_and_import_historical(self):
        ident = self.value.id
        with self.assertRaises(KeyError):
            self.service.get('tenant-two', ident)
        bound = self.service.bind('tenant-one', ident, 0, self.bindings)
        self.assertFalse(bound.graph['unknowns'])
        with self.assertRaises(Conflict):
            self.service.bind('tenant-one', ident, 0, self.bindings)
        exported = self.service.export('tenant-one', ident)
        imported = self.service.import_record('tenant-two', 'project-two', 'actor-two', exported)
        self.assertEqual(imported.status, 'historical')
        self.assertNotEqual(imported.id, ident)
        self.assertIsNone(imported.requestKey)
        self.assertEqual(imported.snapshots, bound.snapshots)
        corrupt = copy.deepcopy(exported)
        corrupt['aggregate']['snapshots'][0]['files'][0]['text'] += '# altered'
        with self.assertRaisesRegex(ValueError, 'integrity'):
            self.service.import_record('tenant-two', 'project-two', 'actor-two', corrupt)

    def test_ready_import_demotes_nested_receipts_and_cannot_restore_release_authority(self):
        value = self.value
        value.status = 'local_release_checked'
        value.result = {'status': 'local_release_checked', 'checks': [{'status': 'passed'}],
                        'moduleReceipts': [{'status': 'passed'}], 'releaseChecks': [{'status': 'passed'}]}
        value.history = [{'status': 'ready_for_review', 'checks': [{'status': 'passed'}]}]
        self.service.store.put(value, 0)
        exported = self.service.export('tenant-one', value.id)
        imported = self.service.import_record('tenant-two', 'project-two', 'actor-two', exported)
        self.assertEqual(imported.status, 'historical')
        self.assertEqual(imported.result['status'], 'historical')
        self.assertEqual(imported.history[0]['checks'][0]['status'], 'historical')
        self.assertTrue(all(imported.result[key][0]['status'] == 'historical'
                            for key in ['checks', 'moduleReceipts', 'releaseChecks']))
        self.assertEqual(exported['aggregate']['result']['checks'][0]['status'], 'passed')
        from types import SimpleNamespace
        self.service.worker = SimpleNamespace(identity='a' * 64)
        with self.assertRaisesRegex(Conflict, 'Prepare'):
            self.service.start('tenant-two', imported.id, 0, imported.graph['digest'], 'request-new', True,
                               release={'source': 'unused'})

    def test_expired_executor_cannot_commit_or_release_new_lease(self):
        value = self.value
        lease = self.service.store.acquire('tenant-one', value.id, 1200)
        value.status = 'checking'
        current = self.service.store.put(value, 0, lease=lease)
        # Another process's live lease is respected, never replayed/fenced by a read.
        self.assertEqual(self.service.get('tenant-one', value.id).status, 'checking')
        self.service.store.fence('tenant-one', value.id)
        with self.assertRaises(Conflict):
            self.service.store.put(current, current.revision, lease=lease)
        blocked = self.service.get('tenant-one', value.id)
        self.assertEqual(blocked.phase, 'execution_unknown')
        new_lease = self.service.store.acquire('tenant-one', value.id, 1200)
        self.service.store.release('tenant-one', value.id, lease)
        self.assertTrue(self.service.store.live('tenant-one', value.id))
        self.service.store.release('tenant-one', value.id, new_lease)

    def test_cancel_fences_late_results(self):
        lease = self.service.store.acquire('tenant-one', self.value.id, 1200)
        self.value.status = 'checking'
        current = self.service.store.put(self.value, 0, lease=lease)
        event = threading.Event()
        self.service.running[current.id] = event
        canceled = self.service.cancel('tenant-one', current.id, current.revision)
        self.assertTrue(event.is_set())
        self.assertEqual(canceled.status, 'canceled')
        with self.assertRaises(Conflict):
            self.service.store.put(current, current.revision, lease=lease)
        self.service.running.clear()


class CampaignRouteTests(unittest.TestCase):
    def test_local_auth_no_paths_no_unqualified_execution_and_export_import(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(local, 'home', return_value=Path(folder)), patch.object(local, 'setting', return_value=None):
            routes.close(); local.close()
            try:
                client = TestClient(app)
                headers = {'Authorization': 'Bearer ' + TOKEN}
                files = {'main.tf': 'terraform { required_providers { aws = { source = "hashicorp/aws", version = "5.100.0" } } }'}
                payload = {'projectId': 'project-one', 'repositories': [{'repositoryId': 'repository-one', 'files': files, 'roots': {'root-one': '.'}}]}
                self.assertEqual(client.post('/api/maintenance/campaigns', json=payload).status_code, 401)
                self.assertEqual(client.post('/api/maintenance/campaigns', json={**payload, 'path': '/private'}, headers=headers).status_code, 422)
                created = client.post('/api/maintenance/campaigns', json=payload, headers=headers)
                self.assertEqual(created.status_code, 200, created.text)
                value = created.json()['aggregate']
                started = client.post('/api/maintenance/campaigns/' + value['id'] + '/prepare', headers={**headers, 'Idempotency-Key': 'request-one'},
                                      json={'expectedProjectRevision': 0, 'graphDigest': value['graph']['digest'], 'computeConfirmed': True, 'module': 'root-one'})
                self.assertEqual(started.status_code, 503)
                exported = client.get('/api/maintenance/campaigns/' + value['id'] + '/export').json()
                imported = client.post('/api/maintenance/campaigns/import', headers=headers, json={'projectId': 'project-two', 'section': exported})
                self.assertEqual(imported.status_code, 200, imported.text)
                self.assertEqual(imported.json()['aggregate']['status'], 'historical')
            finally:
                routes.close(); local.close()
