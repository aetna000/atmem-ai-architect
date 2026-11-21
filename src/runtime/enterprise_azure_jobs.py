"""Owned Azure Batch document request contract, not an admitted native executor.

Host preparation/release helpers, private pool/IAM provisioning, durable recovery
and actual node-agent checks must be composed before enabling this provider in
enterprise_worker. Schema-valid requests alone do not prove a running sandbox.
"""
import hashlib
import copy
import json
import re
import shlex

API_VERSION = '2026-10-01'
FORMAT = 'enterprise-azure-document-job-v1'
_UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
_HASH = r'[0-9a-f]{64}'


def configuration(value):
    fields = {'format', 'subscriptionId', 'region', 'resourceGroup', 'batchAccount',
              'poolId', 'storageAccount', 'container', 'workerClientId',
              'transferClientId', 'parserImage', 'transferImage', 'hostHelperSha256'}
    if not isinstance(value, dict) or set(value) != fields or value['format'] != FORMAT:
        raise ValueError('Use the exact owned Azure document-job configuration')
    patterns = {'subscriptionId': _UUID, 'region': r'[a-z][a-z0-9]{1,30}',
                'resourceGroup': r'[A-Za-z0-9_()-](?:[A-Za-z0-9_().-]{0,88}[A-Za-z0-9_()-])?',
                'batchAccount': r'[a-z0-9]{3,24}', 'poolId': r'document-[a-z0-9-]{1,54}',
                'storageAccount': r'[a-z0-9]{3,24}',
                'container': r'[a-z0-9]+(?:-[a-z0-9]+)*',
                'workerClientId': _UUID, 'transferClientId': _UUID,
                'hostHelperSha256': _HASH}
    for name, pattern in patterns.items():
        if not isinstance(value[name], str) or not re.fullmatch(pattern, value[name]):
            raise ValueError('Invalid owned Azure job destination or identity')
    if not 3 <= len(value['container']) <= 63:
        raise ValueError('Use the owned temporary container')
    if value['workerClientId'] == value['transferClientId']:
        raise ValueError('Transfer hosts must not inherit the question worker identity')
    registry = None
    for name in ['parserImage', 'transferImage']:
        if not isinstance(value[name], str) or not re.fullmatch(
                r'[a-z0-9]{5,50}\.azurecr\.io/[a-z0-9]+(?:[._/-][a-z0-9]+)*@sha256:' + _HASH, value[name]):
            raise ValueError('Use immutable owned Azure Container Registry artifacts')
        current = value[name].split('/', 1)[0]
        if registry is not None and registry != current:
            raise ValueError('Use the same owned artifact registry')
        registry = current
    if value['parserImage'] == value['transferImage']:
        raise ValueError('Keep parser and trusted transfer artifacts separate')
    # Registry/account names alone cannot prove subscription or regional ownership.
    # The future native preflight must check ARM identity/location, not infer them.
    return dict(value)


def identity(value):
    if not isinstance(value, str) or not re.fullmatch(_HASH, value):
        raise ValueError('Use the exact opaque per-file identity')
    return value


def transfer_metadata(config, metadata, etag):
    owned = configuration(config)
    if (not isinstance(metadata, dict) or set(metadata) != {'format', 'requestId', 'sha256', 'mediaType'}
            or metadata['format'] != 'enterprise-document-job-v1'
            or not isinstance(metadata['sha256'], str) or not re.fullmatch(_HASH, metadata['sha256'])):
        raise ValueError('Use the exact byte-bound document request')
    identity(metadata['requestId'])
    from enterprise_document_contract import MEDIA_TYPES, media_type
    if (media_type(metadata['mediaType']) != metadata['mediaType'] or
            metadata['mediaType'] not in MEDIA_TYPES | {'application/octet-stream'}):
        raise ValueError('Use a supported canonical document MIME')
    # Azure Blob ETags are conditional tokens; never use one as a content digest.
    if not isinstance(etag, str) or not re.fullmatch(r'"0x[0-9A-Fa-f]{1,32}"', etag):
        raise ValueError('Use the acknowledged native Azure input ETag')
    return {'format': 'enterprise-azure-document-transfer-v1',
            'subscriptionId': owned['subscriptionId'], 'region': owned['region'],
            'resourceGroup': owned['resourceGroup'], 'storageAccount': owned['storageAccount'],
            'container': owned['container'], 'transferClientId': owned['transferClientId'],
            'request': dict(metadata), 'inputETag': etag}


