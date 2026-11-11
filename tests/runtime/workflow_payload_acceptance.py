"""Independent payload/SQL and real queue/worker/loopback TLS fixture checks.

No application intake HTTP, cloud identity or real business destination is
established. Each test allocates new owned fixture accounts; processors are synthetic.
"""
import asyncio
import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=Path(os.environ.get('ATMEM_PAYLOAD_TEST_RUNTIME',ROOT/'src/runtime')).resolve()
sys.path[:0]=[str(RUNTIME),str(Path(__file__).resolve().parent)]
from workflow_payload import PayloadContract
from durable_workflow import WorkflowStore, Conflict, Denied, Missing
from durable_fixture_tasks import FIXTURE_CONTRACT
from durable_postgres_acceptance import DurableFixture
sys.path.insert(0,str(RUNTIME))


def text(maximum=128): return {'type':'string','minBytes':1,'maxBytes':maximum}
def obj(fields): return {'type':'object','properties':fields,'required':list(fields)}
def definition(domain='equipment-reservation'):
    if domain=='equipment-reservation':
        source=obj({'itemId':text(), 'memberId':text()})
        result=obj({'loanDays':{'type':'integer','minimum':1,'maximum':30},'inspectionRequired':{'type':'boolean'}})
    else:
        source=obj({'articleId':text(), 'revision':{'type':'integer','minimum':1,'maximum':10000}})
        result=obj({'title':text(80),'channels':{'type':'array','maxItems':3,'items':{'type':'enum','values':['web','print']}}})
    return {'version':1,'id':domain,'source':source,'result':result}


class PayloadContractTests(unittest.TestCase):
    def test_selected_emitted_modules_are_the_actual_imports(self):
        for name in ['workflow_payload','workflow_contract','durable_workflow']:
            self.assertEqual(Path(sys.modules[name].__file__).resolve().parent,RUNTIME)
    def test_contract_owns_exact_deep_snapshot_and_digest(self):
        value=definition(); contract=PayloadContract(value)
        expected=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(contract.sha256,expected)
        value['result']['properties']['loanDays']['maximum']=1000
        with self.assertRaises(ValueError):contract.validate('result',{'loanDays':31,'inspectionRequired':True})
        with self.assertRaises(FrozenInstanceError):contract._encoded=b'{}'
    def test_no_boolean_integer_alias_unknown_fields_or_coercion(self):
        contract=PayloadContract(definition())
        for value in [{'loanDays':True,'inspectionRequired':True},{'loanDays':'7','inspectionRequired':True},
                      {'loanDays':7,'inspectionRequired':True,'role':'owner'},{'loanDays':7}]:
            with self.subTest(value=value),self.assertRaises(ValueError):contract.validate('result',value)
    def test_utf8_is_measured_without_clipping_and_result_is_detached(self):
        definition_=definition('editorial-publication'); definition_['result']['properties']['title']=text(4)
        contract=PayloadContract(definition_)
        original={'title':'éé','channels':['web']}; copied=contract.validate('result',original)
        original['channels'].append('print');self.assertEqual(copied['channels'],['web'])
        with self.assertRaises(ValueError):contract.validate('result',{'title':'ééé','channels':['web']})
    def test_unknown_language_keywords_nested_shape_and_depth_are_rejected(self):
        for mutation in ['additionalProperties','version','tuple','key','depth']:
            value=definition()
            if mutation=='additionalProperties':value['source']['additionalProperties']=True
            elif mutation=='version':value['version']=True
            elif mutation=='tuple':value['source']['required']=tuple(value['source']['required'])
            elif mutation=='key':value['source']['properties']={1:text()}
            else:
                item=text()
                for _ in range(10):item={'type':'array','items':item,'maxItems':1}
                value['source']=obj({'nested':item})
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):PayloadContract(value)
    def test_arrays_enums_and_oversize_payloads_are_rejected(self):
        contract=PayloadContract(definition('editorial-publication'))
        for value in [{'title':'a','channels':['web']*4},{'title':'a','channels':['admin']},
                      {'title':'a'*64001,'channels':['web']}]:
            with self.assertRaises(ValueError):contract.validate('result',value)
    def test_changed_rules_change_digest_but_dictionary_order_does_not(self):
        first=definition();reordered=dict(reversed(list(first.items())))
        self.assertEqual(PayloadContract(first).sha256,PayloadContract(reordered).sha256)
        changed=copy.deepcopy(first);changed['result']['properties']['loanDays']['maximum']=20
        self.assertNotEqual(PayloadContract(first).sha256,PayloadContract(changed).sha256)


