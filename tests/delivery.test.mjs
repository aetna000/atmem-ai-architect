import test from 'node:test';
import assert from 'node:assert/strict';
import { estimate, setPrice, setUsage, consultingEstimate, WORK_PHASES } from '../src/estimate.mjs';
import { deliveryPack } from '../src/delivery.mjs';
import { resourcePlan } from '../src/resources.mjs';
import { terraformSketch } from '../src/terraform.mjs';
import { toProjectFile, fromProjectFile } from '../src/project-file.mjs';
import { agentContext } from '../src/local-agent.mjs';
const block=(id,label,provider='aws',kind='source',origin='proposed')=>({id,type:'resource',position:{x:0,y:0},data:{label,provider,kind,description:label,origin,config:{region:'ap-southeast-2',classification:'Internal',timeout:5000}}});
const project=()=>({id:'test-project',version:1,revision:7,name:'Policy assistant',provider:'aws',requirements:'Help staff answer policy questions',nodes:[block('files','Amazon S3')],edges:[],needs:[],assumptions:[],decisions:[],openQuestions:[]});
const detail=(id,componentId,patch={})=>({id,componentId,description:'Storage',quantity:100,unit:'GB-month',price:0.02,currency:'USD',source:'Entered test quote — synthetic, not AWS pricing',date:'2026-11-05',region:'ap-southeast-2',service:'S3 storage',...patch});
const now=new Date('2026-11-05T12:00:00Z');

