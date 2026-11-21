"""Scripted ARM/Blob wire checks, not an Azure account or storage emulator."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / '.local/azure-runtime-sdk')]
from enterprise_azure_objects import AzureDocumentObjects, ARM_VERSION, BLOB_VERSION, object_key
from enterprise_document_contract import MAX_INPUT
from enterprise_document_job import MAX_ENVELOPE
from enterprise_sources import SourceUnavailable


class Credential:
    def __init__(self):
        self.scopes, self.closed, self.token = [], False, 'SYNTHETIC-NATIVE-TOKEN'
    def get_token(self, scope):
        self.scopes.append(scope)
        return SimpleNamespace(token=self.token)
    def close(self): self.closed = True


class Response:
    def __init__(self, raw=b'', *, status=200, headers=None, chunks=None):
        self.raw, self.status_code, self.headers = raw, status, headers or {}
        self.closed, self.chunks = False, chunks
    def __enter__(self): return self
    def __exit__(self, *args): self.closed = True
    def iter_content(self, size):
        if self.chunks is not None:
            yield from self.chunks
        else:
            for offset in range(0, len(self.raw), size): yield self.raw[offset:offset + size]


class NativeHttp:
    def __init__(self):
        self.calls, self.replies, self.closed, self.trust_env = [], [], False, True
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.replies: raise AssertionError('Unexpected native HTTP call')
        value = self.replies.pop(0)
        if isinstance(value, Exception): raise value
        return value
    def close(self): self.closed = True


def objects(session=None, credential=None, **overrides):
    return AzureDocumentObjects(**{
        'subscription': '11111111-1111-1111-1111-111111111111',
        'resource_group': 'owned-documents', 'region': 'australiaeast',
        'account': 'ownedtemporary', 'container': 'documents',
        'client_id': '22222222-2222-2222-2222-222222222222',
        'session': session or NativeHttp(), 'credential': credential or Credential(), **overrides})


def policy(owner):
    return [
        {'id': owner.account_id, 'location': 'australiaeast', 'kind': 'StorageV2',
         'sku': {'name': 'Standard_LRS'}, 'properties': {'primaryLocation': 'australiaeast',
            'supportsHttpsTrafficOnly': True, 'minimumTlsVersion': 'TLS1_2',
            'allowSharedKeyAccess': False, 'allowBlobPublicAccess': False,
            'publicNetworkAccess': 'Disabled', 'encryption': {'services': {'blob': {'enabled': True}}}}},
        {'id': owner.service_id, 'properties': {'isVersioningEnabled': False,
            **{name: {'enabled': False} for name in ['deleteRetentionPolicy', 'containerDeleteRetentionPolicy', 'restorePolicy', 'changeFeed']}}},
        {'id': owner.container_id, 'properties': {'publicAccess': 'None',
            'hasImmutabilityPolicy': False, 'hasLegalHold': False}}
    ]


def enqueue_policy(owner, values=None):
    values = policy(owner) if values is None else values
    owner.session.replies.extend(Response(json.dumps(value).encode()) for value in values)


def blob_headers(raw=b'private fixture'):
    return {'ETag': '"0x8DA123ABCDEF"', 'Content-Length': str(len(raw)),
            'x-ms-blob-type': 'BlockBlob', 'x-ms-server-encrypted': 'true'}


class AzureDocumentObjectContract(unittest.TestCase):
    def setUp(self):
        self.objects = objects()
        self.identifier = 'd' * 64
        self.raw = b'private fixture'

    def test_create_only_byte_upload_observes_policy_before_any_payload(self):
        owner = self.objects
        enqueue_policy(owner)
        response = Response(status=201, headers={'ETag': '"0x8DA123ABCDEF"', 'x-ms-request-server-encrypted': 'true'})
        owner.session.replies.append(response)
        self.assertEqual(owner.put(self.identifier, 'input', self.raw), '"0x8DA123ABCDEF"')
        self.assertEqual(len(owner.session.calls), 4)
        for method, url, options in owner.session.calls[:3]:
            self.assertEqual(method, 'GET')
            self.assertTrue(url.startswith('https://management.azure.com/subscriptions/'))
            self.assertEqual(options['params'], {'api-version': ARM_VERSION})
            self.assertIsNone(options['data'])
        method, url, options = owner.session.calls[-1]
        self.assertEqual(method, 'PUT')
        self.assertEqual(url, 'https://ownedtemporary.blob.core.windows.net/documents/document-jobs/' + self.identifier + '/input')
        self.assertEqual(options['headers']['If-None-Match'], '*')
        self.assertEqual(options['headers']['x-ms-blob-type'], 'BlockBlob')
        self.assertEqual(options['headers']['x-ms-version'], BLOB_VERSION)
        self.assertEqual(options['headers']['Content-MD5'], base64.b64encode(hashlib.md5(self.raw, usedforsecurity=False).digest()).decode())
        self.assertEqual(options['data'], self.raw)
        self.assertEqual(owner.credential.scopes, ['https://management.azure.com/.default'] * 3 + ['https://storage.azure.com/.default'])
        self.assertFalse(options['allow_redirects'])
        self.assertTrue(options['stream'])
        self.assertEqual(options['timeout'], (2, 8))
        self.assertFalse(owner.session.trust_env)
        self.assertTrue(response.closed)

    def test_conditional_read_uses_native_etag_and_exact_length(self):
        owner = self.objects
        enqueue_policy(owner)
        response = Response(self.raw, headers=blob_headers(self.raw))
        owner.session.replies.append(response)
        self.assertEqual(owner.load(self.identifier, 'input', '"0x8DA123ABCDEF"'), self.raw)
        options = owner.session.calls[-1][2]
        self.assertEqual(options['headers']['If-Match'], '"0x8DA123ABCDEF"')
        self.assertEqual(options['headers']['Accept-Encoding'], 'identity')
        self.assertIsNone(options['params'])
        self.assertTrue(response.closed)

    def test_policy_change_never_sends_payload_or_delete(self):
        mutations = [(0, ['location'], 'eastus'), (0, ['sku', 'name'], 'Standard_GRS'),
            (0, ['properties', 'secondaryLocation'], 'eastus'),
            (0, ['properties', 'allowSharedKeyAccess'], True),
            (0, ['properties', 'allowBlobPublicAccess'], True),
            (0, ['properties', 'publicNetworkAccess'], 'Enabled'),
            (0, ['properties', 'supportsHttpsTrafficOnly'], False),
            (0, ['properties', 'minimumTlsVersion'], 'TLS1_0'),
            (0, ['properties', 'encryption', 'services', 'blob', 'enabled'], False),
            (0, ['properties', 'immutableStorageWithVersioning'], {'enabled': True}),
            (1, ['properties', 'isVersioningEnabled'], True),
            (2, ['properties', 'publicAccess'], 'Blob'),
            (2, ['properties', 'hasLegalHold'], True),
            (2, ['properties', 'hasImmutabilityPolicy'], True),
            (2, ['properties', 'immutableStorageWithVersioning'], {'enabled': True})]
        mutations += [(1, ['properties', name, 'enabled'], True) for name in
                      ['deleteRetentionPolicy', 'containerDeleteRetentionPolicy', 'restorePolicy', 'changeFeed']]
        for index, path, value in mutations:
            for operation in ['put', 'delete']:
                with self.subTest(path=path, operation=operation):
                    owner = objects()
                    values = policy(owner)
                    target = values[index]
                    for key in path[:-1]: target = target[key]
                    target[path[-1]] = value
                    enqueue_policy(owner, values)
                    with self.assertRaisesRegex(SourceUnavailable, 'document_object_policy_unavailable'):
                        if operation == 'put': owner.put(self.identifier, 'input', self.raw)
                        else: owner.delete(self.identifier, 'input')
                    self.assertTrue(all(method == 'GET' and options['data'] is None for method, _, options in owner.session.calls))

    def test_missing_history_flags_are_not_assumed_safe(self):
        for name in ['isVersioningEnabled', 'deleteRetentionPolicy', 'containerDeleteRetentionPolicy', 'restorePolicy', 'changeFeed']:
            with self.subTest(name=name):
                owner = objects(); values = policy(owner)
                del values[1]['properties'][name]
                enqueue_policy(owner, values)
                with self.assertRaises(SourceUnavailable): owner.preflight()

    def test_foreign_arm_identity_and_duplicate_keys_fail_closed(self):
        for index in range(3):
            owner = objects(); values = policy(owner)
            values[index]['id'] += '-foreign'
            enqueue_policy(owner, values)
            with self.assertRaises(SourceUnavailable): owner.preflight()
        owner = objects()
        owner.session.replies.append(Response(b'{"id":"' + owner.account_id.encode() + b'","id":"foreign"}'))
        with self.assertRaises(SourceUnavailable): owner.preflight()

    def test_result_body_is_bounded_and_invalid_transport_metadata_rejected(self):
        changes = [{'Content-Length': '1'}, {'x-ms-server-encrypted': 'false'},
                   {'x-ms-version-id': 'retained-version'}, {'x-ms-blob-type': 'PageBlob'},
                   {'Content-Encoding': 'gzip'}, {'ETag': '"0xOTHER"'}]
        for change in changes:
            with self.subTest(change=change):
                owner = objects(); enqueue_policy(owner)
                response = Response(self.raw, headers={**blob_headers(self.raw), **change})
                owner.session.replies.append(response)
                with self.assertRaises(SourceUnavailable): owner.load(self.identifier, 'result', '"0x8DA123ABCDEF"')
                self.assertTrue(response.closed)
        owner = objects(); enqueue_policy(owner)
        response = Response(headers=blob_headers(self.raw), chunks=[b'x' * (MAX_ENVELOPE + 1)])
        owner.session.replies.append(response)
        with self.assertRaises(SourceUnavailable): owner.load(self.identifier, 'result')
        self.assertTrue(response.closed)

    def test_redirects_and_http_errors_do_not_follow_or_disclose_provider_body(self):
        for code in [301, 302, 307, 401, 403, 409, 412, 500]:
            owner = objects(); enqueue_policy(owner)
            response = Response(b'PRIVATE SOURCE ERROR WITH TOKEN', status=code,
                                headers={'Location': 'https://attacker.invalid/'})
            owner.session.replies.append(response)
            with self.assertRaises(SourceUnavailable) as raised:
                owner.load(self.identifier, 'input')
            self.assertEqual(str(raised.exception), 'document_object_unavailable')
            self.assertEqual(len(owner.session.calls), 4)
            self.assertFalse(owner.session.calls[-1][2]['allow_redirects'])
            self.assertTrue(response.closed)

    def test_create_ack_must_confirm_encryption_and_no_version(self):
        for change in [{'x-ms-request-server-encrypted': 'false'}, {'x-ms-version-id': 'old'}, {'ETag': '*'}]:
            owner = objects(); enqueue_policy(owner)
            owner.session.replies.append(Response(status=201, headers={
                'ETag': '"0x8DA123ABCDEF"', 'x-ms-request-server-encrypted': 'true', **change}))
            with self.assertRaises(SourceUnavailable): owner.put(self.identifier, 'input', self.raw)

    def test_delete_is_repeatable_but_not_a_soft_delete_claim(self):
        for status in [202, 404]:
            owner = objects(); enqueue_policy(owner)
            owner.session.replies.append(Response(status=status))
            owner.delete(self.identifier, 'result')
            method, _, options = owner.session.calls[-1]
            self.assertEqual(method, 'DELETE')
            self.assertEqual(options['headers']['x-ms-delete-snapshots'], 'include')
        owner = objects(); enqueue_policy(owner)
        owner.session.replies.append(Response(status=202, headers={'x-ms-version-id': 'retained'}))
        with self.assertRaisesRegex(SourceUnavailable, 'document_cleanup_unavailable'):
            owner.delete(self.identifier, 'result')

    def test_untrusted_paths_sizes_and_conditions_rejected_before_native_io(self):
        owner = self.objects
        for identifier, side in [('../other', 'input'), ('d' * 65, 'result'), (self.identifier, '../keys')]:
            with self.assertRaises(ValueError): owner.load(identifier, side)
        for side, raw in [('input', b''), ('input', b'x' * (MAX_INPUT + 1)), ('result', b'x' * (MAX_ENVELOPE + 1)), ('input', 'text')]:
            with self.assertRaises(ValueError): owner.put(self.identifier, side, raw)
        with self.assertRaises(SourceUnavailable): owner.load(self.identifier, 'input', '*')
        self.assertEqual(owner.session.calls, [])
        for args in [{'account': 'ownedtemporary.attacker.invalid'}, {'container': 'other/keys'},
                     {'subscription': 'other'}, {'region': 'australiaeast\n'}, {'client_id': 'default'}]:
            with self.assertRaises(ValueError): objects(**args)

    def test_invalid_managed_identity_token_is_not_sent(self):
        for token in ['short', 'a\r\nsecret', 'a' * 20001]:
            owner = objects(); owner.credential.token = token
            with self.assertRaises(SourceUnavailable): owner.preflight()
            self.assertEqual(owner.session.calls, [])

    def test_fixed_native_identity_constructor_never_uses_default_credential_chain(self):
        owner = self.objects
        owner.credential = None
        with patch('azure.identity.ManagedIdentityCredential') as native:
            owner._credential()
            native.assert_called_once_with(client_id=owner.client_id, retry_total=0, connection_timeout=1, read_timeout=2)

    def test_response_deadline_and_resource_close(self):
        owner = self.objects; enqueue_policy(owner)
        owner.session.replies.append(Response(self.raw, headers=blob_headers(self.raw)))
        with patch('enterprise_azure_objects.time.monotonic', side_effect=[0, 0, 0, 0, 0, 0, 0, 16]):
            with self.assertRaises(SourceUnavailable): owner.load(self.identifier, 'input')
        owner.close()
        self.assertTrue(owner.session.closed)
        self.assertTrue(owner.credential.closed)


if __name__ == '__main__':
    unittest.main()
