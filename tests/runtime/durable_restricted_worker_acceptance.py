"""Execute real queue workers with separate, nonadministrative API/worker logins."""
import asyncio
from pathlib import Path
import sys
import uuid
import psycopg

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
import durable_worker_acceptance
from durable_fixture_tasks import FIXTURE_CONTRACT
from durable_privileges_acceptance import create_runtime_roles
from workflow_worker import WorkflowRuntime,producer_store

class RestrictedWorkerTests(durable_worker_acceptance.DurableWorkerTests):
    @classmethod
    def setUpClass(cls):
        cls.owner_dsn,_,_,cls.api_dsn,cls.worker_dsn=create_runtime_roles()

    async def start(self,processor,deliver,*,idempotent=False):
        namespace='q'+uuid.uuid4().hex[:12]
        runtime=WorkflowRuntime(self.worker_dsn,processor,deliver,destination_contract=FIXTURE_CONTRACT,idempotent_destination=idempotent,namespace=namespace,retry_wait=0,lease_seconds=10)
        api=producer_store(self.api_dsn,destination_contract=FIXTURE_CONTRACT,namespace=namespace,lease_seconds=10)
        with psycopg.connect(self.owner_dsn)as conn:
            conn.execute('INSERT INTO workflow.accounts(id) VALUES(%s)',(self.account,))
            for actor,roles in [(self.user,['user']),(self.reviewer,['reviewer'])]:
                conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)',(actor.account_id,actor.subject,roles))
        # Tests submit/read/approve through the API login. Worker callbacks retain
        # their own restricted store, including native queue maintenance/recovery.
        task=asyncio.create_task(runtime.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=2))
        self.tasks.append(task)
        class ApiFacingRuntime:
            store=api
        return ApiFacingRuntime(),task

if __name__=='__main__':
    import unittest
    unittest.main(verbosity=2)
