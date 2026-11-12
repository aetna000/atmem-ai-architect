import test from 'node:test';
import assert from 'node:assert/strict';
import {gcpStructuredProject} from './fixtures/gcp-structured-project.mjs';
import {terraformSketch} from '../src/terraform.mjs';
import {resourcePlan} from '../src/resources.mjs';
import {validateImport} from '../src/core.mjs';
import {toAgentProject} from '../src/local-agent.mjs';
import {deliveryPack} from '../src/delivery.mjs';

test('Google composition emits IAP-protected source, dedicated workload identity and read-only model controls',()=>{
 for(const p of [gcpStructuredProject(),validateImport(gcpStructuredProject()),toAgentProject(gcpStructuredProject())]){
  assert.equal(p.nodes[1].data.implementation,'gcp-structured-app');
  const files=terraformSketch(p),tf=JSON.parse(files['main.tf.json']),n=resourcePlan(p).rows.find(r=>r.id==='workspace').address;
  assert.deepEqual(tf.locals.unfinished_work,[]);
  const app=tf.resource.google_cloud_run_v2_service[n];assert.equal(app.iap_enabled,true);assert.equal(app.invoker_iam_disabled,false);
  assert.equal(tf.resource.google_cloud_run_v2_service_iam_member[n].role,'roles/run.invoker');
  assert.equal(tf.resource.google_cloud_run_v2_service_iam_member[n].member,'${google_project_service_identity.required_iap.member}');
  assert.match(tf.resource.google_iap_web_cloud_run_service_iam_member[n].member,/^group:/);
  assert.equal(tf.resource.google_artifact_registry_repository_iam_member.image_pull.member,'${google_project_service_identity.required_run.member}');
  const permissions=tf.resource.google_project_iam_custom_role[n].permissions;
  assert.deepEqual(permissions,['aiplatform.endpoints.predict','aiplatform.cacheConfigs.get','aiplatform.endpoints.fetchPublisherModelConfig']);
  for(const api of Object.values(tf.resource.google_project_service))assert.equal(api.disable_on_destroy,false);
  assert.equal(tf.resource.google_project_service_identity.required_iap.provider,'google-beta');
  const root='applications/'+n+'/';assert.match(files[root+'gcp_structured.py'],/class IapVerifier/);assert.match(files[root+'Dockerfile'],/--require-hashes/);assert.match(files[root+'Dockerfile'],/USER 10001:10001/);
  assert.ok(files[root+'structured_http.py']);assert.ok(files[root+'gcp_acceptance.py']);assert.match(files[root+'web/index.html'],/Clear input and result/);
  assert.ok(!files[root+'web/app.js'].includes('localStorage'));
  assert.ok(!JSON.stringify(tf).includes('allUsers'));assert.ok(!JSON.stringify(tf).includes('service_account_key'));
 }
});

test('unimplemented persistence and unknown flows remain blocked, existing services are preserved',()=>{
 const p=gcpStructuredProject();p.nodes.push({id:'ledger',position:{x:0,y:0},data:{label:'Durable credits',kind:'resource',provider:'gcp',service:'Cloud SQL'}});p.edges.push({id:'durable',source:'workspace',target:'ledger'});
 const tf=JSON.parse(terraformSketch(p)['main.tf.json']);assert.ok(tf.locals.unfinished_work.some(g=>g.startsWith('resource-')));assert.ok(tf.locals.unfinished_work.some(g=>g.startsWith('connection-')));
 const existing=gcpStructuredProject();existing.nodes[1].data.origin='existing';existing.nodes[1].data.binding='existing-service';existing.nodes[1].data.deploymentMode='reference';
 assert.ok(!JSON.parse(terraformSketch(existing)['main.tf.json']).resource?.google_cloud_run_v2_service);
 const missing=gcpStructuredProject();delete missing.nodes[1].data.config.outputContract;assert.ok(resourcePlan(missing).gapDetails.some(g=>g.componentIds?.includes('workspace')));
});

test('Google model instructions stay data and input limits are never silently reduced',()=>{
 const p=gcpStructuredProject();p.nodes[1].data.config.maxInputBytes=100000;assert.throws(()=>terraformSketch(p),/limits/);
 p.nodes[1].data.config.maxInputBytes=20000;p.nodes[1].data.config.outputContract.instruction='${file("/private/secret")}';
 const tf=JSON.parse(terraformSketch(p)['main.tf.json']);const env=Object.values(tf.resource.google_cloud_run_v2_service)[0].template.containers.env;
 const contract=JSON.parse(Buffer.from(env.find(e=>e.name==='OUTPUT_CONTRACT_BASE64').value,'base64').toString());
 assert.equal(contract.instruction,'${file("/private/secret")}');assert.ok(!JSON.stringify(tf).includes('/private/secret'));
});

test('policy examples and production do not silently approve the destination',()=>{
 const files=terraformSketch(gcpStructuredProject(),'production'),tf=JSON.parse(files['main.tf.json']),example=JSON.parse(files['deployment.tfvars.json.example']);
 assert.equal(tf.variable.review_approved.default,false);assert.equal(example.review_approved,false);
 assert.ok(tf.locals.unfinished_work.includes('production-state-backup-and-operating-review-required'));
 assert.ok(Object.entries(example).filter(([k])=>k.endsWith('_policy_review')).every(([,v])=>v.abuseLogging==='REVIEW_REQUIRED'));
 assert.match(files['README.md'],/operator-attested/);assert.match(files['README.md'],/not a continuous directory check/);
});

test('the readable Spec Kit names the same concrete setup artifacts as its task JSON',()=>{
 const files=deliveryPack(gcpStructuredProject(),null),tasks=JSON.parse(files['spec-kit/tasks.json']).tasks;
 const setup=tasks.find(task=>task.steps.some(step=>step.includes('gcp_acceptance.py')));
 assert.ok(setup.files.some(file=>file.endsWith('/Dockerfile')));assert.ok(setup.files.some(file=>file.endsWith('/test-requirements.lock')));
 const section=files['spec-kit/tasks.md'].split('## '+setup.id+' — ')[1].split('\n## ')[0];
 for(const file of setup.files)assert.ok(section.includes(file),file);
 assert.ok(!section.includes('No implementation files generated yet'));
 assert.match(files['spec-kit/questions.md'],/Engineering verification/);
});
