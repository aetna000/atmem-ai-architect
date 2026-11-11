import test from 'node:test';import assert from 'node:assert/strict';
import {compositionFixture} from '../scripts/engine-evaluation/composition-fixtures.mjs';import {terraformSketch} from '../src/terraform.mjs';import {resourcePlan} from '../src/resources.mjs';import {generationQuality} from '../src/generation-quality.mjs';
import {invoiceProject} from './fixtures/invoice-project.mjs';import {validInvoiceRegion} from '../src/invoice-region.mjs';
for(const [region,partition]of [['eu-west-1','aws'],['cn-north-1','aws-cn'],['cn-northwest-1','aws-cn'],['us-gov-west-1','aws-us-gov'],['us-gov-east-1','aws-us-gov']])test(region+': supplied-image partition follows native metadata in standalone and mixed designs',()=>{
 const p=compositionFixture('aws'),node=p.nodes.at(-1);node.data.config={region};const before=structuredClone(p);
 for(const project of [p,{...p,nodes:[node],edges:[]}]){
  const files=terraformSketch(project),plan=resourcePlan(project),unit=plan.composition?.units.find(u=>u.id===node.id),prefix=unit?unit.path+'/':'',tf=JSON.parse(files[prefix+'main.tf.json']),name=plan.rows.find(r=>r.id===node.id).address,examples=JSON.parse(files[prefix+'deployment.tfvars.json.example']);
  assert.equal(tf.variable.region.default,region);assert.deepEqual(tf.data.aws_partition[name],{});assert(Object.values(tf.resource.aws_iam_role).every(r=>JSON.parse(r.assume_role_policy).Statement[0].Condition.ArnLike['aws:SourceArn']==='arn:${data.aws_partition.'+name+'.partition}:ecs:${var.region}:${var.account_id}:*'));assert(examples[name+'_repository_arn'].startsWith('arn:'+partition+':ecr:'+region+':'));assert.deepEqual(JSON.parse(files['generation-quality.json']).fatalFindings,[]);assert.equal(JSON.parse(files['generation-quality.json']).infrastructureComplete,true);
 }
 assert.deepEqual(p,before);
});
test('invoice partition support is separate from the supplied-image contract; no requested destination is replaced',()=>{
 for(const region of ['cn-north-1','us-gov-west-1']){
  assert.equal(validInvoiceRegion('aws',region),false);const p=invoiceProject('aws');p.nodes.find(n=>n.data.implementation==='invoice-workflow').data.config.region=region;const before=structuredClone(p),files=terraformSketch(p),plan=resourcePlan(p);assert(plan.gapDetails.some(g=>g.id==='invoice-config-region'&&g.message.includes('partition')));assert.equal(plan.rows.find(r=>r.invoice).region,region);assert.equal(JSON.parse(files['generation-quality.json']).infrastructureComplete,false);assert(JSON.parse(files['main.tf.json']).locals.unfinished_work.includes('invoice-config-region'));assert.deepEqual(p,before);
 }
});
test('independent inspection rejects substituted partition metadata, hardcoded trust and removed repository/region guards',()=>{
 const p=compositionFixture('aws');p.nodes.at(-1).data.config={region:'cn-north-1'};const plan=resourcePlan(p),files=terraformSketch(p),unit=plan.composition.units.find(u=>u.implementation==='container-service'),key=unit.path+'/main.tf.json',name=plan.rows.find(r=>r.id===unit.id).address;
 for(const mutation of ['metadata','hardcoded-trust','repository-guard','native-family-guard']){
  const tf=JSON.parse(files[key]);if(mutation==='metadata')tf.data.aws_partition[name]={provider:'aws.foreign'};
  if(mutation==='hardcoded-trust'){const trust=JSON.parse(tf.resource.aws_iam_role[name].assume_role_policy);trust.Statement[0].Condition.ArnLike['aws:SourceArn']='arn:aws:ecs:${var.region}:${var.account_id}:*';tf.resource.aws_iam_role[name].assume_role_policy=JSON.stringify(trust);}
  if(mutation==='repository-guard')tf.resource.aws_iam_role_policy[name].lifecycle.precondition=[];
  if(mutation==='native-family-guard')tf.resource.aws_ecs_service[name].lifecycle.precondition.pop();
  assert(generationQuality(p,plan,{...files,[key]:JSON.stringify(tf)}).fatalFindings.some(f=>f.code==='container-constraint-mismatch'),mutation);
 }
});
test('an invoice cannot claim partition support by suppressing planner gaps or deployment blockers',()=>{
 const p=invoiceProject('aws');p.nodes.find(n=>n.data.implementation==='invoice-workflow').data.config.region='cn-north-1';const plan=resourcePlan(p),files=terraformSketch(p),root=JSON.parse(files['main.tf.json']);plan.gapDetails=[];plan.gaps=[];root.locals.unfinished_work=[];
 const q=generationQuality(p,plan,{...files,'main.tf.json':JSON.stringify(root)});assert.equal(q.infrastructureComplete,false);assert(q.findings.some(f=>f.code==='partition-implementation-required'));assert(q.fatalFindings.some(f=>f.code==='missing-work-gate'));
});
