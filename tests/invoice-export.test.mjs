import test from'node:test';
import assert from'node:assert/strict';
import{invoiceProject}from'./fixtures/invoice-project.mjs';
import{resourcePlan}from'../src/resources.mjs';
import{terraformSketch}from'../src/terraform.mjs';
import{deliveryPack}from'../src/delivery.mjs';
import{interfaceContracts}from'../src/interface-contracts.mjs';
import{validateImport}from'../src/core.mjs';
import{toAgentProject}from'../src/local-agent.mjs';
import{generationQuality}from'../src/generation-quality.mjs';

for(const provider of ['aws','azure','gcp','ibm']){
 test(provider+' preserves unresolved placement and never interpolates imported region expressions',()=>{
  for(const region of ['Australia','${file("/not-permitted") }']){
   const p=invoiceProject(provider);p.nodes[1].data.config.region=region;const files=terraformSketch(p),config=JSON.parse(files['main.tf.json']);
   assert.ok(config.locals.unfinished_work.includes('invoice-config-region'));assert.equal(config.variable.region.default,undefined);assert.ok(!files['main.tf.json'].includes('/not-permitted'));assert.equal(resourcePlan(p).rows.find(row=>row.id==='invoice').region,region);assert.equal(p.nodes[1].data.config.region,region);
  }
 });
 test(provider+' cannot pass structural coverage when its native API deployment unit is missing',()=>{
  const p=invoiceProject(provider),plan=resourcePlan(p),files=terraformSketch(p),config=JSON.parse(files['main.tf.json']),type={aws:'aws_ecs_service',azure:'azapi_resource',gcp:'google_cloud_run_v2_service',ibm:'ibm_code_engine_app'}[provider];
  delete config.resource[type].block_696e766f696365_api;files['main.tf.json']=JSON.stringify(config);
  const quality=generationQuality(p,plan,files);assert.equal(quality.infrastructureComplete,false);assert.ok(quality.fatalFindings.some(f=>f.code==='missing-resource'&&f.message.includes(type+'.block_696e766f696365_api')));
 });
 test(provider+' invoice contract survives design/model boundaries and selects complete native source',()=>{
  const original=invoiceProject(provider);
  for(const p of [original,validateImport(original),{...toAgentProject(original),id:original.id}]){
   const before=JSON.stringify(p),plan=resourcePlan(p),files=terraformSketch(p),quality=JSON.parse(files['generation-quality.json']);
   assert.equal(JSON.stringify(p),before);assert.deepEqual(plan.gapDetails,[]);assert.equal(plan.invoicePlan.entries.length,1);assert.deepEqual(quality.fatalFindings,[]);assert.equal(quality.infrastructureComplete,true);assert.equal(quality.deploymentCandidate,false);
   assert.equal(p.nodes[1].data.config.maxPdfBytes,10000000);assert.equal(p.nodes[1].data.config.retentionDays,90);assert.equal(p.edges[1].integration,'approved-accounting-api');
   for(const name of ['invoice_http.py','invoice_worker.py','workflow_schema.sql','tests/run.py','tests/invoice_http_acceptance.py','test-requirements.lock','Dockerfile.tests','parser/invoice_parser_service.py'])assert.ok(files['applications/block_696e766f696365/'+name],name);
   const native=JSON.parse(files['main.tf.json']);assert.deepEqual(native.locals.unfinished_work,[]);assert.equal(native.terraform.backend,undefined);assert.match(files['STATE.md'],/locking/);assert.match(files['OPERATING_JOBS.md'],/operator|operating/i);
   assert.ok(Object.values(native.resource).every(group=>Object.keys(group).every(name=>!name.includes('block_6163636f756e74696e67'))));
   const interfaces=interfaceContracts(p,plan);assert.equal(interfaces.length,2);assert.match(interfaces[0].authorization,/Ordinary uploaders cannot approve/);assert.match(interfaces[1].idempotency,/uncertain|unknown/);assert.equal(interfaces[1].contract,'normalized-action-v1');
  }
 });
 test(provider+' invoice preserves extra components, flows and incompatible limits as blocked scope',()=>{
  const p=invoiceProject(provider);p.nodes.push({id:'extra',type:'resource',position:{x:0,y:300},data:{label:'Required additional store',provider,kind:'resource',implementation:'private-object-storage',service:'Do not replace'}});p.edges.push({id:'extra-edge',source:'invoice',target:'extra',label:'Additional required persistence'});p.nodes[1].data.config.retentionDays=365;
  const files=terraformSketch(p),tf=JSON.parse(files['main.tf.json']),plan=JSON.parse(files['resource-schedule.json']);assert.equal(plan.rows.length,4);assert.equal(plan.connections.length,3);assert.ok(tf.locals.unfinished_work.includes('resource-block_6578747261'));assert.ok(tf.locals.unfinished_work.includes('invoice-config-retentionDays'));assert.ok(tf.locals.unfinished_work.some(id=>id.startsWith('connection-')));assert.equal(JSON.parse(files['generation-quality.json']).infrastructureComplete,false);assert.match(JSON.stringify(tf.resource.terraform_data.review_gate.lifecycle.precondition),/unfinished_work/);assert.equal(p.nodes[1].data.config.retentionDays,365);
 });
 test(provider+' invoice cannot recreate an existing deployment or hide a second workflow',()=>{
  const p=invoiceProject(provider);p.nodes[1].data.origin='existing';let files=terraformSketch(p);assert.equal(resourcePlan(p).invoicePlan.entries.length,0);assert.equal(Object.keys(JSON.parse(files['main.tf.json']).resource||{}).filter(name=>name!=='terraform_data').length,0);
  const other=invoiceProject(provider);other.nodes.push({...structuredClone(other.nodes[1]),id:'second'});files=terraformSketch(other);assert.equal(resourcePlan(other).invoicePlan.entries.length,0);assert.equal(JSON.parse(files['generation-quality.json']).infrastructureComplete,false);
 });
 test(provider+' production state is explicit and the invoice Spec Kit has an executable phased DAG',()=>{
  const p=invoiceProject(provider),before=JSON.stringify(p),files=deliveryPack(p,null,'production');assert.equal(JSON.stringify(p),before);
  const config=JSON.parse(files['terraform/main.tf.json']);assert.deepEqual(Object.keys(config.terraform.backend),[{aws:'s3',azure:'azurerm',gcp:'gcs',ibm:'http'}[provider]]);if(provider!=='aws')assert.ok(!config.terraform.backend.s3);assert.match(files['terraform/.gitignore'],/backend\.hcl/);
  const tasks=JSON.parse(files['spec-kit/tasks.json']).tasks,ids=new Set(tasks.map(t=>t.id)),done=new Set();
  while(done.size<tasks.length){const ready=tasks.filter(t=>!done.has(t.id)&&t.dependsOn.every(id=>done.has(id)));assert.ok(ready.length,'cyclic/missing invoice task dependencies');ready.forEach(t=>done.add(t.id));}
  for(const phase of ['SOURCE','STATE','FOUNDATION','IMAGES','BOOTSTRAP','OPERATIONS','APPLICATION'])assert.ok([...ids].some(id=>id.startsWith('TASK-INVOICE-'+phase+'-')),phase);
  const implementation=JSON.parse(files['spec-kit/implementation-map.json']).components.find(c=>c.id==='invoice');assert.ok(implementation.requiredInputs.includes('runtime_image'));assert.ok(implementation.generatedFiles.includes('terraform/OPERATING_JOBS.md'));assert.ok(implementation.requirements.includes('invoice-approval'));
  assert.match(files['spec-kit/tasks.md'],/tests\/run.py/);assert.match(files['spec-kit/tasks.md'],/SQL user\/reviewer/);assert.ok(files['spec-kit/invoice-delivery.md']);assert.equal(JSON.parse(files['spec-kit/progress.json']).tasks.length,tasks.length);
 });
}
