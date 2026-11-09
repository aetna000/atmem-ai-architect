// Headless adapter of the product's discovery, response reducers and export pipeline.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
import {validateImport} from '../src/core.mjs';import {understand} from '../src/discovery.mjs';import {withDerived} from '../src/derive.mjs';import {keepEngagement} from '../src/engagement.mjs';
import {applyDecisionUpdates,applyRequirementDrafts} from '../src/consultation.mjs';import {toAgentProject,agentContext} from '../src/local-agent.mjs';import {deliveryPack} from '../src/delivery.mjs';import {resourcePlan} from '../src/resources.mjs';
let input='';for await(const c of process.stdin)input+=c;const request=JSON.parse(input);let p=request.project;
if(request.action==='initial'){
 p=validateImport({id:request.id,version:1,revision:1,name:request.scenario.name,provider:request.provider,requirements:request.message,nodes:[],edges:[]});
}
if(request.action==='initial'||request.action==='prepare'){
 p=withDerived(understand(request.message,p).project);
 process.stdout.write(JSON.stringify({project:p,agentProject:toAgentProject(p),context:agentContext(p)}));
}else if(request.action==='apply'){
 const r=request.response,old=p;
 if(r.proposal){if(r.proposal.baseRevision!==p.revision)throw Error('Wrong proposal revision');p=withDerived({...keepEngagement(validateImport(r.proposal.next),p),revision:p.revision+1});}
 if(r.decisionUpdates?.length)p=withDerived(applyDecisionUpdates(p,r.decisionUpdates,request.message));
 if(r.requirementDrafts?.length)p=withDerived(applyRequirementDrafts(p,r.requirementDrafts));
 p={...p,lastAsked:r.followUp?{id:'architect-question',topic:r.followUp.topic||'',question:r.followUp.question,why:r.followUp.why,beginner:r.followUp.example||''}:null,extensions:{...p.extensions,activeConsultation:{hasQuestion:!!r.followUp}}};
 process.stdout.write(JSON.stringify({project:validateImport(p),scopePreserved:p.requirements===old.requirements}));
}else if(request.action==='export'){
 const files=deliveryPack(p,null,'staging'),dir=path.resolve(request.output);fs.mkdirSync(dir,{recursive:true});
 for(const [name,body] of Object.entries(files)){if(path.isAbsolute(name)||name.split('/').includes('..')||typeof body!=='string')throw Error('Unsafe export path/type');const target=path.join(dir,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,body);}
 const q=JSON.parse(files['generation-quality.json']),plan=resourcePlan(p),tasks=JSON.parse(files['spec-kit/tasks.json']);
 const list=Array.isArray(tasks)?tasks:tasks.tasks||[];const ids=new Set(list.map(t=>t.id));const missingDependencies=list.flatMap(t=>(t.dependsOn||[]).filter(id=>!ids.has(id)).map(id=>({task:t.id,missing:id})));
 process.stdout.write(JSON.stringify({quality:q,resourcePlan:plan,files:Object.keys(files),digests:Object.fromEntries(Object.entries(files).map(([k,v])=>[k,createHash('sha256').update(v).digest('hex')])),taskCount:list.length,missingDependencies,scopeEvidence:'Static export facts only. Runtime and semantic completeness require independent qualification.'}));
}else if(!['initial','prepare'].includes(request.action))throw Error('Unknown bridge action');
