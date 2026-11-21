import {STRUCTURED_OPERATION_POLICY as policy} from '../src/structured-operation-policy.mjs';
import {deliveryPack} from '../src/delivery.mjs';
import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {spawnSync} from 'node:child_process';
import {structuredWebProject} from './fixtures/structured-web-project.mjs';import {terraformSketch} from '../src/terraform.mjs';import {resourcePlan} from '../src/resources.mjs';import {validateImport} from '../src/core.mjs';import {toAgentProject} from '../src/local-agent.mjs';
test('complete web composition emits application, private assets, JWT scope and authoritative revocation checks without a catalog',()=>{
 for(const p of [structuredWebProject(),validateImport(structuredWebProject()),toAgentProject(structuredWebProject())]){
  const f=terraformSketch(p),tf=JSON.parse(f['main.tf.json']),q=JSON.parse(f['generation-quality.json']);assert.deepEqual(q.findings,[]);assert.deepEqual(tf.locals.unfinished_work,[]);assert.equal(tf.resource.aws_dynamodb_table,undefined);
  assert.equal(Object.values(tf.resource.aws_apigatewayv2_route)[0].authorization_type,'JWT');
  assert.deepEqual(Object.values(tf.resource.aws_apigatewayv2_route)[0].authorization_scopes,['atmem/ask']);
  assert.equal(Object.values(tf.resource.aws_cognito_user_pool)[0].mfa_configuration,'ON');
  assert.equal(Object.values(tf.resource.aws_lambda_permission).length,1);
  assert.match(Object.entries(f).find(([k])=>k.startsWith('handlers/'))[1],/admin_get_user/);
  const app=Object.entries(f).find(([k])=>k.endsWith('/app.js'))[1];assert.ok(!app.includes('result.citations'));assert.ok(app.includes('requiresHumanReview'));assert.ok(!app.includes('localStorage'));
 }
});
test('missing identity route, implementation or worker schema never passes as a complete web app',()=>{
 for(const edge of ['identity-api','web-identity','api-worker','worker-model']){const p=structuredWebProject();p.edges=p.edges.filter(e=>e.id!==edge);assert.ok(resourcePlan(p).gaps.length);assert.equal(JSON.parse(terraformSketch(p)['generation-quality.json']).infrastructureComplete,false);}
});
test('emitted HTTP handler denies spoofed context, stale users and identity outages, and withholds results on mid-request revocation',()=>{
 const f=terraformSketch(structuredWebProject()),source=Object.entries(f).find(([k])=>k.startsWith('handlers/'))[1],dir=fs.mkdtempSync(path.join(os.tmpdir(),'architect-http-'));
 try{
  fs.writeFileSync(path.join(dir,'generated.py'),source);
  const script=`import generated as m,json,os,copy
from unittest.mock import MagicMock
os.environ.update(EXPECTED_API_ID="api",COGNITO_ISSUER="issuer",COGNITO_CLIENT_ID="client",COGNITO_USER_POOL_ID="pool",MAX_INPUT_BYTES="20000",MODEL_ARN="synthetic",MAX_OUTPUT_TOKENS="512")
user={"Enabled":True,"UserStatus":"CONFIRMED","UserAttributes":[{"Name":"sub","Value":"subject"}]}
event={"version":"2.0","requestContext":{"apiId":"api","routeKey":"POST /api/ask","authorizer":{"jwt":{"claims":{"iss":"issuer","client_id":"client","token_use":"access","scope":"atmem/ask","sub":"subject","username":"user"}}}},"isBase64Encoded":False,"body":json.dumps({"text":"synthetic input"})}
def reset():
 m._identity=MagicMock();m._client=MagicMock();m._retention=MagicMock();m._retention.get_account_data_retention.return_value={"mode":"none"};m._retention.get_model_invocation_logging_configuration.return_value={};m._identity.admin_get_user.return_value=copy.deepcopy(user)
 m._client.converse.return_value={"output":{"message":{"content":[{"text":json.dumps({"topic":"technical","uncertain":True})}]}},"stopReason":"end_turn"}
reset();assert m.handler(event,None)["statusCode"]==200
assert m._identity.admin_get_user.call_count==2
for key,value in [("iss","wrong"),("client_id","wrong"),("scope","openid"),("token_use","id"),("sub","")]:
 reset();bad=copy.deepcopy(event);bad["requestContext"]["authorizer"]["jwt"]["claims"][key]=value
 assert m.handler(bad,None)["statusCode"]==403;m._client.converse.assert_not_called()
for key,value in [("Enabled",False),("UserStatus","FORCE_CHANGE_PASSWORD"),("UserAttributes",[{"Name":"sub","Value":"another-user"}])]:
 reset();m._identity.admin_get_user.return_value[key]=value
 assert m.handler(event,None)["statusCode"]==403;m._client.converse.assert_not_called()
reset();m._identity.admin_get_user.side_effect=RuntimeError("PRIVATE DETAIL")
assert m.handler(event,None)["statusCode"]==503;m._client.converse.assert_not_called()
reset();m._identity.admin_get_user.side_effect=[user,{**user,"Enabled":False}]
assert m.handler(event,None)["statusCode"]==403;m._client.converse.assert_called_once()
for body in ['{"text":"a","text":"b"}',json.dumps({"text":"x","user":"admin"}),json.dumps({"text":"x"*20001})]:
 reset();bad={**event,"body":body};assert m.handler(bad,None)["statusCode"]==400;m._client.converse.assert_not_called()
reset();assert m.handler({"text":"direct invocation"},None)["statusCode"]==403
m._client.converse.assert_not_called()
print("Emitted HTTP handler authorization and revocation behavior passed with mocked identity/model services")
`;
  fs.writeFileSync(path.join(dir,'check.py'),script);const r=spawnSync(path.resolve('.venv/bin/python'),['check.py'],{cwd:dir,encoding:'utf8'});assert.equal(r.status,0,r.stdout+r.stderr);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

test('handoff uses implemented runtime choices and typed interface contracts instead of generic storage instructions',()=>{
 const p=structuredWebProject(),files=deliveryPack(p),tasks=JSON.parse(files['spec-kit/tasks.json']).tasks;
 const setup=tasks.find(t=>t.id==='TASK-SETUP');assert.match(setup.steps.join(' '),/python3 build-runtime.py/);assert.ok(setup.files.includes('terraform/.terraform.lock.hcl'));
 const apiTask=tasks.find(t=>t.id.startsWith('TASK-INTEGRATION-')&&t.edgeIds.includes('web-api'));assert.ok(!apiTask.steps.join(' ').includes('bucket-scoped'));assert.ok(apiTask.files.includes('spec-kit/interfaces.json'));
 const interfaces=JSON.parse(files['spec-kit/interfaces.json']).interfaces;assert.equal(interfaces.find(i=>i.id==='web-api').request.text.maxUtf8Bytes,20000);assert.match(interfaces.find(i=>i.id==='worker-model').quality,/do not prove/);
 delete p.nodes[4].data.config.outputContract;assert.doesNotThrow(()=>deliveryPack(p));
});

test('untrusted application names and field descriptions cannot become Terraform template expressions',()=>{
 const p=structuredWebProject();p.nodes[1].data.label='Review ${file("/private-secret")} %{ if true }';p.nodes[4].data.config.outputContract.fields[0].description='Meaning ${file("/private-secret")} %{ if true }';
 const files=terraformSketch(p),main=files['main.tf.json'];assert.ok(!main.includes('${file('));assert.ok(!main.includes('%{ if true }'));
 const config=JSON.parse(Object.entries(files).find(([k])=>k.endsWith('/config.json'))[1]);const fields=JSON.parse(Buffer.from(config.fieldsBase64,'base64').toString('utf8'));assert.equal(fields[0].description,p.nodes[4].data.config.outputContract.fields[0].description);
 assert.match(Object.entries(files).find(([k])=>k.endsWith('/index.html'))[1],/&#36;/);
});

test('the complete structured HTTP call chain has bounded SDK attempts beneath the proxy deadline',()=>{
 const budget=policy.modelConnectSeconds+policy.modelReadSeconds+2*(policy.identityConnectSeconds+policy.identityReadSeconds)+2*(policy.policyConnectSeconds+policy.policyReadSeconds);
 assert.equal(policy.sdkAttempts,1);assert.ok(budget*1000<policy.browserDeadlineMs);assert.ok(policy.browserDeadlineMs<policy.gatewayDeadlineMs);
});
