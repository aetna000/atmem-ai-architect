import concurrent.futures
import json
from pathlib import Path
import tempfile
import unittest

from pydantic import ValidationError
from server.maintenance.models import MigrationProject, Job
from server.maintenance.store import Store, Conflict
from server.maintenance.portable import export_section, import_section


class MaintenanceStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'maintenance.sqlite')
        self.project = MigrationProject(tenantId='tenant-001', projectId='project-001', actor='actor-001', name='Migration')
        self.store.create(self.project)

    def test_strict_records_and_tenant_scope(self):
        with self.assertRaises(ValidationError):
            MigrationProject(**self.project.model_dump(), token='do-not-store')
        with self.assertRaises(KeyError):
            self.store.get('tenant-002', self.project.projectId)
        with self.assertRaises(ValidationError):
            MigrationProject.model_validate({**self.project.model_dump(), 'revision': '0'})

    def test_concurrent_compare_and_swap_and_restart(self):
        candidates = [self.store.get(self.project.tenantId, self.project.projectId) for _ in range(8)]
        def write(value):
            try:
                Store(self.store.path).save(value, 0)
                return 'written'
            except Conflict:
                return 'conflict'
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(write, candidates))
        self.assertEqual(results.count('written'), 1)
        self.assertEqual(Store(self.store.path).get(self.project.tenantId, self.project.projectId).revision, 1)

    def test_fence_stale_executor_and_no_epoch_reuse(self):
        scope = (self.project.tenantId, self.project.projectId)
        first = self.store.acquire(*scope, 'executor-001')
        with self.assertRaises(Conflict):
            self.store.acquire(*scope, 'executor-002')
        self.store.fence(*scope)
        next_epoch = self.store.acquire(*scope, 'executor-002')
        self.assertGreater(next_epoch, first)
        with self.assertRaises(Conflict):
            self.store.save(self.project, 0, lease=('executor-001', first))
        self.store.save(self.project, 0, lease=('executor-002', next_epoch))
        self.store.release(*scope, 'executor-001', first)
        with self.assertRaises(Conflict):
            self.store.acquire(*scope, 'executor-003')

    def test_import_is_historical_without_restoring_scope(self):
        self.project.jobs.append(Job(idempotencyKey='request-001', inputDigest='a' * 64, status='ready_for_review'))
        section = export_section(self.project)
        imported = import_section(section, tenant='tenant-002', project_id='project-002', actor='actor-002')
        self.assertEqual(imported.jobs[0].status, 'historical')
        self.assertNotEqual(imported.id, self.project.id)
        self.assertEqual(imported.tenantId, 'tenant-002')
        section['aggregate']['name'] = 'tampered'
        with self.assertRaises(ValueError):
            import_section(section, tenant='tenant-002', project_id='project-002', actor='actor-002')

    def test_delete_fences_pending_worker(self):
        epoch = self.store.acquire(self.project.tenantId, self.project.projectId, 'executor-001')
        self.store.delete(self.project.tenantId, self.project.projectId)
        with self.assertRaises(KeyError):
            self.store.get(self.project.tenantId, self.project.projectId)
        with self.assertRaises(Conflict):
            self.store.save(self.project, 0, lease=('executor-001', epoch))

    def test_shared_cross_language_fixture_has_matching_content_digest(self):
        path = Path(__file__).resolve().parents[2] / 'tests/maintenance/fixtures/portable-section.json'
        section = json.loads(path.read_text())
        aggregate = MigrationProject.model_validate(section['aggregate'])
        self.assertEqual(export_section(aggregate)['sha256'], section['sha256'])
        self.assertEqual(aggregate.jobs[0].receipts[0].durationSeconds, 0.0)
