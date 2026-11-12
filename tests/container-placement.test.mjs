import test from 'node:test';import assert from 'node:assert/strict';
import {compositionFixture} from '../scripts/engine-evaluation/composition-fixtures.mjs';
import {resourcePlan} from '../src/resources.mjs';import {terraformSketch} from '../src/terraform.mjs';import {generationQuality} from '../src/generation-quality.mjs';
const regions={aws:'eu-west-1',azure:'westeurope',gcp:'europe-west1',ibm:'eu-de'};
for(const [provider,region]of Object.entries(regions))test(provider+': accepted placement is bound in standalone and mixed output with no source mutation',()=>{
 const p=compositionFixture(provider),node=p.nodes.at(-1);node.data.config={region};const before=structuredClone(p);
 for(const project of [p,{...p,nodes:[node],edges:[]}]){
  const plan=resourcePlan(project),files=terraformSketch(project),unit=plan.composition?.units.find(u=>u.id===node.id),tf=JSON.parse(files[(unit?unit.path+'/':'')+'main.tf.json']),root=JSON.parse(files['main.tf.json']),key=unit?unit.module+'__region':'region';
  assert.equal(tf.variable.region.default,region);assert.equal(root.variable[key].default,region);assert(tf.variable.region.validation.condition.includes('var.region == '+JSON.stringify(region)));assert.equal(JSON.parse(files['generation-quality.json']).infrastructureComplete,true);assert.deepEqual(plan.gaps,[]);
  assert(files[(unit?unit.path+'/':'')+'tests/container.tftest.hcl'].includes('changed_accepted_region_blocked'));
  if(provider==='azure')assert(tf.data.azurerm_container_app_environment);if(provider==='ibm')assert(tf.data.ibm_code_engine_project);
 }
 assert.deepEqual(p,before);
});
test('unknown placement requires an explicit input; unsupported placement is retained as blocking scope',()=>{
 for(const provider of Object.keys(regions)){
  const p=compositionFixture(provider);let files=terraformSketch(p),plan=resourcePlan(p),unit=plan.composition.units.find(u=>u.id===p.nodes.at(-1).id);assert.equal(JSON.parse(files[unit.path+'/main.tf.json']).variable.region.default,undefined);
  p.nodes.at(-1).data.config={region:'Sydney (proposed)'};files=terraformSketch(p);assert.equal(resourcePlan(p).rows.at(-1).region,'Sydney (proposed)');assert(resourcePlan(p).gaps.some(g=>g.includes('region="Sydney (proposed)"')));assert.equal(JSON.parse(files['generation-quality.json']).infrastructureComplete,false);assert.deepEqual(JSON.parse(files['generation-quality.json']).fatalFindings,[]);
 }
});
for(const provider of Object.keys(regions))test(provider+': independent inspection rejects region input/provider/data-binding mutations',()=>{
 const p=compositionFixture(provider),node=p.nodes.at(-1);node.data.config={region:regions[provider]};const plan=resourcePlan(p),files=terraformSketch(p),unit=plan.composition.units.find(u=>u.id===node.id),key=unit.path+'/main.tf.json';
 for(const mutation of ['provider','default','region-guard','native-binding','unowned-query','unowned-resource']){
  const changed={...files},root=JSON.parse(files['main.tf.json']),tf=JSON.parse(files[key]),name=plan.rows.find(r=>r.id===node.id).address;
  if(mutation==='provider'){const providerName=provider==='gcp'?'google':provider==='azure'?'azurerm':provider;const config=root.provider[providerName].find(v=>v.alias===unit.module);config[provider==='azure'?'subscription_id':'region']='foreign-destination';}
  if(mutation==='default')tf.variable.region.default='another-region';
  if(mutation==='region-guard')tf.variable.region.validation.condition='${true}';
  if(mutation==='unowned-query'){tf.data||={};tf.data[provider==='aws'?'aws_caller_identity':provider==='azure'?'azurerm_client_config':provider==='gcp'?'google_client_config':'ibm_iam_account_settings']={unowned:{}};}
  if(mutation==='unowned-resource'){tf.resource[provider==='aws'?'aws_s3_bucket':provider==='azure'?'azurerm_resource_group':provider==='gcp'?'google_storage_bucket':'ibm_cos_bucket']={unowned:{}};}
  if(mutation==='native-binding'){
   if(provider==='aws')tf.resource.aws_ecs_service[name].region='us-east-1';
   if(provider==='gcp')tf.resource.google_cloud_run_v2_service[name].location='us-central1';
   if(provider==='azure')tf.resource.azurerm_container_app[name].lifecycle.precondition=[];
   if(provider==='ibm')tf.resource.ibm_code_engine_app[name].lifecycle.precondition=[];
  }
  changed['main.tf.json']=JSON.stringify(root);changed[key]=JSON.stringify(tf);
  assert(generationQuality(p,plan,changed).fatalFindings.some(f=>f.code==='container-constraint-mismatch'),mutation);
 }
});
test('separate regions in one cloud retain distinct provider aliases and locked root inputs',()=>{
 const p=compositionFixture('gcp'),node=structuredClone(p.nodes.at(-1));node.data.config={region:'us-central1'};p.nodes.at(-1).data.config={region:'europe-west1'};node.id='other-instrument';p.nodes.push(node);const files=terraformSketch(p),plan=resourcePlan(p),root=JSON.parse(files['main.tf.json']);
 for(const id of [p.nodes.at(-2).id,node.id]){const unit=plan.composition.units.find(u=>u.id===id);assert(root.provider.google.some(v=>v.alias===unit.module&&v.region==='${var.'+unit.module+'__region}'));assert.equal(root.variable[unit.module+'__region'].default,p.nodes.find(n=>n.id===id).data.config.region);}
 assert.deepEqual(JSON.parse(files['generation-quality.json']).fatalFindings,[]);
});
