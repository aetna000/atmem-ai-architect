import test from 'node:test';
import assert from 'node:assert/strict';
import {resourcePlan} from '../src/resources.mjs';
import {terraformSketch} from '../src/terraform.mjs';
import {deliveryPack} from '../src/delivery.mjs';
const node=(id,label,service,provider='aws',origin='proposed')=>({id,type:'resource',position:{x:0,y:0},data:{label,service,kind:'resource',provider,origin,description:label,config:{region:'To be selected'}}});
const project=(nodes=[])=>({id:'quality',version:1,revision:1,name:'Scenario',provider:'aws',requirements:'Answer questions with evidence',nodes,edges:[],needs:[],decisions:[],openQuestions:[],assumptions:[]});

test('explicit service beats a misleading label and mixed labels cannot create S3',()=>{
 for(const n of [node('a','S3 migration processor','AWS Lambda'),node('a','S3 Lambda integration'),node('a','Amazon S3','Unknown custom service')]) {
  const p=project([n]);assert.equal(resourcePlan(p).rows[0].foundation,false);
  assert.equal(JSON.parse(terraformSketch(p)['main.tf.json']).resource.aws_s3_bucket,undefined);
 }
 assert.equal(resourcePlan(project([node('a','S3 migration processor','AWS Lambda')])).rows[0].service,'AWS Lambda');
});
test('OpenSearch deployment mode must be explicit',()=>{
 for(const [name,types] of [['Amazon OpenSearch',[]],['Amazon OpenSearch Serverless',['aws_opensearchserverless_collection']],['Amazon OpenSearch domain',['aws_opensearch_domain']]])assert.deepEqual(resourcePlan(project([node('a',name)])).rows[0].resources,types);
});
test('accepted design ADRs survive while country does not confirm region',()=>{
 const p=project([node('app','Application')]);p.decisions=[{id:'country',subject:'data.country',status:'Accepted',decision:'Australia'},{id:'design',subject:'design.shared-app',status:'Accepted',decision:'One application; region proposed'}];
 const files=deliveryPack(p,null),context=JSON.parse(files['spec-kit/context.json']);
 assert.equal(context.acceptedDecisions.length,2);assert.match(files['spec-kit/questions.md'],/\[cloud.region\]/);assert.doesNotMatch(files['spec-kit/questions.md'],/\[data.country\]/);
 assert.match(files['spec-kit/plan.md'],/One application; region proposed/);
});

