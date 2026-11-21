import test from 'node:test';
import assert from 'node:assert/strict';
import {asyncProject} from './fixtures/async-project.mjs';
import {terraformSketch} from '../src/terraform.mjs';
import {resourcePlan} from '../src/resources.mjs';
import {validateImport} from '../src/core.mjs';
import {toAgentProject} from '../src/local-agent.mjs';
test('complete typed async topology survives serialization and generates scoped processing',()=>{
 for(const p of [asyncProject(),validateImport(asyncProject()),toAgentProject(asyncProject())]){
  const plan=resourcePlan(p);assert.deepEqual(plan.gaps,[]);assert.equal(plan.asyncPlan.pipelines.length,1);
  const files=terraformSketch(p,'production'),tf=JSON.parse(files['main.tf.json']);assert.deepEqual(tf.locals.unfinished_work,[]);
  for(const type of ['aws_sqs_queue','aws_lambda_event_source_mapping','aws_s3_bucket_notification','aws_dynamodb_table','aws_cloudwatch_metric_alarm'])assert.ok(tf.resource[type],type);
  assert.equal(Object.keys(tf.resource.aws_sqs_queue).length,2);
  const policy=JSON.parse(Object.values(tf.resource.aws_iam_role_policy)[0].policy);
  assert.ok(policy.Statement.some(s=>s.Action.includes('s3:GetObjectVersion')));
  assert.ok(policy.Statement.every(s=>s.Resource!=='*'));
  const mapping=Object.values(tf.resource.aws_lambda_event_source_mapping)[0];assert.deepEqual(mapping.function_response_types,['ReportBatchItemFailures']);
  assert.equal(Object.values(tf.resource.aws_dynamodb_table)[0].deletion_protection_enabled,true);
  assert.ok(files['runtime-requirements.lock'].includes('--hash=sha256:'));
 }
});
test('missing or conflicting async contracts never silently produce a complete pipeline',()=>{
 for(const index of [1,2,3,4,5]){
  const p=asyncProject();p.edges.splice(index,1);const plan=resourcePlan(p);assert.equal(plan.asyncPlan.pipelines.length,0);assert.ok(plan.gaps.length);
 }
 const p=asyncProject();p.edges.push({...p.edges[2],id:'second-trigger'});assert.equal(resourcePlan(p).asyncPlan.pipelines.length,0);
 const labelOnly=asyncProject();delete labelOnly.nodes.find(n=>n.id==='worker').data.implementation;assert.equal(resourcePlan(labelOnly).asyncPlan.pipelines.length,0);
});
