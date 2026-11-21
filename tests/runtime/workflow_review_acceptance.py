"""Shared policy transfer: actual SQL/queue, ASGI and real TLS; fixture identities.

No native cloud, separate-process HTTP/child isolation or release claim. No client
artifact is patched. Semantic callbacks belong to this evaluator, not production.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'src/runtime'), str(Path(__file__).resolve().parent)]
from fastapi.testclient import TestClient
from psycopg.types.json import Json
from workflow_payload import PayloadContract
from workflow_review import ReviewPolicy
from workflow_contract import bind_review_policy
from durable_workflow import WorkflowStore, Principal, Conflict, Missing, Denied
from durable_postgres_acceptance import DurableFixture, fixture_dsn
from durable_fixture_tasks import FIXTURE_CONTRACT
from workflow_http import create_app
from workflow_worker import producer_store, WorkflowRuntime
from approved_http_destination import ApprovedHttpDestination
from workflow_tls_destination_fixture import TlsDestinationFixture
from workflow_errors import InvalidDispatch
from workflow_review_fixture import definition, parcel_result, audio_result, transforming_validator, returning_validator, accepting_validator

VALIDATORS = Path(__file__).with_name('workflow_review_fixture.py')
ORIGIN = 'https://policy.example'
PARCEL = {'massGrams': 499, 'priority': 'rush', 'note': ' field\0🙂 '}
PARCEL_RESULT = {'massMilligrams': 499000, 'lane': 'express', 'reviewNote': ' field\0🙂 '}
AUDIO = {'durationSeconds': 61, 'verbatim': ' exact\0🙂 '}
AUDIO_RESULT = {'chargeUnits': 2, 'caption': ' exact\0🙂 '}


def policy(domain='parcel-weighing', **options):
    payload = PayloadContract(definition(domain))
    return payload, ReviewPolicy(payload, **{
        'id': domain+'-review', 'editable_fields': ['reviewNote' if domain == 'parcel-weighing' else 'caption'],
        'validator': parcel_result if domain == 'parcel-weighing' else audio_result,
        'validation_sources': [VALIDATORS], **options})


class PolicyContractTests(unittest.TestCase):
    def test_policy_is_immutable_detached_portable_and_payload_bound(self):
        payload, review = policy(); data = review.data
        data['editableFields'].append('lane')
        self.assertEqual(review.data['editableFields'], ['reviewNote'])
        self.assertEqual(review.data['payloadContractSha256'], payload.sha256)
        self.assertNotIn(str(ROOT), json.dumps(review.data))
        with self.assertRaises(FrozenInstanceError): review._encoded = b'{}'
        self.assertEqual(bind_review_policy(FIXTURE_CONTRACT, payload, review)['reviewPolicySha256'], review.sha256)
        with self.assertRaises(ValueError): bind_review_policy(FIXTURE_CONTRACT, policy('audio-caption')[0], review)
        with self.assertRaises(ValueError): bind_review_policy(bind_review_policy(FIXTURE_CONTRACT, payload, review), payload, None)
        self.assertNotEqual(review.sha256, policy(read_scope='account')[1].sha256)

    def test_exact_types_unbound_code_and_unknown_fields_are_rejected(self):
        for options in [{'editable_fields':['admin']}, {'editable_fields':['lane','lane']},
                        {'inspection_ttl_seconds':True}, {'inspection_ttl_seconds':0},
                        {'read_scope':'provider'}, {'validation_sources':[]}, {'validator':'execute'},
                        {'validation_sources':[__file__]}]:
            with self.subTest(options=options), self.assertRaises(ValueError): policy(**options)

    def test_both_directions_of_derived_edits_and_two_domain_unicode_boundaries(self):
        for domain, source, result, field, number in [
            ('parcel-weighing', PARCEL, PARCEL_RESULT, 'reviewNote', 'massMilligrams'),
            ('audio-caption', AUDIO, AUDIO_RESULT, 'caption', 'chargeUnits')]:
            _, review = policy(domain)
            for delta in [-1, 1]:
                with self.subTest(domain=domain, delta=delta), self.assertRaises(ValueError):
                    review.validate_result(source, {**result, number:result[number]+delta})
            for note in ['', '\0🙂', '🙂'*128]:
                self.assertEqual(review.validate_edit(source, result, {**result, field:note})[field], note)
            for note in ['🙂'*129, '\ud800']:
                with self.assertRaises(ValueError): review.validate_edit(source, result, {**result, field:note})
        # Even a policy without semantics freezes its declared noneditable fields.
        payload = policy()[0]
        review = ReviewPolicy(payload, id='shape-review', editable_fields=['reviewNote'])
        with self.assertRaises(ValueError): review.validate_edit(PARCEL, PARCEL_RESULT, {**PARCEL_RESULT,'lane':'standard'})

    def test_validator_cannot_silently_normalize_or_return_replacement(self):
        for callback in [transforming_validator, returning_validator]:
            _, review = policy(validator=callback)
            with self.assertRaises(ValueError): review.validate_result(PARCEL, PARCEL_RESULT)
            self.assertEqual(PARCEL_RESULT['reviewNote'], ' field\0🙂 ')

    def test_declared_source_change_is_rejected_by_existing_policy(self):
        # This scratch file is an additional declared dependency, never imported.
        with tempfile.TemporaryDirectory() as tmp:
            dependency = Path(tmp)/'owned_constants.py'; dependency.write_text('LIMIT = 500\n')
            _, review = policy(validation_sources=[VALIDATORS, dependency])
            review.validate_result(PARCEL, PARCEL_RESULT)
            dependency.write_text('LIMIT = 499\n')
            with self.assertRaises(ValueError): review.validate_result(PARCEL, PARCEL_RESULT)
            self.assertNotEqual(review.sha256, policy(validation_sources=[VALIDATORS, dependency])[1].sha256)

    def test_separate_source_result_byte_budgets_are_not_silently_combined(self):
        fields = {'value':{'type':'string','minBytes':0,'maxBytes':60000}}
        shape = {'type':'object','properties':fields,'required':['value']}
        payload = PayloadContract({'version':1,'id':'large-text-pair','source':shape,'result':shape})
        review = ReviewPolicy(payload,id='large-pair-review',editable_fields=['value'],
                              validator=accepting_validator,validation_sources=[VALIDATORS])
        value = {'value':'🙂'*15000}
        self.assertEqual(review.validate_result(value,value),value)

    def test_package_dependencies_can_share_filenames_with_explicit_relative_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp)/'a/limits.py'; second = Path(tmp)/'b/limits.py'
            first.parent.mkdir(); second.parent.mkdir(); first.write_text('MINIMUM = 0\n'); second.write_text('MAXIMUM = 500\n')
            with self.assertRaises(ValueError): policy(validation_sources=[VALIDATORS,first,second])
            _, review = policy(validation_sources={'checks.py':VALIDATORS,'a/limits.py':first,'b/limits.py':second})
            self.assertEqual(set(review.data['validator']['sources']),{'checks.py','a/limits.py','b/limits.py'})
            review.validate_result(PARCEL,PARCEL_RESULT)
            for invalid in ['../checks.py','/checks.py','a//checks.py','a/../checks.py','a\\checks.py']:
                with self.subTest(label=invalid), self.assertRaises(ValueError): policy(validation_sources={invalid:VALIDATORS})


class PolicyStoreTests(DurableFixture, unittest.TestCase):
    def setUp(self):
        super().setUp(); self.payload, self.policy = policy()
        self.store = self.owned(self.policy)
        self.other_user = Principal(self.account, 'other-user')
        self.other_reviewer = Principal(self.account, 'other-reviewer')
        with self.store.connect() as conn:
            for actor, roles in [(self.other_user,['user']), (self.other_reviewer,['reviewer'])]:
                conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles)VALUES(%s,%s,%s)', (self.account,actor.subject,roles))

    def owned(self, review):
        return WorkflowStore(self.dsn,self.extract,self.dispatch,destination_contract=FIXTURE_CONTRACT,
                             payload_contract=self.payload,operation_kind='draft',review_policy=review)

    def reviewed(self):
        operation = self.store.submit(self.user,'draft',str(uuid.uuid4()),PARCEL)
        row = self.store.claim_extract(operation)
        self.store.record_result(operation,str(row['lease_token']),PARCEL_RESULT)
        return operation

    def test_wrong_semantics_cannot_record_edit_approve_or_dispatch(self):
        operation = self.store.submit(self.user,'draft','bad-result',PARCEL)
        lease = self.store.claim_extract(operation)
        with self.assertRaises(ValueError): self.store.record_result(operation,str(lease['lease_token']),{**PARCEL_RESULT,'massMilligrams':499001})
        self.assertEqual(self.store.result_history(self.user,operation),[])
        self.store.record_result(operation,str(lease['lease_token']),PARCEL_RESULT)
        for delta in [-1,1]:
            with self.assertRaises(ValueError): self.store.edit_result(self.reviewer,operation,1,{**PARCEL_RESULT,'massMilligrams':499000+delta})
        row = self.store.inspect(self.reviewer,operation); digest = self.store._fingerprint(row)
        self.store.approve(self.reviewer,operation,1,digest)
        # Disposable fixture operator corruption: valid shape, invalid derivation.
        with self.store.connect() as conn:
            conn.execute('UPDATE workflow.operations SET result=%s WHERE id=%s',(Json({**PARCEL_RESULT,'lane':'standard'}),operation))
        with self.assertRaises(ValueError): self.store.claim_dispatch(operation)
        with self.assertRaises(ValueError): self.store.approve(self.reviewer,operation,1,digest)

    def test_atomic_duplicate_identity_and_cross_owner_conflict(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(lambda _:self.store.submit(self.user,'draft','same',PARCEL),range(4)))
        self.assertEqual(len(set(ids)),1); self.assertEqual(self.queue_count(self.extract,ids[0]),1)
        with self.assertRaises(Conflict): self.store.submit(self.other_user,'draft','same',PARCEL)
        with self.assertRaises(Conflict): self.store.submit(self.user,'draft','same',{**PARCEL,'massGrams':498})

    def test_owner_read_policy_applies_to_get_list_cursor_history_events_and_live_roles(self):
        operation = self.reviewed()
        for action in [lambda:self.store.get(self.other_user,operation),lambda:self.store.list(self.other_user,before=operation),
                       lambda:self.store.result_history(self.other_user,operation),lambda:self.store.events(self.other_user,operation)]:
            with self.assertRaises(Missing): action()
        self.assertEqual(self.store.list(self.other_user),[])
        self.assertEqual(str(self.store.get(self.other_reviewer,operation)['id']),operation)
        with self.store.connect() as conn:
            conn.execute("UPDATE workflow.memberships SET roles=ARRAY['user'] WHERE account_id=%s AND subject=%s",(self.account,self.other_reviewer.subject))
        with self.assertRaises(Missing): self.store.get(self.other_reviewer,operation)
        # Explicit account scope is a different policy, never an implicit fallback.
        account_store = self.owned(policy(read_scope='account')[1])
        self.assertEqual(str(account_store.get(self.other_user,operation)['id']),operation)

    def test_inspection_is_actor_revision_hash_time_and_live_role_bound(self):
        operation = self.reviewed(); row = self.store.get(self.reviewer,operation); digest = self.store._fingerprint(row)
        with self.assertRaises(Conflict): self.store.approve(self.reviewer,operation,1,digest)
        with self.assertRaises(Denied): self.store.inspect(self.user,operation)
        self.store.inspect(self.reviewer,operation)
        with self.assertRaises(Conflict): self.store.approve(self.other_reviewer,operation,1,digest)
        with self.assertRaises(Conflict): self.store.approve(self.reviewer,operation,1,'0'*64)
        with self.store.connect() as conn:
            conn.execute("UPDATE workflow.events SET created_at=clock_timestamp()-interval '301 seconds' WHERE operation_id=%s AND event='review_inspected'",(operation,))
        with self.assertRaises(Conflict): self.store.approve(self.reviewer,operation,1,digest)
        self.store.inspect(self.reviewer,operation)
        changed = self.store.edit_result(self.reviewer,operation,1,{**PARCEL_RESULT,'reviewNote':''})
        self.assertEqual(changed['result_revision'],2)
        with self.assertRaises(Conflict): self.store.approve(self.reviewer,operation,1,digest)
        with self.assertRaises(Conflict): self.store.approve(self.reviewer,operation,2,self.store._fingerprint(changed))
        self.store.inspect(self.reviewer,operation)
        with self.store.connect() as conn:
            conn.execute('UPDATE workflow.memberships SET active=false WHERE account_id=%s AND subject=%s',(self.account,self.reviewer.subject))
        with self.assertRaises(Denied): self.store.approve(self.reviewer,operation,2,self.store._fingerprint(changed))
        self.assertEqual(self.queue_count(self.dispatch,operation),0)

    def test_policy_change_and_legacy_worker_cannot_reuse_inspection_or_approval(self):
        operation = self.reviewed(); row = self.store.inspect(self.reviewer,operation); digest = self.store._fingerprint(row)
        self.store.approve(self.reviewer,operation,1,digest)
        for changed in [policy(inspection_ttl_seconds=60)[1],policy(editable_fields=['reviewNote','lane'])[1],policy(read_scope='account')[1]]:
            other = self.owned(changed)
            with self.assertRaises(Conflict): other.approve(self.reviewer,operation,1,digest)
            with self.assertRaises(Conflict): other.claim_dispatch(operation)
        legacy = WorkflowStore(self.dsn,self.extract,self.dispatch,destination_contract=FIXTURE_CONTRACT,payload_contract=self.payload)
        with self.assertRaises(Conflict): legacy.claim_dispatch(operation)
        restarted = self.owned(policy()[1]); dispatched = restarted.claim_dispatch(operation)
        self.assertEqual(dispatched['state'],'dispatching')
        restarted.fail(operation,str(dispatched['lease_token']),'destination_unavailable',ambiguous=True)
        self.assertIsNone(restarted.claim_dispatch(operation))
        self.assertEqual(restarted.approve(self.reviewer,operation,1,digest)['state'],'unknown')
        self.assertEqual(self.queue_count(self.dispatch,operation),1)

    def test_http_exposes_exact_source_and_hash_and_prevents_uninspected_approval(self):
        client = TestClient(create_app(lambda token:token,self.store,account_id=self.account,public_origin=ORIGIN),base_url=ORIGIN)
        self.addCleanup(client.close)
        headers = {'Origin':ORIGIN,'Authorization':'Bearer staff','Idempotency-Key':'http-policy'}
        response = client.post('/api/operations',json={'source':PARCEL},headers=headers)
        self.assertEqual(response.status_code,202,response.text); operation = response.json()['operation']['id']
        self.assertEqual(response.json()['operation']['source'],PARCEL)
        row = self.store.claim_extract(operation); self.store.record_result(operation,str(row['lease_token']),PARCEL_RESULT)
        path = '/api/operations/'+operation
        self.assertEqual(client.get(path,headers={**headers,'Authorization':'Bearer other-user'}).status_code,404)
        reviewer = {**headers,'Authorization':'Bearer reviewer'}
        self.assertEqual(client.post(path+'/approve',json={'revision':1,'payloadSha256':self.store._fingerprint(self.store.get(self.reviewer,operation))},headers=reviewer).status_code,409)
        seen = client.post(path+'/inspect',json={},headers=reviewer)
        self.assertEqual(seen.status_code,200,seen.text)
        self.assertEqual(seen.json()['operation']['source'],PARCEL)
        self.assertEqual(client.get(path+'/history',headers=reviewer).json()['history'][0]['result'],PARCEL_RESULT)
        self.assertEqual(client.post(path+'/review',json={'revision':1,'result':{**PARCEL_RESULT,'lane':'standard'}},headers=reviewer).status_code,400)
        approved = client.post(path+'/approve',json={'revision':1,'payloadSha256':seen.json()['payloadSha256']},headers=reviewer)
        self.assertEqual(approved.status_code,200,approved.text)
        self.assertEqual(approved.headers['cache-control'],'no-store')

    def test_all_four_native_factories_keep_explicit_policy_and_signed_fixture_identity(self):
        from workflow_application import ApplicationProfile, create_native_api, create_native_worker, membership_key
        from workflow_application_acceptance import configuration, SOURCE, RESULT
        from invoice_identity_acceptance import identity_fixture
        for provider in ['aws','azure','gcp','ibm']:
            with self.subTest(provider=provider):
                identity, subject, token, _, _ = identity_fixture(provider)
                profile = ApplicationProfile(configuration(self.account,provider))
                review = ReviewPolicy(profile.payload,id='reservation-review',editable_fields=['loanDays'],
                                      validator=accepting_validator,validation_sources=[VALIDATORS])
                key = membership_key(profile,subject)
                with self.store.connect() as conn:
                    conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles)VALUES(%s,%s,%s)',(self.account,key,['reviewer']))
                app = create_native_api(profile,{},connection=self.dsn,jwks=identity.verify.jwks,review_policy=review)
                worker = create_native_worker(profile,{},lambda row:RESULT,lambda row,**kw:{},connection=self.dsn,review_policy=review)
                headers = {'Origin':'https://application.example','Idempotency-Key':'factory-policy',
                           **({'x-goog-iap-jwt-assertion':token()} if provider=='gcp' else {'Authorization':'Bearer '+token()})}
                with TestClient(app,base_url='https://application.example') as client:
                    response = client.post('/api/operations',json={'source':SOURCE},headers=headers)
                    self.assertEqual(response.status_code,202,response.text); operation = response.json()['operation']['id']
                    lease = worker.store.claim_extract(operation); worker.store.record_result(operation,str(lease['lease_token']),RESULT)
                    seen = client.post('/api/operations/'+operation+'/inspect',json={},headers=headers)
                    self.assertEqual(seen.status_code,200,seen.text)
                    self.assertEqual(seen.json()['destination']['reviewPolicySha256'],review.sha256)
                    approved = client.post('/api/operations/'+operation+'/approve',json={'revision':1,'payloadSha256':seen.json()['payloadSha256']},headers=headers)
                    self.assertEqual(approved.status_code,200,approved.text)
                legacy = create_native_worker(profile,{},lambda row:RESULT,lambda row,**kw:{},connection=self.dsn)
                with self.assertRaises(Conflict): legacy.store.claim_dispatch(operation)

    def test_supervisor_inspection_and_explicit_no_inspection_policy_are_distinct(self):
        store = WorkflowStore(self.dsn,self.extract,self.dispatch,destination_contract=FIXTURE_CONTRACT,
                              payload_contract=self.payload,operation_kind='account_change',review_policy=self.policy)
        operation = store.submit(self.user,'account_change','supervisor',PARCEL)
        lease = store.claim_extract(operation); store.record_result(operation,str(lease['lease_token']),PARCEL_RESULT)
        with self.assertRaises(Denied): store.inspect(self.reviewer,operation)
        row = store.inspect(self.supervisor,operation)
        self.assertEqual(store.approve(self.supervisor,operation,1,store._fingerprint(row))['state'],'approved')
        other = self.owned(policy(inspection_ttl_seconds=None)[1])
        operation = other.submit(self.user,'draft','explicit-no-inspection',PARCEL)
        lease = other.claim_extract(operation); row = other.record_result(operation,str(lease['lease_token']),PARCEL_RESULT)
        with self.assertRaises(Conflict): other.approve(self.reviewer,operation,1)
        self.assertEqual(other.approve(self.reviewer,operation,1,other._fingerprint(row))['state'],'approved')


class PolicyWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_domains_use_shared_producer_actual_queue_worker_review_and_tls(self):
        dsn = fixture_dsn()
        for domain, source, result in [('parcel-weighing',PARCEL,PARCEL_RESULT),('audio-caption',AUDIO,AUDIO_RESULT)]:
            with self.subTest(domain=domain):
                payload, review = policy(domain); namespace = 'q'+uuid.uuid4().hex[:12]
                sink = TlsDestinationFixture()
                deliver = ApprovedHttpDestination(sink.url,lambda:sink.token,destination_scope='policy-transfer',tls_context=sink.context,
                                                  allowed_kinds=('draft',),payload_contract=payload,review_policy=review)
                runtime = WorkflowRuntime(dsn,lambda row:dict(result),deliver,payload_contract=payload,review_policy=review,
                                          namespace=namespace,lease_seconds=10,retry_wait=0)
                api = producer_store(dsn,destination_contract=deliver.contract,payload_contract=payload,review_policy=review,namespace=namespace)
                account = str(uuid.uuid4()); user = Principal(account,'staff'); reviewer = Principal(account,'reviewer')
                with api.connect() as conn:
                    conn.execute('INSERT INTO workflow.accounts(id)VALUES(%s)',(account,))
                    for actor, roles in [(user,['user']),(reviewer,['reviewer'])]:
                        conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles)VALUES(%s,%s,%s)',(account,actor.subject,roles))
                task = asyncio.create_task(runtime.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=2))
                async def until(operation,state):
                    deadline = time.monotonic()+15
                    while time.monotonic()<deadline:
                        if task.done(): task.result()
                        row = await asyncio.to_thread(api.get,user,operation)
                        if row['state']==state:return row
                        await asyncio.sleep(.025)
                    self.fail('Actual policy worker did not reach '+state)
                try:
                    operation = api.submit(user,'draft','queue-policy',source)
                    row = await until(operation,'review'); self.assertEqual(row['result'],result); self.assertEqual(len(sink.effects),0)
                    # Unknown approval cannot bypass actual reviewer inspection.
                    with self.assertRaises(Conflict): api.approve(reviewer,operation,1,api._fingerprint(row))
                    old = api.inspect(reviewer,operation)
                    edited_result = {**result,('reviewNote' if domain=='parcel-weighing' else 'caption'):''}
                    api.edit_result(reviewer,operation,1,edited_result)
                    with self.assertRaises(Conflict): api.approve(reviewer,operation,1,api._fingerprint(old))
                    seen = api.inspect(reviewer,operation); approved = api.approve(reviewer,operation,2,api._fingerprint(seen))
                    sent = await until(operation,'sent')
                    self.assertEqual(sent['source_ref'],source); self.assertEqual(sent['result'],edited_result); self.assertEqual(len(sink.effects),1)
                    self.assertEqual(sent['approved_hash'],approved['approved_hash'])
                    expected_hash = hashlib.sha256(json.dumps({'kind':'draft','source':source,'destination':deliver.contract,
                        'result':edited_result,'revision':2},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
                    self.assertEqual(sent['approved_hash'],expected_hash)
                    self.assertEqual(sink.calls[-1]['body'],{'operation_id':operation,'payload_sha256':expected_hash,'kind':'draft','result':edited_result})
                    changed = {**sent,'state':'dispatching','result':{**result,('massMilligrams' if domain=='parcel-weighing' else 'chargeUnits'):0}}
                    with self.assertRaises(InvalidDispatch): deliver(changed,idempotency_key=operation,payload_sha256=sent['approved_hash'])
                    self.assertEqual(len(sink.effects),1)
                finally:
                    task.cancel()
                    try: await task
                    except asyncio.CancelledError: pass
                    await asyncio.to_thread(sink.close)


if __name__ == '__main__': unittest.main()
