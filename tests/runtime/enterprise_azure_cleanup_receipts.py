"""Offline IMDS/Blob wire contracts and root-to-worker cleanup acknowledgement."""
import copy
import json
from pathlib import Path
import sys
import time
from urllib.parse import parse_qs
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / 'tests/runtime'), str(ROOT / '.local/azure-runtime-sdk')]
from enterprise_azure_jobs_acceptance import config
from enterprise_azure_host import RootReceipts, cleanup_receipt, encoded, owner
from enterprise_azure_objects_acceptance import objects, enqueue_policy, Response as BlobResponse, blob_headers
from enterprise_sources import SourceUnavailable


class Response:
    def __init__(self, status=200, raw=b'', headers=None):
        self.status, self.raw, self.headers, self.offset = status, raw, headers or {}, 0
    def getheaders(self): return list(self.headers.items())
    def read(self, count):
        raw = self.raw[self.offset:self.offset + count]; self.offset += len(raw); return raw


class Connection:
    def __init__(self, response): self.response, self.calls, self.closed = response, [], False
    def request(self, method, path, *, body, headers): self.calls.append((method, path, body, headers))
    def getresponse(self):
        if isinstance(self.response, Exception): raise self.response
        return self.response
    def close(self): self.closed = True


class Connections:
    def __init__(self, replies): self.replies, self.connections, self.destinations = replies, [], []
    def __call__(self, method, host, path):
        self.destinations.append((method, host, path))
        if not self.replies: raise AssertionError('Unexpected native cleanup request')
        value = Connection(self.replies.pop(0)); self.connections.append(value); return value


def token(**changes):
    value = {'access_token': 'SYNTHETIC-NATIVE-TOKEN', 'token_type': 'Bearer',
             'resource': 'https://storage.azure.com/', 'expires_on': str(int(time.time()) + 3600), **changes}
    return Response(raw=json.dumps(value).encode())


def receipt():
    return {'format': 'enterprise-azure-document-cleanup-v1', 'requestId': 'd' * 64,
            'owner': owner(config()), 'cleaned': True}


def acknowledged(**changes):
    return Response(201, headers={'ETag': '"0x8DA123ABCDEF"', 'x-ms-request-server-encrypted': 'true', **changes})


