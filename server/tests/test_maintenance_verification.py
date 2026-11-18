import concurrent.futures
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest

from server.maintenance.budget import Budget
from server.maintenance.egress import selection, request_payload
from server.maintenance.models import MigrationProject, ComputePolicy
from server.maintenance.store import Store, Conflict
from server.maintenance.inventory import snapshot
from server.maintenance.workers import MaintenanceWorker
from server.maintenance.verification import prepare
from server.maintenance.portable import export_section, import_section

ROOT = Path(__file__).resolve().parents[2]


class BudgetEgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'store.sqlite')
        for tenant, project in [('tenant-001', 'project-001'), ('tenant-001', 'project-002'), ('tenant-002', 'project-003')]:
            self.store.create(MigrationProject(tenantId=tenant, projectId=project, actor='actor-001', name='Upgrade'))
        self.budget = Budget(self.store)

    def test_aggregate_owner_limit_prevents_cross_project_and_tenant_bypass(self):
        scopes = [('tenant-001', 'project-001'), ('tenant-001', 'project-002'), ('tenant-002', 'project-003')]
        def reserve(item):
            i, (tenant, project) = item
            try:
                self.budget.reserve(tenant, project, 'same-credential-owner', f'job-0000{i}', 'a' * 64, 60,
                                    tenant_limit=100, project_limit=100, owner_limit=100)
                return 'reserved'
            except Conflict:
                return 'blocked'
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(reserve, enumerate(scopes)))
        self.assertEqual(results.count('reserved'), 1)

    def test_unknown_spend_is_not_released_or_replayed_and_idempotency_is_exact(self):
        params = ('tenant-001', 'project-001', 'credential-owner', 'job-00001', 'a' * 64, 60)
        limits = {'tenant_limit': 100, 'project_limit': 100, 'owner_limit': 100}
        self.budget.reserve(*params, **limits)
        self.budget.reserve(*params, **limits)
        self.budget.settle('tenant-001', 'job-00001')
        with self.assertRaises(Conflict):
            self.budget.reserve(*params, **limits)
        with self.assertRaises(Conflict):
            self.budget.reserve('tenant-001', 'project-002', 'credential-owner', 'job-00002', 'b' * 64, 60, **limits)

    def test_source_confirmation_and_every_derived_payload_have_separate_identities(self):
        files = {'main.tf': 'terraform {}'}
        approved = selection(files, backend='openrouter', model='selected-model', vendor_terms='terms-reviewed-2026-11-17', credential_owner='customer-001')
        confirmation = {'selectionDigest': approved['digest'], 'actor': 'actor-001', 'expiresAt': 100, 'revoked': False}
        _, first = request_payload(files, approved, confirmation=confirmation, now=10)
        _, second = request_payload(files, approved, findings='A schema argument is missing.', confirmation=confirmation, now=10)
        self.assertEqual(first['selectionDigest'], second['selectionDigest'])
        self.assertNotEqual(first['payloadDigest'], second['payloadDigest'])
        with self.assertRaises(ValueError):
            request_payload({'main.tf': 'terraform {}\n# changed'}, approved, confirmation=confirmation, now=10)
        for change in [{'revoked': True}, {'expiresAt': 9}, {'selectionDigest': 'b' * 64}]:
            with self.assertRaises(ValueError):
                request_payload(files, approved, confirmation={**confirmation, **change}, now=10)
        with self.assertRaises(ValueError):
            request_payload(files, approved, previous_output='sk-' + 'a' * 32, confirmation=confirmation, now=10)
        with self.assertRaises(ValueError):
            selection({'.env': 'PRIVATE=secret'}, backend='router', model='model', vendor_terms='terms', credential_owner='owner')


