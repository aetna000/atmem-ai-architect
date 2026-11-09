import test from 'node:test';
import assert from 'node:assert/strict';
import {publicFaqProject} from './fixtures/public-faq-project.mjs';
import {terraformSketch} from '../src/terraform.mjs';
import {resourcePlan} from '../src/resources.mjs';
import {validateImport} from '../src/core.mjs';
import {toAgentProject} from '../src/local-agent.mjs';
import {interfaceContracts} from '../src/interface-contracts.mjs';
import {generationQuality} from '../src/generation-quality.mjs';

for(const provider of ['aws','azure','gcp','ibm']){
 test(provider+' public FAQ survives project boundaries and emits a complete registered composition',()=>{
  for(const project of [publicFaqProject(provider),validateImport(publicFaqProject(provider)),toAgentProject(publicFaqProject(provider))]){
   assert.equal(project.nodes[1].data.implementation,'public-faq-app');
   const plan=resourcePlan(project),files=terraformSketch(project),tf=JSON.parse(files['main.tf.json']),quality=JSON.parse(files['generation-quality.json']);
   assert.equal(plan.publicFaqPlan.entries.length,1);assert.deepEqual(plan.gapDetails,[]);assert.deepEqual(tf.locals.unfinished_work,[]);assert.deepEqual(quality.fatalFindings,[]);assert.equal(quality.infrastructureComplete,true);assert.equal(quality.deploymentCandidate,false);
   const n=plan.rows.find(r=>r.id==='faq').address,folder='applications/'+n+'/';
   for(const name of ['public_faq.py','public_faq_app.py','public_catalog_store.py','public_catalog_admin.py','faq_acceptance.py','requirements.lock','output-contract.json','faq-deployment.json','web/app.js'])assert.ok(files[folder+name],name);
   assert.equal(JSON.parse(files[folder+'faq-deployment.json']).provider,provider);assert.match(files[folder+'Dockerfile'],/USER 10001:10001/);assert.ok(!files[folder+'Dockerfile'].includes('public_catalog_admin.py'));
   const edge=interfaceContracts(project,plan)[0];assert.equal(edge.generated,true);assert.match(edge.identity,/anonymous/);assert.match(edge.sourceLifecycle,/version/);
  }
 });
 test(provider+' keeps independent additional requirements and custom operations as unfinished work',()=>{
  const project=publicFaqProject(provider);project.nodes.push({id:'extra',position:{x:0,y:0},data:{label:'Required extra service',kind:'resource',provider,service:provider==='aws'?'Amazon S3':'Required durable service'}});project.edges.push({id:'extra-edge',source:'faq',target:'extra'});
  const files=terraformSketch(project),tf=JSON.parse(files['main.tf.json']);assert.ok(tf.locals.unfinished_work.includes('resource-block_6578747261'));assert.ok(tf.locals.unfinished_work.some(g=>g.startsWith('connection-')));assert.equal(JSON.parse(files['generation-quality.json']).infrastructureComplete,false);
  const custom=publicFaqProject(provider);custom.nodes[1].data.config.outputContract={instruction:'Separate job',fields:[{name:'answer',type:'string',description:'Custom'}]};assert.throws(()=>terraformSketch(custom),/custom operation/);
 });
 test(provider+' never converts an existing FAQ deployment into new infrastructure',()=>{
  const project=publicFaqProject(provider);project.nodes[1].data.origin='existing';project.nodes[1].data.existingHandling='reference';
  assert.equal(resourcePlan(project).publicFaqPlan.entries.length,0);
 });
 test(provider+' represents the authorized editor as a distinct typed operator interface',()=>{
  const project=publicFaqProject(provider);project.nodes.push({id:'editor',position:{x:0,y:0},data:{label:'Company content editors',kind:'tool',provider:'tools',origin:'existing',binding:'public-catalog-editor'}});project.edges.push({id:'editor-faq',source:'editor',target:'faq',integration:'public-catalog-edit'});
  for(const p of [project,validateImport(project),toAgentProject(project)]){
   const plan=resourcePlan(p),files=terraformSketch(p),tf=JSON.parse(files['main.tf.json']);assert.deepEqual(plan.publicFaqPlan.editorIds,['editor']);assert.deepEqual(plan.gapDetails,[]);assert.deepEqual(tf.locals.unfinished_work,[]);assert.ok(!JSON.stringify(tf.resource).includes('block_656469746f72'));
   const contract=interfaceContracts(p,plan).find(e=>e.id==='editor-faq');assert.equal(contract.generated,true);assert.match(contract.transport,/operator CLI/);
  }
  project.edges[1].integration=undefined;assert.ok(resourcePlan(project).gapDetails.some(g=>g.edgeIds?.includes('editor-faq')),'Labels must never silently authorize editing');
 });
}

test('Azure mocks exercise the paired App Service health-check configuration',()=>{
 const project=publicFaqProject('azure'),files=terraformSketch(project),tf=JSON.parse(files['main.tf.json']),app=Object.values(tf.resource.azurerm_linux_web_app)[0];
 assert.equal(app.site_config.health_check_path,'/healthz');assert.equal(app.site_config.health_check_eviction_time_in_min,2);assert.match(files['tests/public-faq.tftest.hcl'],/override_during = plan/);
});

test('an independent S3 access edge cannot borrow FAQ composition coverage',()=>{
 const project=publicFaqProject('aws');project.nodes.push({id:'extra',position:{x:0,y:0},data:{label:'Additional required storage',kind:'resource',provider:'aws',service:'Amazon S3'}},{id:'operator',position:{x:0,y:0},data:{label:'Existing storage operator',kind:'tool',provider:'tools',origin:'existing',binding:'aws-iam-principal'}});project.edges.push({id:'external-storage',source:'operator',target:'extra',access:'s3-read-write'});
 const plan=resourcePlan(project);assert.equal(plan.connections.find(e=>e.id==='external-storage').generated,false);assert.ok(plan.gapDetails.some(g=>g.edgeIds?.includes('external-storage')));
});

test('new AWS FAQ source avoids a service closed to new customers and catches reintroduction',()=>{
 const project=publicFaqProject('aws'),plan=resourcePlan(project),files=terraformSketch(project),tf=JSON.parse(files['main.tf.json']);
 assert.ok(!tf.resource.aws_apprunner_service);assert.ok(tf.resource.aws_lambda_function);assert.ok(files['build-runtime.py']);assert.match(files['applications/block_666171/BUILD.md'],/not the Lambda deployment artifact/);assert.ok(!tf.variable.block_666171_image_digest);
 tf.resource.aws_apprunner_service={unsafe_default:{service_name:'unsafe-default'}};
 const quality=generationQuality(project,plan,{...files,'main.tf.json':JSON.stringify(tf)});assert.ok(quality.fatalFindings.some(f=>f.code==='service-eligibility-unverified'));
});