def volume_names(identifier):
    # IDs are 64 hex characters, also satisfying Batch's maximum job ID length.
    token = identity(identifier)
    return ('atmem-document-' + token + '-input', 'atmem-document-' + token + '-output')


def _host_command(owned, mode):
    if mode not in {'prepare', 'release'}:
        raise ValueError('Use the fixed trusted host operation')
    digest = owned['hostHelperSha256']
    path = '/opt/atmem/document-host/' + digest + '/enterprise_azure_host.py'
    # No shell/path expansion, application-package default version, URL fetching,
    # inherited PYTHONPATH or unverified host script. The root-owned helper tree
    # and its parents are separately required by pool provisioning/preflight.
    code = (
        'import os,stat,hashlib,sys;'
        'f=os.open(' + repr(path) + ',os.O_RDONLY|os.O_NOFOLLOW);'
        's=os.fstat(f);'
        'assert stat.S_ISREG(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022 and s.st_size<=262144;'
        'b=os.read(f,262145);os.close(f);'
        'assert len(b)==s.st_size and hashlib.sha256(b).hexdigest()==' + repr(digest) + ';'
        'sys.argv=[' + repr(path) + ',' + repr(mode) + '];'
        'exec(compile(b,' + repr(path) + ',"exec"),{"__name__":"__main__","__file__":' + repr(path) + '})'
    )
    return '/usr/bin/python3 -I -c ' + shlex.quote(code)


def job_spec(config, metadata, etag):
    owned = configuration(config)
    transfer = transfer_metadata(owned, metadata, etag)
    encoded = json.dumps(transfer, separators=(',', ':'), allow_nan=False)
    # Never use commonEnvironmentSettings: those are inherited by the parser.
    environment = [{'name': 'DOCUMENT_JOB', 'value': encoded},
                   {'name': 'DOCUMENT_TRANSFER_IMAGE', 'value': owned['transferImage']}]
    admin = {'autoUser': {'scope': 'task', 'elevationLevel': 'admin'}}
    return {'id': metadata['requestId'], 'poolInfo': {'poolId': owned['poolId']},
            'constraints': {'maxWallClockTime': 'PT8M', 'maxTaskRetryCount': 0},
            # Keep active until its single task is observed. terminatejob here
            # would complete an empty job before the task can be submitted.
            'onAllTasksComplete': 'noaction',
            'jobPreparationTask': {'id': 'prepare', 'commandLine': _host_command(owned, 'prepare'),
                'waitForSuccess': True, 'rerunOnNodeRebootAfterSuccess': True,
                'userIdentity': admin, 'environmentSettings': environment,
                'constraints': {'maxWallClockTime': 'PT1M', 'maxTaskRetryCount': 0, 'retentionTime': 'PT0S'}},
            'jobReleaseTask': {'id': 'release', 'commandLine': _host_command(owned, 'release'),
                'userIdentity': {'autoUser': dict(admin['autoUser'])},
                'environmentSettings': [dict(item) for item in environment],
                'maxWallClockTime': 'PT1M', 'retentionTime': 'PT0S'},
            'metadata': [{'name': 'atmem-owner', 'value': fingerprint(owned)},
                {'name': 'atmem-parser-image', 'value': owned['parserImage']},
                {'name': 'atmem-helper-sha256', 'value': owned['hostHelperSha256']},
                {'name': 'atmem-worker-client', 'value': owned['workerClientId']}]}


