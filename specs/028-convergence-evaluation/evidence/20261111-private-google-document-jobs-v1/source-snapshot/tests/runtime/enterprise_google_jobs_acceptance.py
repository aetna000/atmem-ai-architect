"""Pinned public Google API schema + scripted native HTTP; no account calls."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / '.local/azure-runtime-sdk')]
from enterprise_google_jobs import GoogleBatchDocuments, GoogleDocumentApi, configuration, job_spec, transfer_metadata
from enterprise_document_job import request
from enterprise_google_transfer import metadata as checked_transfer, download, upload
from enterprise_sources import SourceUnavailable, SourceDenied


def config():
    return {'format': 'enterprise-google-document-job-v1', 'projectId': 'owned-project', 'region': 'australia-southeast1',
        'bucket': 'owned-ephemeral-documents', 'parserImage': 'australia-southeast1-docker.pkg.dev/owned-project/runtime/parser@sha256:' + 'a' * 64,
        'transferImage': 'australia-southeast1-docker.pkg.dev/owned-project/runtime/transfer@sha256:' + 'b' * 64,
        'workerServiceAccount': 'owned-worker@owned-project.iam.gserviceaccount.com', 'vmServiceAccount': 'document-transfer@owned-project.iam.gserviceaccount.com',
        'network': 'projects/owned-project/global/networks/owned-private',
        'subnetwork': 'projects/owned-project/regions/australia-southeast1/subnetworks/owned-private'}


def discovery_check(value, schema, schemas, path='Job'):
    if '$ref' in schema: return discovery_check(value, schemas[schema['$ref']], schemas, path)
    if schema.get('readOnly'): raise AssertionError(path + ' is read-only')
    if 'enum' in schema: assert value in schema['enum'], path
    kind = schema.get('type')
    if kind == 'object':
        assert isinstance(value, dict), path
        for name, item in value.items():
            shape = schema.get('properties', {}).get(name, schema.get('additionalProperties'))
            assert shape is not None, path + '.' + name
            discovery_check(item, shape, schemas, path + '.' + name)
    elif kind == 'array':
        assert isinstance(value, list), path
        for item in value: discovery_check(item, schema['items'], schemas, path + '[]')
    elif kind == 'string': assert isinstance(value, str), path
    elif kind == 'boolean': assert type(value) is bool, path
    elif kind == 'integer': assert type(value) is int, path
    elif kind == 'number': assert type(value) in {int, float}, path
    else: raise AssertionError('Unhandled public discovery type: ' + str(kind))


class Response:
    def __init__(self, value, status=200):
        self.raw = value if isinstance(value, bytes) else json.dumps(value).encode()
        self.status_code, self.closed = status, False
    def __enter__(self): return self
    def __exit__(self, *args): self.closed = True
    def iter_content(self, size):
        for offset in range(0, len(self.raw), size): yield self.raw[offset:offset + size]


class NativeHttp:
    def __init__(self):
        self.calls = []; self.responses = []; self.trust_env = True
        self.job = None; self.spec = None; self.state = 'SUCCEEDED'; self.forge = False
        self.lost_create = False; self.cleanup_error = False; self.operation_polls = 0
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if 'upload/storage' in url: reply = Response({'generation': '123'})
        elif method == 'POST' and 'batch.googleapis.com' in url:
            self.job = 'projects/owned-project/locations/australia-southeast1/jobs/' + kwargs['params']['jobId']
            self.spec = kwargs['json']
            if self.lost_create: raise TimeoutError('PRIVATE bearer and document must not reach callers')
            reply = Response({'name': self.job})
        elif '/operations/' in url:
            self.operation_polls += 1
            reply = Response({'name': url.split('/v1/')[1], 'done': True, **({'error': {'message': 'PRIVATE upstream'}} if self.cleanup_error else {})})
        elif 'batch.googleapis.com' in url:
            if method == 'DELETE': reply = Response({'name': 'projects/owned-project/locations/australia-southeast1/operations/owned-delete'})
            else: reply = Response({'name': self.job, 'status': {'state': self.state}})
        elif method == 'DELETE': reply = Response(b'', 204)
        else:
            transfer = json.loads(self.spec['taskGroups'][0]['taskSpec']['runnables'][0]['environment']['variables']['DOCUMENT_JOB'])
            expected = transfer['request']
            reply = Response({'format': expected['format'], 'requestId': expected['requestId'], 'status': 'ok',
                'document': {'format': 'enterprise-document-v1', 'sha256': '0' * 64 if self.forge else expected['sha256'], 'mediaType': expected['mediaType'], 'text': 'PRIVATE approved policy.'}})
        self.responses.append(reply); return reply


class GoogleDocumentJobs(unittest.TestCase):
    def setUp(self):
        self.http = NativeHttp(); self.api = GoogleDocumentApi(session=self.http, credential=lambda: 'SYNTHETIC-NATIVE-TOKEN')
        self.runner = GoogleBatchDocuments(config(), api=self.api, poll_seconds=.01)
        self.raw = b'PRIVATE approved policy.'; self.mime = 'text/plain'

    def test_job_matches_pinned_independent_official_discovery_schema(self):
        path = ROOT / 'tests/fixtures/providers/google-batch-v1-discovery-20261111.json'
        provenance = json.loads(path.with_suffix('.provenance.json').read_text())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), provenance['sha256'])
        schemas = json.loads(path.read_text())['schemas']
        value = job_spec(config(), request(self.raw, self.mime, 'a' * 64), '123')
        discovery_check(value, schemas['Job'], schemas)
        for wrong in [{'logsPolicy': {'destination': 'NONE'}}, {'notARealField': True}]:
            with self.assertRaises(AssertionError): discovery_check({**value, **wrong}, schemas['Job'], schemas)

    def test_parser_has_explicit_local_mounts_and_no_identity_network_or_logging_fallback(self):
        value = job_spec(config(), request(self.raw, self.mime, 'a' * 64), '123')
        task = value['taskGroups'][0]['taskSpec']; before, parser, after = task['runnables']
        self.assertNotIn('environment', task); self.assertNotIn('environment', parser)
        self.assertTrue(parser['container']['blockExternalNetwork'])
        self.assertEqual(parser['container']['volumes'], ['/mnt/disks/share/document-' + 'a' * 64 + '/input:/input:ro', '/mnt/disks/share/document-' + 'a' * 64 + '/output:/output:rw'])
        for flag in ['--cap-drop=ALL', '--read-only', '--user=10001:10001', '--log-driver=none', '--pids-limit=128']:
            self.assertIn(flag, parser['container']['options'])
        self.assertNotIn('enableImageStreaming', parser['container'])
        self.assertNotIn('--network', parser['container']['options'])
        self.assertNotIn('background', before); self.assertNotIn('alwaysRun', after)
        self.assertEqual(value['allocationPolicy']['serviceAccount']['email'], config()['vmServiceAccount'])
        self.assertTrue(value['allocationPolicy']['network']['networkInterfaces'][0]['noExternalIpAddress'])

    def test_current_guard_success_uses_native_apis_and_waits_for_cleanup(self):
        checks = []
        value = self.runner.from_source(self.raw, self.mime, lambda: checks.append(True))
        self.assertEqual(value['text'], self.raw.decode()); self.assertGreaterEqual(len(checks), 5)
        self.assertEqual(self.http.operation_polls, 1)
        self.assertEqual(sum(method == 'DELETE' for method, _, _ in self.http.calls), 3)
        self.assertNotIn(self.raw.decode(), json.dumps(self.http.spec))
        self.assertFalse(self.http.trust_env); self.assertTrue(all(r.closed for r in self.http.responses))
        self.assertTrue(all(call['headers']['Authorization'] == 'Bearer SYNTHETIC-NATIVE-TOKEN' and not call['allow_redirects'] for _, _, call in self.http.calls))

    def test_plain_callback_and_initial_revocation_make_no_remote_calls(self):
        with self.assertRaises(SourceUnavailable): self.runner(self.raw, self.mime)
        def deny(): raise SourceDenied('source_access_denied')
        with self.assertRaises(SourceDenied): self.runner.from_source(self.raw, self.mime, deny)
        self.assertEqual(self.http.calls, [])

    def test_revocation_during_job_wait_withholds_result_and_cleans_owned_resources(self):
        checks = []
        def guard():
            checks.append(True)
            if len(checks) == 3: raise SourceDenied('source_access_denied')
        with self.assertRaises(SourceDenied): self.runner.from_source(self.raw, self.mime, guard)
        self.assertFalse(any(method == 'GET' and 'storage.googleapis.com' in url for method, url, _ in self.http.calls))
        self.assertEqual(sum(method == 'DELETE' for method, _, _ in self.http.calls), 3)

    def test_lost_create_ack_still_deletes_only_the_owned_job_and_objects(self):
        self.http.lost_create = True
        with self.assertRaises(SourceUnavailable) as error: self.runner.from_source(self.raw, self.mime, lambda: None)
        self.assertNotIn('PRIVATE', str(error.exception))
        deleted = [url for method, url, _ in self.http.calls if method == 'DELETE']
        self.assertEqual(len(deleted), 3); self.assertIn(self.http.job, deleted[0])

    def test_forged_result_and_failed_job_do_not_return_text(self):
        for state, forged in [('FAILED', False), ('SUCCEEDED', True)]:
            self.http.state, self.http.forge = state, forged
            with self.assertRaises((SourceUnavailable, ValueError)):
                self.runner.from_source(self.raw, self.mime, lambda: None)

    def test_cleanup_failure_withholds_an_otherwise_valid_answer(self):
        self.http.cleanup_error = True
        with self.assertRaisesRegex(SourceUnavailable, 'document_job_cleanup_unavailable'):
            self.runner.from_source(self.raw, self.mime, lambda: None)

    def test_native_job_wait_deadline_still_runs_cleanup(self):
        now = [0]
        def clock(): now[0] += 1; return now[0]
        self.runner.deadline = 1
        with patch('enterprise_google_jobs.time.monotonic', side_effect=clock):
            with self.assertRaises(SourceUnavailable): self.runner.from_source(self.raw, self.mime, lambda: None)
        self.assertEqual(sum(method == 'DELETE' for method, _, _ in self.http.calls), 3)

    def test_other_projects_regions_floating_images_and_shared_worker_identity_are_rejected(self):
        for patch_value in [{'parserImage': config()['parserImage'].split('@')[0] + ':latest'},
            {'region': 'us-central1'}, {'vmServiceAccount': config()['workerServiceAccount']},
            {'vmServiceAccount': 'document-transfer@other-project.iam.gserviceaccount.com'},
            {'vmServiceAccount': 'short@owned-project.iam.gserviceaccount.com'},
            {'network': config()['network'] + '-'},
            {'parserImage': config()['parserImage'].replace('/parser@', '/parser//other@')},
            {'subnetwork': 'projects/owned-project/regions/us-central1/subnetworks/owned-private'}, {'extra': 'credentials'}]:
            with self.assertRaises(ValueError): configuration({**config(), **patch_value})

    def test_error_bodies_redirects_duplicate_and_oversized_metadata_are_sanitized(self):
        class Broken:
            def __init__(self, response): self.response = response
            def request(self, *args, **kwargs): return self.response
        for response in [Response(b'PRIVATE token', 302), Response(b'PRIVATE token', 403),
                         Response(b'{"generation":"123","generation":"456"}'), Response(b' ' * 32769)]:
            client = GoogleDocumentApi(session=Broken(response), credential=lambda: 'SYNTHETIC-TOKEN')
            with self.assertRaises(SourceUnavailable) as error: client.json('GET', 'https://storage.googleapis.com/storage/v1/b/owned')
            self.assertNotIn('PRIVATE', str(error.exception)); self.assertTrue(response.closed)

    def test_transfer_metadata_rejects_extra_destinations_or_ambiguous_request_values(self):
        value = transfer_metadata(config(), request(self.raw, self.mime, 'a' * 64), '123')
        self.assertEqual(checked_transfer(json.dumps(value)), value)
        for raw in [json.dumps({**value, 'endpoint': 'https://unowned.invalid'}), ' ' * 4097,
                    json.dumps(value)[:-1] + ',"bucket":"other"}', json.dumps({**value, 'inputGeneration': 'latest'}),
                    json.dumps({**value, 'request': {**value['request'], 'sha256': 123}})]:
            with self.assertRaises(ValueError): checked_transfer(raw)

    def test_transfer_download_and_upload_bind_bytes_and_reject_reused_state(self):
        value = transfer_metadata(config(), request(self.raw, self.mime, 'a' * 64), '123')
        outer = self
        class Objects:
            def __init__(self): self.uploads = []
            def load(self, identifier, side, generation):
                outer.assertEqual((identifier, side, generation), ('a' * 64, 'input', '123')); return outer.raw
            def put(self, identifier, side, raw): self.uploads.append((identifier, side, raw))
        objects = Objects()
        with tempfile.TemporaryDirectory() as mount, patch('enterprise_google_transfer.os.fchown'):
            # Host-only filesystem fixture: UID transitions are exercised in the
            # separate Linux three-stage qualification, not simulated here.
            download(value, objects, mount)
            path = Path(mount); self.assertEqual((path / 'input/document').read_bytes(), self.raw)
            encoded = json.dumps({'format': value['request']['format'], 'requestId': 'a' * 64, 'status': 'ok',
                'document': {'format': 'enterprise-document-v1', 'sha256': hashlib.sha256(self.raw).hexdigest(), 'mediaType': self.mime, 'text': self.raw.decode()}}).encode()
            (path / 'output/result.json').write_bytes(encoded)
            upload(value, objects, mount); self.assertEqual(objects.uploads, [('a' * 64, 'result', encoded)])
            with self.assertRaises(FileExistsError): download(value, objects, mount)
            (path / 'output/result.json').unlink(); (path / 'output/result.json').symlink_to(path / 'input/document')
            with self.assertRaises(OSError): upload(value, objects, mount)
            self.assertEqual(len(objects.uploads), 1)
            (path / 'input').chmod(0o700)

    def test_transfer_changed_source_does_not_write_or_upload(self):
        value = transfer_metadata(config(), request(self.raw, self.mime, 'a' * 64), '123')
        class Changed:
            def load(self, *args): return b'changed private input'
            def put(self, *args): raise AssertionError('Do not upload changed content')
        with tempfile.TemporaryDirectory() as mount:
            with self.assertRaises(ValueError): download(value, Changed(), mount)
            self.assertEqual(list(Path(mount).iterdir()), [])


if __name__ == '__main__': unittest.main(verbosity=2)
