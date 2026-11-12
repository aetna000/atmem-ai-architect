"""Owned Batch pool observation before source upload; never provisions a pool.

The contract is separate from the fourteen-field job/host policy to avoid a
bootstrap/hash cycle. Native installation, IAM/network resources and actual pool
image compatibility still need infrastructure/artifact and account evidence.
"""
import copy
import hashlib
import json
import re
from enterprise_azure_jobs import configuration as job_configuration, fingerprint, typed_equal
from enterprise_sources import SourceUnavailable


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def configuration(value, job):
    job = job_configuration(job)
    fields = {'format', 'identityResourceId', 'subnetId', 'vmSize', 'imageReference',
              'nodeAgentSkuId', 'startTaskSha256', 'dedicatedNodes', 'taskSlotsPerNode'}
    if not isinstance(value, dict) or set(value) != fields or value['format'] != 'enterprise-azure-document-pool-v1':
        raise ValueError('Use the exact owned Azure pool contract')
    base = re.escape('/subscriptions/' + job['subscriptionId'] + '/resourceGroups/')
    group = r'[A-Za-z0-9_().-]{1,90}'
    name = r'[A-Za-z0-9_-]{1,80}'
    patterns = {'identityResourceId': base + group + r'/providers/Microsoft.ManagedIdentity/userAssignedIdentities/' + name,
                'subnetId': base + group + r'/providers/Microsoft.Network/virtualNetworks/' + name + '/subnets/' + name,
                'vmSize': r'Standard_[A-Za-z0-9_]{2,64}', 'startTaskSha256': r'[0-9a-f]{64}',
                'nodeAgentSkuId': r'batch\.node\.[a-z][a-z0-9 ._-]{1,64}'}
    for key, pattern in patterns.items():
        if not isinstance(value[key], str) or not re.fullmatch(pattern, value[key]):
            raise ValueError('Invalid owned Azure pool placement or artifact contract')
    image = value['imageReference']
    if (not isinstance(image, dict) or set(image) != {'publisher', 'offer', 'sku', 'version'} or
            not isinstance(image['publisher'], str) or not isinstance(image['offer'], str) or
            (image['publisher'], image['offer']) not in {('microsoft-dsvm', 'ubuntu-hpc'), ('almalinux', '8-hpc-gen1'), ('almalinux', '8-hpc-gen2')} or
            not isinstance(image['sku'], str) or not re.fullmatch('[a-zA-Z0-9_.-]{1,64}', image['sku']) or
            not isinstance(image['version'], str) or not re.fullmatch(r'[0-9]{1,12}\.[0-9]{1,12}\.[0-9]{1,12}', image['version'])):
        raise ValueError('Use a pinned reviewed container-compatible Linux image')
    if (type(value['dedicatedNodes']) is not int or not 1 <= value['dedicatedNodes'] <= 100 or
            type(value['taskSlotsPerNode']) is not int or not 1 <= value['taskSlotsPerNode'] <= 4):
        raise ValueError('Use explicit bounded dedicated pool capacity')
    return copy.deepcopy(value)


def metadata(value):
    if not isinstance(value, list): raise ValueError('Native ownership metadata is required')
    result = {}
    for item in value:
        if (not isinstance(item, dict) or set(item) != {'name', 'value'} or not isinstance(item['name'], str) or
                not isinstance(item['value'], str) or item['name'] in result):
            raise ValueError('Ambiguous native pool ownership metadata')
        result[item['name']] = item['value']
    return result


def image_matches(expected, observed):
    if not isinstance(observed, dict): return False
    allowed = set(expected) | {'exactVersion'}
    return (not set(observed) - allowed and all(observed.get(k) == v for k, v in expected.items()) and
            observed.get('exactVersion', expected['version']) == expected['version'])


def verify_start_task(value, contract, job):
    fields = {'commandLine', 'resourceFiles', 'userIdentity', 'maxTaskRetryCount', 'waitForSuccess'}
    if (not isinstance(value, dict) or set(value) != fields or value['waitForSuccess'] is not True or
            type(value['maxTaskRetryCount']) is not int or value['maxTaskRetryCount'] != 0 or
            value['userIdentity'] != {'autoUser': {'scope': 'pool', 'elevationLevel': 'admin'}} or
            not isinstance(value['commandLine'], str) or len(value['commandLine'].encode()) > 32768 or
            not value['commandLine'].startswith('/usr/bin/python3 -I -c ') or
            not isinstance(value['resourceFiles'], list) or not 1 <= len(value['resourceFiles']) <= 3 or
            sha(value) != contract['startTaskSha256']):
        raise ValueError('Owned native installation task changed')
    for resource in value['resourceFiles']:
        if (not isinstance(resource, dict) or set(resource) != {'httpUrl', 'filePath', 'fileMode', 'identityReference'} or
                resource['identityReference'] != {'resourceId': contract['identityResourceId']} or
                resource['fileMode'] != '0400' or not isinstance(resource['filePath'], str) or
                not re.fullmatch(r'[a-z][a-z0-9-]{0,63}\.zip', resource['filePath']) or
                not isinstance(resource['httpUrl'], str) or not re.fullmatch(
                    re.escape('https://' + job['storageAccount'] + '.blob.core.windows.net/bootstrap/') + r'[0-9a-f]{64}\.zip', resource['httpUrl'])):
            raise ValueError('Use only immutable owned-MI bootstrap packages')