class CleanupReceiptContracts(unittest.TestCase):
    def test_native_mi_and_create_only_metadata_do_not_forward_credentials_or_source(self):
        connections = Connections([token(), acknowledged()])
        RootReceipts(config(), connection=connections).publish(receipt())
        method, host, path = connections.destinations[0]
        self.assertEqual((method, host), ('GET', '169.254.169.254'))
        self.assertEqual(parse_qs(path.split('?', 1)[1]), {'api-version': ['2018-02-01'],
            'resource': ['https://storage.azure.com/'], 'client_id': [config()['transferClientId']]})
        headers = connections.connections[0].calls[0][3]
        self.assertEqual(headers['Metadata'], 'true')
        self.assertNotIn('Authorization', headers)
        method, host, path = connections.destinations[1]
        self.assertEqual((method, host), ('PUT', 'ownedtemporary.blob.core.windows.net'))
        self.assertEqual(path, '/documents/document-jobs/' + 'd' * 64 + '/cleanup')
        _, _, raw, headers = connections.connections[1].calls[0]
        self.assertEqual(raw, encoded(receipt()))
        self.assertEqual(headers['If-None-Match'], '*')
        self.assertEqual(headers['Authorization'], 'Bearer SYNTHETIC-NATIVE-TOKEN')
        self.assertTrue(all(item.closed for item in connections.connections))
        self.assertEqual(set(json.loads(raw)), {'format', 'requestId', 'owner', 'cleaned'})

    def test_lost_create_acknowledgement_adopts_only_the_exact_existing_receipt(self):
        raw = encoded(receipt())
        headers = {'Content-Length': str(len(raw)), 'x-ms-server-encrypted': 'true', 'x-ms-blob-type': 'BlockBlob'}
        connections = Connections([token(), Response(412), Response(raw=raw, headers=headers)])
        RootReceipts(config(), connection=connections).publish(receipt())
        self.assertEqual([method for method, _, _ in connections.destinations], ['GET', 'PUT', 'GET'])
        for bad in [raw.replace(b'"cleaned":true', b'"cleaned":false'), encoded({**receipt(), 'owner': 'f' * 64})]:
            connections = Connections([token(), Response(412), Response(raw=bad, headers={**headers, 'Content-Length': str(len(bad))})])
            with self.assertRaisesRegex(ValueError, 'acknowledgement remains pending'):
                RootReceipts(config(), connection=connections).publish(receipt())

    def test_bad_or_expiring_token_never_causes_blob_request(self):
        for change in [{'access_token': 'PRIVATE\r\nTOKEN'}, {'expires_on': '0'},
                       {'resource': 'https://management.azure.com/'}, {'token_type': 'other'}]:
            connections = Connections([token(**change)])
            with self.assertRaises(ValueError): RootReceipts(config(), connection=connections).publish(receipt())
            self.assertEqual(len(connections.destinations), 1)
            self.assertTrue(connections.connections[0].closed)

    def test_redirect_failure_version_and_missing_encryption_do_not_acknowledge(self):
        for reply in [Response(302, headers={'Location': 'https://attacker.invalid/'}),
                      Response(500, b'PRIVATE PROVIDER TOKEN'),
                      acknowledged(**{'x-ms-version-id': 'retained-version'}),
                      acknowledged(**{'x-ms-request-server-encrypted': 'false'}),
                      acknowledged(ETag='*'), ConnectionError('PRIVATE PROVIDER TOKEN')]:
            connections = Connections([token(), reply])
            with self.assertRaisesRegex(ValueError, '^Owned cleanup acknowledgement remains pending$'):
                RootReceipts(config(), connection=connections).publish(receipt())
            self.assertEqual(len(connections.destinations), 2)
            self.assertTrue(all(value.closed for value in connections.connections))

    def test_only_completed_cleanup_has_a_receipt_and_no_arbitrary_fields_can_leave_host(self):
        with self.assertRaises(ValueError): cleanup_receipt({'phase': 'ready', 'requestId': 'd' * 64, 'owner': owner(config())})
        connections = Connections([])
        for value in [None, {**receipt(), 'sourceText': 'PRIVATE DOCUMENT'}, {**receipt(), 'owner': 'f' * 64},
                      {**receipt(), 'cleaned': 1}, {**receipt(), 'requestId': '../../other'}]:
            with self.assertRaises(ValueError): RootReceipts(config(), connection=connections).publish(value)
        self.assertEqual(connections.destinations, [])

    def test_root_response_compression_and_size_are_bounded(self):
        for reply in [Response(raw=b'x' * 32769), Response(raw=b'compressed', headers={'Content-Encoding': 'gzip'}),
                      Response(headers={'Content-Length': '1', 'content-length': '2'})]:
            connections = Connections([reply])
            with self.assertRaises(ValueError): RootReceipts(config(), connection=connections).publish(receipt())
            self.assertTrue(connections.connections[0].closed)

    def test_worker_accepts_exact_producer_bytes_and_distinguishes_missing_from_error(self):
        owner_ = objects()
        enqueue_policy(owner_)
        raw = encoded(receipt())
        owner_.session.replies.append(BlobResponse(raw, headers=blob_headers(raw)))
        self.assertTrue(owner_.cleanup_acknowledged('d' * 64, owner(config())))
        self.assertTrue(owner_.session.calls[-1][1].endswith('/cleanup'))
        owner_ = objects(); enqueue_policy(owner_)
        owner_.session.replies.append(BlobResponse(status=404))
        self.assertFalse(owner_.cleanup_acknowledged('d' * 64, owner(config())))
        owner_ = objects(); enqueue_policy(owner_)
        owner_.session.replies.append(BlobResponse(status=403))
        with self.assertRaises(SourceUnavailable): owner_.cleanup_acknowledged('d' * 64, owner(config()))

    def test_worker_does_not_accept_forged_duplicate_or_oversize_cleanup_receipts(self):
        values = [encoded({**receipt(), 'owner': 'f' * 64}), encoded({**receipt(), 'requestId': 'e' * 64}),
                  encoded({**receipt(), 'cleaned': 1}), encoded({**receipt(), 'extra': 'text'}),
                  encoded(receipt())[:-1] + b',"cleaned":false}', b'x' * 1025]
        for raw in values:
            owner_ = objects(); enqueue_policy(owner_)
            owner_.session.replies.append(BlobResponse(raw, headers=blob_headers(raw)))
            with self.assertRaises(SourceUnavailable): owner_.cleanup_acknowledged('d' * 64, owner(config()))

    def test_document_worker_cannot_publish_or_delete_root_receipts_through_byte_api(self):
        owner_ = objects()
        with self.assertRaises(ValueError): owner_.put('d' * 64, 'cleanup', encoded(receipt()))
        with self.assertRaises(ValueError): owner_.delete('d' * 64, 'cleanup')
        self.assertEqual(owner_.session.calls, [])


if __name__ == '__main__': unittest.main()