test('ROM stays unknown without prices, then exposes its assumptions and uncosted components',()=>{
 let p=project();assert.equal(estimate(p,now).maturity,'Not estimated');
 p=setPrice(setUsage(p,'data_gb',100),'files',{price:0.02,currency:'USD'});
 p.nodes.push(block('ui','Web app','tools','output'));
 const e=estimate(p,now);assert.equal(e.maturity,'ROM');assert.equal(e.expected,2);assert.equal(e.low,1.4);assert.equal(e.high,3);assert.ok(e.gaps.some(g=>g.includes('Web app')));
});
test('detailed lines replace a ROM and independently price input and output tokens',()=>{
 const p=project();p.nodes=[block('llm','Amazon Bedrock','aws','agent')];
 p.estimate={prices:{llm:{price:999,source:'synthetic',currency:'USD'}},details:[detail('input','llm',{description:'Input tokens',quantity:1200,price:0.003,unit:'1k tokens'}),detail('output','llm',{description:'Output tokens',quantity:200,price:0.015,unit:'1k tokens'})]};
 const e=estimate(p,now);assert.equal(e.lines.length,2);assert.equal(e.expected,6.6);assert.equal(e.maturity,'Detailed worksheet');assert.equal(e.gaps.length,0);assert.equal(e.complete,true);
 const dirty=structuredClone(p);dirty.estimate.details[0].source='';assert.equal(estimate(dirty,now).complete,false);assert.equal(estimate(dirty,now).expected,3);
});
test('mixed currencies are never summed, including in exported estimates',()=>{
 const p=project();p.estimate={details:[detail('a','files'),detail('b','files',{currency:'AUD'})]};
 const e=estimate(p,now);assert.equal(e.expected,null);assert.equal(e.low,null);assert.equal(e.high,null);assert.equal(e.complete,false);assert.equal(e.mixedCurrencies,true);
 const pack=deliveryPack(p,null,'staging',now);assert.equal(JSON.parse(pack['estimate.json']).cloud.expected,null);
});
test('negative usage and invalid price are refused; range bounds stay ordered',()=>{
 let p=setUsage(project(),'data_gb',-50);assert.equal(p.estimate.usage.data_gb,undefined);
 p.estimate={usage:{data_gb:100},low:2,high:-1,prices:{files:{price:-2,currency:'USD',source:'bad'}}};
 const e=estimate(p,now);assert.equal(e.lines[0].cost,null);assert.deepEqual(e.factors,{low:0.7,high:1.5});
});
test('stale prices and removed components become explicit gaps',()=>{
 const p=project();p.estimate={details:[detail('a','files',{date:'2025-01-01'}),detail('b','deleted')]};
 const e=estimate(p,now);assert.ok(e.gaps.some(g=>g.includes('90 days')));assert.ok(e.gaps.some(g=>g.includes('removed')));assert.equal(e.expected,2);
});
test('one-off build work is separate and unknown phases never become free',()=>{
 const p=project();assert.equal(consultingEstimate(p).expected,null);
 p.estimate={consulting:{currency:'AUD',phases:{}}};
 for(const [id] of WORK_PHASES)p.estimate.consulting.phases[id]={lowDays:1,days:2,highDays:3,rate:1000,basis:'Synthetic test scope and rate'};
 let c=consultingEstimate(p);assert.equal(c.complete,true);assert.equal(c.expected,10000);assert.equal(c.low,5000);assert.equal(c.high,15000);
 p.estimate.consulting.phases.build.lowDays=4;c=consultingEstimate(p);assert.equal(c.complete,false);assert.equal(c.expected,8000);
 assert.equal(estimate(p,now).expected,null);
});
test('detailed prices and work estimates survive project save/open; old 2.1 projects still open',()=>{
 const p=project();p.estimate={details:[detail('a','files')],consulting:{currency:'USD',phases:{build:{lowDays:1,days:2,highDays:4,rate:500,basis:'Build'}}}};
 const file=toProjectFile(p,now),back=fromProjectFile(JSON.parse(JSON.stringify(file))).project;
 assert.equal(file.formatVersion,'2.3.0');assert.deepEqual(back.estimate.details,p.estimate.details);assert.equal(consultingEstimate(back).expected,1000);
 assert.equal(fromProjectFile({...file,formatVersion:'2.1.0'}).migrated,true);
});
test('resource schedule distinguishes existing systems, cloud choices, and drawn integrations',()=>{
 const p=project();p.nodes.push(block('model','Amazon Bedrock','aws','agent'),block('legacy','Amazon S3','aws','source','existing'),block('other','Azure Storage','azure'));
 p.edges=[{id:'e',source:'files',target:'model',label:'documents'}];
 const plan=resourcePlan(p);assert.equal(plan.rows.length,4);assert.equal(plan.rows.filter(r=>r.foundation).length,1);assert.equal(plan.rows[2].existing,true);assert.equal(plan.connections.length,1);assert.ok(plan.gaps.some(g=>g.includes('Wire files')));
});
test('Terraform is a native S3 foundation with an account/review gate and stable safe addresses',()=>{
 const p=project();p.nodes.push(block('existing','Amazon S3','aws','source','existing'));
 const files=terraformSketch(p),tf=JSON.parse(files['main.tf.json']);
 assert.equal(Object.keys(tf.resource.aws_s3_bucket).length,1);assert.equal(tf.variable.review_approved.default,false);assert.deepEqual(tf.provider.aws.allowed_account_ids,['${var.aws_account_id}']);
 const [address,bucket]=Object.entries(tf.resource.aws_s3_bucket)[0];assert.equal(bucket.lifecycle.prevent_destroy,true);assert.deepEqual(bucket.depends_on,['terraform_data.review_gate']);assert.equal(tf.locals.unfinished_work.length,2);assert.ok(tf.locals.unfinished_work.some(g=>g.startsWith("access-")));
 p.nodes.reverse();assert.ok(JSON.parse(terraformSketch(p)['main.tf.json']).resource.aws_s3_bucket[address]);
 p.nodes[1].data.label='Amazon S3 ${file("/etc/passwd")}';assert.ok(!terraformSketch(p)['main.tf.json'].includes('/etc/passwd'));
 assert.match(files['README.md'],/not a complete deployable application/);
});
test('delivery pack tracks one snapshot, regenerates after edits and refuses credentials',()=>{
 const p=project();p.openQuestions=[{id:'q1',question:'Which retention period?',status:'open'}];
 const files=deliveryPack(p,null,'staging',now),manifest=JSON.parse(files['manifest.json']);
 assert.equal(manifest.designRevision,7);assert.equal(manifest.deploymentExecuted,false);assert.deepEqual(manifest.files.sort(),Object.keys(files).sort());
 assert.match(files['specification.md'],/Policy assistant/);assert.match(files['handoff.md'],/Which retention period/);assert.match(files['architecture-and-deployment.md'],/Cloud resource schedule/);assert.match(files['specification.md'],new RegExp(manifest.snapshotId));
 p.name='Revised solution';const again=deliveryPack(p,null,'staging',now);assert.match(again['specification.md'],/Revised solution/);assert.notEqual(JSON.parse(again['manifest.json']).snapshotId,manifest.snapshotId);
 p.extensions={password:'do-not-export'};assert.throws(()=>deliveryPack(p,null),/credential/);
});
test('the architect sees estimate and infrastructure gaps in supported read-only context',()=>{
 const context=agentContext(project());assert.ok(context.some(c=>c.id==='estimate-summary'));assert.ok(context.some(c=>c.id==='infrastructure-coverage'));assert.ok(context.some(c=>c.id==='cost-gap-0'));
 assert.ok(context.every(c=>['requirement','assumption','question','decision','discovery'].includes(c.type)));
});
