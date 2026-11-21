import test from 'node:test';
import assert from 'node:assert/strict';
import {ibmStructuredProject} from './fixtures/ibm-structured-project.mjs';
import {terraformSketch} from '../src/terraform.mjs';
import {resourcePlan} from '../src/resources.mjs';
import {validateImport} from '../src/core.mjs';
import {toAgentProject} from '../src/local-agent.mjs';
import {deliveryPack} from '../src/delivery.mjs';

test('IBM composes user and workload identity without static credentials or a compute-link cycle',()=>{
 for(const p of [ibmStructuredProject(),validateImport(ibmStructuredProject()),toAgentProject(ibmStructuredProject())]){
  assert.equal(p.nodes[1].data.implementation,'ibm-structured-app');
  const files=terraformSketch(p),tf=JSON.parse(files['main.tf.json']),n=resourcePlan(p).rows.find(r=>r.id==='workspace').address;
  assert.deepEqual(tf.locals.unfinished_work,[]);assert.deepEqual(JSON.parse(files['generation-quality.json']).fatalFindings,[]);
  const app=tf.resource.ibm_code_engine_app[n];assert.equal(app.run_compute_resource_token_enabled,true);assert.equal(app.run_as_user,10001);
  assert.ok(!app.depends_on.includes('ibm_iam_trusted_profile_link.'+n));assert.equal(tf.resource.ibm_iam_trusted_profile_link[n].link.component_name,'${ibm_code_engine_app.'+n+'.name}');
  const policy=tf.resource.ibm_iam_trusted_profile_policy[n];assert.deepEqual(policy.roles,['Writer']);assert.equal(policy.resources.service,'pm-20');assert.equal(policy.resources.resource_instance_id,'${var.'+n+'_runtime_instance_id}');
  assert.equal(tf.resource.ibm_appid_application[n].type,'singlepageapp');assert.equal(tf.resource.ibm_appid_idp_cloud_directory[n].signup_enabled,false);
  assert.equal(tf.resource.ibm_appid_idp_cloud_directory[n].self_service_enabled,false);
  for(const idp of ['facebook','google','saml'])assert.equal(tf.resource['ibm_appid_idp_'+idp][n].is_active,false);
  assert.deepEqual(tf.variable[n+'_authorized_user_subjects'].default,[]);assert.equal(tf.resource.ibm_appid_user_roles[n].tenant_id,'${ibm_resource_instance.'+n+'.guid}');
  assert.equal(tf.data.ibm_code_engine_project.destination.project_id,'${var.code_engine_project_id}');assert.ok(!tf.resource.ibm_code_engine_project);
  assert.equal(tf.resource.ibm_appid_redirect_urls[n].urls[0],'${ibm_code_engine_app.'+n+'.endpoint}/');
  const folder='applications/'+n+'/';assert.match(files[folder+'Dockerfile'],/USER 10001:10001/);assert.match(files[folder+'Dockerfile'],/--checksum=sha256:/);assert.ok(files[folder+'policy_review.py']);assert.ok(files[folder+'ibm_acceptance.py']);assert.match(files[folder+'web/index.html'],/Clear workspace/);
  assert.ok(!JSON.stringify(tf).includes('ibmcloud_api_key'));assert.ok(!JSON.stringify(tf).includes('client_secret'));
 }
});
test('IBM preserves unrelated required scope, existing deployments and accepted model instructions',()=>{
 const p=ibmStructuredProject();p.nodes.push({id:'ledger',position:{x:0,y:0},data:{label:'Durable credits',kind:'resource',provider:'ibm',service:'IBM Cloudant'}});p.edges.push({id:'durable',source:'workspace',target:'ledger'});
 const tf=JSON.parse(terraformSketch(p)['main.tf.json']);assert.ok(tf.locals.unfinished_work.some(g=>g.startsWith('resource-')));assert.ok(tf.locals.unfinished_work.some(g=>g.startsWith('connection-')));
 const missing=ibmStructuredProject();delete missing.nodes[1].data.config.outputContract;assert.ok(resourcePlan(missing).gapDetails.some(g=>g.componentIds?.includes('workspace')));
 const existing=ibmStructuredProject();Object.assign(existing.nodes[1].data,{origin:'existing',binding:'existing-service',deploymentMode:'reference'});assert.ok(!JSON.parse(terraformSketch(existing)['main.tf.json']).resource?.ibm_code_engine_app);
 const text=ibmStructuredProject();text.nodes[1].data.config.outputContract.instruction='${file("/private/secret")}';const config=JSON.parse(terraformSketch(text)['main.tf.json']);const env=Object.values(config.resource.ibm_code_engine_app)[0].run_env_variables;assert.equal(JSON.parse(Buffer.from(env.find(e=>e.name==='OUTPUT_CONTRACT_BASE64').value,'base64')).instruction,'${file("/private/secret")}');
 text.nodes[1].data.config.maxInputBytes=100000;assert.throws(()=>terraformSketch(text),/limits/);
});
test('IBM readable handoff names executable artifacts and exact interface with unapproved account boundaries',()=>{
 const files=deliveryPack(ibmStructuredProject(),null),tasks=JSON.parse(files['spec-kit/tasks.json']).tasks;
 const setup=tasks.find(t=>t.steps.some(step=>step.includes('ibm_acceptance.py')));assert.ok(setup);assert.ok(setup.files.some(f=>f.endsWith('/Dockerfile')));
 const interfaces=JSON.parse(files['spec-kit/interfaces.json']);assert.match(JSON.stringify(interfaces),/App ID/);
 const tf=JSON.parse(terraformSketch(ibmStructuredProject(),'production')['main.tf.json']);assert.equal(tf.variable.review_approved.default,false);assert.ok(tf.locals.unfinished_work.includes('production-state-backup-and-operating-review-required'));
});
