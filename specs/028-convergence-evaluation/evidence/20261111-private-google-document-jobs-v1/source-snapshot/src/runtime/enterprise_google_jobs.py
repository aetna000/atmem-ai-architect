"""Owned Google Batch per-file jobs; no source/model/SQL credentials in workloads.

The VM transfer identity is trusted, distinct from the question worker. Only the
parser runnable is network-blocked. Its mounts are explicit local POSIX paths;
no FUSE, identity mounts, background listener or shared parser service is used.
Cloud IAM/network/provisioning remain required parts of the generated composition.
"""
import json
import re
import time
import uuid
from urllib.parse import quote
import requests
from enterprise_document_contract import MAX_INPUT
from enterprise_document_job import MAX_ENVELOPE, request, result, unique
from enterprise_sources import SourceUnavailable
from workflow_connection import google_metadata_token


def configuration(value):
    fields = {'format', 'projectId', 'region', 'bucket', 'parserImage', 'transferImage',
              'workerServiceAccount', 'vmServiceAccount', 'network', 'subnetwork'}
    if not isinstance(value, dict) or set(value) != fields or value['format'] != 'enterprise-google-document-job-v1':
        raise ValueError('Use the exact owned Google document-job configuration')
    patterns = {'projectId': '[a-z][a-z0-9-]{4,28}[a-z0-9]', 'region': '[a-z]+-[a-z]+[1-9][0-9]?',
                'bucket': '[a-z0-9][a-z0-9-]{1,61}[a-z0-9]'}
    for key, pattern in patterns.items():
        if not isinstance(value[key], str) or not re.fullmatch(pattern, value[key]): raise ValueError('Invalid owned Google job destination')
    project, region = value['projectId'], value['region']
    for key in ['workerServiceAccount', 'vmServiceAccount']:
        if not isinstance(value[key], str) or not re.fullmatch('[a-z][a-z0-9-]{4,28}[a-z0-9]@' + re.escape(project) + r'\.iam\.gserviceaccount\.com', value[key]):
            raise ValueError('Use distinct existing owned worker and VM service accounts')
    if value['workerServiceAccount'] == value['vmServiceAccount']: raise ValueError('Parser transfer VM must not inherit worker authority')
    for key in ['parserImage', 'transferImage']:
        if not isinstance(value[key], str) or not re.fullmatch(re.escape(region + '-docker.pkg.dev/' + project + '/') + r'[a-z][a-z0-9_-]{0,62}/[a-z][a-z0-9_-]{0,62}(?:/[a-z][a-z0-9_-]{0,62}){0,3}@sha256:[0-9a-f]{64}', value[key]):
            raise ValueError('Use immutable owned regional Artifact Registry images')
    for key, prefix in [('network', 'projects/' + project + '/global/networks/'),
                        ('subnetwork', 'projects/' + project + '/regions/' + region + '/subnetworks/')]:
        if not isinstance(value[key], str) or not re.fullmatch(re.escape(prefix) + '[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?', value[key]):
            raise ValueError('Use explicit same-project regional private networking')
    return dict(value)


def identity(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value): raise ValueError('Invalid owned per-file identity')
    return value


def object_key(identifier, side):
    if side not in {'input', 'result'}: raise ValueError('Use the owned input or result object')
    return 'document-jobs/' + identity(identifier) + '/' + side


def transfer_metadata(config, metadata, generation):
    if (not isinstance(metadata, dict) or set(metadata) != {'format', 'requestId', 'sha256', 'mediaType'} or
        metadata['format'] != 'enterprise-document-job-v1' or not isinstance(metadata['sha256'], str) or
        not re.fullmatch('[0-9a-f]{64}', metadata['sha256'])):
        raise ValueError('Use the exact byte-bound document request')
    identity(metadata['requestId'])
    from enterprise_document_contract import media_type
    if media_type(metadata['mediaType']) != metadata['mediaType']: raise ValueError('Use canonical document MIME')
    if not isinstance(generation, str) or not re.fullmatch('[1-9][0-9]{0,29}', generation): raise ValueError('Use the immutable native input generation')
    return {'format': 'enterprise-google-document-transfer-v1', 'projectId': config['projectId'],
            'region': config['region'], 'bucket': config['bucket'], 'request': dict(metadata), 'inputGeneration': generation}


