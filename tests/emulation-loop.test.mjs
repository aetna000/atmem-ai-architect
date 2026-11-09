import test from 'node:test';
import assert from 'node:assert/strict';
import {emulationPrompt,emulationFeedback,guardEmulationCorrection,groundEmulationMessage,emulationCoachReady} from '../src/emulation-feedback.mjs';
import {CLOUD_STORAGE_SCENARIOS} from '../src/cloud-storage-scenarios.mjs';
import {terraformSketch} from '../src/terraform.mjs';
import {resourcePlan} from '../src/resources.mjs';
import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';
for(const {id,project} of CLOUD_STORAGE_SCENARIOS){
 test(`${id}: typed storage survives save/open and gates missing permissions`,()=>{
  const reopened=fromProjectFile(toProjectFile(project)).project;
  assert.equal(reopened.nodes[0].data.implementation,'private-object-storage');assert.equal(reopened.edges[0].access,'storage-object-admin');
  assert.equal(resourcePlan(reopened).gaps.length,0);
  const tf=JSON.parse(terraformSketch(reopened)['main.tf.json']);assert.deepEqual(tf.locals.unfinished_work,[]);assert.equal(Object.keys(tf.terraform.required_providers).length,1);
  const missing=structuredClone(reopened);delete missing.edges[0].access;assert.ok(resourcePlan(missing).gaps.length);assert.ok(JSON.parse(terraformSketch(missing)['main.tf.json']).locals.unfinished_work.length);
  const production=JSON.parse(terraformSketch(reopened,'production')['main.tf.json']);assert.ok(production.locals.unfinished_work.includes('production-remote-state-and-operational-review-required'));
 });
 test(`${id}: required compute scope cannot disappear behind a storage pass`,()=>{
  const p=structuredClone(project);p.nodes.push({id:'compute',data:{label:'Required AI runtime',provider:id,kind:'agent',origin:'proposed'}});p.edges.push({id:'flow',source:'documents',target:'compute'});assert.ok(resourcePlan(p).gapDetails.some(g=>g.componentIds?.includes('compute')));
 });
}
test('mentor evidence is bounded, separates proof, and asks one useful question',()=>{
 const p=structuredClone(CLOUD_STORAGE_SCENARIOS[0].project);delete p.edges[0].access;
 const report={status:'blocked',blockers:['x'.repeat(20000)],checks:[],limitations:['Unverified IAM']};
 assert.match(emulationFeedback(p,report).question,/Who should access/);
 const prompt=emulationPrompt(p,report);assert.ok(prompt.length<=8000);assert.match(prompt,/patient architecture consultant/);assert.match(prompt,/untrusted evidence/);assert.match(prompt,/not a cloud plan or deployment/);
 assert.match(emulationPrompt(p,report,'question'),/do not change the graph yet/);
});
test('corrections can fill missing contracts but cannot remove scope or change trust boundaries',()=>{
 const after=structuredClone(CLOUD_STORAGE_SCENARIOS[0].project),before=structuredClone(after);delete before.edges[0].access;assert.equal(guardEmulationCorrection(before,after),true);
 for(const mutate of [p=>p.nodes.pop(),p=>p.edges.pop(),p=>p.nodes[0].data.kind='note',p=>p.nodes[1].data.origin='proposed',p=>p.nodes[0].data.provider='aws',p=>p.nodes[0].data.origin='existing',p=>p.nodes[1].data.binding='web-browser',p=>p.edges[0].source='documents',p=>p.edges[0].access='s3-read']){
  const changed=structuredClone(after);mutate(changed);assert.throws(()=>guardEmulationCorrection(after,changed));
 }
});

test('an empty run cannot be turned into success by reassuring model prose',()=>{
 const text=groundEmulationMessage({status:'blocked',checks:[]},'Good news: the design itself checks out. The emulation found no failures. We need a native runtime implementation. Which country must the data remain in?');
 assert.match(text,/Testing couldn’t start/);assert.doesNotMatch(text,/checks out|found no failures|Which country|runtime checks/);assert.match(text,/Next:/);assert.ok(text.split(/\s+/).length<70);
});

import {AI_QUALIFICATION_SCENARIOS,assessAiArchitecture} from '../src/ai-qualification-scenarios.mjs';
test('all four providers have ten AI workload acceptance contracts beyond storage',()=>{
 assert.equal(AI_QUALIFICATION_SCENARIOS.length,40);assert.equal(new Set(AI_QUALIFICATION_SCENARIOS.map(s=>s.id)).size,40);
 for(const provider of ['aws','azure','gcp','ibm'])assert.equal(AI_QUALIFICATION_SCENARIOS.filter(s=>s.provider===provider).length,10);
 for(const s of AI_QUALIFICATION_SCENARIOS){assert.equal(s.checks.length,5);assert.ok(s.question.endsWith('?'));assert.match(s.prompt,/Do not reduce this application to storage/);assert.equal(assessAiArchitecture(CLOUD_STORAGE_SCENARIOS[0].project,s).passed,false);}
});

test('automatic mentoring waits for a ready provider instead of spending failed turns',()=>{
 const connection={provider:'claude-code'};
 assert.equal(emulationCoachReady(null,connection),false);
 assert.equal(emulationCoachReady({token:'fixture',providers:{'claude-code':{available:true,signedIn:false}}},connection),false);
 assert.equal(emulationCoachReady({token:'fixture',providers:{'claude-code':{available:true,signedIn:true}}},connection),true);
});

import {emulationGuidance,emulationRepairTask,guidanceMessage} from '../src/emulation-guidance.mjs';
test('implementation gaps belong to Architect, with one next action and a traceable repair task',()=>{
 const p=structuredClone(CLOUD_STORAGE_SCENARIOS[0].project);p.nodes.push({id:'app',data:{label:'Application backend',provider:'azure',kind:'resource',origin:'proposed'}});
 const report={status:'blocked',checks:[],designRevision:95,artifactDigest:'a'.repeat(64),blockers:['implementation-required']};const g=emulationGuidance(p,report);assert.equal(g.owner,'engineering');assert.equal(g.needsModel,false);assert.equal(g.componentId,'app');assert.ok(guidanceMessage(g).split(/\s+/).length<70);assert.doesNotMatch(guidanceMessage(g),/95|artifact|runtime checks|Which|What port/);const task=emulationRepairTask(p,report);assert.match(task,/95/);assert.match(task,/implementation-required/);assert.match(task,/Checks executed: 0/);
});
test('a supported missing access correction still gets Architect help; empty success is not success',()=>{
 const p=structuredClone(CLOUD_STORAGE_SCENARIOS[0].project);delete p.edges[0].access;const g=emulationGuidance(p,{status:'blocked',checks:[]});assert.equal(g.needsModel,true);assert.match(g.next,/who should be allowed/);assert.notEqual(emulationGuidance(p,{status:'passed',checks:[]}).title,'Local emulation checks passed');assert.equal(emulationGuidance(p,{status:'passed',checks:[{passed:true}]}),null);
});
