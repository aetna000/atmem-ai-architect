"""Pinned native REST shape and hostile contract checks; no Azure account calls."""
import copy
import hashlib
import json
from pathlib import Path
import shlex
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src/runtime'))
from enterprise_azure_jobs import (API_VERSION, configuration, transfer_metadata, job_spec,
                                   task_spec, verify_job, verify_task, volume_names, fingerprint)
from enterprise_document_job import request


def config():
    return {'format': 'enterprise-azure-document-job-v1',
            'subscriptionId': '11111111-1111-1111-1111-111111111111',
            'region': 'australiaeast', 'resourceGroup': 'owned-documents',
            'batchAccount': 'owneddocuments', 'poolId': 'document-private',
            'storageAccount': 'ownedtemporary', 'container': 'documents',
            'workerClientId': '22222222-2222-2222-2222-222222222222',
            'transferClientId': '33333333-3333-3333-3333-333333333333',
            'parserImage': 'ownedregistry.azurecr.io/parser@sha256:' + 'a' * 64,
            'transferImage': 'ownedregistry.azurecr.io/transfer@sha256:' + 'b' * 64,
            'hostHelperSha256': 'c' * 64}


def shape(value, schema, definitions, path='request'):
    """Independent fail-closed traversal of Microsoft's pinned Swagger shapes."""
    if '$ref' in schema:
        return shape(value, definitions[schema['$ref'].removeprefix('#/definitions/')], definitions, path)
    if schema.get('readOnly'):
        raise AssertionError(path + ' is response-only')
    for parent in schema.get('allOf', []):
        shape(value, parent, definitions, path)
    if 'enum' in schema:
        assert value in schema['enum'], path + ' enum'
    kind = schema.get('type')
    if kind == 'object' or 'properties' in schema:
        assert isinstance(value, dict), path
        assert set(schema.get('required', [])) <= set(value), path + ' required'
        for key, item in value.items():
            child = schema.get('properties', {}).get(key)
            assert child is not None, path + '.' + key + ' unknown'
            shape(item, child, definitions, path + '.' + key)
    elif kind == 'array':
        assert isinstance(value, list), path
        for item in value:
            shape(item, schema['items'], definitions, path + '[]')
    elif kind == 'string':
        assert isinstance(value, str), path
    elif kind == 'boolean':
        assert type(value) is bool, path
    elif kind == 'integer':
        assert type(value) is int, path
    elif kind == 'number':
        assert type(value) in {float, int}, path
    else:
        assert schema.get('allOf'), path + ' unsupported shape'