@unittest.skipUnless(os.getenv('ATMEM_MAINTENANCE_TEST_CONFIG'), 'Explicit qualified local Docker registration required')
class RealMaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = MaintenanceWorker.from_file(os.environ['ATMEM_MAINTENANCE_TEST_CONFIG'])

    def test_real_baseline_control_candidate_and_distinct_holdout(self):
        for name in ['baseline', 'holdout']:
            with self.subTest(name=name):
                text = (ROOT / f'tests/maintenance/fixtures/{name}/main.tf').read_text()
                source = snapshot({'main.tf': text}, 'repository-001')
                status, candidate, receipts, findings = prepare(source, self.worker, ComputePolicy())
                self.assertEqual(status, 'ready_for_review', findings)
                self.assertEqual([r.status for r in receipts], ['passed', 'failed', 'passed', 'passed'])
                self.assertEqual(receipts[-1].binding.patchDigest, candidate.digest)
                self.assertIn('.terraform.lock.hcl', [c.path for c in candidate.changes])
                self.assertEqual(source.files[0].text, text)
                self.assertIn('Unsupported argument', receipts[1].output)

    def test_baseline_failure_is_retained_and_never_drafted_away(self):
        source = snapshot({'main.tf': (ROOT / 'tests/maintenance/fixtures/baseline-failure/main.tf').read_text()}, 'repository-001')
        status, candidate, receipts, findings = prepare(source, self.worker, ComputePolicy())
        self.assertEqual(status, 'blocked')
        self.assertIsNone(candidate)
        self.assertEqual([r.kind for r in receipts], ['baseline'])
        self.assertEqual(receipts[0].status, 'failed')
        self.assertIn('priority', receipts[0].output)

    def test_cancellation_never_earns_readiness(self):
        source = snapshot({'main.tf': (ROOT / 'tests/maintenance/fixtures/baseline/main.tf').read_text()}, 'repository-001')
        cancel = threading.Event()
        cancel.set()
        status, candidate, receipts, _ = prepare(source, self.worker, ComputePolicy(), cancel_event=cancel)
        self.assertEqual(status, 'canceled')
        self.assertFalse(receipts)

    def test_mismatched_existing_lock_is_a_baseline_failure_not_silently_repaired(self):
        files = {'main.tf': (ROOT / 'tests/maintenance/fixtures/baseline/main.tf').read_text(),
                 '.terraform.lock.hcl': 'provider "registry.terraform.io/hashicorp/aws" {\n version = "6.0.0"\n hashes = ["h1:incorrect"]\n}\n'}
        status, candidate, receipts, findings = prepare(snapshot(files, 'repository-001'), self.worker, ComputePolicy())
        self.assertEqual(status, 'blocked')
        self.assertIsNone(candidate)
        self.assertEqual([r.kind for r in receipts], ['baseline'])
        self.assertEqual(findings[0].code, 'baseline_failed')

    def test_export_to_clean_store_reproduces_exact_candidate(self):
        files = {'main.tf': (ROOT / 'tests/maintenance/fixtures/holdout/main.tf').read_text()}
        source = snapshot(files, 'repository-001')
        first = prepare(source, self.worker, ComputePolicy())
        self.assertEqual(first[0], 'ready_for_review')
        project = MigrationProject(tenantId='tenant-001', projectId='project-001', actor='actor-001', name='Portable', snapshots=[source])
        from server.maintenance.models import Job
        project.jobs = [Job(idempotencyKey='request-001', inputDigest='a' * 64, status=first[0], candidate=first[1], receipts=first[2])]
        imported = import_section(export_section(project), tenant='tenant-002', project_id='project-002', actor='actor-002')
        self.assertEqual(imported.jobs[0].status, 'historical')
        with tempfile.TemporaryDirectory() as directory:
            clean = Store(Path(directory) / 'clean.sqlite')
            clean.create(imported)
            second = prepare(clean.get('tenant-002', 'project-002').snapshots[0], self.worker, ComputePolicy())
        self.assertEqual(second[0], 'ready_for_review')
        self.assertEqual(first[1].digest, second[1].digest)
        self.assertEqual([r.artifactDigest for r in first[2]], [r.artifactDigest for r in second[2]])
