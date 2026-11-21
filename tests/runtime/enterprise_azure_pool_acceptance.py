"""Pinned response shapes + hostile readiness cases; synthetic installation only.

The startup command/package/version are explicitly synthetic, not published
artifacts or evidence that a Marketplace version exists or was installed.
"""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / 'tests/runtime')]
from enterprise_azure_jobs_acceptance import config, shape
from enterprise_azure_jobs import fingerprint
from enterprise_azure_pool import configuration, sha, verify_pool, verify_nodes, preflight
from enterprise_sources import SourceUnavailable


def fixture(job=None):
    job = job or config()
    base = '/subscriptions/' + job['subscriptionId'] + '/resourceGroups/owned-documents/providers/'
    identity = base + 'Microsoft.ManagedIdentity/userAssignedIdentities/document-transfer'
    startup = {'commandLine': '/usr/bin/python3 -I -c \'print("SYNTHETIC_INSTALLATION_FIXTURE")\'',
        'resourceFiles': [{'httpUrl': 'https://' + job['storageAccount'] + '.blob.core.windows.net/bootstrap/' + 'a' * 64 + '.zip',
            'filePath': 'host-bootstrap.zip', 'fileMode': '0400', 'identityReference': {'resourceId': identity}}],
        'userIdentity': {'autoUser': {'scope': 'pool', 'elevationLevel': 'admin'}}, 'maxTaskRetryCount': 0, 'waitForSuccess': True}
    contract = {'format': 'enterprise-azure-document-pool-v1', 'identityResourceId': identity,
        'subnetId': base + 'Microsoft.Network/virtualNetworks/owned-private/subnets/document-jobs',
        'vmSize': 'Standard_D2s_v5', 'imageReference': {'publisher': 'microsoft-dsvm', 'offer': 'ubuntu-hpc', 'sku': '2204', 'version': '1.0.20261101'},
        'nodeAgentSkuId': 'batch.node.ubuntu 22.04', 'startTaskSha256': sha(startup), 'dedicatedNodes': 1, 'taskSlotsPerNode': 2}
    now = '2026-11-11T00:00:00Z'
    endpoint = 'https://' + job['batchAccount'] + '.' + job['region'] + '.batch.azure.com'
    pool = {'id': job['poolId'], 'url': endpoint + '/pools/' + job['poolId'], 'eTag': '"fixture"',
        'lastModified': now, 'creationTime': now, 'state': 'active', 'stateTransitionTime': now,
        'allocationState': 'steady', 'vmSize': contract['vmSize'], 'enableAutoScale': False,
        'enableInterNodeCommunication': False, 'targetDedicatedNodes': 1, 'currentDedicatedNodes': 1,
        'targetLowPriorityNodes': 0, 'currentLowPriorityNodes': 0, 'taskSlotsPerNode': 2,
        'metadata': [{'name': 'atmem-document-policy', 'value': fingerprint(job)},
                     {'name': 'atmem-start-task-sha256', 'value': contract['startTaskSha256']}],
        'identity': {'type': 'UserAssigned', 'userAssignedIdentities': [{'resourceId': identity,
            'clientId': job['transferClientId'], 'principalId': '77777777-7777-7777-7777-777777777777'}]},
        'networkConfiguration': {'subnetId': contract['subnetId'], 'publicIPAddressConfiguration': {'provision': 'nopublicipaddresses'}},
        'startTask': startup,
        'virtualMachineConfiguration': {'imageReference': copy.deepcopy(contract['imageReference']), 'nodeAgentSKUId': contract['nodeAgentSkuId'],
            'diskEncryptionConfiguration': {'targets': ['osdisk', 'temporarydisk']},
            'containerConfiguration': {'type': 'dockerCompatible', 'containerImageNames': [job['parserImage'], job['transferImage']],
                'containerRegistries': [{'registryServer': job['parserImage'].split('/')[0], 'identityReference': {'resourceId': identity}}]}}}
    node = {'id': 'tvm-fixture-node', 'url': endpoint + '/pools/' + job['poolId'] + '/nodes/tvm-fixture-node',
        'state': 'idle', 'schedulingState': 'enabled', 'stateTransitionTime': now, 'lastBootTime': now, 'allocationTime': now,
        'ipAddress': '10.0.1.4', 'ipv6Address': 'fd00::4', 'affinityId': 'TVM:tvm-fixture-node',
        'vmSize': contract['vmSize'], 'isDedicated': True, 'totalTasksRun': 0,
        'nodeAgentInfo': {'version': '1.11.12', 'lastUpdateTime': now},
        'startTask': copy.deepcopy(startup), 'startTaskInfo': {'state': 'completed', 'exitCode': 0, 'result': 'success', 'startTime': now, 'endTime': now, 'retryCount': 0},
        'virtualMachineInfo': {'imageReference': copy.deepcopy(contract['imageReference'])}}
    return contract, pool, {'value': [node]}


