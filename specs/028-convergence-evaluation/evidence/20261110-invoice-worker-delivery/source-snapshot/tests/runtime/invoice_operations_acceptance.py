"""Real SQL operator operations; no cloud backup/restore or accounting query."""
from pathlib import Path
import sys
import unittest
import uuid
import psycopg
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from durable_postgres_acceptance import DurableFixture
from durable_privileges_acceptance import create_runtime_roles
from invoice_operations import purge_expired,quarantine_restored_deliveries,reconcile_completed,set_membership

class InvoiceOperatorTests(DurableFixture,unittest.TestCase):
    def scope(self):return{'account_id':self.account,'namespace':self.extract.name.removesuffix('.extract')}
    def setUp(self):
        super().setUp()
        # Production namespace bound is twenty chars; fixture normally uses 32.
        from durable_fixture_tasks import FIXTURE_CONTRACT
        from workflow_worker import producer_store
        self.namespace='ops'+uuid.uuid4().hex[:12]
        self.store=producer_store(self.dsn,destination_contract=FIXTURE_CONTRACT,namespace=self.namespace)
        self.extract=self.store.tasks['extract'];self.dispatch=self.store.tasks['dispatch']
    def age(self,operation):
        with self.store.connect()as conn:conn.execute("UPDATE workflow.operations SET created_at=clock_timestamp()-interval '91 days' WHERE id=%s",(operation,))
    def test_expiry_removes_exact_scope_data_and_queue_history_and_preserves_young_and_other_account(self):
        expired=self.review();young=self.submit(key='young');other=self.store.submit(self.outsider,'document','other',{'sha256':'b'*64})
        self.age(expired);self.age(other)
        with self.store.connect()as conn:receipt=purge_expired(conn,**self.scope())
        self.assertEqual(receipt['purgedOperations'],1)
        with self.store.connect()as conn:
            for table,column in [('operations','id'),('results_history','operation_id'),('events','operation_id')]:self.assertEqual(conn.execute('SELECT count(*) AS n FROM workflow.'+table+' WHERE '+column+'=%s',(expired,)).fetchone()['n'],0)
            self.assertEqual(conn.execute("SELECT count(*) AS n FROM workflow.procrastinate_jobs WHERE args->>'operation_id'=%s",(expired,)).fetchone()['n'],0)
        self.assertEqual(str(self.store.get(self.user,young)['id']),young);self.assertEqual(str(self.store.get(self.outsider,other)['id']),other)
        with self.store.connect()as conn:self.assertEqual(purge_expired(conn,**self.scope())['purgedOperations'],0)
    def test_live_lease_blocks_purge_and_rolls_back_without_erasing_evidence(self):
        operation=self.submit();self.store.claim_extract(operation);self.age(operation)
        with self.assertRaisesRegex(ValueError,'live execution'):
            with self.store.connect()as conn:purge_expired(conn,**self.scope())
        self.assertEqual(self.store.get(self.user,operation)['state'],'processing')
    def test_restore_quarantines_stale_delivery_in_bounded_progressing_batches_without_replaying(self):
        operations=[]
        for i in range(3):
            operation=self.submit(key='restore-'+str(i));lease=self.store.claim_extract(operation);self.store.record_result(operation,str(lease['lease_token']),{'supplier':'Synthetic'});self.store.approve(self.reviewer,operation,1);operations.append(operation)
        lease=self.store.claim_dispatch(operations[0])
        with self.store.connect()as conn:conn.execute("UPDATE workflow.procrastinate_jobs SET status='doing' WHERE task_name=%s AND args->>'operation_id'=%s",(self.dispatch.name,operations[0]))
        with self.assertRaises(ValueError):
            with self.store.connect()as conn:quarantine_restored_deliveries(conn,**self.scope(),workloads_stopped=False)
        for expected in [1,1,1,0]:
            with self.store.connect()as conn:self.assertEqual(quarantine_restored_deliveries(conn,**self.scope(),workloads_stopped=True,limit=1)['quarantinedDeliveries'],expected)
        for operation in operations:
            row=self.store.get(self.user,operation);self.assertEqual(row['state'],'unknown');self.assertIsNone(row['lease_token']);self.assertIsNone(self.store.claim_dispatch(operation));self.assertEqual(self.queue_count(self.dispatch,operation),0)
    def test_completion_requires_verified_exact_snapshot_and_records_operator_without_sending(self):
        operation=self.approved();lease=self.store.claim_dispatch(operation);self.store.fail(operation,str(lease['lease_token']),'destination_unavailable',ambiguous=True)
        row=self.store.get(self.user,operation)
        for digest in ['a'*64,row['approved_hash']]:
            if digest!=row['approved_hash']:
                with self.assertRaises(ValueError):
                    with self.store.connect()as conn:reconcile_completed(conn,**self.scope(),operation_id=operation,payload_sha256=digest,external_id='receipt-1',operator='authorized.operator')
            else:
                with self.store.connect()as conn:receipt=reconcile_completed(conn,**self.scope(),operation_id=operation,payload_sha256=digest,external_id='receipt-1',operator='authorized.operator')
                self.assertEqual(receipt['state'],'sent')
        self.assertEqual(self.store.get(self.user,operation)['receipt']['externalId'],'receipt-1');self.assertEqual(self.store.events(self.user,operation)[-1]['actor'],'operator:authorized.operator')
    def test_membership_changes_are_explicit_and_runtime_roles_cannot_operate_or_purge(self):
        subject='native-subject-'+uuid.uuid4().hex
        with self.store.connect()as conn:set_membership(conn,**self.scope(),subject=subject,roles=['reviewer'])
        with self.store.connect()as conn:
            row=conn.execute('SELECT active,roles FROM workflow.memberships WHERE account_id=%s AND subject=%s',(self.account,subject)).fetchone();self.assertTrue(row['active']);self.assertEqual(row['roles'],['reviewer'])
        with self.store.connect()as conn:set_membership(conn,**self.scope(),subject=subject,roles=['user'],active=False)
        _,_,_,api_dsn,worker_dsn=create_runtime_roles()
        for dsn in [api_dsn,worker_dsn]:
            for action in [lambda conn:purge_expired(conn,**self.scope()),lambda conn:set_membership(conn,**self.scope(),subject='forbidden',roles=['owner'])]:
                with self.assertRaises((PermissionError,psycopg.errors.InsufficientPrivilege)):
                    with psycopg.connect(dsn)as conn:action(conn)

if __name__=='__main__':unittest.main(verbosity=2)
