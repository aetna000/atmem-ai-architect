"""An incompatible database must fail before the queue worker mutates it."""
import asyncio, unittest
import psycopg
import test_persistence as fixture
from workflow_worker import WorkflowRuntime
from durable_fixture_tasks import FIXTURE_CONTRACT


class WorkerAdmission(unittest.TestCase):
    # Each unittest module shares this test-owned disposable database; the first
    # module initializes it and all accounts/roles remain fixture-only.
    @classmethod
    def setUpClass(cls): cls.admin = fixture.Persistence.admin
    setUp = fixture.Persistence.setUp

    def test_stale_schema_prevents_queue_registration_and_callbacks(self):
        callbacks = []
        def processor(row): callbacks.append('process'); return {}
        def destination(row, **kw): callbacks.append('publish'); return {}
        runtime = WorkflowRuntime(self.worker_dsn, processor, destination,
            namespace='admission', destination_contract=FIXTURE_CONTRACT)
        with psycopg.connect(self.admin) as c:
            original = c.execute('SELECT source_sha256 FROM workflow.schema_version').fetchone()[0]
            before = c.execute('SELECT count(*) FROM workflow.procrastinate_workers').fetchone()[0]
            c.execute("UPDATE workflow.schema_version SET source_sha256='unreviewed-worker-schema'")
        async def run():
            with self.assertRaises(ValueError):
                await asyncio.wait_for(runtime.run(), timeout=3)
        try:
            asyncio.run(run())
            self.assertEqual(callbacks, [])
            with psycopg.connect(self.admin) as c:
                self.assertEqual(c.execute('SELECT count(*) FROM workflow.procrastinate_workers').fetchone()[0], before)
                self.assertEqual(c.execute('SELECT source_sha256 FROM workflow.schema_version').fetchone()[0], 'unreviewed-worker-schema')
        finally:
            with psycopg.connect(self.admin) as c: c.execute('UPDATE workflow.schema_version SET source_sha256=%s', (original,))