class AzureDocumentContract(unittest.TestCase):
    def setUp(self):
        self.config = config()
        self.identifier = 'd' * 64
        self.metadata = request(b'private source fixture', 'application/pdf', self.identifier)
        self.etag = '"0x8DA123ABCDEF"'

    def test_official_native_job_task_shapes_and_source_binding(self):
        base = ROOT / 'tests/fixtures/providers/azure-batch-2026-10-01-20261111'
        raw = base.with_suffix('.json').read_bytes()
        provenance = json.loads(base.with_suffix('.provenance.json').read_text())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), provenance['sha256'])
        self.assertIn('/' + provenance['revision'] + '/', provenance['url'])
        document = json.loads(raw)
        self.assertEqual(document['info']['version'], API_VERSION)
        definitions = document['definitions']
        shape(job_spec(self.config, self.metadata, self.etag), definitions['BatchJobCreateOptions'], definitions)
        shape(task_spec(self.config, self.identifier), definitions['BatchTaskCreateOptions'], definitions)
        # Prove this checker rejects an invented API field and wrong enum.
        task = task_spec(self.config, self.identifier)
        task['containerSettings']['containerHostBatchBindMount'] = []
        with self.assertRaises(AssertionError):
            shape(task, definitions['BatchTaskCreateOptions'], definitions)
        del task['containerSettings']['containerHostBatchBindMount']
        task['userIdentity']['autoUser']['elevationLevel'] = 'root'
        with self.assertRaises(AssertionError):
            shape(task, definitions['BatchTaskCreateOptions'], definitions)

    def test_only_trusted_host_stages_receive_transfer_metadata(self):
        job = job_spec(self.config, self.metadata, self.etag)
        task = task_spec(self.config, self.identifier)
        self.assertNotIn('commonEnvironmentSettings', job)
        self.assertNotIn('environmentSettings', task)
        for name in ['jobPreparationTask', 'jobReleaseTask']:
            value = {item['name']: item['value'] for item in job[name]['environmentSettings']}
            self.assertEqual(set(value), {'DOCUMENT_JOB', 'DOCUMENT_TRANSFER_IMAGE'})
            transfer = json.loads(value['DOCUMENT_JOB'])
            self.assertEqual(transfer['request'], self.metadata)
            self.assertNotIn('workerClientId', transfer)
            self.assertNotIn('private source fixture', json.dumps(job))
        self.assertEqual(len(job['id']), 64)

    def test_parser_native_mounts_and_resources(self):
        task = task_spec(self.config, self.identifier)
        settings = task['containerSettings']
        self.assertEqual(settings['containerHostBatchBindMounts'], [])
        self.assertEqual(settings['workingDirectory'], 'containerImageDefault')
        self.assertEqual(task['userIdentity']['autoUser']['elevationLevel'], 'nonadmin')
        options = shlex.split(settings['containerRunOptions'])
        for item in ['--rm', '--network=none', '--read-only', '--cap-drop=ALL',
                     '--security-opt=no-new-privileges:true', '--pids-limit=128',
                     '--memory=2g', '--memory-swap=2g', '--cpus=2', '--log-driver=none']:
            self.assertIn(item, options)
        mounts = [item for item in options if item.startswith('--mount=')]
        self.assertEqual(len(mounts), 2)
        self.assertIn('target=/input,readonly', mounts[0])
        self.assertIn('target=/output', mounts[1])
        self.assertNotIn('--user=0', settings['containerRunOptions'])
        self.assertNotIn('docker.sock', json.dumps(task))
        self.assertEqual(task['constraints']['maxTaskRetryCount'], 0)

    def test_owned_lifecycle_waits_preparation_and_does_not_terminate_empty_job(self):
        job = job_spec(self.config, self.metadata, self.etag)
        self.assertTrue(job['jobPreparationTask']['waitForSuccess'])
        self.assertTrue(job['jobPreparationTask']['rerunOnNodeRebootAfterSuccess'])
        self.assertEqual(job['onAllTasksComplete'], 'noaction')
        self.assertEqual(job['jobReleaseTask']['maxWallClockTime'], 'PT1M')
        self.assertEqual(job['constraints']['maxTaskRetryCount'], 0)

    def test_verified_fixed_host_helper_is_not_a_shell_or_download(self):
        job = job_spec(self.config, self.metadata, self.etag)
        for name, mode in [('jobPreparationTask', 'prepare'), ('jobReleaseTask', 'release')]:
            args = shlex.split(job[name]['commandLine'])
            self.assertEqual(args[:3], ['/usr/bin/python3', '-I', '-c'])
            self.assertEqual(len(args), 4)
            compile(args[3], '<host-bootstrap>', 'exec')
            self.assertIn(self.config['hostHelperSha256'], args[3])
            self.assertIn('O_NOFOLLOW', args[3])
            self.assertIn('s.st_uid==0', args[3])
            self.assertIn(repr(mode), args[3])
            self.assertNotIn('https:', args[3])
            self.assertNotIn('$', args[3])

    def test_config_rejects_aliases_mutable_images_authority_sharing_and_injection(self):
        for field, value in [('format', 'enterprise-google-document-job-v1'),
                             ('workerClientId', self.config['transferClientId']),
                             ('poolId', 'existing-mixed-pool'),
                             ('storageAccount', 'https://arbitrary.example'),
                             ('container', 'input/../../other'),
                             ('parserImage', 'ownedregistry.azurecr.io/parser:latest'),
                             ('transferImage', self.config['parserImage']),
                             ('hostHelperSha256', 'abc;touch /tmp/owned'),
                             ('parserImage', 'otherregistry.azurecr.io/parser@sha256:' + 'a' * 64)]:
            with self.subTest(field=field, value=value):
                changed = {**self.config, field: value}
                with self.assertRaises(ValueError): configuration(changed)
        with self.assertRaises(ValueError): configuration({**self.config, 'sourceToken': 'private'})

    def test_request_rejects_content_or_opaque_id_tampering(self):
        for field, value in [('requestId', '../../other'), ('sha256', 'x' * 64),
                             ('format', 'other'), ('mediaType', 'text/x-python')]:
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    transfer_metadata(self.config, {**self.metadata, field: value}, self.etag)
        with self.assertRaises(ValueError):
            transfer_metadata(self.config, {**self.metadata, 'sourceUrl': 'https://private'}, self.etag)
        for value in ['*', 'unquoted', self.etag + '\r\nAuthorization: private', 1]:
            with self.assertRaises(ValueError): transfer_metadata(self.config, self.metadata, value)
        with self.assertRaises(ValueError): volume_names('d' * 65)

    def test_readback_rejects_network_mount_and_identity_weakening(self):
        base = task_spec(self.config, self.identifier)
        self.assertTrue(verify_task(self.config, self.identifier, {**base, 'state': 'completed'}))
        mutations = []
        for key, value in [('containerHostBatchBindMounts', None), ('workingDirectory', 'taskWorkingDirectory'),
                           ('containerRunOptions', base['containerSettings']['containerRunOptions'].replace('--network=none', '--network=host'))]:
            changed = copy.deepcopy(base)
            changed['containerSettings'][key] = value
            mutations.append(changed)
        changed = copy.deepcopy(base)
        changed['userIdentity']['autoUser']['elevationLevel'] = 'admin'
        mutations.append(changed)
        for key in ['environmentSettings', 'resourceFiles', 'applicationPackageReferences', 'outputFiles']:
            mutations.append({**base, key: []})
        for changed in mutations:
            with self.assertRaises(ValueError): verify_task(self.config, self.identifier, changed)

    def test_readback_rejects_job_adoption_and_cleanup_substitution(self):
        base = job_spec(self.config, self.metadata, self.etag)
        self.assertTrue(verify_job(self.config, self.metadata, self.etag, {**base, 'state': 'active'}))
        changed = copy.deepcopy(base)
        changed['jobReleaseTask']['commandLine'] = '/bin/true'
        with self.assertRaises(ValueError): verify_job(self.config, self.metadata, self.etag, changed)
        for key, value in [('commonEnvironmentSettings', []), ('jobManagerTask', {}),
                           ('poolInfo', {'poolId': 'foreign'}), ('metadata', [])]:
            with self.assertRaises(ValueError):
                verify_job(self.config, self.metadata, self.etag, {**base, key: value})
        self.assertNotEqual(fingerprint(self.config), fingerprint({**self.config, 'poolId': 'document-next'}))

    def test_incomplete_provider_is_not_enabled_in_worker_inventory(self):
        inventory = json.loads((ROOT / 'src/runtime/enterprise-application-manifest.json').read_text())
        self.assertNotIn('azure', inventory['nativeDocumentWorkerProviders'])


if __name__ == '__main__':
    unittest.main()
