import test from 'node:test';
import assert from 'node:assert/strict';
import {summaryProject} from './fixtures/summary-project.mjs';
import {terraformSketch} from '../src/terraform.mjs';
import {validateImport} from '../src/core.mjs';
import {toAgentProject} from '../src/local-agent.mjs';
test('summary contract generates bounded runtime and exact regional model permissions',()=>{
 for(const p of [summaryProject(),validateImport(summaryProject()),toAgentProject(summaryProject())]){
  const tf=JSON.parse(terraformSketch(p)['main.tf.json']);assert.deepEqual(tf.locals.unfinished_work,[]);
  const policy=JSON.parse(Object.values(tf.resource.aws_iam_role_policy)[0].policy);
  const grant=policy.Statement.find(s=>s.Action.includes('bedrock:InvokeModel'));assert.ok(grant);assert.ok(!grant.Resource.includes('*'));
  const model=Object.entries(tf.variable).find(([k])=>k.endsWith('_model_id'));assert.ok(model);assert.equal(model[1].default,undefined);
  assert.equal(Object.keys(tf.resource.aws_lambda_permission).length,1);
  assert.equal(Object.values(tf.resource.aws_lambda_function)[0].reserved_concurrent_executions.includes('_concurrency'),true);
 }
});
test('missing model contract and unsupported profile topology remain blocked',()=>{
 const p=summaryProject();delete p.nodes[2].data.binding;const tf=JSON.parse(terraformSketch(p)['main.tf.json']);assert.ok(tf.locals.unfinished_work.length);assert.equal(tf.resource.aws_lambda_function,undefined);
});
test('explicit model and output-token choices survive round trips and affect generated inputs',()=>{
 const p=summaryProject();p.nodes[1].data.config={maxOutputTokens:256};p.nodes[2].data.config={modelId:'amazon.nova-micro-v1:0'};
 for(const copy of [p,validateImport(p),toAgentProject(p)]){
  const variables=JSON.parse(terraformSketch(copy)['main.tf.json']).variable;
  assert.equal(Object.entries(variables).find(([k])=>k.endsWith('_model_id'))[1].default,'amazon.nova-micro-v1:0');
  assert.equal(Object.entries(variables).find(([k])=>k.endsWith('_max_output_tokens'))[1].default,256);
 }
 p.nodes[2].data.config.modelId='arn:aws:bedrock:*';assert.throws(()=>terraformSketch(p),/foundation-model/);
});
