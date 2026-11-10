"""Owned Azure Batch document request contract, not an admitted native executor.

Host preparation/release helpers, private pool/IAM provisioning, durable recovery
and actual node-agent checks must be composed before enabling this provider in
enterprise_worker. Schema-valid requests alone do not prove a running sandbox.
"""
import hashlib
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
            'metadata': [{'name': 'atmem-owner', 'value': fingerprint(owned)}]}


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
    if not isinstance(reply, dict) or any(reply.get(key) != value for key, value in expected.items()):
        raise ValueError('Azure document job ownership or execution contract changed')
    if any(key in reply for key in ['jobManagerTask', 'commonEnvironmentSettings', 'networkConfiguration']):
        raise ValueError('Unexpected Azure document job authority')
    return True


def verify_task(config, identifier, reply):
    expected = task_spec(config, identifier)
    if not isinstance(reply, dict) or any(reply.get(key) != value for key, value in expected.items()):
        raise ValueError('Azure document parser isolation contract changed')
    if any(key in reply for key in ['environmentSettings', 'resourceFiles', 'outputFiles',
                                    'applicationPackageReferences', 'multiInstanceSettings', 'dependsOn']):
        raise ValueError('Unexpected Azure parser input or authority')
    return True
