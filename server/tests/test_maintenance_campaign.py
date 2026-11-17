"""Real offline shared-module overlay and local-release checks; no remote publication."""
import copy
import os
from pathlib import Path
import unittest

from server.maintenance.graph import discover
from server.maintenance.models import Candidate, ComputePolicy
from server.maintenance.patches import apply_candidate
from server.maintenance.planner import prepare_campaign, observe_local_release, overlay, content_digest
from server.maintenance.workers import MaintenanceWorker
from server.tests.test_maintenance_graph import frozen_campaign


class OverlayTests(unittest.TestCase):
    def test_only_validation_copy_gets_local_module_path(self):
        root = {'main.tf': 'module "shared" { source = "company/queue/aws" version = "~> 1.0" }'}
        module = {'main.tf': 'output "answer" { value = 42 }'}
        projected, artifact = overlay(root, module, [{'module': 'shared'}])
        self.assertEqual(root['main.tf'], 'module "shared" { source = "company/queue/aws" version = "~> 1.0" }')
        self.assertEqual(artifact, content_digest(module))
        self.assertIn('./.atmem-modules/' + artifact, projected['main.tf'])
        self.assertNotIn('version', projected['main.tf'])
        self.assertEqual(projected['.atmem-modules/' + artifact + '/main.tf'], module['main.tf'])


@unittest.skipUnless(os.getenv('ATMEM_MAINTENANCE_TEST_CONFIG'), 'Explicit qualified offline Docker registration required')
class RealCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = MaintenanceWorker.from_file(Path(os.environ['ATMEM_MAINTENANCE_TEST_CONFIG']))
        cls.snapshots, cls.roots, cls.bindings = frozen_campaign()
        cls.original = [s.model_dump() for s in cls.snapshots]
        cls.graph = discover(cls.snapshots, cls.roots, cls.bindings)
        cls.campaign = prepare_campaign(cls.snapshots, cls.roots, cls.graph, 'root-shared', cls.worker)

    def test_meaningful_module_and_two_consumers_originals_unchanged(self):
        c = self.campaign
        self.assertEqual(c['status'], 'module_release_pending', c)
        self.assertEqual(c['evidenceLevel'], 'local_exact_module_overlay')
        self.assertEqual(set(c['consumers']), {'root-consumer-a', 'root-consumer-b'})
        self.assertEqual(len(c['checks']), 8)
        for consumer in c['consumers']:
            checks = [r for r in c['checks'] if r['consumer'] == consumer]
            self.assertEqual([r['status'] for r in checks], ['passed', 'failed', 'passed', 'passed'])
            self.assertTrue(all(r['cleanupConfirmed'] for r in checks))
            patch = c['consumers'][consumer]['candidate']
            self.assertNotIn('.atmem-modules', str(patch))
            self.assertNotIn('v2.0.0', str(patch))
        self.assertEqual([s.model_dump() for s in self.snapshots], self.original)
        self.assertEqual(c['waves'], [['root-shared'], ['root-consumer-a', 'root-consumer-b']])

    def test_simulated_release_requires_full_byte_equality_confirmation_and_rechecks(self):
        c = self.campaign
        self.assertEqual(c['status'], 'module_release_pending', c)
        released = apply_candidate(c['moduleBefore'], Candidate.model_validate(c['moduleCandidate']))
        args = {'source': 'git::https://example.invalid/shared-batch.git?ref=v2.0.0', 'version': None,
                'resolved_commit': 'b' * 40, 'worker': self.worker, 'compute_confirmed': True}
        for changed in [{**released, 'README.md': 'extra untested bytes'},
                        {**released, 'main.tf': released['main.tf'] + '\n# changed release\n'}]:
            with self.assertRaisesRegex(ValueError, 'differs'):
                observe_local_release(c, released_files=changed, **args)
        with self.assertRaisesRegex(ValueError, 'Confirm'):
            observe_local_release(c, released_files=released, **{**args, 'compute_confirmed': False})
        observed = observe_local_release(c, released_files=released, **args)
        self.assertEqual(observed['status'], 'local_release_checked')
        self.assertEqual(observed['release']['observation'], 'operator_supplied_local_simulation')
        self.assertEqual(len(observed['releaseChecks']), 2)
        self.assertTrue(all(r['status'] == 'passed' and r['cleanupConfirmed'] for r in observed['releaseChecks']))
        self.assertEqual(c['status'], 'module_release_pending')
        for proposal in observed['consumers'].values():
            self.assertIn('v2.0.0', str(proposal['releasedCandidate']))
            self.assertNotIn('.atmem-modules', str(proposal['releasedCandidate']))

    def test_stale_source_and_tampered_campaign_denied(self):
        changed = copy.deepcopy(self.snapshots)
        changed[1].files[0].text += '\n# new customer commit\n'
        with self.assertRaises(ValueError):
            prepare_campaign(changed, self.roots, self.graph, 'root-shared', self.worker, ComputePolicy(maxSeconds=1))
        tampered = copy.deepcopy(self.campaign)
        tampered['graphDigest'] = 'a' * 64
        with self.assertRaisesRegex(ValueError, 'identity'):
            observe_local_release(tampered, released_files={}, source='module', version=None,
                                  resolved_commit='b' * 40, worker=self.worker, compute_confirmed=True)

