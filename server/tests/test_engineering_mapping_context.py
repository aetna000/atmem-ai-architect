import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import uuid
from server.engineering_handoff import design_value,same_design
from server.engineering_mapping_context import acknowledged_mapping
from server.engineering_sessions import SqliteSessionStore,ProjectScope,ModelSelection,SessionError


class MappingContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=SqliteSessionStore(Path(self.temp.name)/'control.sqlite')
        self.scope=ProjectScope('tenant-museum','project-museum')
        self.session=self.store.create(self.scope,'workspace-owned','test','private',ModelSelection('selected','medium'))['id']
        self.manifest={'id':str(uuid.uuid4()),'sha256':'a'*64,'runId':str(uuid.uuid4())}
        self.before={'format':'atmem.ai-architect.project','meta':{'id':self.scope.project,'revision':3},'design':{'provider':'tools','nodes':[
            {'id':'catalogue','type':'resource','position':{'x':0,'y':0},'data':{'label':'Museum catalogue','provider':'tools','kind':'resource','origin':'existing','config':{'attempts':1}}},
            {'id':'scans','type':'resource','position':{'x':80,'y':0},'data':{'label':'Collection intake','provider':'tools','kind':'resource','origin':'proposed','parentBlockId':'catalogue'}}],
            'edges':[{'id':'register','source':'scans','target':'catalogue','label':'Register accession','type':'smoothstep','interfaceSpec':{'transport':'Command','input':'Accession','output':'Receipt','authorization':'Curator','failure':'Reconcile','verification':'Replay once'}}]},
            'discovery':{'problem':'Preserve café 🍊 accession evidence.','workflow':'Museum intake'},
            'requirements':[{'id':'retain','statement':'Retain original accession evidence.','kind':'functional','priority':'must','source':'user','status':'open','links':['scans']}],
            'decisions':[{'id':'adr-one','title':'Preserve catalogue','status':'Accepted','decision':'Keep the existing museum system.'}],
            'assumptions':[],'openQuestions':[],'extensions':{'designSources':[{'sha256':'b'*64,'text':'Keep original evidence'}]}}
        record={'id':'intake-code','kind':'implementation','title':'Accession implementation','description':'Source file binding','dependsOn':['block:scans','requirement:retain'],'data':{'files':['app/intake.rb']}}
        content=json.dumps(self.before,ensure_ascii=False)
        self.payload={'format':'atmem.architecture-proposal','version':1,'projectId':self.scope.project,'sessionId':self.session,'runId':self.manifest['runId'],
            'artifactId':self.manifest['id'],'artifactSha256':self.manifest['sha256'],'proposalSha256':'c'*64,'definitionSha256':'d'*64,
            'context':{'id':str(uuid.uuid4()),'revision':1,'projectId':self.scope.project,'content':content,'sha256':hashlib.sha256(content.encode()).hexdigest()},
            'events':[],'proposal':{'version':1,'records':[record]},'files':[{'path':'app/intake.rb','bytes':1,'sha256':'e'*64}],'boundary':'artifact_file_binding_only'}
        self.receipt_id=str(uuid.uuid4());encoded=json.dumps(self.payload,ensure_ascii=False,separators=(',',':'));self.receipt_sha=hashlib.sha256(encoded.encode()).hexdigest()
        self.store.db.execute('CREATE TABLE engineering_reconciliations(id TEXT,session TEXT,artifact TEXT,sha256 TEXT,payload TEXT)')
        self.store.db.execute('INSERT INTO engineering_reconciliations VALUES (?,?,?,?,?)',(self.receipt_id,self.session,self.manifest['id'],self.receipt_sha,encoded));self.store.db.commit()
        # Use the real JavaScript import path, not a hand-authored imitation of its snapshots.
        script="""import fs from 'node:fs';import {applyArtifactWork} from './src/artifact-work.mjs';
const x=JSON.parse(fs.readFileSync(0,'utf8')),f=x.file,d=f.discovery,p={id:f.meta.id,provider:f.design.provider,nodes:f.design.nodes,edges:f.design.edges,requirements:d.problem,workflow:d.workflow,needs:f.requirements,decisions:f.decisions,assumptions:f.assumptions,openQuestions:f.openQuestions,extensions:f.extensions};
const result=applyArtifactWork(p,p.id,x.receipt,{now:new Date('2026-11-19T00:00:00.000Z')});console.log(JSON.stringify({...f,extensions:{...f.extensions,architectureWork:result.extensions.architectureWork}}));"""
        result=subprocess.run(['node','--input-type=module','-e',script],input=json.dumps({'file':self.before,'receipt':{'id':self.receipt_id,'receiptSha256':self.receipt_sha,'payload':self.payload}}),text=True,capture_output=True,cwd=Path(__file__).resolve().parents[2],check=True)
        self.current=json.loads(result.stdout)

    def tearDown(self):self.store.close();self.temp.cleanup()

    def project(self,current=None,before=None,scope=None):
        return acknowledged_mapping(self.store,scope or self.scope,self.session,self.manifest,
            design_value(json.dumps(before or self.before).encode(),self.scope.project),design_value(json.dumps(current or self.current).encode(),self.scope.project))

    def matches(self,current=None,before=None):
        projected=self.project(current,before)
        return projected is not None and same_design(design_value(json.dumps(before or self.before).encode(),self.scope.project),projected,self.session,[])

    def test_real_javascript_file_mapping_matches_original_design_without_rewriting_sources(self):
        unchanged=copy.deepcopy(self.current)
        self.assertFalse(same_design(self.before,self.current,self.session,[]))
        self.assertTrue(self.matches());self.assertEqual(self.current,unchanged)
        self.assertEqual(self.project()['extensions']['designSources'],self.before['extensions']['designSources'])

    def test_changed_sources_requirements_ownership_and_decisions_are_not_hidden_by_mapping(self):
        for mutate in [lambda p:p['requirements'][0].update(statement='Drop evidence'),lambda p:p['design']['nodes'][0]['data'].update(provider='aws'),
            lambda p:p['design']['edges'][0].update(target='scans'),lambda p:p['decisions'][0].update(decision='Replace catalogue'),
            lambda p:p['extensions']['designSources'][0].update(text='Changed input')]:
            candidate=copy.deepcopy(self.current);mutate(candidate);self.assertFalse(self.matches(candidate))

    def test_forged_records_files_receipts_and_artifact_identity_are_rejected(self):
        mutations=[lambda m:m.update(receiptSha256='f'*64),lambda m:m.update(artifactId=str(uuid.uuid4())),lambda m:m['files'][0].update(sha256='f'*64),
            lambda m:m['records'][0].update(agreement='accepted'),lambda m:m.update(contextSha256='f'*64),lambda m:m.update(recordedAt='2026-99-99T00:00:00.000Z'),lambda m:m.update(extra='hidden')]
        for mutate in mutations:
            candidate=copy.deepcopy(self.current);mutate(candidate['extensions']['architectureWork']['artifactMappings'][0]);self.assertFalse(self.matches(candidate))
        candidate=copy.deepcopy(self.current);candidate['extensions']['architectureWork']['records'][0]['data']['files']=['secret.txt'];self.assertFalse(self.matches(candidate))

    def test_snapshot_tampering_missing_basis_and_review_history_are_rejected(self):
        for mutate in [lambda w:w['snapshots'][0]['value']['value'].update(invented=True),lambda w:w['snapshots'][0].update(id='basis-9000'),
            lambda w:w['snapshots'].append(copy.deepcopy(w['snapshots'][0])),lambda w:w['artifactMappings'][0]['sourceSnapshotIds'].pop(),
            lambda w:w['bindings'].append({'ref':'accepted-review'}),lambda w:w['history'].append({'ref':'old-review'})]:
            candidate=copy.deepcopy(self.current);mutate(candidate['extensions']['architectureWork']);self.assertFalse(self.matches(candidate))

    def test_accepted_owner_work_record_cannot_be_overwritten_by_an_artifact_mapping(self):
        before=copy.deepcopy(self.before);old={**self.current['extensions']['architectureWork'],'records':[{**self.current['extensions']['architectureWork']['records'][0],'source':'user','agreement':'accepted'}],
            'snapshots':[],'artifactMappings':[]};before['extensions']['architectureWork']=old
        payload=copy.deepcopy(self.payload);payload['context']['content']=json.dumps(before);payload['context']['sha256']=hashlib.sha256(payload['context']['content'].encode()).hexdigest()
        encoded=json.dumps(payload,ensure_ascii=False,separators=(',',':'));sha=hashlib.sha256(encoded.encode()).hexdigest()
        self.store.db.execute('UPDATE engineering_reconciliations SET payload=?,sha256=?',(encoded,sha));self.store.db.commit()
        current=copy.deepcopy(self.current);mapping=current['extensions']['architectureWork']['artifactMappings'][0];mapping.update(receiptSha256=sha,contextSha256=payload['context']['sha256'])
        self.assertFalse(self.matches(current,before))

    def repair_chain(self):
        current=copy.deepcopy(self.current);payload=copy.deepcopy(self.payload)
        payload.update(artifactId=str(uuid.uuid4()),artifactSha256='f'*64,runId=str(uuid.uuid4()),proposalSha256='1'*64)
        payload['proposal']['records'][0]['description']='Repaired code under the same preserved work identity'
        encoded=json.dumps(payload,ensure_ascii=False,separators=(',',':'));sha=hashlib.sha256(encoded.encode()).hexdigest();ident=str(uuid.uuid4())
        self.store.db.execute('INSERT INTO engineering_reconciliations VALUES (?,?,?,?,?)',(ident,self.session,payload['artifactId'],sha,encoded));self.store.db.commit()
        mapping=copy.deepcopy(current['extensions']['architectureWork']['artifactMappings'][0]);mapping.update(id=ident,receiptSha256=sha,
            artifactId=payload['artifactId'],artifactSha256=payload['artifactSha256'],runId=payload['runId'],proposalSha256=payload['proposalSha256'],
            records=[{**record,'source':'agent','agreement':'proposed'}for record in payload['proposal']['records']])
        current['extensions']['architectureWork']['artifactMappings'].append(mapping);current['extensions']['architectureWork']['records']=mapping['records']
        self.manifest={'id':payload['artifactId'],'sha256':payload['artifactSha256'],'runId':payload['runId']}
        return current

    def test_same_context_repair_chain_keeps_both_exact_receipts_and_current_delivery(self):
        current=self.repair_chain();self.assertTrue(self.matches(current));self.assertEqual(len(current['extensions']['architectureWork']['artifactMappings']),2)
        changed=copy.deepcopy(current);changed['requirements'][0]['statement']='Change museum ownership';self.assertFalse(self.matches(changed))

    def test_repair_chain_cannot_hide_a_forged_earlier_receipt_or_drop_prior_work_identity(self):
        current=self.repair_chain();current['extensions']['architectureWork']['artifactMappings'][0]['receiptSha256']='9'*64;self.assertFalse(self.matches(current))
        current=self.repair_chain();current['extensions']['architectureWork']['records'][0]['agreement']='accepted';self.assertFalse(self.matches(current))

    def test_boolean_cannot_impersonate_numeric_context_or_source_values(self):
        candidate=copy.deepcopy(self.current)
        candidate['extensions']['architectureWork']['artifactMappings'][0]['contextRevision']=True
        self.assertFalse(self.matches(candidate))
        candidate=copy.deepcopy(self.current)
        snapshot=next(s for s in candidate['extensions']['architectureWork']['snapshots']if s['ref']=='block:catalogue')
        snapshot['value']['value']['config']['attempts']=True
        self.assertFalse(self.matches(candidate))
        before=copy.deepcopy(self.before);after=copy.deepcopy(before)
        after['design']['nodes'][0]['data']['config']['attempts']=True
        self.assertFalse(same_design(before,after,self.session,[]))

    def test_database_receipt_tampering_and_cross_scope_are_rejected(self):
        self.store.db.execute('UPDATE engineering_reconciliations SET payload=payload||?',(' ',));self.store.db.commit();self.assertFalse(self.matches())
        with self.assertRaises(SessionError):self.project(scope=ProjectScope('other-tenant',self.scope.project))