import {handoffAssessment} from '../src/handoff.mjs';
import {agentContext} from '../src/local-agent.mjs';
test('readiness exposes priorities and evidence boundaries to both engineer and architect',()=>{
 const p=project([node('search','Amazon OpenSearch'),node('app','AWS App Runner')]);
 const before=JSON.stringify(p),files=deliveryPack(p,null),report=JSON.parse(files['spec-kit/readiness.json']);
 assert.equal(JSON.stringify(p),before);assert.equal(report.status,'engineering_required');
 assert.equal(report.stages.cloudPlan,'not_run');assert.equal(report.stages.localValidation,'not_attached');
 assert.ok(report.findings.some(f=>f.id.startsWith('search-mode-')));assert.ok(report.findings.some(f=>f.id.startsWith('service-lifecycle-')));
 assert.match(files['spec-kit/contracts.md'],/embedding model/);assert.match(files['spec-kit/contracts.md'],/closed to new customers/);
 assert.ok(agentContext(p).some(c=>c.id==='handoff-readiness'));
 const ids=new Set(JSON.parse(files['spec-kit/tasks.json']).tasks.map(t=>t.id));
 for(const f of report.findings)for(const id of f.taskIds)assert.ok(ids.has(id),id);
});
test('task order permits local work before access and requires staging before live tests',()=>{
 const p=project([node('source','Amazon S3'),node('model','Amazon Bedrock')]);p.edges=[{id:'e',source:'source',target:'model'},{id:'back',source:'model',target:'source'}];
 p.needs=[{id:'security',statement:'Restrict documents',source:'user',kind:'functional',links:['model']}];
 const list=JSON.parse(deliveryPack(p,null)['spec-kit/tasks.json']).tasks;
 const ancestors=id=>{const seen=new Set();function walk(i){for(const d of list.find(t=>t.id===i).dependsOn){assert.ok(!seen.has(`active:${d}`),'cycle');if(seen.has(d))continue;seen.add(`active:${d}`);walk(d);seen.delete(`active:${d}`);seen.add(d);}}walk(id);return seen;};
 assert.ok(!ancestors('TASK-INFRA-STATIC').has('TASK-STAGING'));
 assert.ok(!ancestors('TASK-CLOUD-PLAN').has('TASK-STAGING'));
 assert.ok(ancestors('TASK-STAGING').has('TASK-COST'));
 for(const t of list.filter(t=>t.phase==='Staging verification'))assert.ok(ancestors(t.id).has('TASK-STAGING'));
 assert.ok(ancestors('TASK-RELEASE').has('TASK-STAGING'));
});
test('readiness keeps broken requirement links, proposals and shared units visible',()=>{
 const p=project([node('chat','AWS App Runner'),node('answer','AWS App Runner')]);
 p.needs=[{id:'r',statement:'Fast answers',source:'agent',links:['deleted'],measure:{metric:'latency',op:'<=',target:5,unit:'s'}}];
 const report=handoffAssessment(p);
 for(const id of ['deployment-unit-mapping','traceability-72','requirement-proposed-72','acceptance-72'])assert.ok(report.findings.some(f=>f.id===id));
});
test('stable gap identifiers survive reordering and renaming',()=>{
 const p=project([node('a','AWS Lambda'),node('b','Amazon Bedrock')]);p.edges=[{id:'edge',source:'a',target:'b'}];
 const before=JSON.parse(terraformSketch(p)['main.tf.json']).locals.unfinished_work.sort();
 p.nodes.reverse();p.nodes[0].data.label='Bedrock model renamed';
 assert.deepEqual(JSON.parse(terraformSketch(p)['main.tf.json']).locals.unfinished_work.sort(),before);
});
test('multi-provider exports stay explicit about unsupported generation',()=>{
 for(const provider of ['azure','gcp','ibm']){
  const p=project([node('data','Existing documents',undefined,provider,'existing'),node('app','Application runtime',undefined,provider)]);p.provider=provider;
  const files=deliveryPack(p,null),tf=JSON.parse(files['terraform/main.tf.json']);
  assert.deepEqual(Object.keys(tf.resource),['terraform_data']);
  assert.match(files['spec-kit/contracts.md'],new RegExp(`exact ${provider} service`));
  assert.match(files['spec-kit/contracts.md'],/instead of recreating/);
  assert.equal(JSON.parse(files['spec-kit/readiness.json']).stages.infrastructure,'not_implemented');
 }
});

test('placement contradictions, cost gaps and open security findings reach the handoff',()=>{
 const p=project([node('app','AWS Lambda')]);p.nodes[0].data.config.region='eu-west-1';
 p.decisions=[{id:'region',subject:'cloud.region',decision:'ap-southeast-2',status:'Accepted'}];
 const report=handoffAssessment(p);
 assert.ok(report.findings.some(f=>f.id.startsWith('region-conflict-')));
 assert.ok(report.findings.some(f=>f.id==='cost-coverage'));
 const files=deliveryPack(p,null),ids=new Set(JSON.parse(files['spec-kit/tasks.json']).tasks.map(t=>t.id));
 for(const f of report.findings)for(const id of f.taskIds)assert.ok(ids.has(id));
 const llm=project([node('m','Amazon Bedrock'),node('o','Answer')]);llm.nodes[0].data.role='llm';llm.nodes[1].data.role='output';llm.edges=[{id:'answer',source:'m',target:'o'}];
 assert.ok(handoffAssessment(llm).findings.some(f=>f.area==='security'&&f.priority===1));
});
