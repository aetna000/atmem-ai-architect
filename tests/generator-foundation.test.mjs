import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {terraformSketch} from '../src/terraform.mjs';
import {fromProjectFile,toProjectFile} from '../src/project-file.mjs';
import {validateImport} from '../src/core.mjs';
import {toAgentProject} from '../src/local-agent.mjs';
import {CLOUD_STORAGE_SCENARIOS} from '../src/cloud-storage-scenarios.mjs';
import {handoffAssessment,engineeringSteps} from '../src/handoff.mjs';
import {implementationOutcome} from '../src/implementation-outcome.mjs';
const fixture=JSON.parse(readFileSync(new URL('./fixtures/generator/architect-website-r13.json',import.meta.url)));
const base=provider=>({version:1,revision:1,name:'Quality fixture',provider,nodes:[{id:'app',position:{x:0,y:0},data:{kind:'resource',label:'Application',provider,origin:'proposed'}}],edges:[]});
test('r13 never produces AWS infrastructure or AWS account inputs for GCP',()=>{
 const p=fromProjectFile(fixture).project,files=terraformSketch(p),tf=JSON.parse(files['main.tf.json']);
 assert.equal(tf.provider?.aws,undefined);assert.equal(tf.variable.aws_account_id,undefined);assert.equal(files['preflight-aws.py'],undefined);
 assert.equal(JSON.parse(files['generation-status.json']).deployable,false);
 assert.ok(files['existing-references.json']);assert.ok(tf.locals.unfinished_work.length);
 assert.equal(handoffAssessment(p).stages.infrastructure,'not_implemented');
});
test('all providers retain their identity; unsupported designs cannot substitute providers',()=>{
 for(const provider of ['aws','azure','gcp','ibm']){
  const files=terraformSketch(base(provider)),tf=JSON.parse(files['main.tf.json']);
  if(provider==='aws')assert.ok(tf.provider.aws);else {assert.equal(tf.provider,undefined);assert.deepEqual(JSON.parse(files['generation-status.json']).providers,[provider]);}
 }
 for(const scenario of CLOUD_STORAGE_SCENARIOS){const tf=JSON.parse(terraformSketch(scenario.project)['main.tf.json']);assert.ok(tf.provider[{azure:'azurerm',gcp:'google',ibm:'ibm'}[scenario.id]]);assert.equal(tf.provider.aws,undefined);}
});
test('mixed storage design never silently selects a provider',()=>{
 const p=structuredClone(CLOUD_STORAGE_SCENARIOS[0].project);p.nodes.push(base('gcp').nodes[0]);
 const files=terraformSketch(p),tf=JSON.parse(files['main.tf.json']);assert.equal(tf.provider,undefined);assert.equal(files['tests/storage.tftest.hcl'],undefined);assert.equal(JSON.parse(files['generation-status.json']).deployable,false);
});
test('long descriptions round-trip intact through project, agent and handoff boundaries',()=>{
 const p=base('aws');p.nodes[0].data.description='Responsibility and acceptance details. '.repeat(100);
 const clean=validateImport(p),reopened=fromProjectFile(toProjectFile(clean)).project;
 assert.equal(reopened.nodes[0].data.description,p.nodes[0].data.description);assert.equal(toAgentProject(clean).nodes[0].data.description,p.nodes[0].data.description);
 p.nodes[0].data.description='x'.repeat(16001);assert.throws(()=>validateImport(p),/Nothing was truncated/);
});
test('external client guidance and brief do not invent infrastructure or reuse chat fragments',()=>{
 assert.match(engineeringSteps({externalReference:true,existing:true})[0],/no resource or import/);
 const p={name:'Example',requirements:'yes\nwhat do we have\naustralia',needs:[{statement:'Preserve the existing website.'}]};
 assert.ok(!implementationOutcome(p).includes('what do we have'));assert.match(implementationOutcome(p),/Preserve the existing website/);
});

test('a contradictory existing-reference binding cannot accidentally provision replacement storage',()=>{
 const p=base('aws');p.nodes[0].data.service='Amazon S3';p.nodes[0].data.binding='existing-service';
 assert.throws(()=>terraformSketch(p),/Reference bindings/);assert.throws(()=>validateImport(p),/Reference bindings/);
 p.nodes[0].data.origin='existing';p.nodes[0].data.deploymentMode='create';assert.throws(()=>terraformSketch(p),/Reference bindings/);
 p.nodes[0].data.deploymentMode='reference';assert.doesNotThrow(()=>terraformSketch(p));
});