def job_spec(config, metadata, generation):
    owned = configuration(config)
    transfer = transfer_metadata(owned, metadata, generation)
    base = '/mnt/disks/share/document-' + metadata['requestId']
    common = '--read-only --cap-drop=ALL --security-opt=no-new-privileges:true --pids-limit=128 --log-driver=none'
    def bridge(mode, user):
        return {'container': {'imageUri': owned['transferImage'], 'entrypoint': 'python',
            'commands': ['-I', '/app/enterprise_google_transfer.py', mode],
            'volumes': [base + ':/work:' + ('rw' if mode == 'download' else 'ro')],
            'options': common + ' --user=' + user + (' --cap-add=CHOWN' if mode == 'download' else '')},
            'environment': {'variables': {'DOCUMENT_JOB': json.dumps(transfer, separators=(',', ':'))}},
            'timeout': '25s'}
    parser = {'container': {'imageUri': owned['parserImage'], 'entrypoint': 'python',
        'commands': ['-I', '/app/enterprise_document_cli.py', '--job'],
        'volumes': [base + '/input:/input:ro', base + '/output:/output:rw'],
        'options': common + ' --user=10001:10001 --tmpfs=/tmp:rw,noexec,nosuid,size=128m',
        'blockExternalNetwork': True}, 'timeout': '110s'}
    return {'taskGroups': [{'taskCount': '1', 'parallelism': '1', 'taskCountPerNode': '1',
        'taskSpec': {'runnables': [bridge('download', '0:0'), parser, bridge('upload', '10001:10001')],
            'maxRetryCount': 0, 'maxRunDuration': '160s', 'computeResource': {'cpuMilli': '2000', 'memoryMib': '2048'}}}],
        'allocationPolicy': {'location': {'allowedLocations': ['regions/' + owned['region']]},
            'serviceAccount': {'email': owned['vmServiceAccount']},
            'network': {'networkInterfaces': [{'network': owned['network'], 'subnetwork': owned['subnetwork'], 'noExternalIpAddress': True}]},
            'instances': [{'policy': {'machineType': 'e2-standard-2', 'provisioningModel': 'STANDARD'}, 'blockProjectSshKeys': True}]},
        'logsPolicy': {'destination': 'DESTINATION_UNSPECIFIED'}, 'labels': {'atmem-workload': 'document-parser'}}


class GoogleDocumentApi:
    def __init__(self, *, session=None, credential=None):
        self.session = session or requests.Session(); self.session.trust_env = False
        self.credential = credential or google_metadata_token

    def send(self, method, url, *, body=None, data=None, params=None, limit=32768, allow_missing=False):
        # Destinations are constructed internally, never supplied by a document,
        # browser, model or source redirect. No environment proxies or redirects.
        if not url.startswith(('https://batch.googleapis.com/v1/projects/', 'https://storage.googleapis.com/storage/v1/b/',
                               'https://storage.googleapis.com/upload/storage/v1/b/')):
            raise ValueError('Use the fixed native document APIs')
        try:
            token = self.credential()
            if not isinstance(token, str) or not 8 <= len(token) <= 20000 or any(ord(c) < 33 or ord(c) > 126 for c in token): raise ValueError()
            started = time.monotonic()
            headers = {'Authorization': 'Bearer ' + token}
            if data is not None: headers['Content-Type'] = 'application/octet-stream'
            with self.session.request(method, url, headers=headers, json=body, data=data, params=params,
                stream=True, allow_redirects=False, timeout=(2, 8)) as response:
                if allow_missing and response.status_code == 404: return None
                if response.status_code not in {200, 201, 204}: raise ValueError()
                raw = bytearray()
                for chunk in response.iter_content(16384):
                    raw.extend(chunk)
                    if len(raw) > limit or time.monotonic() - started > 15: raise ValueError()
                return bytes(raw)
        except Exception:
            raise SourceUnavailable('document_job_unavailable') from None

    def json(self, *args, **kwargs):
        raw = self.send(*args, **kwargs)
        if raw is None: return None
        try:
            value = json.loads(raw, object_pairs_hook=unique)
            if not isinstance(value, dict): raise ValueError()
            return value
        except Exception: raise SourceUnavailable('document_job_unavailable') from None