class AzurePoolObservation(unittest.TestCase):
    def setUp(self): self.job = config(); self.contract, self.pool, self.nodes = fixture(self.job)

    def test_independent_official_response_schema_and_positive_observation(self):
        document = json.loads((ROOT / 'tests/fixtures/providers/azure-batch-2026-10-01-20261111.json').read_text())
        def response_schema(value):
            if isinstance(value, dict): return {k: response_schema(v) for k, v in value.items() if k != 'readOnly'}
            if isinstance(value, list): return [response_schema(v) for v in value]
            return value
        # Read-only properties are valid here because these are server responses.
        definitions = response_schema(document['definitions'])
        shape(self.pool, definitions['BatchPool'], definitions)
        shape(self.nodes, definitions['BatchNodeListResult'], definitions)
        self.assertTrue(verify_pool(self.job, self.contract, self.pool))
        self.assertEqual(verify_nodes(self.job, self.contract, self.nodes), frozenset({'tvm-fixture-node'}))

    def test_no_other_identity_or_static_registry_authority_is_accepted(self):
        for mutate in ['extra-identity', 'worker-identity', 'password']:
            pool = copy.deepcopy(self.pool)
            if mutate == 'extra-identity': pool['identity']['userAssignedIdentities'].append(dict(pool['identity']['userAssignedIdentities'][0]))
            if mutate == 'worker-identity': pool['identity']['userAssignedIdentities'][0]['clientId'] = self.job['workerClientId']
            if mutate == 'password': pool['virtualMachineConfiguration']['containerConfiguration']['containerRegistries'][0]['password'] = 'PRIVATE'
            with self.assertRaises(ValueError): verify_pool(self.job, self.contract, pool)

    def test_readiness_fails_for_unsafe_agent_missing_node_reboot_and_startup_failure(self):
        for mutate in ['old-agent', 'prerelease-agent', 'reboot', 'start-fail', 'public', 'wrong-image']:
            nodes = copy.deepcopy(self.nodes); node = nodes['value'][0]
            if mutate == 'old-agent': node['nodeAgentInfo']['version'] = '1.11.11'
            if mutate == 'prerelease-agent': node['nodeAgentInfo']['version'] = '1.11.12-preview'
            if mutate == 'reboot': node['state'] = 'rebooting'
            if mutate == 'start-fail': node['startTaskInfo']['exitCode'] = 1
            if mutate == 'public': node['publicIPAddress'] = '203.0.113.1'
            if mutate == 'wrong-image': node['virtualMachineInfo']['imageReference']['version'] = '1.0.1'
            with self.assertRaises(ValueError): verify_nodes(self.job, self.contract, nodes)
        for nodes in [{'value': []}, {'value': self.nodes['value'] * 2}, {**self.nodes, 'odata.nextLink': 'https://foreign'}]:
            with self.assertRaises(ValueError): verify_nodes(self.job, self.contract, nodes)

    def test_pin_private_network_capacity_images_and_exact_startup(self):
        for mutate in ['subnet', 'public', 'autoscale', 'capacity', 'encryption', 'image', 'startup', 'shared-mount']:
            pool = copy.deepcopy(self.pool)
            if mutate == 'subnet': pool['networkConfiguration']['subnetId'] += '-foreign'
            if mutate == 'public': pool['networkConfiguration']['publicIPAddressConfiguration']['provision'] = 'batchmanaged'
            if mutate == 'autoscale': pool['enableAutoScale'] = True
            if mutate == 'capacity': pool['currentDedicatedNodes'] = 0
            if mutate == 'encryption': pool['virtualMachineConfiguration']['diskEncryptionConfiguration']['targets'] = ['osdisk']
            if mutate == 'image': pool['virtualMachineConfiguration']['containerConfiguration']['containerImageNames'][0] += '-foreign'
            if mutate == 'startup': pool['startTask']['commandLine'] = '/bin/true'
            if mutate == 'shared-mount': pool['mountConfiguration'] = [{'foreign': 'mount'}]
            with self.assertRaises(ValueError): verify_pool(self.job, self.contract, pool)

    def test_foreign_bootstrap_even_with_changed_hash_is_not_owned(self):
        pool = copy.deepcopy(self.pool)
        pool['startTask']['resourceFiles'][0]['httpUrl'] = 'https://foreign.blob.core.windows.net/bootstrap/' + 'a' * 64 + '.zip'
        changed = {**self.contract, 'startTaskSha256': sha(pool['startTask'])}
        pool['metadata'][1]['value'] = changed['startTaskSha256']
        with self.assertRaises(ValueError): verify_pool(self.job, changed, pool)

    def test_mutable_deprecated_and_foreign_contracts_are_rejected(self):
        for change in [{'imageReference': {**self.contract['imageReference'], 'version': 'latest'}},
                       {'imageReference': {**self.contract['imageReference'], 'publisher': 'microsoft-azure-batch'}},
                       {'identityResourceId': self.contract['identityResourceId'].replace(self.job['subscriptionId'], '99999999-9999-9999-9999-999999999999')},
                       {'dedicatedNodes': True}, {'taskSlotsPerNode': 0}]:
            with self.assertRaises(ValueError): configuration({**self.contract, **change}, self.job)

    def test_preflight_orders_account_pool_nodes_and_sanitizes_native_failures(self):
        calls = []
        class Api:
            def account(inner): calls.append('account')
            def pool(inner): calls.append('pool'); return self.pool
            def nodes(inner): calls.append('nodes'); return self.nodes
        self.assertEqual(preflight(self.job, self.contract, Api()), frozenset({'tvm-fixture-node'}))
        self.assertEqual(calls, ['account', 'pool', 'nodes'])
        self.nodes['value'][0]['startTaskInfo']['exitCode'] = 1
        with self.assertRaisesRegex(SourceUnavailable, '^document_batch_pool_unavailable$'):
            preflight(self.job, self.contract, Api())


if __name__ == '__main__': unittest.main()
