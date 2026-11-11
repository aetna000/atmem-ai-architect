import test from 'node:test';import assert from 'node:assert/strict';
import {invoiceProject} from './fixtures/invoice-project.mjs';import {CONTAINER_SERVICES} from '../src/container-contracts.mjs';import {resourcePlan} from '../src/resources.mjs';import {capabilityCompositionPlan,compileCapabilityComposition} from '../src/delivery-capabilities.mjs';import {generationQuality} from '../src/generation-quality.mjs';
function fixture(provider='aws'){
 const project=invoiceProject(provider);project.nodes.push({id:'laboratory',position:{x:900,y:0},data:{label:'Independent laboratory instrument',kind:'resource',provider,origin:'proposed',implementation:'container-service',service:CONTAINER_SERVICES[provider].service}});const plan=capabilityCompositionPlan(project,resourcePlan),files=compileCapabilityComposition(project,plan,resourcePlan);return {project,plan,files};
}
const change=(f,path,mutate)=>{const value=JSON.parse(f.files[path]);mutate(value);f.files[path]=JSON.stringify(value);};
const unit=f=>f.plan.composition.units.find(u=>u.id==='invoice');
const codes=f=>generationQuality(f.project,f.plan,f.files).fatalFindings.map(f=>f.code);
for(const provider of Object.keys(CONTAINER_SERVICES))test(provider+': admission checks actual owned module resources without trusting row/manifest paths',()=>{
 const f=fixture(provider),q=generationQuality(f.project,f.plan,f.files);assert.deepEqual(q.fatalFindings,[]);assert.equal(q.infrastructureComplete,true);assert.equal(q.deploymentCandidate,false);assert.equal(q.validation.schema,'not_run');assert(q.components.find(c=>c.id==='invoice').terraformModule);
 const contract={aws:'aws_ecs_service',azure:'azapi_resource',gcp:'google_cloud_run_v2_service',ibm:'ibm_code_engine_app'}[provider],u=unit(f);change(f,u.path+'/main.tf.json',config=>{delete config.resource[contract].block_696e766f696365_api;});assert(codes(f).includes('missing-resource'));
});
for(const [name,mutate,expected]of [
 ['remote source',f=>change(f,'main.tf.json',c=>{c.module[unit(f).module].source='git::https://unreviewed.test/module';}),'unreviewed-module'],
 ['provider alias borrowed from sibling',f=>change(f,'main.tf.json',c=>{c.module[unit(f).module].providers.aws='aws.'+f.plan.composition.units.find(u=>u.id==='laboratory').module;}),'unreviewed-module'],
 ['expanded instances',f=>change(f,'main.tf.json',c=>{c.module[unit(f).module].count=2;}),'unreviewed-module'],
 ['root gate removed',f=>change(f,'main.tf.json',c=>{delete c.resource.terraform_data.review_gate;}),'missing-work-gate'],
 ['root approval default enabled',f=>change(f,'main.tf.json',c=>{c.variable.review_approved.default=true;}),'missing-work-gate'],
 ['child approval bypassed',f=>change(f,'main.tf.json',c=>{c.module[unit(f).module].review_approved=true;}),'unreviewed-module'],
 ['input bound to sibling',f=>change(f,'main.tf.json',c=>{c.module[unit(f).module].region='${var.foreign_region}';}),'unreviewed-module'],
 ['variable validation removed',f=>change(f,'main.tf.json',c=>{delete c.variable[unit(f).module+'__region'].validation;}),'unreviewed-module'],
 ['provider credential hidden in alias array',f=>change(f,'main.tf.json',c=>{c.provider.aws[0].secret_key='fixture-credential';}),'embedded-provider-credential'],
 ['child execution hook',f=>change(f,unit(f).path+'/main.tf.json',c=>{c.resource.terraform_data.review_gate.provisioner={'local-exec':{command:'unreviewed'}};}),'execution-hook'],
 ['child external-state reader',f=>change(f,unit(f).path+'/main.tf.json',c=>{c.data.terraform_remote_state={unreviewed:{}};}),'external-execution-or-state'],
 ['nested module',f=>change(f,unit(f).path+'/main.tf.json',c=>{c.module={remote:{source:'unreviewed'}};}),'unreviewed-module'],
 ['child backend',f=>change(f,unit(f).path+'/main.tf.json',c=>{c.terraform.backend={http:{address:'https://foreign.test/state'}};}),'unreviewed-module'],
 ['unowned root resource',f=>change(f,'main.tf.json',c=>{c.resource.aws_s3_bucket={foreign:{}};}),'unreviewed-module'],
 ['extra child Terraform file',f=>{f.files[unit(f).path+'/extra.tf']='resource "terraform_data" "unreviewed" {}';},'unreviewed-module'],
 ['forged metadata cannot approve foreign closure',f=>change(f,'composition.json',c=>{c.units[0].path='units/unreviewed';}),'unreviewed-module'],
 ['missing owned module',f=>{delete f.files[unit(f).path+'/main.tf.json'];},'unreviewed-module'],
 ['malformed manifest',f=>{f.files['composition.json']='{"version":1,"units":{}}';},'unreviewed-module'],
 ['unknown child provider',f=>change(f,unit(f).path+'/main.tf.json',c=>{c.terraform.required_providers.aws.source='unreviewed/aws';}),'unreviewed-provider'],
 ['missing unit schedule row',f=>{f.plan.rows=f.plan.rows.filter(r=>r.id!=='invoice');},'unregistered-implementation'],
 ['claimed external ownership',f=>{f.plan.rows.find(r=>r.id==='invoice').existing=true;},'unregistered-implementation'],
])test('module admission rejects '+name,()=>{const f=fixture();mutate(f);assert(codes(f).includes(expected),JSON.stringify(codes(f)));assert.equal(generationQuality(f.project,f.plan,f.files).infrastructureComplete,false);});
test('required configuration scope remains incomplete even when a forged root drops its blockers',()=>{
 const f=fixture();f.project.nodes[1].data.config.retentionDays=365;f.plan=capabilityCompositionPlan(f.project,resourcePlan);f.files=compileCapabilityComposition(f.project,f.plan,resourcePlan);change(f,'main.tf.json',c=>{c.locals.unfinished_work=[];});const q=generationQuality(f.project,f.plan,f.files);assert(q.fatalFindings.some(f=>f.code==='missing-work-gate'));assert(q.findings.some(f=>f.code==='unfinished-scope'));assert.equal(q.infrastructureComplete,false);
});
test('required unit tests cannot disappear behind a forged complete metadata report',()=>{
 const f=fixture();delete f.files[unit(f).path+'/tests/invoice.tftest.hcl'];assert(codes(f).includes('unreviewed-module'));
});
test('a child cannot borrow another cloud merely because that cloud is present elsewhere',()=>{
 const f=fixture();f.project.nodes.at(-1).data.provider='gcp';f.project.nodes.at(-1).data.service=CONTAINER_SERVICES.gcp.service;f.plan=capabilityCompositionPlan(f.project,resourcePlan);f.files=compileCapabilityComposition(f.project,f.plan,resourcePlan);change(f,unit(f).path+'/main.tf.json',c=>{c.resource.google_storage_bucket={foreign:{}};});assert(codes(f).includes('provider-mismatch'));
});
