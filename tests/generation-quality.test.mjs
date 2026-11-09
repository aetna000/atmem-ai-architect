import test from 'node:test';import assert from 'node:assert/strict';
import {generationQuality} from '../src/generation-quality.mjs';
import {resourcePlan} from '../src/resources.mjs';import {terraformSketch} from '../src/terraform.mjs';
import {CLOUD_STORAGE_SCENARIOS} from '../src/cloud-storage-scenarios.mjs';
import {deliveryPack} from '../src/delivery.mjs';
test('all native storage contracts record matching provider skills without claiming validation',()=>{
 for(const {project:p,id} of CLOUD_STORAGE_SCENARIOS){const q=generationQuality(p,resourcePlan(p),terraformSketch(p));assert.equal(q.findings.length,0,JSON.stringify(q.findings));assert.ok(q.skills.some(s=>s.id===id&&s.sha256.length===64));assert.equal(q.validation.runtime,'not_run');assert.equal(q.deploymentCandidate,false);}
});
test('independent output inspection catches missing resources and wrong-provider code',()=>{
 const p=CLOUD_STORAGE_SCENARIOS[1].project,files=terraformSketch(p);let tf=JSON.parse(files['main.tf.json']);delete tf.resource.google_storage_bucket;tf.resource.aws_s3_bucket={injected:{}};files['main.tf.json']=JSON.stringify(tf);
 const q=generationQuality(p,resourcePlan(p),files);assert.ok(q.findings.some(f=>f.code==='provider-mismatch'));assert.ok(q.findings.some(f=>f.code==='missing-resource'));assert.equal(q.infrastructureComplete,false);
});
test('delivery manifest includes the actual capability and skill report',()=>{
 const p=CLOUD_STORAGE_SCENARIOS[0].project,files=deliveryPack(p,null);const q=JSON.parse(files['generation-quality.json']);assert.ok(q.skills.some(s=>s.id==='terraform'));assert.ok(JSON.parse(files['manifest.json']).files.includes('generation-quality.json'));assert.ok(!files['README.md'].includes('partial AWS foundation'));
});
test('unsafe generated execution, unreviewed modules and embedded credentials fail independent admission',()=>{
 const p=CLOUD_STORAGE_SCENARIOS[1].project,files=terraformSketch(p),tf=JSON.parse(files['main.tf.json']);tf.provider.google.credentials='not-a-real-credential';tf.resource.terraform_data.review_gate.provisioner={'local-exec':{command:'unreviewed'}};tf.module={unknown:{source:'https://example.com/unreviewed'}};files['main.tf.json']=JSON.stringify(tf);
 const q=generationQuality(p,resourcePlan(p),files);for(const code of ['execution-hook','embedded-provider-credential','unreviewed-module'])assert.ok(q.fatalFindings.some(f=>f.code===code),code);assert.equal(q.infrastructureComplete,false);
});

test('all seven established AWS compositions pass independent compiler admission',async()=>{
 const {readFileSync,readdirSync}=await import('node:fs');
 for(const id of readdirSync('examples/aws').filter(n=>/^0[1-7]-/.test(n))){
  const meta=JSON.parse(readFileSync(`examples/aws/${id}/results.json`));
  const p=JSON.parse(readFileSync(`examples/aws/${id}/history/${meta.sourceRun}/round-2/workspace.json`));
  const q=JSON.parse(terraformSketch(p)['generation-quality.json']);
  assert.deepEqual(q.fatalFindings,[],id);assert.equal(q.deploymentCandidate,false);
 }
});