class PartialMergeTests(unittest.TestCase):
    def campaign(self):
        from server.maintenance.store import digest
        value = {'status': 'local_release_checked', 'consumers': {
            'consumer-one': {'before': {'main.tf': '# original one'}, 'releasedCandidate': {}},
            'consumer-two': {'before': {'main.tf': '# original two'}, 'releasedCandidate': {}}},
            'checks': [{'consumer': 'consumer-one', 'status': 'passed'}, {'consumer': 'consumer-two', 'status': 'passed'}],
            'releaseChecks': [{'consumer': 'consumer-two', 'status': 'passed'}]}
        value['digest'] = digest(value)
        return value

    def test_partial_merge_invalidates_remaining_wave_without_overwriting_sources(self):
        from server.maintenance.planner import invalidate_after_partial_merge
        campaign = self.campaign()
        identity = content_digest(campaign['consumers']['consumer-two']['before'])
        result = invalidate_after_partial_merge(campaign, merged=['consumer-one'], current_consumer_digests={'consumer-two': identity})
        self.assertEqual(result['status'], 'module_release_pending')
        self.assertEqual(result['checks'][1]['status'], 'stale')
        self.assertFalse(result['releaseChecks'])
        self.assertNotIn('releasedCandidate', result['consumers']['consumer-two'])
        self.assertEqual(campaign['checks'][1]['status'], 'passed')
        changed = invalidate_after_partial_merge(campaign, merged=['consumer-one'], current_consumer_digests={'consumer-two': 'b' * 64})
        self.assertEqual(changed['status'], 'blocked')
        self.assertEqual(changed['findings'][0]['code'], 'consumer_source_changed')
        with self.assertRaises(ValueError):
            invalidate_after_partial_merge(campaign, merged=['consumer-one'], current_consumer_digests={})

class ReleaseFailureEvidenceTests(unittest.TestCase):
    def test_failed_fresh_release_check_retains_receipt_and_cannot_keep_ready_status(self):
        import json
        from server.maintenance.planner import planner_digest
        from server.maintenance.store import digest
        evidence_path = Path(__file__).resolve().parents[2] / 'specs/032-infrastructure-upgrades/evidence/r2.json'
        campaign = json.loads(evidence_path.read_text())['primary']
        # Fixture supplies recorded candidate bytes, never the verdict under test.
        campaign['plannerDigest'] = planner_digest()
        campaign['digest'] = digest({k: v for k, v in campaign.items() if k != 'digest'})
        released = apply_candidate(campaign['moduleBefore'], Candidate.model_validate(campaign['moduleCandidate']))
        class FailedWorker:
            identity = campaign['workerIdentity']
            def check(self, files, **kwargs):
                return {'status': 'failed', 'cleanupConfirmed': True, 'exitCode': 1,
                        'durationSeconds': 0.001, 'output': 'independent validation failure', 'artifactSha256': 'a' * 64}
        observed = observe_local_release(campaign, released_files=released,
            source='git::https://example.invalid/module?ref=v2', version=None, resolved_commit='b' * 40,
            worker=FailedWorker(), compute_confirmed=True)
        self.assertEqual(observed['status'], 'blocked')
        self.assertEqual(observed['releaseChecks'][-1]['status'], 'failed')
        self.assertEqual(observed['findings'][0]['code'], 'released_consumer_check_failed')
        self.assertNotIn('releasedCandidate', observed['consumers']['root-consumer-a'])
