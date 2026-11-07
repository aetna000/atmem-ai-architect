// Deterministic export/review cycles. No model calls, cloud plans or deployments.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {deliveryPack} from '../src/delivery.mjs';
import {fromProjectFile} from '../src/project-file.mjs';
const node=(id,label,service,provider='aws',origin='proposed')=>({id,type:'resource',position:{x:0,y:0},data:{label,service,provider,origin,kind:'resource',description:`${label} responsibility`,config:{region:'To be selected'}}});
const base=(name,nodes)=>({id:name,name,version:1,revision:1,provider:'aws',requirements:'Synthetic handoff scenario',nodes,edges:[],needs:[],decisions:[],assumptions:[],openQuestions:[]});
const scenarios=[
 base('empty',[]),base('s3',[node('store','Amazon S3')]),
 base('explicit-lambda',[node('sync','S3 sync worker','AWS Lambda')]),
 base('ambiguous',[node('mixed','Amazon S3 and AWS Lambda')]),
 ...['Amazon OpenSearch','Amazon OpenSearch Serverless','Amazon OpenSearch domain'].map((name,i)=>base(`search-${i}`,[node('search',name)])),
 base('shared-app',[node('chat','AWS App Runner'),node('answer','AWS App Runner')]),
 base('knowledge-base',[node('kb','Amazon Bedrock Knowledge Bases'),node('guard','Amazon Bedrock Guardrails')]),
 ...['azure','gcp','ibm'].map(provider=>({...base(provider,[node('legacy','Existing source',undefined,provider,'existing'),node('app','Runtime',undefined,provider)]),provider})),
];
const rag=base('cyclic-rag',[node('source','SharePoint',undefined,'tools','existing'),node('sync','AWS Lambda'),node('search','Amazon OpenSearch'),node('model','Amazon Bedrock'),node('app','Amazon ECS')]);
rag.edges=[['source','sync'],['sync','search'],['search','model'],['model','app'],['app','search']].map(([source,target],i)=>({id:`edge-${i}`,source,target,label:'document context'}));
rag.needs=[{id:'acl',statement:'Exclude unauthorized evidence',source:'user',kind:'functional',links:['search','model']},{id:'latency',statement:'Fast answers',source:'agent',kind:'nonfunctional',links:['deleted'],measure:{metric:'latency',op:'<=',target:5,unit:'s'}}];
rag.decisions=[{id:'country',subject:'data.country',decision:'Australia',status:'Accepted'},{id:'design',subject:'design.shared',decision:'One application serves answers and chat; region proposed',status:'Accepted'}];
scenarios.push(rag);
if(process.argv[2])scenarios.push(fromProjectFile(JSON.parse(fs.readFileSync(process.argv[2],'utf8'))).project);
const out=fs.mkdtempSync(path.join(os.tmpdir(),'atmem-handoff-review-'));
const results=[];
for(const [index,p] of scenarios.entries()){
 const original=JSON.stringify(p),files=deliveryPack(p,null),tasks=JSON.parse(files['spec-kit/tasks.json']).tasks,report=JSON.parse(files['spec-kit/readiness.json']);
 assert.equal(JSON.stringify(p),original,'generation must not mutate source');
 const taskIds=new Set(tasks.map(t=>t.id));assert.equal(taskIds.size,tasks.length);
 const done=new Set();while(done.size<tasks.length){const ready=tasks.filter(t=>!done.has(t.id)&&t.dependsOn.every(d=>done.has(d)));assert.ok(ready.length,`${p.name}: dependency cycle or missing dependency`);ready.forEach(t=>done.add(t.id));}
 for(const f of report.findings)for(const id of f.taskIds)assert.ok(taskIds.has(id),`${p.name}: unlinked finding ${id}`);
 assert.equal(report.stages.cloudPlan,'not_run');assert.equal(report.stages.localValidation,'not_attached');
 assert.equal(JSON.parse(files['spec-kit/context.json']).acceptedDecisions.length,(p.decisions||[]).filter(d=>d.status==='Accepted').length);
 const manifest=JSON.parse(files['manifest.json']);assert.deepEqual(manifest.files.sort(),Object.keys(files).sort());
 const reopened=fromProjectFile(JSON.parse(files['project.atmem-ai-architect.json'])).project;
 assert.equal(reopened.nodes.length,p.nodes.length);
 const folder=path.join(out,String(index));fs.mkdirSync(folder);
 for(const [name,content]of Object.entries(files)){const dest=path.join(folder,name);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,content);}
 // Second pass: reorder input and ensure task and resource identities stay stable.
 const reordered={...p,nodes:[...p.nodes].reverse(),edges:[...p.edges].reverse()};
 const again=deliveryPack(reordered,null);
 assert.deepEqual(JSON.parse(again['spec-kit/tasks.json']).tasks.map(t=>t.id).sort(),[...taskIds].sort());
 assert.deepEqual(JSON.parse(again['terraform/main.tf.json']).locals.unfinished_work.sort(),JSON.parse(files['terraform/main.tf.json']).locals.unfinished_work.sort());
 results.push({scenario:p.name,taskCount:tasks.length,findings:report.findings.length,priorityDecisions:report.counts.priorityDecisions,generatedFoundations:report.counts.generatedFoundations,passes:['export invariants','reorder stability'],folder});
}
fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({type:'local-generated-artifact-review',cloudOperations:false,results},null,2));
console.log(JSON.stringify({scenarios:results.length,cycles:2,results:path.join(out,'results.json')},null,2));
