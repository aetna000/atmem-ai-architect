import test from 'node:test';
import assert from 'node:assert/strict';
import {azureStructuredProject} from './fixtures/azure-structured-project.mjs';
import {terraformSketch} from '../src/terraform.mjs';
import {resourcePlan} from '../src/resources.mjs';
import {validateImport} from '../src/core.mjs';
import {toAgentProject} from '../src/local-agent.mjs';
import {implementationMap} from '../src/implementation-map.mjs';

test('Azure composition preserves contract, emits real source, immutable packaging and scoped identities',()=>{
 for(const p of [azureStructuredProject(),validateImport(azureStructuredProject()),toAgentProject(azureStructuredProject())]){
  assert.equal(p.nodes[1].data.implementation,'azure-structured-app');
  const files=terraformSketch(p),tf=JSON.parse(files['main.tf.json']),plan=resourcePlan(p),n=plan.rows.find(r=>r.id==='workspace').address;
  assert.deepEqual(tf.locals.unfinished_work,[]);
  const root='applications/'+n+'/';
  assert.match(files[root+'azure_structured.py'],/class EntraVerifier/);
  assert.match(files[root+'Dockerfile'],/python:3\.13-slim-bookworm@sha256:[0-9a-f]{64}/);
  assert.match(files[root+'Dockerfile'],/--require-hashes/);assert.match(files[root+'Dockerfile'],/USER 10001:10001/);
  assert.ok(files[root+'azure_acceptance.py']);assert.ok(files[root+'web/app.js']);
  assert.equal(tf.resource.azurerm_cognitive_deployment[n].sku.name,'Standard');
  assert.equal(tf.resource.azurerm_cognitive_account[n].local_auth_enabled,false);
  assert.equal(tf.resource.azuread_application_registration[n].requested_access_token_version,2);
  assert.equal(tf.resource.azuread_service_principal[n].app_role_assignment_required,true);
  assert.equal(tf.resource.azurerm_role_assignment[n].scope,'${azurerm_cognitive_account.'+n+'.id}');
  assert.equal(tf.resource.azurerm_role_assignment[n+'_policy'].scope,tf.resource.azurerm_role_assignment[n].scope);
  assert.match(tf.resource.azurerm_role_assignment[n+'_pull'].scope,/Microsoft\.ContainerRegistry\/registries/);
  assert.equal(tf.provider.azuread.tenant_id,tf.provider.azurerm.tenant_id);
  assert.equal(tf.provider.azurerm.resource_provider_registrations,'none');
  assert.equal(implementationMap(p,plan,files).components.find(c=>c.id==='workspace').applicationImplementation,'generated_application_unverified');
 }
});

test('missing schema, extra data services, untyped wires and existing ownership never receive fake coverage',()=>{
 const missing=azureStructuredProject();delete missing.nodes[1].data.config.outputContract;
 assert.ok(resourcePlan(missing).gapDetails.some(g=>g.componentIds?.includes('workspace')));
 const extra=azureStructuredProject();extra.nodes.push({id:'database',position:{x:0,y:0},data:{label:'Durable credit ledger',kind:'resource',provider:'azure',service:'Azure Database for PostgreSQL'}});extra.edges.push({id:'store',source:'workspace',target:'database'});
 const tf=JSON.parse(terraformSketch(extra)['main.tf.json']);assert.ok(tf.locals.unfinished_work.some(g=>g.startsWith('resource-')));assert.ok(tf.locals.unfinished_work.some(g=>g.startsWith('connection-')));
 const existing=azureStructuredProject();existing.nodes[1].data.origin='existing';existing.nodes[1].data.binding='existing-service';existing.nodes[1].data.deploymentMode='reference';
 const config=JSON.parse(terraformSketch(existing)['main.tf.json']);assert.equal(Object.keys(config.resource||{}).some(k=>k==='azurerm_linux_web_app'),false);
 const untyped=azureStructuredProject();delete untyped.edges[0].integration;assert.ok(resourcePlan(untyped).gapDetails.some(g=>g.edgeIds?.includes('browser-app')));
});

test('compiler never changes requested input bounds or interprets model text as Terraform code',()=>{
 const p=azureStructuredProject();p.nodes[1].data.config.maxInputBytes=20001;assert.throws(()=>terraformSketch(p),/limits/);
 p.nodes[1].data.config.maxInputBytes=20000;p.nodes[1].data.config.outputContract.instruction='${file("/private/secret")}';p.nodes[1].data.config.outputContract.fields[0].description='%{if true} ${path.root}';
 const tf=JSON.parse(terraformSketch(p)['main.tf.json']);const app=Object.values(tf.resource.azurerm_linux_web_app)[0];
 const contract=JSON.parse(Buffer.from(app.app_settings.OUTPUT_CONTRACT_BASE64,'base64').toString());
 assert.equal(contract.instruction,'${file("/private/secret")}');assert.ok(!JSON.stringify(tf).includes('/private/secret'));
});

test('production retains the unresolved operating gate and immutable source examples do not autoapprove',()=>{
 const files=terraformSketch(azureStructuredProject(),'production'),tf=JSON.parse(files['main.tf.json']);
 assert.ok(tf.locals.unfinished_work.includes('production-state-backup-and-operating-review-required'));
 assert.equal(tf.variable.review_approved.default,false);assert.equal(JSON.parse(files['deployment.tfvars.json.example']).review_approved,false);
 assert.match(files['README.md'],/until expiry/);assert.match(files['README.md'],/not a high-availability SLA/);
});
