from pathlib import Path
import tempfile
import threading
import time
import unittest

from server.maintenance.inventory import sha
from server.maintenance.models import Job, identity
from server.maintenance.recipes import recipe_digest
from server.maintenance.service import Service
from server.maintenance.store import Store, Conflict

ROOT = Path(__file__).resolve().parents[2]


class SlowWorker:
    identity = 'a' * 64
    def __init__(self):
        self.started = threading.Event()
        self.calls = 0

    def check(self, files, *, kind, cancel_event):
        self.calls += 1
        self.started.set()
        cancel_event.wait(3)
        return {'status': 'failed', 'reason': 'cancelled', 'artifactSha256': 'b' * 64,
                'exitCode': 1, 'durationSeconds': .001, 'output': '', 'report': None}


class MaintenanceServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'store.sqlite')
        self.worker = SlowWorker()
        self.service = Service(self.store, self.worker)
        self.addCleanup(self.service.close)
        self.files = {'main.tf': (ROOT / 'tests/maintenance/fixtures/baseline/main.tf').read_text()}
        self.project = self.service.create('tenant-001', 'project-001', 'actor-001', 'Upgrade', self.files)

    def start(self, **extra):
        return self.service.start('tenant-001', 'project-001', expected_revision=0,
                                  source_digest=self.project.snapshots[0].treeDigest, recipe=recipe_digest(),
                                  key='request-001', compute_confirmed=True, **extra)

    def test_exact_request_idempotency_and_cancellation_fence_worker(self):
        _, job = self.start()
        self.assertTrue(self.worker.started.wait(5))
        current, again = self.start()
        self.assertEqual(job.id, again.id)
        current = self.service.get('tenant-001', 'project-001')
        canceled = self.service.cancel('tenant-001', 'project-001', job.id, current.revision)
        self.assertEqual(canceled.jobs[0].status, 'canceled')
        for _ in range(500):
            if not self.service.running:
                break
            time.sleep(.01)
        self.assertFalse(self.service.running)
        self.assertEqual(self.service.get('tenant-001', 'project-001').jobs[0].status, 'canceled')
        self.assertEqual(self.worker.calls, 1)

    def test_source_replacement_requires_revision_and_invalidates_old_readiness(self):
        project = self.service.get('tenant-001', 'project-001')
        project.jobs = [Job(idempotencyKey='request-old', inputDigest='b' * 64, status='ready_for_review')]
        self.store.save(project, 0)
        current = self.service.get('tenant-001', 'project-001')
        self.assertEqual(current.jobs[0].status, 'stale')
        with self.assertRaises(Conflict):
            self.service.inventory('tenant-001', 'project-001', 0, self.files)
        changed, _ = self.service.inventory('tenant-001', 'project-001', current.revision, {'main.tf': self.files['main.tf'] + '\n# fresh source'})
        self.assertNotEqual(changed.snapshots[-1].treeDigest, self.project.snapshots[0].treeDigest)
        self.assertEqual(changed.snapshots[0].treeDigest, self.project.snapshots[0].treeDigest)

    def test_restart_never_replays_unknown_execution(self):
        project = self.service.get('tenant-001', 'project-001')
        project.jobs.append(Job(idempotencyKey='request-old', inputDigest='b' * 64))
        self.store.save(project, 0)
        current = Service(Store(self.store.path), self.worker)
        self.addCleanup(current.close)
        value = current.get('tenant-001', 'project-001')
        self.assertEqual(value.jobs[0].phase, 'execution_unknown')
        self.assertEqual(value.jobs[0].status, 'blocked')
        self.assertEqual(self.worker.calls, 0)
        with self.assertRaises(KeyError):
            current.get('tenant-002', 'project-001')
