import test from 'node:test';
import assert from 'node:assert/strict';
import {webProject} from './fixtures/web-project.mjs';
import {terraformSketch} from '../src/terraform.mjs';
import {validateImport} from '../src/core.mjs';
import {toAgentProject} from '../src/local-agent.mjs';
test('web application exports private assets, PKCE, MFA and scoped JWT route',()=>{
 for(const p of [webProject(),validateImport(webProject()),toAgentProject(webProject())]){
  const files=terraformSketch(p,'production'),tf=JSON.parse(files['main.tf.json']);assert.deepEqual(tf.locals.unfinished_work,[]);
  const pool=Object.values(tf.resource.aws_cognito_user_pool)[0];assert.equal(pool.mfa_configuration,'ON');assert.equal(pool.admin_create_user_config.allow_admin_create_user_only,true);
  const client=Object.values(tf.resource.aws_cognito_user_pool_client)[0];assert.equal(client.generate_secret,false);assert.deepEqual(client.allowed_oauth_flows,['code']);assert.equal(client.access_token_validity,15);
  const route=Object.values(tf.resource.aws_apigatewayv2_route).find(r=>r.route_key==='POST /api/ask');assert.equal(route.authorization_type,'JWT');assert.deepEqual(route.authorization_scopes,['atmem/ask']);
  assert.equal(Object.values(tf.resource.aws_cloudfront_origin_access_control)[0].signing_behavior,'always');assert.ok(files['manage-web-users.py']);assert.ok(files['WEB.md']);
  assert.ok(Object.entries(files).some(([name,content])=>name.endsWith('/app.js')&&content.includes("code_challenge_method:'S256'")));
 }
});
test('browser-only users do not require an invented IAM caller or silently skip mock tests',()=>{
 const p=webProject();p.nodes=p.nodes.filter(n=>n.id!=='alice');p.edges=p.edges.filter(e=>e.id!=='caller');const files=terraformSketch(p);
 assert.deepEqual(JSON.parse(files['main.tf.json']).locals.unfinished_work,[]);assert.ok(files['tests/storage-access.tftest.hcl']);assert.ok(!files['tests/storage-access.tftest.hcl'].includes('undefined'));
});
test('typed existing browser actors are references, and deferred notes are retained outside deployment scope',()=>{
 const p=webProject();p.nodes.push({id:'human',position:{x:0,y:0},data:{kind:'resource',label:'Browser user',provider:'tools',origin:'existing',binding:'web-browser'}},{id:'teams-later',position:{x:0,y:200},data:{kind:'note',label:'Teams: later phase',provider:'tools'}});p.edges.push({id:'browse',source:'human',target:'web',integration:'browser-https'});
 const tf=JSON.parse(terraformSketch(p)['main.tf.json']);assert.deepEqual(tf.locals.unfinished_work,[]);
 assert.equal(p.nodes.find(n=>n.id==='teams-later').data.kind,'note');
});