def verify_pool(job, contract, observed):
    if (not isinstance(observed, dict) or observed.get('id') != job['poolId'] or observed.get('state') != 'active' or
            observed.get('allocationState') != 'steady'):
        raise ValueError('Owned native pool is not active')
    if metadata(observed.get('metadata')) != {'atmem-document-policy': fingerprint(job), 'atmem-start-task-sha256': contract['startTaskSha256']}:
        raise ValueError('Owned native pool policy changed')
    exact = {'enableAutoScale': False, 'enableInterNodeCommunication': False, 'targetLowPriorityNodes': 0,
             'currentLowPriorityNodes': 0, 'targetDedicatedNodes': contract['dedicatedNodes'],
             'currentDedicatedNodes': contract['dedicatedNodes'], 'taskSlotsPerNode': contract['taskSlotsPerNode']}
    if any(not typed_equal(value, observed.get(key)) for key, value in exact.items()) or observed.get('vmSize') != contract['vmSize']:
        raise ValueError('Owned native pool scheduling or capacity changed')
    for field in ['applicationPackageReferences', 'userAccounts', 'mountConfiguration', 'resizeErrors']:
        if observed.get(field) not in [None, []]: raise ValueError('Unexpected shared pool input or resize error')
    native_identity = observed.get('identity')
    if not isinstance(native_identity, dict) or set(native_identity) != {'type', 'userAssignedIdentities'} or native_identity['type'] != 'UserAssigned':
        raise ValueError('Use only the dedicated transfer identity on the node')
    identities = native_identity['userAssignedIdentities']
    if not isinstance(identities, list) or len(identities) != 1: raise ValueError('Do not expose other workload identities to the node')
    identity = identities[0]
    if (not isinstance(identity, dict) or set(identity) != {'resourceId', 'clientId', 'principalId'} or
            not isinstance(identity['resourceId'], str) or identity['resourceId'].lower() != contract['identityResourceId'].lower() or
            identity['clientId'] != job['transferClientId'] or not isinstance(identity['principalId'], str) or
            not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', identity['principalId'])):
        raise ValueError('Native pool managed identity changed')
    network = observed.get('networkConfiguration')
    if (not isinstance(network, dict) or not set(network) <= {'subnetId', 'publicIPAddressConfiguration', 'endpointConfiguration', 'enableAcceleratedNetworking'} or
            network.get('subnetId', '').lower() != contract['subnetId'].lower() or
            network.get('publicIPAddressConfiguration') != {'provision': 'nopublicipaddresses'} or
            network.get('endpointConfiguration') not in [None, {'inboundNATPools': []}]):
        raise ValueError('Use the exact same-subscription private subnet without public endpoints')
    machine = observed.get('virtualMachineConfiguration')
    if (not isinstance(machine, dict) or set(machine) != {'imageReference', 'nodeAgentSKUId', 'containerConfiguration', 'diskEncryptionConfiguration'} or
            not image_matches(contract['imageReference'], machine['imageReference']) or machine['nodeAgentSKUId'] != contract['nodeAgentSkuId'] or
            machine['diskEncryptionConfiguration'] != {'targets': ['osdisk', 'temporarydisk']}):
        raise ValueError('Owned native image, agent SKU or disk encryption changed')
    registry = job['parserImage'].split('/')[0]
    expected = {'type': 'dockerCompatible', 'containerImageNames': [job['parserImage'], job['transferImage']],
                'containerRegistries': [{'registryServer': registry, 'identityReference': {'resourceId': contract['identityResourceId']}}]}
    if not typed_equal(expected, machine['containerConfiguration']):
        raise ValueError('Use only the prefetched immutable images and dedicated registry identity')
    verify_start_task(observed.get('startTask'), contract, job)
    return True


def verify_nodes(job, contract, response):
    if (not isinstance(response, dict) or response.get('odata.nextLink') or response.get('@odata.nextLink') or
            not isinstance(response.get('value'), list) or len(response['value']) != contract['dedicatedNodes']):
        raise ValueError('Observe every node in the explicit dedicated pool')
    identifiers = set()
    for node in response['value']:
        if (not isinstance(node, dict) or not isinstance(node.get('id'), str) or not re.fullmatch('[A-Za-z0-9_-]{1,128}', node['id']) or
                node['id'] in identifiers or node.get('state') not in {'idle', 'running'} or node.get('schedulingState') != 'enabled' or
                node.get('isDedicated') is not True or node.get('publicIPAddress') or node.get('publicIPv6Address') or node.get('errors') or
                node.get('vmSize') != contract['vmSize']):
            raise ValueError('Native dedicated node is not ready or private')
        version = node.get('nodeAgentInfo', {}).get('version')
        if not isinstance(version, str) or not re.fullmatch(r'[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}', version) or tuple(map(int, version.split('.'))) <= (1, 11, 11):
            raise ValueError('Native node agent must support explicit empty container mounts')
        startup = node.get('startTaskInfo', {})
        if (startup.get('state') != 'completed' or type(startup.get('exitCode')) is not int or startup['exitCode'] != 0 or
                startup.get('result') != 'success' or startup.get('failureInfo') or
                not image_matches(contract['imageReference'], node.get('virtualMachineInfo', {}).get('imageReference'))):
            raise ValueError('Native node did not complete the pinned installation on the pinned image')
        verify_start_task(node.get('startTask'), contract, job)
        identifiers.add(node['id'])
    return frozenset(identifiers)


def preflight(job, contract, api):
    job = job_configuration(job); contract = configuration(contract, job)
    try:
        api.account()
        verify_pool(job, contract, api.pool())
        return verify_nodes(job, contract, api.nodes())
    except Exception:
        raise SourceUnavailable('document_batch_pool_unavailable') from None