class GoogleDocumentObjects:
    def __init__(self, bucket, api):
        if not isinstance(bucket, str) or not re.fullmatch('[a-z0-9][a-z0-9-]{1,61}[a-z0-9]', bucket): raise ValueError('Use the owned ephemeral bucket')
        self.bucket, self.api = bucket, api
        self.base = 'https://storage.googleapis.com/storage/v1/b/' + bucket

    def url(self, identifier, side): return self.base + '/o/' + quote(object_key(identifier, side), safe='')

    def put(self, identifier, side, raw):
        maximum = MAX_INPUT if side == 'input' else MAX_ENVELOPE
        if not isinstance(raw, bytes) or not 0 < len(raw) <= maximum: raise ValueError('Invalid bounded document object')
        value = self.api.json('POST', 'https://storage.googleapis.com/upload/storage/v1/b/' + self.bucket + '/o',
            params={'uploadType': 'media', 'name': object_key(identifier, side), 'ifGenerationMatch': '0', 'fields': 'generation'}, data=raw)
        generation = value.get('generation')
        if not isinstance(generation, str) or not re.fullmatch('[1-9][0-9]{0,29}', generation): raise SourceUnavailable('document_job_unavailable')
        return generation

    def load(self, identifier, side, generation=None):
        params = {'alt': 'media'}
        if generation is not None:
            if not isinstance(generation, str) or not re.fullmatch('[1-9][0-9]{0,29}', generation): raise ValueError('Invalid native generation')
            params['generation'] = generation
        return self.api.send('GET', self.url(identifier, side), params=params, limit=MAX_INPUT if side == 'input' else MAX_ENVELOPE)

    def delete(self, identifier, side): self.api.send('DELETE', self.url(identifier, side), allow_missing=True)


class GoogleBatchDocuments:
    """Controller lifecycle; successful delete requests alone do not prove exit."""
    def __init__(self, config, *, api=None, deadline=140, poll_seconds=1):
        self.config = configuration(config)
        if type(deadline) is not int or not 1 <= deadline <= 140 or type(poll_seconds) not in {int, float} or not .01 <= poll_seconds <= 2:
            raise ValueError('Use bounded owned document deadlines')
        self.api = api or GoogleDocumentApi()
        self.objects = GoogleDocumentObjects(self.config['bucket'], self.api)
        self.deadline, self.poll_seconds = deadline, poll_seconds
        self.parent = 'projects/' + self.config['projectId'] + '/locations/' + self.config['region']
        self.base = 'https://batch.googleapis.com/v1/' + self.parent

    def __call__(self, raw, mime):
        raise SourceUnavailable('source_validation_required')

    def from_source(self, raw, mime, guard):
        if not callable(guard): raise ValueError('Supply the current source/company/job check')
        identifier = uuid.uuid4().hex + uuid.uuid4().hex
        metadata = request(raw, mime, identifier)
        name = self.parent + '/jobs/document-' + identifier[:32]
        url = 'https://batch.googleapis.com/v1/' + name
        started = time.monotonic()
        attempted = False
        # Cleanup always inspects this unique owned name, including lost create
        # acknowledgements. It never lists/deletes another project's jobs/files.
        try:
            guard()
            attempted = True
            generation = self.objects.put(identifier, 'input', raw)
            guard()
            value = self.api.json('POST', self.base + '/jobs', params={'jobId': name.rsplit('/', 1)[1]},
                body=job_spec(self.config, metadata, generation))
            if value.get('name') != name: raise SourceUnavailable('document_job_unavailable')
            while True:
                guard()
                if time.monotonic() - started > self.deadline: raise SourceUnavailable('document_job_unavailable')
                current = self.api.json('GET', url)
                if current.get('name') != name: raise SourceUnavailable('document_job_unavailable')
                state = current.get('status', {}).get('state')
                if state == 'SUCCEEDED': break
                if state not in {'QUEUED', 'SCHEDULED', 'RUNNING'}: raise SourceUnavailable('document_job_unavailable')
                time.sleep(self.poll_seconds)
            guard()
            encoded = self.objects.load(identifier, 'result')
            value = result(raw, mime, identifier, encoded)
            guard()
            return value
        finally:
            if attempted: self.cleanup(name, identifier)

    def cleanup(self, name, identifier):
        failure = False
        try:
            operation = self.api.json('DELETE', 'https://batch.googleapis.com/v1/' + name, allow_missing=True)
            if operation is not None:
                expected = self.parent + '/operations/'
                op = operation.get('name')
                if not isinstance(op, str) or not re.fullmatch(re.escape(expected) + '[A-Za-z0-9_-]{1,200}', op): raise ValueError()
                deadline = time.monotonic() + 30
                while True:
                    if type(operation.get('done', False)) is not bool: raise ValueError()
                    if operation.get('done', False): break
                    if time.monotonic() > deadline: raise ValueError()
                    time.sleep(self.poll_seconds)
                    operation = self.api.json('GET', 'https://batch.googleapis.com/v1/' + op)
                    if operation.get('name') != op: raise ValueError()
                if operation.get('error'): raise ValueError()
        except Exception: failure = True
        for side in ['input', 'result']:
            try: self.objects.delete(identifier, side)
            except Exception: failure = True
        if failure: raise SourceUnavailable('document_job_cleanup_unavailable') from None
