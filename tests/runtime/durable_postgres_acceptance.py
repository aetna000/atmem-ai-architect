"""Real PostgreSQL/Procrastinate transaction and domain-state acceptance.

Requires the task-owned loopback fixture and its nonce; creates fresh synthetic
accounts, never drops/truncates tables. No live worker, identity, model, cloud or
external-action adapter is qualified by these primitive checks.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
from pathlib import Path
import sys
import unittest
import uuid
import psycopg
from psycopg.conninfo import make_conninfo

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from durable_workflow import WorkflowStore,Principal,Denied,Missing,Conflict,LostLease
from durable_fixture_tasks import fixture_tasks,FIXTURE_CONTRACT

def fixture_dsn():
    path=Path(os.environ.get('ATMEM_WORKFLOW_TEST_CONFIG',ROOT/'.local/durable-postgres/fixture.json'))
    c=json.loads(path.read_text())
    if c.get('name')!='atmem-durable-qualification' or not isinstance(c.get('database'),str)or not re.fullmatch(r'architect_qualification(?:_[a-z0-9]{1,32})?',c['database']) or not isinstance(c.get('marker'),str)or len(c['marker'])!=64:raise ValueError('Use the owned local qualification fixture')
    dsn=make_conninfo(host='127.0.0.1',port=c['port'],dbname=c['database'],user=c['user'],password=c['password'],sslmode='disable')
    with psycopg.connect(dsn,connect_timeout=2)as conn:
        row=conn.execute('SELECT marker FROM workflow.qualification_guard').fetchone()
        if not row or row[0]!=c['marker']:raise ValueError('This database is not the owned qualification fixture')
    return dsn

class DurableFixture:
    @classmethod
    def setUpClass(cls):cls.dsn=fixture_dsn()
    def setUp(self):
        self.account=str(uuid.uuid4());self.other=str(uuid.uuid4());self.namespace=uuid.uuid4().hex
        self.app,self.extract,self.dispatch=fixture_tasks(self.dsn,self.namespace);self.store=WorkflowStore(self.dsn,self.extract,self.dispatch,destination_contract=FIXTURE_CONTRACT)
        self.user=Principal(self.account,'staff');self.reviewer=Principal(self.account,'reviewer');self.supervisor=Principal(self.account,'supervisor');self.outsider=Principal(self.other,'outsider')
        with self.store.connect()as conn:
            for account in [self.account,self.other]:conn.execute('INSERT INTO workflow.accounts(id) VALUES(%s)',(account,))
            for actor,roles in [(self.user,['user']),(self.reviewer,['reviewer']),(self.supervisor,['supervisor']),(self.outsider,['user'])]:conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)',(actor.account_id,actor.subject,roles))
    def submit(self,key='document-1',kind='document',source=None):return self.store.submit(self.user,kind,key,source or {'sha256':'a'*64,'objectVersion':'synthetic-version-1'})
    def review(self,kind='document',result=None):
        operation=self.submit(kind=kind);lease=self.store.claim_extract(operation)
        self.store.record_result(operation,str(lease['lease_token']),result or {'supplier':'Synthetic supplier','invoice_date':'2026-11-10','total':'42.50','currency':'AUD'})
        return operation
    def approved(self):
        operation=self.review();self.store.approve(self.reviewer,operation,1);return operation
    def queue_count(self,task,operation):
        with self.store.connect()as conn:return conn.execute('SELECT count(*) AS count FROM workflow.procrastinate_jobs WHERE task_name=%s AND args->>\'operation_id\'=%s',(task.name,operation)).fetchone()['count']
    def expire(self,operation):
        with self.store.connect()as conn:conn.execute("UPDATE workflow.operations SET lease_until=clock_timestamp()-interval '1 second' WHERE id=%s AND account_id=%s",(operation,self.account))

class DurablePostgresTests(DurableFixture,unittest.TestCase):
    def test_twenty_concurrent_duplicate_deliveries_create_one_operation_and_one_real_queue_row(self):
        with ThreadPoolExecutor(max_workers=20)as executor:ids=list(executor.map(lambda _:self.submit(),range(20)))
        self.assertEqual(len(set(ids)),1);self.assertEqual(self.queue_count(self.extract,ids[0]),1);self.assertEqual([e['event']for e in self.store.events(self.user,ids[0])],['submitted'])
    def test_same_stable_identity_cannot_silently_point_to_a_changed_original(self):
        self.submit()
        with self.assertRaises(Conflict):self.submit(source={'sha256':'b'*64,'objectVersion':'synthetic-version-2'})
    def test_approved_operation_cannot_move_to_a_changed_destination_endpoint_or_account(self):
        for index,changed in enumerate([{'endpointSha256':'b'*64},{'scope':'different-account'},{'mappingVersion':2}]):
            with self.subTest(changed=changed):
                key='destination-'+str(index);self.store.destination_contract=dict(FIXTURE_CONTRACT);operation=self.submit(key=key)
                lease=self.store.claim_extract(operation);self.store.record_result(operation,str(lease['lease_token']),{'supplier':'Synthetic'});self.store.approve(self.reviewer,operation,1)
                original=self.store.get(self.user,operation);self.assertEqual(original['destination_contract'],FIXTURE_CONTRACT)
                self.store.destination_contract={**FIXTURE_CONTRACT,**changed}
                with self.assertRaises(Conflict):self.submit(key=key)
                with self.assertRaises(Conflict):self.store.approve(self.supervisor,operation,1)
                with self.assertRaises(Conflict):self.store.claim_dispatch(operation)
                self.store.destination_contract=dict(FIXTURE_CONTRACT)
    def test_post_queue_fault_rolls_back_both_operation_and_real_deferred_job(self):
        delegate=self.extract;captured={}
        class FailAfterQueueInsert:
            name=delegate.name
            queue=delegate.queue
            def configure(self,**kwargs):self.configured=delegate.configure(**kwargs);return self
            def defer(self,**kwargs):
                captured['operation']=kwargs['operation_id'];captured['job']=self.configured.defer(**kwargs);raise RuntimeError('Synthetic fault after the real queue INSERT')
        store=WorkflowStore(self.dsn,FailAfterQueueInsert(),self.dispatch,destination_contract=FIXTURE_CONTRACT)
        with self.assertRaises(RuntimeError):store.submit(self.user,'document','rollback',{'sha256':'c'*64})
        with self.store.connect()as conn:
            self.assertEqual(conn.execute('SELECT count(*) AS count FROM workflow.operations WHERE id=%s',(captured['operation'],)).fetchone()['count'],0)
            self.assertEqual(conn.execute('SELECT count(*) AS count FROM workflow.procrastinate_jobs WHERE id=%s',(captured['job'],)).fetchone()['count'],0)
    def test_cross_account_reads_audit_and_approvals_cannot_observe_an_operation(self):
        operation=self.review()
        for action in [lambda:self.store.get(self.outsider,operation),lambda:self.store.events(self.outsider,operation),lambda:self.store.approve(self.outsider,operation,1)]:
            with self.assertRaises(Missing):action()
        other_operation=self.store.submit(self.outsider,'document','document-1',{'sha256':'a'*64});self.assertNotEqual(operation,other_operation)
    def test_unknown_or_inactive_membership_denies_even_with_a_well_formed_identity(self):
        with self.assertRaises(Denied):self.store.submit(Principal(self.account,'unknown'),'document','unknown',{})
        with self.store.connect()as conn:conn.execute('UPDATE workflow.memberships SET active=false WHERE account_id=%s AND subject=%s',(self.account,self.user.subject))
        with self.assertRaises(Denied):self.submit()
    def test_only_one_of_twenty_workers_can_claim_and_stale_completion_is_fenced(self):
        operation=self.submit()
        with ThreadPoolExecutor(max_workers=20)as executor:leases=list(executor.map(lambda _:self.store.claim_extract(operation),range(20)))
        active=[row for row in leases if row];self.assertEqual(len(active),1);old=active[0];self.expire(operation);new=self.store.claim_extract(operation);self.assertGreater(new['execution_epoch'],old['execution_epoch'])
        with self.assertRaises(LostLease):self.store.record_result(operation,str(old['lease_token']),{'supplier':'Stale result'})
        current=self.store.record_result(operation,str(new['lease_token']),{'supplier':'Current result'});self.assertEqual(current['result']['supplier'],'Current result')
    def test_model_role_or_approval_text_does_not_create_dispatch_authority(self):
        operation=self.review(result={'recommendedAction':'send','role':'owner','approved':True});self.assertEqual(self.queue_count(self.dispatch,operation),0)
        with self.assertRaises(Denied):self.store.approve(self.user,operation,1)
        self.assertIsNone(self.store.claim_dispatch(operation));self.assertEqual(self.store.get(self.user,operation)['state'],'review')
    def test_supervisor_required_for_account_changes(self):
        operation=self.review(kind='account_change',result={'action':'suspend-test-account','target':'synthetic-customer'})
        with self.assertRaises(Denied):self.store.approve(self.reviewer,operation,1)
        self.assertEqual(self.store.approve(self.supervisor,operation,1)['state'],'approved')
    def test_concurrent_repeated_approval_enqueues_one_dispatch_and_one_audit_event(self):
        operation=self.review()
        with ThreadPoolExecutor(max_workers=20)as executor:rows=list(executor.map(lambda _:self.store.approve(self.reviewer,operation,1),range(20)))
        self.assertEqual({row['state']for row in rows},{'approved'});self.assertEqual(self.queue_count(self.dispatch,operation),1);self.assertEqual(sum(e['event']=='approved'for e in self.store.events(self.user,operation)),1)
    def test_edit_requires_current_revision_and_approval_binds_that_exact_snapshot(self):
        operation=self.review();changed=self.store.edit_result(self.reviewer,operation,1,{'supplier':'Corrected by reviewer'});self.assertEqual(changed['result_revision'],2)
        with self.assertRaises(Conflict):self.store.approve(self.reviewer,operation,1)
        with self.assertRaises(Conflict):self.store.edit_result(self.reviewer,operation,1,{'supplier':'Lost concurrent edit'})
        approved=self.store.approve(self.reviewer,operation,2)
        with self.assertRaises(Conflict):self.store.edit_result(self.reviewer,operation,2,{'supplier':'Change after approval'})
        lease=self.store.claim_dispatch(operation);self.assertEqual(lease['approved_hash'],approved['approved_hash'])
    def test_each_extraction_and_review_revision_is_retained_with_its_actual_actor(self):
        operation=self.review(result={'supplier':'Original extraction'})
        self.store.edit_result(self.reviewer,operation,1,{'supplier':'Reviewer correction'})
        with self.assertRaises(Conflict):self.store.edit_result(self.reviewer,operation,1,{'supplier':'Stale edit'})
        rows=self.store.result_history(self.user,operation)
        self.assertEqual([row['revision']for row in rows],[1,2]);self.assertEqual([row['result']['supplier']for row in rows],['Original extraction','Reviewer correction']);self.assertEqual([row['actor']for row in rows],['worker',self.reviewer.subject])
        self.assertEqual([row['revision']for row in self.store.result_history(self.user,operation,limit=1)],[1]);self.assertEqual([row['revision']for row in self.store.result_history(self.user,operation,after_revision=1,limit=1)],[2])
        for after,limit in [(True,1),(-1,1),(0,51)]:
            with self.assertRaises(ValueError):self.store.result_history(self.user,operation,after_revision=after,limit=limit)
        with self.assertRaises(Missing):self.store.result_history(self.outsider,operation)
    def test_bounded_listing_and_cursor_are_scoped_to_current_membership_account_and_workflow(self):
        operations=[self.submit(key='page-'+str(index))for index in range(3)]
        first=self.store.list(self.user,limit=2);second=self.store.list(self.user,before=str(first[-1]['id']),limit=2)
        self.assertEqual([str(row['id'])for row in first+second],list(reversed(operations)))
        other=self.store.submit(self.outsider,'document','other-account',{})
        with self.assertRaises(Missing):self.store.list(self.user,before=other)
        for limit in [True,0,51]:
            with self.assertRaises(ValueError):self.store.list(self.user,limit=limit)
    def test_live_application_role_revocation_invalidates_queued_approval(self):
        operation=self.approved()
        with self.store.connect()as conn:conn.execute('UPDATE workflow.memberships SET active=false WHERE account_id=%s AND subject=%s',(self.account,self.reviewer.subject))
        self.assertIsNone(self.store.claim_dispatch(operation));row=self.store.get(self.user,operation);self.assertEqual(row['state'],'review');self.assertIsNone(row['approved_hash']);self.assertIn('approval_revoked',[e['event']for e in self.store.events(self.user,operation)])
        self.assertEqual(self.store.approve(self.supervisor,operation,1)['state'],'approved')
    def test_lost_external_acknowledgement_never_becomes_an_automatic_unverified_retry(self):
        operation=self.approved();lease=self.store.claim_dispatch(operation);unknown=self.store.fail(operation,str(lease['lease_token']),'destination_unavailable',retryable=True)
        self.assertEqual(unknown['state'],'unknown');self.assertIsNone(self.store.claim_dispatch(operation))
        replay=self.store.claim_dispatch(operation,verified_idempotent_replay=True);self.assertEqual(replay['id'],lease['id']);self.assertEqual(replay['approved_hash'],lease['approved_hash']);self.assertEqual(replay['result'],lease['result'])
        with self.assertRaises(LostLease):self.store.record_sent(operation,str(lease['lease_token']),{'externalId':'stale-callback'})
        self.store.record_sent(operation,str(replay['lease_token']),{'externalId':'synthetic-accepted'});self.assertIsNone(self.store.claim_dispatch(operation));self.assertEqual(self.store.get(self.user,operation)['state'],'sent')
    def test_crashed_dispatch_lease_also_requires_a_verified_replay_contract(self):
        operation=self.approved();old=self.store.claim_dispatch(operation);self.expire(operation);self.assertIsNone(self.store.claim_dispatch(operation));new=self.store.claim_dispatch(operation,verified_idempotent_replay=True);self.assertNotEqual(new['lease_token'],old['lease_token'])
    def test_revoking_an_uncertain_dispatch_approver_cannot_reset_it_into_another_send(self):
        operation=self.approved();lease=self.store.claim_dispatch(operation)
        self.store.fail(operation,str(lease['lease_token']),'destination_unavailable',retryable=True,ambiguous=True)
        with self.store.connect()as conn:conn.execute('UPDATE workflow.memberships SET active=false WHERE account_id=%s AND subject=%s',(self.account,self.reviewer.subject))
        self.assertIsNone(self.store.claim_dispatch(operation))
        self.assertEqual(self.store.get(self.user,operation)['state'],'unknown')
        self.assertEqual(self.store.approve(self.supervisor,operation,1)['state'],'unknown')
        self.assertEqual(self.queue_count(self.dispatch,operation),1);self.assertIsNone(self.store.claim_dispatch(operation))
    def test_poison_extraction_is_bounded_audited_and_only_explicitly_recoverable(self):
        operation=self.submit()
        for attempt in range(5):
            lease=self.store.claim_extract(operation);row=self.store.fail(operation,str(lease['lease_token']),'invalid_result',retryable=True)
        self.assertEqual(row['state'],'dead');self.assertIsNone(self.store.claim_extract(operation))
        with self.assertRaises(Denied):self.store.recover_extraction(self.reviewer,operation)
        recovered=self.store.recover_extraction(self.supervisor,operation);self.assertEqual(recovered['state'],'pending');self.assertEqual(recovered['attempts'],0);self.assertIsNotNone(self.store.claim_extract(operation));self.assertIn('recovered',[e['event']for e in self.store.events(self.user,operation)])
    def test_nonfinite_output_and_raw_provider_error_text_are_rejected_without_audit_leaks(self):
        operation=self.submit();lease=self.store.claim_extract(operation)
        with self.assertRaises(ValueError):self.store.record_result(operation,str(lease['lease_token']),{'total':float('nan')})
        with self.assertRaises(ValueError):self.store.fail(operation,str(lease['lease_token']),'PRIVATE_PROVIDER_PAYLOAD')
        self.assertNotIn('PRIVATE_PROVIDER_PAYLOAD',str(self.store.events(self.user,operation)))
    def test_queue_configuration_rejects_native_notification_overflow_and_inherited_queueing_lock(self):
        self.extract.queue='x'*41
        with self.assertRaisesRegex(ValueError,'notification'):WorkflowStore(self.dsn,self.extract,self.dispatch,destination_contract=FIXTURE_CONTRACT)
        self.extract.queue='qualification-safe';self.extract.queueing_lock='unsafe-default'
        with self.assertRaisesRegex(ValueError,'queueing lock'):WorkflowStore(self.dsn,self.extract,self.dispatch,destination_contract=FIXTURE_CONTRACT)

if __name__=='__main__':unittest.main(verbosity=2)