def task_spec(config, identifier):
    owned = configuration(config)
    source, target = volume_names(identifier)
    options = ['--rm', '--network=none', '--read-only', '--cap-drop=ALL',
               '--security-opt=no-new-privileges:true', '--pids-limit=128',
               '--memory=2g', '--memory-swap=2g', '--cpus=2', '--log-driver=none',
               '--label=atmem.document.owner=' + cleanup_owner(owned),
               '--label=atmem.document.request=' + identity(identifier),
               '--label=atmem.document.policy=' + fingerprint(owned),
               '--label=atmem.document.stage=parser',
               '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=128m',
               '--mount=type=volume,source=' + source + ',target=/input,readonly',
               '--mount=type=volume,source=' + target + ',target=/output']
    return {'id': 'document', 'commandLine': 'python -I /app/enterprise_document_cli.py --job',
            'containerSettings': {'imageName': owned['parserImage'],
                'containerRunOptions': ' '.join(options),
                'containerHostBatchBindMounts': [], 'workingDirectory': 'containerImageDefault'},
            # Batch maps a native non-admin task UID. Do not assume the image's
            # 10001 UID or give the untrusted parser admin to bypass permissions.
            'userIdentity': {'autoUser': {'scope': 'task', 'elevationLevel': 'nonadmin'}},
            'constraints': {'maxWallClockTime': 'PT2M', 'maxTaskRetryCount': 0, 'retentionTime': 'PT0S'}}


