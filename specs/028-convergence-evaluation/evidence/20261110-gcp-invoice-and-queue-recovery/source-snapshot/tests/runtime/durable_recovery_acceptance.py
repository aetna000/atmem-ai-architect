"""Domain recovery must survive lost notifications and respect workflow ownership."""
from pathlib import Path
import sys
import unittest
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from durable_postgres_acceptance import DurableFixture
from durable_fixture_tasks import fixture_tasks,FIXTURE_CONTRACT
from durable_workflow import WorkflowStore,Missing,LostLease

class DomainRecoveryTests(DurableFixture,unittest.TestCase):
    def fail_queue(self,task,operation):
        with self.store.connect()as conn:conn.execute("UPDATE workflow.procrastinate_jobs SET status='failed'WHERE task_name=%s AND args->>'operation_id'=%s",(task.name,operation))
    def test_failed_notification_before_claim_does_not_strand_pending_or_approved_work(self):
        first=self.submit();self.fail_queue(self.extract,first)
        self.assertEqual(self.store.reconcile_notifications(),[first]);self.assertEqual(self.queue_count(self.extract,first),2);self.assertEqual(self.store.reconcile_notifications(),[])
        second=self.approved();original=self.store.get(self.user,second);self.fail_queue(self.dispatch,second)
        self.assertEqual(self.store.reconcile_notifications(),[second]);current=self.store.get(self.user,second);self.assertEqual(current['approved_hash'],original['approved_hash']);self.assertEqual(current['destination_contract'],original['destination_contract']);self.assertEqual(self.queue_count(self.dispatch,second),2)
    def test_notification_repair_never_requeues_an_uncertain_external_outcome(self):
        operation=self.approved();lease=self.store.claim_dispatch(operation);self.store.fail(operation,str(lease['lease_token']),'destination_unavailable',retryable=True,ambiguous=True);self.fail_queue(self.dispatch,operation)
        self.assertEqual(self.store.reconcile_notifications(),[]);self.assertEqual(self.store.get(self.user,operation)['state'],'unknown');self.assertEqual(self.queue_count(self.dispatch,operation),1)
    def test_expired_processing_is_requeued_even_after_a_notification_was_acknowledged(self):
        operation=self.submit();lease=self.store.claim_extract(operation)
        # A notification can be acknowledged while an earlier live domain lease
        # still owns the operation. Recovery must not depend on a todo queue row.
        with self.store.connect()as conn:
            conn.execute("UPDATE workflow.procrastinate_jobs SET status='succeeded' WHERE task_name=%s AND args->>'operation_id'=%s",(self.extract.name,operation))
        self.expire(operation);self.assertEqual(self.store.recover_expired(),[operation]);self.assertEqual(self.queue_count(self.extract,operation),2)
        current=self.store.claim_extract(operation)
        with self.assertRaises(LostLease):self.store.record_result(operation,str(lease['lease_token']),{'supplier':'Expired'})
        self.store.record_result(operation,str(current['lease_token']),{'supplier':'Recovered'})
        self.assertEqual(self.store.get(self.user,operation)['state'],'review')
    def test_recovery_and_reads_never_cross_owned_workflow_namespaces(self):
        _,extract,dispatch=fixture_tasks(self.dsn,uuid.uuid4().hex);other=WorkflowStore(self.dsn,extract,dispatch,destination_contract=FIXTURE_CONTRACT)
        first=self.submit();second=other.submit(self.user,'document','same-account-other-workflow',{})
        self.store.claim_extract(first);other.claim_extract(second);self.expire(first);self.expire(second)
        self.assertEqual(self.store.recover_expired(),[first])
        with self.assertRaises(Missing):self.store.get(self.user,second)
        self.assertEqual(other.get(self.user,second)['state'],'processing');self.assertEqual(other.recover_expired(),[second])

if __name__=='__main__':unittest.main(verbosity=2)
