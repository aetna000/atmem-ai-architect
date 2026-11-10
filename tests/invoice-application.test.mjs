import test from'node:test';
import assert from'node:assert/strict';
import {invoiceApplicationFiles}from'../src/invoice-application.mjs';
import {invoiceDependencies}from'../src/invoice-dependencies.mjs';
import {pythonContainer}from'../src/python-container.mjs';
import {createHash}from'node:crypto';
import {awsInvoiceTerraform}from'../src/invoice-aws.mjs';

test('every emitted invoice application contains its local runtime import closure and private parser source',()=>{
 for(const provider of ['aws','azure','gcp','ibm']){
  const root='applications/block_696e766f696365/',files=invoiceApplicationFiles(provider,'block_696e766f696365');
  assert.equal(JSON.parse(files[root+'invoice-deployment.json']).provider,provider);
  for(const[name,source]of Object.entries(files))if(name.startsWith(root)&&name.endsWith('.py')){
   const folder=name.slice(0,name.lastIndexOf('/')+1);
   for(const match of source.matchAll(/^from ([a-z_][a-z_0-9]*) import /gm))if(/^(?:invoice_|workflow_|durable_workflow$|approved_http_destination$|structured_|policy_review$|aws_json_model$|azure_structured$|gcp_structured$|ibm_structured$)/.test(match[1]))assert.ok(files[folder+match[1]+'.py'],'Missing '+match[1]+' imported by '+name);
  }
  assert.ok(files[root+'workflow_schema.sql']);assert.ok(files[root+'invoice_runtime_secrets.py']);assert.match(files[root+'Dockerfile'],/"--limit-concurrency", "32"/);assert.doesNotMatch(files[root+'Dockerfile'],/COPY web\//);
  assert.ok(files[root+'parser/invoice_parser_service.py']);assert.match(files[root+'parser/Dockerfile'],/USER 10001:10001/);
 }
});
test('invoice dependency unions retain strict pins, hashes and explicit IBM compatibility decision',()=>{
 for(const provider of ['aws','azure','gcp','ibm']){
  const lock=invoiceDependencies(provider),testing=invoiceDependencies(provider,{tests:true});assert.match(lock.requirements,/psycopg==3\.3\.8/);assert.match(lock.requirements,/procrastinate==3\.10\.0/);assert.match(testing.requirements,/httpx==0\.28\.1/);
  assert.ok(lock.sources.every(source=>source.metadataSha256));assert.equal(lock.resolutions.length,provider==='ibm'?1:0);
  if(provider==='ibm'){assert.match(lock.requirements,/python-dateutil==3\.0\.0/);assert.doesNotMatch(lock.requirements,/boto3==/);}else assert.match(lock.requirements,/python-dateutil==2\.9\.0\.post0/);
 }
 assert.doesNotMatch(invoiceDependencies('aws').requirements,/mangum==/);
});
test('invoice emission rejects foreign provider/address rather than falling back',()=>{
 for(const provider of ['tools','other',''])assert.throws(()=>invoiceApplicationFiles(provider,'block_696e766f696365'));
 for(const address of ['../private','block_hello','${local.other}'])assert.throws(()=>invoiceApplicationFiles('aws',address));
});
test('shared container helper keeps existing defaults and rejects path/capacity overrides',()=>{
 const standard=pythonContainer('public_faq_app',['public_faq_app.py'],['faq-deployment.json']);assert.match(standard,/COPY output-contract.json/);assert.match(standard,/COPY web\//);assert.match(standard,/"--limit-concurrency", "16"/);
 for(const options of [{assets:['../secret.pem']},{assets:['private.key']},{concurrency:0},{concurrency:101},{web:'false'},{unknown:true}])assert.throws(()=>pythonContainer('invoice_native',['invoice_native.py'],[],options));
});
test('AWS invoice export contains the exact trusted database CA and functional operator source',()=>{
 const root='applications/block_696e766f696365/',files=invoiceApplicationFiles('aws','block_696e766f696365'),receipt=JSON.parse(files[root+'rds-ca-source.json']);
 assert.equal(createHash('sha256').update(files[root+'rds-global-ca.pem']).digest('hex'),receipt.sha256);assert.equal((files[root+'rds-global-ca.pem'].match(/BEGIN CERTIFICATE/g)||[]).length,receipt.certificates);
 assert.match(files[root+'Dockerfile'],/COPY .*rds-global-ca.pem/);assert.ok(files[root+'invoice_operator.py']);assert.ok(files[root+'invoice_operations.py']);assert.ok(files[root+'invoice_retention.py']);
 for(const provider of['azure','gcp','ibm'])assert.equal(invoiceApplicationFiles(provider,'block_696e766f696365')[root+'rds-global-ca.pem'],undefined);
});
test('AWS infrastructure keeps parser authority, workload identities, immutable releases and existing DNS separate',()=>{
 const files=awsInvoiceTerraform({id:'11111111-1111-4111-8111-111111111111',revision:1,nodes:[],edges:[]},{id:'invoice',address:'block_696e766f696365',provider:'aws',region:'ap-southeast-2'}),config=JSON.parse(files['main.tf.json']),n='block_696e766f696365';
 assert.equal(config.resource.aws_db_instance[n].publicly_accessible,false);assert.equal(config.resource.aws_db_instance[n].iam_database_authentication_enabled,true);
 assert.equal(config.resource.aws_ecs_task_definition[n+'_parser'].task_role_arn,undefined);assert.notEqual(config.resource.aws_ecs_task_definition[n+'_api'].task_role_arn,config.resource.aws_ecs_task_definition[n+'_worker'].task_role_arn);
 assert.deepEqual(config.resource.aws_ecs_task_definition[n+'_parser'].depends_on,['terraform_data.review_gate','aws_iam_role_policy.'+n+'_parser_execution']);
 const parser=JSON.parse(config.resource.aws_ecs_task_definition[n+'_parser'].container_definitions).find(container=>container.name==='parser');assert.deepEqual(parser.environment,[{name:'PORT',value:'8080'}]);assert.equal(parser.secrets,undefined);
 assert.ok(Object.values(config.resource.aws_vpc_security_group_egress_rule).every(rule=>rule.security_group_id!=='${aws_security_group.'+n+'_parser.id}'));
 assert.equal(config.data.aws_route53_zone.destination.private_zone,false);assert.equal(Object.keys(config.resource.aws_route53_zone).length,1);assert.ok(config.output.operator_deployment);
 assert.match(files['OPERATIONS.md'],/quarantine-restore/);assert.match(files['tests/invoice.tftest.hcl'],/foreign_image_rejected/);assert.match(files['tests/invoice.tftest.hcl'],/mutable_image_rejected/);
 assert.equal(config.variable.applications_enabled.default,false);assert.ok(config.resource.terraform_data.review_gate.lifecycle.precondition.some(rule=>rule.error_message.includes('ECR')));
});