def fingerprint(config):
    return hashlib.sha256(json.dumps(configuration(config), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def cleanup_owner(config):
    checked = configuration(config)
    keys = ['subscriptionId', 'region', 'resourceGroup', 'batchAccount', 'poolId',
            'storageAccount', 'container', 'transferClientId']
    return hashlib.sha256(json.dumps({**{key: checked[key] for key in keys},
        'registry': checked['parserImage'].split('/')[0]}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def verify_job(config, metadata, etag, reply):
    """Reject unowned/replaced jobs before adopting them during recovery."""
    expected = job_spec(config, metadata, etag)
    if not isinstance(reply, dict) or not typed_equal(job_observation(expected), job_observation({key: reply.get(key) for key in expected})):
        raise ValueError('Azure document job ownership or execution contract changed')
    if any(key in reply for key in ['jobManagerTask', 'commonEnvironmentSettings', 'networkConfiguration']):
        raise ValueError('Unexpected Azure document job authority')
    return True


def verify_task(config, identifier, reply):
    expected = task_spec(config, identifier)
    if not isinstance(reply, dict) or any(not typed_equal(value, reply.get(key)) for key, value in expected.items()):
        raise ValueError('Azure document parser isolation contract changed')
    if any(key in reply for key in ['environmentSettings', 'resourceFiles', 'outputFiles',
                                    'applicationPackageReferences', 'multiInstanceSettings', 'dependsOn']):
        raise ValueError('Unexpected Azure parser input or authority')
    return True


def typed_equal(expected, observed):
    if type(expected) is not type(observed): return False
    if isinstance(expected, dict):
        return set(expected) == set(observed) and all(typed_equal(value, observed[key]) for key, value in expected.items())
    if isinstance(expected, list):
        return len(expected) == len(observed) and all(typed_equal(left, right) for left, right in zip(expected, observed))
    return expected == observed


def job_observation(value):
    """Only documented name/value arrays are unordered; no fields are dropped."""
    value = copy.deepcopy(value)
    arrays = [value.get('metadata')]
    for key in ['jobPreparationTask', 'jobReleaseTask']:
        task = value.get(key)
        if isinstance(task, dict): arrays.append(task.get('environmentSettings'))
    for items in arrays:
        if not isinstance(items, list): raise ValueError('Use exact native name/value settings')
        names = set()
        for item in items:
            if (not isinstance(item, dict) or set(item) != {'name', 'value'} or
                    not isinstance(item['name'], str) or not isinstance(item['value'], str) or item['name'] in names):
                raise ValueError('Ambiguous native name/value settings')
            names.add(item['name'])
        items.sort(key=lambda entry: entry['name'])
    return value


def recover_job(config, identifier, reply):
    """Recover only an exact owned historical job, without executing its text.

    The SQL ledger stores opaque IDs, not source metadata or arbitrary cleanup
    endpoints. The native job supplies its bounded original byte/ETag/artifact
    binding; the stable destination and full immutable shape are checked here.
    This result is for observation/cleanup, never permission to launch old code.
    """
    current = configuration(config)
    identity(identifier)
    if not isinstance(reply, dict) or reply.get('id') != identifier:
        raise ValueError('Native job identity changed')
    def settings(value, names):
        if not isinstance(value, list) or len(value) != len(names):
            raise ValueError('Use exact original job metadata')
        result = {}
        for entry in value:
            if (not isinstance(entry, dict) or set(entry) != {'name', 'value'} or
                    not isinstance(entry['name'], str) or entry['name'] not in names or entry['name'] in result or not isinstance(entry['value'], str)):
                raise ValueError('Ambiguous original job metadata')
            result[entry['name']] = entry['value']
        return result
    metadata = settings(reply.get('metadata'), {'atmem-owner', 'atmem-parser-image',
                                               'atmem-helper-sha256', 'atmem-worker-client'})
    prepare = reply.get('jobPreparationTask')
    if not isinstance(prepare, dict): raise ValueError('Original preparation contract is required')
    environment = settings(prepare.get('environmentSettings'), {'DOCUMENT_JOB', 'DOCUMENT_TRANSFER_IMAGE'})
    historical = configuration({**current, 'parserImage': metadata['atmem-parser-image'],
        'transferImage': environment['DOCUMENT_TRANSFER_IMAGE'], 'hostHelperSha256': metadata['atmem-helper-sha256'],
        'workerClientId': metadata['atmem-worker-client']})
    if cleanup_owner(historical) != cleanup_owner(current):
        raise ValueError('Do not adopt a different cleanup destination or artifact registry')
    if not 0 < len(environment['DOCUMENT_JOB'].encode()) <= 4096:
        raise ValueError('Original transfer metadata exceeds the bound')
    from enterprise_document_job import unique
    value = json.loads(environment['DOCUMENT_JOB'], object_pairs_hook=unique)
    if not isinstance(value, dict) or not isinstance(value.get('request'), dict) or value['request'].get('requestId') != identifier:
        raise ValueError('Original file identity changed')
    expected = transfer_metadata(historical, value['request'], value.get('inputETag'))
    if value != expected:
        raise ValueError('Original transfer destination changed')
    verify_job(historical, expected['request'], expected['inputETag'], reply)
    return historical, expected


def terminal_writer_nodes(config, identifier, job, task, status):
    """Seal the complete native preparation-node set only after job completion.

    A preflight snapshot or one task's current node omits earlier retry nodes.
    This function observes provider metadata; it does not certify local cleanup
    or erase storage. Every returned node still requires its own acknowledgement.
    """
    historical, transfer = recover_job(config, identifier, job)
    if job.get('state') != 'completed': raise ValueError('Native work has not completed termination/release')
    if (not isinstance(status, dict) or status.get('odata.nextLink') or status.get('@odata.nextLink') or
            not isinstance(status.get('value'), list) or len(status['value']) > 100):
        raise ValueError('Observe the complete native preparation/release history')
    nodes = set()
    for row in status['value']:
        if (not isinstance(row, dict) or row.get('poolId') != historical['poolId'] or
                not isinstance(row.get('nodeId'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', row['nodeId']) or
                row['nodeId'] in nodes or not isinstance(row.get('jobPreparationTaskExecutionInfo'), dict) or
                row['jobPreparationTaskExecutionInfo'].get('state') != 'completed'):
            raise ValueError('Native preparation history is incomplete or foreign')
        release = row.get('jobReleaseTaskExecutionInfo')
        if release is not None and (not isinstance(release, dict) or release.get('state') != 'completed'):
            raise ValueError('Native release is still active or unknown')
        nodes.add(row['nodeId'])
    if task is not None:
        verify_task(historical, identifier, task)
        if task.get('state') != 'completed': raise ValueError('Native parser task is not terminal')
        assigned = task.get('nodeInfo')
        if assigned is not None and (not isinstance(assigned, dict) or assigned.get('poolId') != historical['poolId'] or
                                     assigned.get('nodeId') not in nodes):
            raise ValueError('Native task assignment is missing from complete preparation history')
    return historical, transfer, frozenset(nodes)
