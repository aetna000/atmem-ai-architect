import test from 'node:test';
import assert from 'node:assert/strict';
import {AWS_SCENARIOS} from '../src/aws-validation-scenarios.mjs';
import {assessAwsArchitecture} from '../src/aws-validation.mjs';
const node=(id,label,origin='proposed',provider='aws')=>({id,data:{label,origin,provider,kind:'resource'}});
test('seven synthetic scenarios have distinct IDs and observable acceptance checks',()=>{
 assert.equal(AWS_SCENARIOS.length,7);assert.equal(new Set(AWS_SCENARIOS.map(s=>s.id)).size,7);
 for(const s of AWS_SCENARIOS){assert.ok(s.prompt.length>50);assert.ok(s.expected.length);assert.ok(s.checks.length>=4);}
});
test('an overbuilt storage design fails the intended scenario',()=>{
 const actor=node('actor','Operator','existing','tools');actor.data.binding='aws-iam-principal';
 const p={nodes:[node('store','Amazon S3'),actor],edges:[{source:'actor',target:'store',access:'s3-read-write'}]};assert.equal(assessAwsArchitecture(p,AWS_SCENARIOS[0]).passed,true);
 p.nodes.push(node('model','Amazon Bedrock'));assert.equal(assessAwsArchitecture(p,AWS_SCENARIOS[0]).passed,false);
});
test('async architecture must actually connect queue to worker',()=>{
 const p={nodes:[node('s','Amazon S3'),node('q','Amazon SQS'),node('l','AWS Lambda')],edges:[]};
 assert.equal(assessAwsArchitecture(p,AWS_SCENARIOS[2]).passed,false);
 p.edges=[{source:'s',target:'q'},{source:'q',target:'l'}];assert.equal(assessAwsArchitecture(p,AWS_SCENARIOS[2]).passed,true);
});
test('enterprise source systems must be existing and connected',()=>{
 const p={nodes:[node('s','SharePoint','existing','tools'),node('c','Confluence','existing','tools'),node('k','Bedrock Knowledge Bases')],edges:[{source:'s',target:'k'},{source:'c',target:'k'}]};
 assert.equal(assessAwsArchitecture(p,AWS_SCENARIOS[6]).passed,false); // The requested web channel is required.
 const web=node('web','Amazon CloudFront');web.data.implementation='rag-web-app';p.nodes.push(web);p.edges.push({source:'web',target:'k'});
 assert.equal(assessAwsArchitecture(p,AWS_SCENARIOS[6]).passed,true);
 p.nodes[0].data.origin='proposed';assert.equal(assessAwsArchitecture(p,AWS_SCENARIOS[6]).passed,false);
});

import {terraformSketch} from '../src/terraform.mjs';
test('S3 generation enforces the ownership and transport controls stated in a private storage architecture',()=>{
 const p={version:1,revision:1,nodes:[node('s','Amazon S3')],edges:[]};
 const tf=JSON.parse(terraformSketch(p)['main.tf.json']);
 assert.equal(tf.resource.aws_s3_bucket_ownership_controls.block_73.rule.object_ownership,'BucketOwnerEnforced');
 const policy=JSON.parse(tf.resource.aws_s3_bucket_policy.block_73.policy),statement=policy.Statement[0];
 assert.equal(statement.Effect,'Deny');assert.equal(statement.Condition.Bool['aws:SecureTransport'],'false');assert.equal(statement.Condition.Bool['aws:PrincipalIsAWSService'],'false');
 assert.equal(tf.output.buckets.value.block_73.name,'${aws_s3_bucket.block_73.id}');
});
test('a human actor is not mistaken for a proposed non-AWS workload',()=>{
 const operator=node('actor','Test operator','proposed','tools');operator.data.role='human';
 const p={nodes:[node('s','Amazon S3'),operator],edges:[{source:'actor',target:'s'}]};
 assert.equal(assessAwsArchitecture(p,AWS_SCENARIOS[0]).checks.find(c=>c.id==='aws-proposed-components').passed,true);
});

import {assessAwsDeploymentCandidate,awsRefinementPrompt} from '../src/aws-validation.mjs';
test('explicit unsupported service cannot pass through a misleading S3 label',()=>{
 const n=node('s','S3 bucket');n.data.service='Amazon DynamoDB';
 assert.equal(assessAwsArchitecture({nodes:[n],edges:[]},AWS_SCENARIOS[0]).passed,false);
});
test('two disconnected pairs and dangling edges fail graph checks',()=>{
 const p={nodes:[node('s','S3'),node('q','SQS'),node('l','Lambda'),node('o','S3')],edges:[{source:'s',target:'q'},{source:'l',target:'o'}]};
 assert.equal(assessAwsArchitecture(p,AWS_SCENARIOS[2]).checks.find(c=>c.id==='connected-graph').passed,false);
 p.edges.push({source:'q',target:'missing'});
 assert.equal(assessAwsArchitecture(p,AWS_SCENARIOS[2]).checks.find(c=>c.id==='valid-edge-endpoints').passed,false);
});
test('schema-valid empty Terraform cannot qualify a compute deployment',()=>{
 const p={nodes:[node('l','Lambda')],edges:[]};
 const a=assessAwsDeploymentCandidate(p,AWS_SCENARIOS[1],{resource:{terraform_data:{gate:{}}},locals:{unfinished_work:[]}},{providerSchema:'passed',requirementsReview:'passed'});
 assert.equal(a.status,'blocked');assert.ok(a.blockers.some(b=>b.id==='missing-lambda'));assert.ok(a.blockers.some(b=>b.id==='no-cloud-resources'));assert.ok(a.blockers.some(b=>b.id==='application-not-qualified'));
});
test('S3 schema pass retains unresolved integration and requirements blockers',()=>{
 const p={nodes:[node('s','S3')],edges:[]};
 const a=assessAwsDeploymentCandidate(p,AWS_SCENARIOS[0],{resource:{aws_s3_bucket:{s:{}}},locals:{unfinished_work:['identity']}},{providerSchema:'passed'});
 assert.equal(a.status,'blocked');assert.ok(a.blockers.some(b=>b.id==='unfinished-identity'));assert.ok(a.blockers.some(b=>b.id==='requirements-review-unverified'));
 assert.match(awsRefinementPrompt(a),/Do not remove required components/);
});

import {detectWorkflow} from '../src/discovery.mjs';
import {resolveService} from '../src/resources.mjs';
test('storage, counts and summaries do not select RAG just because they mention documents',()=>{
 for(const scenario of AWS_SCENARIOS.slice(0,4))assert.notEqual(detectWorkflow(scenario.prompt)?.id,'knowledge-assistant',scenario.id);
 assert.equal(detectWorkflow(AWS_SCENARIOS[4].prompt)?.id,'knowledge-assistant');
 assert.equal(detectWorkflow('A chatbot over SharePoint policy documents')?.id,'knowledge-assistant');
});
test('combined physical AWS services remain ambiguous rather than silently losing one service',()=>{
 assert.equal(resolveService({provider:'aws',service:'AWS CloudTrail + Amazon CloudWatch Logs'}).ambiguous,true);
 assert.equal(resolveService({provider:'aws',service:'Amazon Bedrock model with Bedrock Guardrails'}).ambiguous,true);
 assert.equal(resolveService({provider:'aws',service:'Amazon Bedrock Guardrails'}).name,'Amazon Bedrock Guardrails');
});