class PayloadPostgresTests(DurableFixture,unittest.TestCase):
    def owned(self,value):
        return WorkflowStore(self.dsn,self.extract,self.dispatch,destination_contract=FIXTURE_CONTRACT,payload_contract=PayloadContract(value))
    def test_two_domains_use_same_real_approval_and_queue_mechanisms(self):
        for domain,source,result in [
            ('equipment-reservation',{'itemId':'microscope','memberId':'member-1'},{'loanDays':7,'inspectionRequired':True}),
            ('editorial-publication',{'articleId':'community-news','revision':4},{'title':'Local news','channels':['web','print']})]:
            with self.subTest(domain=domain):
                store=self.owned(definition(domain));key=str(uuid.uuid4())
                operation=store.submit(self.user,'draft',key,source)
                self.assertEqual(operation,store.submit(self.user,'draft',key,source))
                self.assertEqual(self.queue_count(self.extract,operation),1)
                lease=store.claim_extract(operation);store.record_result(operation,str(lease['lease_token']),result)
                with self.assertRaises(Denied):store.approve(self.user,operation,1)
                with self.assertRaises(Missing):store.get(self.outsider,operation)
                approved=store.approve(self.reviewer,operation,1)
                self.assertEqual(approved['destination_contract']['payloadContractSha256'],store.payload_contract.sha256)
                expected={'kind':'draft','source':source,'destination':approved['destination_contract'],'result':result,'revision':1}
                self.assertEqual(approved['approved_hash'],hashlib.sha256(json.dumps(expected,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest())
                dispatched=store.claim_dispatch(operation)
                self.assertEqual(dispatched['state'],'dispatching');self.assertEqual(self.queue_count(self.dispatch,operation),1)
    def test_invalid_input_or_result_creates_no_queue_or_result_history(self):
        store=self.owned(definition())
        with self.assertRaises(ValueError):store.submit(self.user,'draft','bad',{'itemId':'scope','memberId':'member','accountId':self.other})
        with store.connect()as conn:
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM workflow.operations WHERE account_id=%s',(self.account,)).fetchone()['n'],0)
        operation=store.submit(self.user,'draft','good',{'itemId':'scope','memberId':'member'})
        lease=store.claim_extract(operation)
        with self.assertRaises(ValueError):store.record_result(operation,str(lease['lease_token']),{'loanDays':True,'inspectionRequired':True})
        self.assertEqual(store.get(self.user,operation)['state'],'processing')
        self.assertEqual(store.result_history(self.user,operation),[])
        store.record_result(operation,str(lease['lease_token']),{'loanDays':7,'inspectionRequired':True})
        with self.assertRaises(ValueError):store.edit_result(self.reviewer,operation,1,{'loanDays':31,'inspectionRequired':True})
        self.assertEqual(store.get(self.user,operation)['result_revision'],1)
    def test_changed_contract_blocks_old_work_before_processing_and_commit(self):
        store=self.owned(definition()); source={'itemId':'scope','memberId':'member'}
        operation=store.submit(self.user,'draft','stable',source)
        changed=definition();changed['result']['properties']['loanDays']['maximum']=20
        replacement=self.owned(changed)
        with self.assertRaises(Conflict):replacement.submit(self.user,'draft','stable',source)
        with self.assertRaises(Conflict):replacement.claim_extract(operation)
        lease=store.claim_extract(operation)
        with self.assertRaises(Conflict):replacement.record_result(operation,str(lease['lease_token']),{'loanDays':7,'inspectionRequired':True})
        self.assertEqual(store.get(self.user,operation)['state'],'processing')
    def test_restart_keeps_contract_but_changed_or_legacy_worker_cannot_approve_or_send(self):
        store=self.owned(definition());operation=store.submit(self.user,'draft','stable',{'itemId':'scope','memberId':'member'})
        lease=store.claim_extract(operation);store.record_result(operation,str(lease['lease_token']),{'loanDays':7,'inspectionRequired':True})
        restarted=self.owned(definition());restarted.approve(self.reviewer,operation,1)
        changed=definition();changed['result']['properties']['loanDays']['maximum']=20
        for other in [self.owned(changed),self.store]:
            with self.assertRaises(Conflict):other.approve(self.reviewer,operation,1)
            with self.assertRaises(Conflict):other.claim_dispatch(operation)
        self.assertEqual(restarted.claim_dispatch(operation)['state'],'dispatching')
    def test_mutated_persisted_shape_cannot_be_approved(self):
        from psycopg.types.json import Jsonb
        store=self.owned(definition());operation=store.submit(self.user,'draft','stable',{'itemId':'scope','memberId':'member'})
        lease=store.claim_extract(operation);store.record_result(operation,str(lease['lease_token']),{'loanDays':7,'inspectionRequired':True})
        with store.connect()as conn:conn.execute('UPDATE workflow.operations SET result=%s WHERE id=%s',(Jsonb({'loanDays':False,'inspectionRequired':True}),operation))
        with self.assertRaises(ValueError):store.approve(self.reviewer,operation,1)
        self.assertEqual(self.queue_count(self.dispatch,operation),0)


class PayloadWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_domains_cross_real_producer_queue_worker_approval_and_tls_destination(self):
        from durable_workflow import Principal
        from workflow_worker import WorkflowRuntime,producer_store
        from approved_http_destination import ApprovedHttpDestination
        from workflow_tls_destination_fixture import TlsDestinationFixture
        from workflow_errors import InvalidDispatch
        from durable_postgres_acceptance import fixture_dsn
        self.assertEqual(Path(sys.modules['workflow_worker'].__file__).resolve().parent,RUNTIME)
        dsn=fixture_dsn()
        for domain,source,result in [
            ('equipment-reservation',{'itemId':'microscope','memberId':'member-1'},{'loanDays':7,'inspectionRequired':True}),
            ('editorial-publication',{'articleId':'community-news','revision':4},{'title':'Local news','channels':['web']})]:
            contract=PayloadContract(definition(domain));namespace='q'+uuid.uuid4().hex[:12]
            processed=[];sink=TlsDestinationFixture()
            def process(row):processed.append(str(row['id']));return result
            deliver=ApprovedHttpDestination(sink.url,lambda:sink.token,destination_scope='synthetic-domain',tls_context=sink.context,allowed_kinds=('draft',),payload_contract=contract)
            runtime=WorkflowRuntime(dsn,process,deliver,destination_contract=deliver.contract,payload_contract=contract,namespace=namespace,retry_wait=0,lease_seconds=10)
            api=producer_store(dsn,destination_contract=deliver.contract,payload_contract=contract,namespace=namespace)
            account=str(uuid.uuid4());user=Principal(account,'member');reviewer=Principal(account,'reviewer')
            with api.connect()as conn:
                conn.execute('INSERT INTO workflow.accounts(id) VALUES(%s)',(account,))
                for actor,roles in [(user,['user']),(reviewer,['reviewer'])]:conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)',(account,actor.subject,roles))
            task=asyncio.create_task(runtime.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=2))
            async def until(operation,state):
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    if task.done():task.result()
                    row=await asyncio.to_thread(api.get,user,operation)
                    if row['state']==state:return row
                    await asyncio.sleep(.03)
                self.fail('Owned worker did not reach '+state)
            try:
                operation=await asyncio.to_thread(api.submit,user,'draft','stable',source)
                self.assertEqual(await asyncio.to_thread(api.submit,user,'draft','stable',source),operation)
                row=await until(operation,'review');self.assertEqual(row['result'],result)
                self.assertEqual(processed,[operation]);self.assertEqual(sink.calls,[])
                with self.assertRaises(Denied):await asyncio.to_thread(api.approve,user,operation,1)
                await asyncio.to_thread(api.approve,reviewer,operation,1)
                row=await until(operation,'sent')
                self.assertEqual(sink.calls,[{'key':operation,'body':{'operation_id':operation,'payload_sha256':row['approved_hash'],'kind':'draft','result':result}}])
                self.assertEqual(len(sink.effects),1)
                changed=definition(domain);changed['id']+='-v2'
                wrong=ApprovedHttpDestination(sink.url,lambda:self.fail('Changed contract requested credentials'),destination_scope='synthetic-domain',tls_context=sink.context,allowed_kinds=('draft',),payload_contract=PayloadContract(changed))
                with self.assertRaises(InvalidDispatch):wrong({**row,'state':'dispatching'},idempotency_key=operation,payload_sha256=row['approved_hash'])
                self.assertEqual(len(sink.calls),1)
                events=await asyncio.to_thread(api.events,user,operation)
                self.assertEqual([e['event']for e in events],['submitted','claimed','result_ready','approved','dispatch_claimed','sent'])
            finally:
                task.cancel()
                try:await task
                except asyncio.CancelledError:pass
                await asyncio.to_thread(sink.close)


if __name__=='__main__':unittest.main()
