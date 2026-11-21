"""Pinned native payload shapes and scripted HTTP; no Batch account requests."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / 'tests/runtime'), str(ROOT / '.local/azure-runtime-sdk')]
from enterprise_azure_jobs_acceptance import config, shape
from enterprise_azure_objects_acceptance import NativeHttp, Credential, Response
from enterprise_azure_batch_api import AzureBatchApi
from enterprise_document_job import request
from enterprise_sources import SourceUnavailable


class AzureBatchWireContracts(unittest.TestCase):
    def setUp(self):
        self.session, self.credential = NativeHttp(), Credential()
        self.api = AzureBatchApi(config(), session=self.session, credential=self.credential)
        self.identifier = 'd' * 64
        self.metadata = request(b'private fixture', 'text/plain', self.identifier)

    def test_native_payloads_verbs_and_statuses_match_pinned_service_schema(self):
        native = json.loads((ROOT / 'tests/fixtures/providers/azure-batch-2026-10-01-20261111.json').read_text())
        self.session.replies = [Response(status=201), Response(status=201), Response(status=202), Response(status=202)]
        self.assertEqual(self.api.create_job(self.metadata, '"0x8DA123ABCDEF"'), {})
        self.assertEqual(self.api.create_task(self.identifier), {})
        self.assertEqual(self.api.terminate(self.identifier), {})
        self.assertEqual(self.api.delete(self.identifier), {})
        definitions = native['definitions']
        for index, model in enumerate(['BatchJobCreateOptions', 'BatchTaskCreateOptions', 'BatchJobTerminateOptions']):
            value = json.loads(self.session.calls[index][2]['data'])
            shape(value, definitions[model], definitions)
        for method, template, status in [('post', '/jobs', '201'), ('post', '/jobs/{jobId}/tasks', '201'),
                                         ('post', '/jobs/{jobId}/terminate', '202'), ('delete', '/jobs/{jobId}', '202')]:
            self.assertIn(status, native['paths'][template][method]['responses'])
        for method, url, options in self.session.calls:
            self.assertTrue(url.startswith('https://owneddocuments.australiaeast.batch.azure.com/jobs'))
            self.assertEqual(options['params'], {'api-version': '2026-10-01'})
            self.assertNotIn('force', options['params'])
            self.assertFalse(options['allow_redirects'])
            self.assertTrue(options['stream'])
            self.assertIn('ocp-date', options['headers'])
            self.assertEqual(options['headers']['Authorization'], 'Bearer SYNTHETIC-NATIVE-TOKEN')
        self.assertEqual(self.credential.scopes, ['https://batch.core.windows.net/.default'] * 4)
        self.assertFalse(self.session.trust_env)

    def test_unsafe_paths_methods_and_document_fields_fail_before_identity_or_http(self):
        for method, path in [('POST', '/pools'), ('DELETE', '/pools/document-private'),
                             ('GET', '/jobs'), ('GET', 'https://attacker.invalid/jobs'),
                             ('GET', '/jobs/' + self.identifier + '/tasks/document/files/secret'),
                             ('POST', '/pools/document-private/nodes/node/reimage'),
                             ('POST', '/jobs/' + self.identifier + '/tasks/document/reactivate')]:
            with self.assertRaises(ValueError): self.api._send(method, path)
        with self.assertRaises(ValueError): self.api.create_job({**self.metadata, 'sourceUrl': 'https://private'}, '"0x8DA123ABCDEF"')
        with self.assertRaises(ValueError): self.api.job('../foreign', missing=True)
        self.assertEqual(self.session.calls, [])
        self.assertEqual(self.credential.scopes, [])

    def test_missing_lookup_is_distinct_from_failed_pool_or_permission(self):
        self.session.replies = [Response(status=404), Response(status=404), Response(status=404), Response(status=403)]
        self.assertIsNone(self.api.job(self.identifier, missing=True))
        self.assertIsNone(self.api.task(self.identifier, missing=True))
        with self.assertRaises(SourceUnavailable): self.api.pool()
        with self.assertRaises(SourceUnavailable): self.api.job(self.identifier, missing=True)

    def test_account_observation_binds_arm_owner_endpoint_region_aad_and_private_access(self):
        value = {'id': self.api.account_id, 'location': 'australiaeast', 'properties': {
            'provisioningState': 'Succeeded', 'accountEndpoint': 'owneddocuments.australiaeast.batch.azure.com',
            'publicNetworkAccess': 'Disabled', 'allowedAuthenticationModes': ['AAD']}}
        self.session.replies = [Response(json.dumps(value).encode())]
        self.assertEqual(self.api.account(), value)
        self.assertEqual(self.credential.scopes, ['https://management.azure.com/.default'])
        for change in [{'accountEndpoint': 'foreign.australiaeast.batch.azure.com'}, {'allowedAuthenticationModes': ['AAD', 'SharedKey']},
                       {'publicNetworkAccess': 'Enabled'}, {'provisioningState': 'Updating'}]:
            changed = {**value, 'properties': {**value['properties'], **change}}
            self.session.replies = [Response(json.dumps(changed).encode())]
            with self.assertRaisesRegex(SourceUnavailable, 'account_changed'): self.api.account()
        for change in [{'id': self.api.account_id + '-foreign'}, {'location': 'eastus'}]:
            self.session.replies = [Response(json.dumps({**value, **change}).encode())]
            with self.assertRaises(SourceUnavailable): self.api.account()

    def test_redirect_provider_error_and_bad_json_are_closed_and_sanitized(self):
        for response in [Response(b'PRIVATE PROVIDER TOKEN', status=302, headers={'Location': 'https://attacker.invalid'}),
                         Response(b'PRIVATE PROVIDER TOKEN', status=500), Response(b'{"id":"one","id":"two"}'),
                         Response(b'[]'), Response(b''), Response(b'x' * 262145),
                         Response(b'compressed', headers={'Content-Encoding': 'gzip'})]:
            self.session.replies = [response]
            with self.assertRaisesRegex(SourceUnavailable, '^document_batch_api_unavailable$'):
                self.api.job(self.identifier)
            self.assertTrue(response.closed)

    def test_explicit_mi_identity_and_config_cannot_fall_back_or_mutate(self):
        self.api.credential = None
        with patch('azure.identity.ManagedIdentityCredential') as native:
            self.api._credential()
            native.assert_called_once_with(client_id=config()['workerClientId'], retry_total=0, connection_timeout=1, read_timeout=2)
        with self.assertRaises(TypeError): self.api.config['region'] = 'eastus'

    def test_bad_token_is_not_sent_and_both_resources_close(self):
        self.credential.token = 'PRIVATE\r\nTOKEN'
        with self.assertRaises(SourceUnavailable): self.api.pool()
        self.assertEqual(self.session.calls, [])
        self.api.close()
        self.assertTrue(self.session.closed)
        self.assertTrue(self.credential.closed)


if __name__ == '__main__': unittest.main()
