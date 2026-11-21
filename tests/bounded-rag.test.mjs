import test from 'node:test';
import assert from 'node:assert/strict';
import {ragProject} from './fixtures/rag-project.mjs';
import {terraformSketch} from '../src/terraform.mjs';
import {validateImport} from '../src/core.mjs';
import {toAgentProject} from '../src/local-agent.mjs';
test('typed bounded RAG exports authenticated API, scoped roles, catalog and runtime sources',()=>{
 for(const p of [ragProject(),validateImport(ragProject()),toAgentProject(ragProject())]){
  const files=terraformSketch(p,'production'),tf=JSON.parse(files['main.tf.json']);assert.deepEqual(tf.locals.unfinished_work,[]);
  assert.equal(Object.values(tf.resource.aws_apigatewayv2_route)[0].authorization_type,'AWS_IAM');
  const permissions=Object.values(tf.resource.aws_lambda_permission);assert.equal(permissions.length,1);assert.equal(permissions[0].principal,'apigateway.amazonaws.com');assert.ok(permissions[0].source_arn.endsWith('/live/POST/ask'));
  const policies=Object.values(tf.resource.aws_iam_role_policy).map(p=>JSON.parse(p.policy));
  assert.ok(policies.some(p=>p.Statement.some(s=>s.Action.includes('execute-api:Invoke'))));
  assert.ok(policies.every(p=>p.Statement.every(s=>!s.Action.includes('dynamodb:PutItem')&&!s.Action.includes('lambda:InvokeFunction'))));
  assert.ok(files['manage-catalog.py']);assert.ok(files['CATALOG.md']);assert.ok(Object.keys(files).some(n=>n.endsWith('/bounded_rag.py')));
 }
});
test('missing trusted gateway integration never produces a complete RAG deployment',()=>{
 const p=ragProject();p.edges=p.edges.filter(e=>e.integration!=='http-api-lambda');const tf=JSON.parse(terraformSketch(p)['main.tf.json']);assert.ok(tf.locals.unfinished_work.length);assert.equal(tf.resource.aws_lambda_function,undefined);
});
