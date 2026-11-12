import test from 'node:test';import assert from 'node:assert/strict';
import {compositionFixture} from '../scripts/engine-evaluation/composition-fixtures.mjs';
import {reviewWorkContext,architectureWork} from '../src/architecture-work.mjs';
import fs from 'node:fs';import {createHash} from 'node:crypto';
import {validateImport} from '../src/core.mjs';import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';
import {terraformSketch} from '../src/terraform.mjs';import {resourcePlan} from '../src/resources.mjs';import {generationQuality} from '../src/generation-quality.mjs';import {protectedState} from '../src/protected-state.mjs';import {specKit} from '../src/spec-kit.mjs';
const choose=(project,backend,environment='production')=>({...project,decisions:[{id:'state-choice',title:'Existing platform state',subject:'state',status:'Proposed',decision:'Preserve the existing platform state owner.'}],extensions:{...project.extensions,terraformState:{version:1,environments:{[environment]:{backend,owner:'Existing platform team',residency:'Australian custody required; destination unverified',decisionId:'state-choice'}}}}});
for(const provider of ['aws','azure','gcp','ibm'])test(provider+': explicit state backend is independent of target provider and owns only the root',()=>{
 for(const backend of ['s3','azurerm','gcs','http']){
  const p=choose(compositionFixture(provider),backend),before=structuredClone(p),files=terraformSketch(p,'production'),root=JSON.parse(files['main.tf.json']),record=JSON.parse(files['state-custody.json']);
  assert.deepEqual(Object.keys(root.terraform.backend),[backend]);assert.equal(record.selection.backend,backend);assert.equal(record.acceptance,'not_verified');assert.equal(record.decisionStatus,'Proposed');assert.equal(record.migrationAuthorized,false);assert.equal(root.variable.review_approved.default,false);assert(root.locals.unfinished_work.includes('state-custody-and-operations-acceptance-required'));assert.deepEqual(JSON.parse(files['generation-quality.json']).fatalFindings,[]);
  for(const unit of JSON.parse(files['composition.json']).units)assert.equal(JSON.parse(files[unit.path+'/main.tf.json']).terraform.backend,undefined);
  assert.deepEqual(fromProjectFile(toProjectFile(p)).project.extensions.terraformState,p.extensions.terraformState);assert.deepEqual(p,before);
 }
});
test('unknown state contracts retain original input instead of accepting fields or choosing a substitute',()=>{
 const p=choose(compositionFixture('ibm'),'s3');
 for(const mutant of [{version:9,environments:{}},{version:1,environments:{production:{...p.extensions.terraformState.environments.production,password:'synthetic'}}},{version:1,environments:{production:{...p.extensions.terraformState.environments.production,backend:'invented'}}}]){
  const changed=structuredClone(p);changed.extensions.terraformState=mutant;const before=structuredClone(changed);assert.throws(()=>validateImport(changed));assert.throws(()=>toProjectFile(changed));assert.deepEqual(changed,before);
 }
});
test('independent admission rejects root backend diversion even when module addresses are unchanged',()=>{
 for(const selected of [false,true]){
  const p=selected?choose(compositionFixture('ibm'),'gcs'):compositionFixture('ibm'),plan=resourcePlan(p),environment=selected?'production':'staging',files=terraformSketch(p,environment);
  for(const mutation of ['destination','credential','cloud','acceptance','owner','blocker','private-input','example-secret']){
   const changed={...files},root=JSON.parse(files['main.tf.json']);
   if(mutation==='destination')root.terraform.backend={http:{address:'https://foreign.invalid/state',skip_cert_verification:true}};
   if(mutation==='credential')root.terraform.backend={gcs:{credentials:'synthetic-private-key'}};
   if(mutation==='cloud')root.terraform.cloud={organization:'foreign'};
   if(['acceptance','owner','blocker','example-secret'].includes(mutation)&&!selected)continue;
   if(mutation==='private-input')changed['backend.hcl']='password = "synthetic"';
   if(mutation==='example-secret')changed['backend.hcl.example']+='credentials = "synthetic"\n';
   if(mutation==='acceptance'||mutation==='owner'){const record=JSON.parse(changed['state-custody.json']);if(mutation==='owner')record.selection.owner='foreign';else record.acceptance='passed';changed['state-custody.json']=JSON.stringify(record);}
   if(mutation==='blocker')root.locals.unfinished_work=root.locals.unfinished_work.filter(x=>x!=='state-custody-and-operations-acceptance-required');
   changed['main.tf.json']=JSON.stringify(root);assert(generationQuality(p,plan,changed,{environment}).fatalFindings.some(f=>f.code==='state-custody-mismatch'),mutation);
  }
 }
});
test('state examples separate environments, factory settings cannot poison later generations, and decisions do not grant acceptance',()=>{
 const a=protectedState('s3');a.backend.s3.encrypt=false;assert.equal(protectedState('s3').backend.s3.encrypt,true);
 const p=choose(compositionFixture('gcp'),'s3','staging');p.extensions.terraformState.environments.production={...p.extensions.terraformState.environments.staging};p.decisions[0].status='Accepted';
 const staging=terraformSketch(p,'staging'),production=terraformSketch(p,'production');assert(staging['backend.hcl.example'].includes('/staging.tfstate'));assert(production['backend.hcl.example'].includes('/production.tfstate'));assert.equal(JSON.parse(production['state-custody.json']).acceptance,'not_verified');
 p.extensions.terraformState.environments.staging.backend='http';assert(terraformSketch(p,'staging')['backend.hcl.example'].includes('PROJECT_STAGING_STATE'));
});
test('Spec Kit supplies concrete custody files and makes authorized planning depend on verification',()=>{
 const p=choose(compositionFixture('azure'),'http','staging'),files=specKit(p,{snapshotId:'state-probe',stamp:'Synthetic state handoff',environment:'staging',now:new Date('2026-11-12T00:00:00Z')}),tasks=JSON.parse(files['spec-kit/tasks.json']).tasks,task=tasks.find(t=>t.id==='TASK-STATE-CUSTODY');assert(task);assert.equal(task.status,'todo');assert(task.files.includes('terraform/state-custody.json'));assert(tasks.find(t=>t.id==='TASK-CLOUD-PLAN').dependsOn.includes(task.id));
});
test('changing state custody invalidates prior context review without rewriting its saved evidence',()=>{
 let p=choose(compositionFixture('ibm'),'http');p=reviewWorkContext(p,'block:instrument-µ');const before=structuredClone(p.extensions.architectureWork);
 assert.equal(architectureWork(p).entities.find(e=>e.id==='block:instrument-µ').contextStatus,'current');
 p.extensions.terraformState.environments.production.backend='gcs';const changed=architectureWork(p).entities.find(e=>e.id==='block:instrument-µ');assert.equal(changed.contextStatus,'changed');assert(changed.changedRefs.includes('intent:project'));assert.deepEqual(p.extensions.architectureWork,before);
});
test('emitted local state probe is byte-bound and cannot claim selected-backend verification',()=>{
 const p=choose(compositionFixture('gcp'),'gcs','staging'),files=terraformSketch(p),plan=resourcePlan(p),record=JSON.parse(files['state-custody.json']);
 const source=fs.readFileSync(new URL('../src/runtime/state_contract_check.py',import.meta.url),'utf8');assert.equal(files['state-contract-check.py'],source);assert.equal(record.localProbe.sha256,createHash('sha256').update(source).digest('hex'));assert.equal(record.localProbe.selectedBackendVerified,false);assert.equal(record.localProbe.status,'not_run');
 for(const mutation of ['code','claim','missing']){
  const changed={...files},r=structuredClone(record);if(mutation==='code')changed['state-contract-check.py']+='\n# unreviewed modification';if(mutation==='claim')r.localProbe.selectedBackendVerified=true;if(mutation==='missing')delete changed['state-contract-check.py'];changed['state-custody.json']=JSON.stringify(r);
  assert(generationQuality(p,plan,changed).fatalFindings.some(f=>f.code==='state-custody-mismatch'),mutation);
 }
});
