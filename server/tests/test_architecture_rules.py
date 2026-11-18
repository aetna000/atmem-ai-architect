"""Native review integration: real pinned AtMem, real trusted Terraform renderer."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import tempfile
import io
import zipfile
import hashlib
import threading
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from server.app import app,TOKEN
from server.memory_service import MemoryService
from server.architecture_rules import SaveRules,Run,Target,save_rules,read,run,status,ACTIVE,engineering_gate,configuration_snapshot
from server.architecture_rules import artifact_review,remember_engineering,remember_bindings,remember_specification,remember_validation

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=os.getenv('ATMEM_ARCHITECT_MEMORY_PYTHON','')

def rule(expected=True):
    return '---\nschema: atmem-architecture/v1\nnetwork:\n - id: PRIVATE-STORAGE\n   check: {resource: aws_s3_bucket_public_access_block, attribute: block_public_policy, must_equal: '+str(expected).lower()+'}\n---\n'

@unittest.skipUnless(RUNTIME and Path(RUNTIME).is_file(),'Requires explicitly configured pinned AtMem runtime')
class NativeRulesTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from server import architecture_rules as module
        module.LOCK=asyncio.Lock()
        self.tmp=tempfile.TemporaryDirectory();self.memory=MemoryService(self.tmp.name)
        self.project=json.loads(subprocess.check_output(['node','--input-type=module','-e',"import {template} from './src/core.mjs';const p=template('aws');p.id='native-review-project';p.nodes=p.nodes.slice(0,1);p.edges=[];console.log(JSON.stringify(p));"],cwd=ROOT))
        self.ident=self.project['id']
    def tearDown(self):self.tmp.cleanup()

    def save(self,text=None,revision=None):return save_rules(self.memory,SaveRules(projectId=self.ident,content=text or rule(),expectedRevision=revision))

    async def review(self):
        with patch('server.architecture_rules.service',return_value=self.memory):
            started=await run(Run(projectId=self.ident,project=self.project))
            await ACTIVE[(str(self.memory.home),self.ident)]
        result=read(self.memory,self.ident,'architecture.review')
        self.assertEqual(started['id'],result['id']);return result

    def test_exact_policy_roundtrip_scope_owner_revision_and_restart(self):
        first=self.save();self.assertEqual(first['content'],rule());self.assertEqual(first['approvedBy'],self.memory.owner)
        self.assertIsNone(read(self.memory,'other-project','architecture.policy'))
        reopened=MemoryService(self.tmp.name);self.assertEqual(read(reopened,self.ident,'architecture.policy'),first)
        with self.assertRaises(ValueError):self.save(rule(False))
        second=self.save(rule(False),first['revision']);self.assertNotEqual(first['revision'],second['revision'])
        with self.assertRaises(ValueError):self.save(rule(),first['revision'])
        detail=self.memory.record_detail(self.ident,'project',second['recordId'])
        self.assertEqual(detail['record']['governance']['actorType'],'user')

    async def test_real_render_review_pass_fail_and_persisted_activity(self):
        first=self.save();passed=await self.review();self.assertEqual(passed['state'],'completed');self.assertEqual(passed['report']['verdict'],'pass')
        self.assertEqual(len(passed['actions']),4);self.assertTrue(passed['fileDigests'])
        self.save(rule(False),first['revision']);failed=await self.review();self.assertEqual(failed['report']['verdict'],'fail')
        self.assertEqual(failed['report']['violations'][0]['rule_id'],'PRIVATE-STORAGE')

    async def test_backend_gate_rejects_changed_design_rules_and_failure(self):
        policy=self.save();self.project['extensions']={'architecturePolicy':policy};await self.review()
        from server.architecture_rules import render
        design=render(self.project,'staging')['design'];self.assertIsNotNone(engineering_gate(self.memory,self.ident,design))
        design['requirements']='Changed approved requirements'
        with self.assertRaises(ValueError):engineering_gate(self.memory,self.ident,design)
        design=render(self.project,'staging')['design'];self.save(rule(False),policy['revision'])
        with self.assertRaises(ValueError):engineering_gate(self.memory,self.ident,design)
        await self.review()
        with self.assertRaises(ValueError):engineering_gate(self.memory,self.ident,design)

    async def test_running_review_rejects_duplicates_and_changed_policy_goes_stale(self):
        policy=self.save();hold=asyncio.Event()
        from server import architecture_rules as module
        original=module.execute
        async def delayed(*args):await hold.wait();await original(*args)
        with patch('server.architecture_rules.service',return_value=self.memory),patch('server.architecture_rules.execute',side_effect=delayed):
            await run(Run(projectId=self.ident,project=self.project));task=ACTIVE[(str(self.memory.home),self.ident)]
            with self.assertRaises(Exception) as caught:await run(Run(projectId=self.ident,project=self.project))
            self.assertEqual(caught.exception.status_code,409)
            self.save(rule(False),policy['revision']);hold.set();await task
        self.assertEqual(read(self.memory,self.ident,'architecture.review')['state'],'stale')

    async def test_finishing_review_cannot_be_misreported_as_interrupted_by_a_stale_status_read(self):
        from server import architecture_rules as module
        self.save();captured=threading.Event();finish_render=threading.Event();release_status=threading.Event()
        original_read,original_render=module.read,module.render
        def delayed_render(*args):
            if not finish_render.wait(8):raise RuntimeError('Fixture render was not released')
            return original_render(*args)
        def delayed_read(memory,project,key):
            value=original_read(memory,project,key)
            if key=='architecture.review' and value and value['state']=='running' and not captured.is_set():
                captured.set();release_status.wait(8)
            return value
        with patch('server.architecture_rules.service',return_value=self.memory),patch('server.architecture_rules.render',side_effect=delayed_render),patch('server.architecture_rules.read',side_effect=delayed_read):
            await run(Run(projectId=self.ident,project=self.project));job=ACTIVE[(str(self.memory.home),self.ident)]
            pending=asyncio.create_task(status(Target(projectId=self.ident)))
            try:
                self.assertTrue(await asyncio.to_thread(captured.wait,8));finish_render.set()
                for _ in range(80):
                    value=await asyncio.to_thread(original_read,self.memory,self.ident,'architecture.review')
                    if value['state']=='completed':break
                    await asyncio.sleep(.05)
                self.assertEqual(value['state'],'completed')
                release_status.set();first=await pending
                self.assertEqual(first['review']['state'],'running')
                await job
                final=await status(Target(projectId=self.ident));self.assertEqual(final['review']['state'],'completed')
            finally:
                finish_render.set();release_status.set()
                await asyncio.gather(job,pending,return_exceptions=True)

    def test_route_auth_and_forged_scope_fields(self):
        with TestClient(app) as client,patch('server.architecture_rules.service',return_value=self.memory):
            self.assertEqual(client.post('/api/memory/architecture/status',json={'projectId':self.ident}).status_code,401)
            headers={'Authorization':'Bearer '+TOKEN}
            for field in ['owner','database','subject','userId']:
                self.assertEqual(client.post('/api/memory/architecture/status',json={'projectId':self.ident,field:'forged'},headers=headers).status_code,422)
            response=client.post('/api/memory/architecture/rules',headers=headers,json={'projectId':self.ident,'content':rule()})
            self.assertEqual(response.status_code,200)

    def test_actual_captured_output_review_excludes_baseline_and_rejects_tampering(self):
        self.save()
        def captured(expected,*,hcl=False):
            path='main.tf' if hcl else 'main.tf.json'
            text='resource "aws_s3_bucket" "example" {}' if hcl else json.dumps({'resource':{'aws_s3_bucket_public_access_block':{'example':{'block_public_policy':expected}}}})
            baseline=json.dumps({'resource':{'aws_s3_bucket_public_access_block':{'baseline':{'block_public_policy':True}}}})
            stream=io.BytesIO()
            with zipfile.ZipFile(stream,'w') as z:
                z.writestr(path,text);z.writestr('atmem-inputs/handoff/terraform/main.tf.json',baseline)
            raw=stream.getvalue()
            manifest={'id':'captured-artifact','runId':'run-one','sha256':hashlib.sha256(raw).hexdigest(),'files':[{'path':name,'kind':'file','bytes':len(body.encode()),'sha256':hashlib.sha256(body.encode()).hexdigest()} for name,body in [(path,text),('atmem-inputs/handoff/terraform/main.tf.json',baseline)]]}
            return manifest,raw
        for expected,verdict in [(True,'pass'),(False,'fail')]:
            manifest,raw=captured(expected);result=artifact_review(self.memory,self.ident,manifest,raw)
            self.assertEqual(result['report']['verdict'],verdict);self.assertEqual(result['fileCount'],1)
        manifest,raw=captured(True,hcl=True);self.assertEqual(artifact_review(self.memory,self.ident,manifest,raw)['report']['verdict'],'warn')
        manifest['sha256']='0'*64
        with self.assertRaises(ValueError):artifact_review(self.memory,self.ident,manifest,raw)

    def test_engineering_status_uses_observed_scoped_journal_not_completion_claims(self):
        state={'id':'session-one','run':'run-one','state':'running','last_status':None}
        events=[{'sequence':1,'kind':'accepted'},{'sequence':2,'kind':'progress','text':'Everything is tested!'}]
        self.assertEqual(remember_engineering(self.memory,self.ident,state,events),'remembered')
        self.assertEqual(remember_engineering(self.memory,self.ident,state,events),'unchanged')
        fact=read(self.memory,self.ident,'architecture.implementation')
        self.assertEqual(fact['sessions']['session-one']['state'],'running')
        self.assertNotIn('Everything is tested!',json.dumps(fact))
        self.assertIsNone(read(self.memory,'other-project','architecture.implementation'))

    def test_specification_task_file_binding_receipts_are_remembered_without_cross_project_adoption(self):
        payload={'projectId':self.ident,'sessionId':'session-one','runId':'run-one','artifactId':'artifact-one','artifactSha256':'a'*64,
                 'context':{'sha256':'b'*64},'files':[{'path':'app.py','sha256':'c'*64,'bytes':20}],
                 'proposal':{'records':[{'id':'implementation-one','kind':'implementation','dependsOn':['requirement:REQ-1'],'data':{'files':['app.py'],'specTaskIds':['TASK-REQ-1']}}]}}
        content=json.dumps(payload);receipt={'status':'prepared','content':content,'sha256':hashlib.sha256(content.encode()).hexdigest()}
        remember_bindings(self.memory,self.ident,receipt)
        saved=read(self.memory,self.ident,'architecture.bindings')['sessions']['session-one']
        self.assertEqual(saved['contextSha256'],'b'*64);self.assertEqual(saved['records'][0]['specTaskIds'],['TASK-REQ-1'])
        self.assertEqual(saved['fileDigests'][0]['sha256'],'c'*64)
        with self.assertRaises(ValueError):remember_bindings(self.memory,'other-project',receipt)
        self.assertIsNone(read(self.memory,'other-project','architecture.bindings'))

    def test_current_specification_inventory_is_retained_in_real_atmem_before_coding(self):
        context={'id':'context-one','revision':1,'projectId':self.ident,'sha256':'a'*64,
                 'specification':{'contextSha256':'a'*64,'tasks':{'tasks':[{'id':'TASK-ONE','title':'Implement the private adapter'}]}}}
        remember_specification(self.memory,self.ident,context)
        saved=read(self.memory,self.ident,'architecture.specification')
        self.assertEqual(saved['contextSha256'],'a'*64);self.assertEqual(saved['specification']['tasks']['tasks'][0]['id'],'TASK-ONE')
        with self.assertRaises(ValueError):remember_specification(self.memory,'other-project',context)

    def test_validation_memory_preserves_backend_failure_and_rejects_foreign_artifacts(self):
        checks=[{'id':'check-one','sessionId':'session-one','artifactId':'artifact-one','artifactSha256':'a'*64,
                 'validatorId':'unit-tests','label':'Unit tests','contractSha256':'b'*64,'state':'finished',
                 'result':{'status':'failed','output':'A model says everything passed; that is not the result.'}}]
        self.assertEqual(remember_validation(self.memory,self.ident,'session-one','artifact-one',checks),'remembered')
        self.assertEqual(remember_validation(self.memory,self.ident,'session-one','artifact-one',checks),'unchanged')
        saved=read(self.memory,self.ident,'architecture.validation')['sessions']['session-one']['checks'][0]
        self.assertEqual(saved['resultStatus'],'failed');self.assertNotIn('output',saved)
        with self.assertRaises(ValueError):remember_validation(self.memory,self.ident,'session-one','foreign-artifact',checks)

class SnapshotTests(unittest.TestCase):
    def test_expressions_and_unexpanded_instances_never_become_known_values(self):
        plan=configuration_snapshot({'main.tf.json':json.dumps({'resource':{'aws_db_instance':{'example':{'publicly_accessible':'${var.is_public}','for_each':'${var.dbs}'}}}})})
        self.assertIsNone(plan['planned_values']['root_module']['resources'][0]['values']['publicly_accessible']);self.assertFalse(plan['complete'])
