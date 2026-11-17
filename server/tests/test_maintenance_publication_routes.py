"""Local publication API with fake GitHub only; default gate and exact scopes enforced."""
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from server.app import app, TOKEN
from server import maintenance_publication_routes as routes
from server.tests import test_maintenance_publication_protocol as fixtures


class PublicationRouteTests(unittest.TestCase):
    setUp = fixtures.PublicationProtocolTests.setUp

    def test_default_gate_stays_closed_and_auth_rejects_unknown_commands(self):
        client = TestClient(app)
        headers = {'Authorization': 'Bearer ' + TOKEN}
        with patch.object(routes, 'setting', return_value=None):
            self.assertFalse(client.get('/api/maintenance/github/capabilities').json()['enabled'])
            self.assertEqual(client.get('/api/maintenance/github/connections', params={'projectId': 'project-one'}).status_code, 503)
        payload = {'projectId': 'project-one', 'campaignId': self.value.id, 'wave': 'module', 'targets': self.targets}
        path = '/api/maintenance/github/campaigns/' + self.value.id + '/preview'
        self.assertEqual(client.post(path, json=payload).status_code, 401)
        self.assertEqual(client.post(path, json=payload, headers={**headers, 'Origin': 'https://untrusted.invalid'}).status_code, 403)
        for field in ['token', 'command', 'tenantId', 'path']:
            self.assertEqual(client.post(path, json={**payload, field: 'unexpected'}, headers=headers).status_code, 422)
        self.assertFalse(self.remote.writes)

    def test_preview_confirmation_async_publication_idempotency_and_foreign_project(self):
        service = routes.PublicationService(self.service, self.broker)
        self.addCleanup(service.close)
        client = TestClient(app);headers = {'Authorization': 'Bearer ' + TOKEN}
        with patch.object(routes, 'service', return_value=service), patch.object(routes.local, 'TENANT', 'tenant-one'):
            payload = {'projectId': 'project-one', 'campaignId': self.value.id, 'wave': 'module', 'targets': self.targets}
            response = client.post('/api/maintenance/github/campaigns/' + self.value.id + '/preview', json=payload, headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
            preview = response.json();self.assertFalse(self.remote.writes)
            endpoint = '/api/maintenance/github/previews/' + preview['id']
            refused = client.post(endpoint + '/authorize', headers=headers,
                json={'projectId': 'project-one', 'previewDigest': preview['digest'], 'automationAccepted': False})
            self.assertEqual(refused.status_code, 409)
            granted = client.post(endpoint + '/authorize', headers=headers,
                json={'projectId': 'project-one', 'previewDigest': preview['digest'], 'automationAccepted': True})
            self.assertEqual(granted.status_code, 200, granted.text)
            body = {'projectId': 'project-one', 'previewDigest': preview['digest'], 'authorizationId': granted.json()['id']}
            accepted = client.post(endpoint + '/publish', headers={**headers, 'Idempotency-Key': 'request-publication'}, json=body)
            self.assertEqual(accepted.status_code, 202, accepted.text)
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                status = client.get(endpoint, params={'projectId': 'project-one'}).json()
                if status['status'] not in {'queued', 'running'}:break
                time.sleep(.05)
            self.assertEqual(status['status'], 'published_proposals', status)
            before = len(self.remote.writes)
            duplicate = client.post(endpoint + '/publish', headers={**headers, 'Idempotency-Key': 'request-publication'}, json=body)
            self.assertEqual(duplicate.status_code, 202, duplicate.text)
            self.assertEqual(len(self.remote.writes), before)
            conflict = client.post(endpoint + '/publish', headers={**headers, 'Idempotency-Key': 'request-publication'}, json={**body, 'authorizationId': 'different-grant'})
            self.assertEqual(conflict.status_code, 409)
            self.assertEqual(client.get(endpoint, params={'projectId': 'project-two'}).status_code, 403)
            self.assertEqual(len(self.remote.pulls), 1)
