"""Observe original native job bindings across artifact revisions; never execute text."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / 'tests/runtime')]
from enterprise_azure_jobs_acceptance import config
from enterprise_azure_jobs import job_spec, task_spec, recover_job, verify_job, verify_task, terminal_writer_nodes
from enterprise_document_job import request


class AzureJobRecovery(unittest.TestCase):
    def setUp(self):
        self.config = config()
        self.identifier = 'd' * 64
        self.metadata = request(b'private fixture', 'text/plain', self.identifier)
        self.etag = '"0x8DA123ABCDEF"'
        self.job = job_spec(self.config, self.metadata, self.etag)

    def test_recovery_before_task_creation_retains_original_byte_and_artifact_contract(self):
        original, transfer = recover_job(self.config, self.identifier, self.job)
        self.assertEqual(original, self.config)
        self.assertEqual(transfer['request'], self.metadata)
        self.assertEqual(transfer['inputETag'], self.etag)

    def test_current_worker_can_clean_older_artifacts_without_changing_destination(self):
        current = {**self.config, 'parserImage': 'ownedregistry.azurecr.io/parser@sha256:' + 'f' * 64,
                   'transferImage': 'ownedregistry.azurecr.io/transfer@sha256:' + 'e' * 64,
                   'hostHelperSha256': 'a' * 64, 'workerClientId': '55555555-5555-5555-5555-555555555555'}
        original, _ = recover_job(current, self.identifier, self.job)
        self.assertEqual(original, self.config)
        for changed in [{**current, 'container': 'foreign'}, {**current, 'poolId': 'document-foreign'},
                        {**current, 'subscriptionId': '66666666-6666-6666-6666-666666666666'}]:
            with self.assertRaises(ValueError): recover_job(changed, self.identifier, self.job)

    def test_unordered_native_name_value_arrays_preserve_exact_semantics(self):
        observed = copy.deepcopy(self.job)
        observed['metadata'].reverse()
        observed['jobPreparationTask']['environmentSettings'].reverse()
        observed['jobReleaseTask']['environmentSettings'].reverse()
        original, _ = recover_job(self.config, self.identifier, observed)
        self.assertEqual(original, self.config)
        self.assertTrue(verify_job(self.config, self.metadata, self.etag, observed))

    def test_arbitrary_root_command_and_owner_metadata_are_never_adopted(self):
        changed = copy.deepcopy(self.job)
        changed['jobReleaseTask']['commandLine'] = '/bin/true'
        with self.assertRaises(ValueError): recover_job(self.config, self.identifier, changed)
        changed = copy.deepcopy(self.job)
        changed['metadata'][0]['value'] = 'f' * 64
        with self.assertRaises(ValueError): recover_job(self.config, self.identifier, changed)
        changed = copy.deepcopy(self.job)
        changed['metadata'][1]['value'] = 'foreignregistry.azurecr.io/parser@sha256:' + 'a' * 64
        with self.assertRaises(ValueError): recover_job(self.config, self.identifier, changed)

    def test_duplicate_oversize_and_malformed_native_settings_are_rejected(self):
        changed = copy.deepcopy(self.job)
        changed['metadata'][1] = dict(changed['metadata'][0])
        with self.assertRaises(ValueError): recover_job(self.config, self.identifier, changed)
        for raw in ['x' * 4097, '{"request":[]}', '{"request":{},"request":{}}']:
            changed = copy.deepcopy(self.job)
            changed['jobPreparationTask']['environmentSettings'][0]['value'] = raw
            with self.assertRaises(ValueError): recover_job(self.config, self.identifier, changed)
        changed = copy.deepcopy(self.job)
        changed['metadata'][0]['name'] = []
        with self.assertRaises(ValueError): recover_job(self.config, self.identifier, changed)

    def test_boolean_integer_aliases_cannot_weaken_the_observed_contract(self):
        changed = copy.deepcopy(self.job)
        changed['jobPreparationTask']['waitForSuccess'] = 1
        with self.assertRaises(ValueError): recover_job(self.config, self.identifier, changed)
        changed = task_spec(self.config, self.identifier)
        changed['constraints']['maxTaskRetryCount'] = False
        with self.assertRaises(ValueError): verify_task(self.config, self.identifier, changed)

    def test_terminal_writer_set_includes_prior_retry_nodes_not_just_current_assignment(self):
        job = {**self.job, 'state': 'completed'}
        task = {**task_spec(self.config, self.identifier), 'state': 'completed',
                'nodeInfo': {'poolId': self.config['poolId'], 'nodeId': 'node-two'}}
        rows = [{'poolId': self.config['poolId'], 'nodeId': node,
                 'jobPreparationTaskExecutionInfo': {'state': 'completed'},
                 'jobReleaseTaskExecutionInfo': {'state': 'completed'}} for node in ['node-one', 'node-two']]
        _, _, writers = terminal_writer_nodes(self.config, self.identifier, job, task, {'value': rows})
        self.assertEqual(writers, frozenset({'node-one', 'node-two'}))
        with self.assertRaises(ValueError): terminal_writer_nodes(self.config, self.identifier, job, task, {'value': rows[:1]})
        with self.assertRaises(ValueError): terminal_writer_nodes(self.config, self.identifier, {**job, 'state': 'terminating'}, task, {'value': rows})
        with self.assertRaises(ValueError): terminal_writer_nodes(self.config, self.identifier, job, task, {'value': rows, 'odata.nextLink': 'https://foreign'})

    def test_no_writer_proof_is_not_inferred_from_active_or_inconsistent_native_state(self):
        job = {**self.job, 'state': 'completed'}
        self.assertEqual(terminal_writer_nodes(self.config, self.identifier, job, None, {'value': []})[2], frozenset())
        row = {'poolId': self.config['poolId'], 'nodeId': 'node-one', 'jobPreparationTaskExecutionInfo': {'state': 'running'}}
        with self.assertRaises(ValueError): terminal_writer_nodes(self.config, self.identifier, job, None, {'value': [row]})
        row['jobPreparationTaskExecutionInfo']['state'] = 'completed'
        with self.assertRaises(ValueError): terminal_writer_nodes(self.config, self.identifier, job, None, {'value': [row, row]})


if __name__ == '__main__': unittest.main()
