import test from 'node:test';import assert from 'node:assert/strict';
import {validateVerificationCases,validateVerificationReferences}from '../src/verification-cases.mjs';
import {toProjectFile,parseProjectFile}from '../src/project-file.mjs';
import {createBlockHandoff}from '../src/block-handoff.mjs';
import {blockSpecPath}from '../src/block-spec-kit.mjs';
import {architectureConsistency}from '../src/architecture-consistency.mjs';
import {amendCanvasGraph}from '../src/canvas-amendments.mjs';
const caseRecord=()=>({id:'race-last-slot',name:'Concurrent last-slot requests',category:'integration',requirementIds:['exclusive'],environment:'Local transactional implementation with two independent clients; external scheduling stub.',setup:'Create resource A with one open slot [10:00,11:00). No confirmed reservations.',input:'Two different request IDs, same resource A and slot; callers P and Q.',action:'Release both clients through one barrier and await both terminal outcomes; read authoritative schedule.',expected:'Exactly one accepted outcome and one conflict. Exactly one confirmed reservation. No overwritten receipt.',evidence:'Record barrier release, both request IDs and outcomes, final schedule rows and transaction traces.'});
const project=()=>({version:1,revision:1,name:'Shared studio scheduling',provider:'tools',nodes:['scheduler','catalog'].map((id,i)=>({id,type:'resource',position:{x:i*400,y:0},data:{label:id,kind:'resource',provider:'tools',...(id==='scheduler'?{buildSpec:{verificationCases:[caseRecord()]}}:{})}})),edges:[{id:'resource-check',source:'scheduler',target:'catalog',label:'Read resource'}],needs:[{id:'exclusive',statement:'Allow one confirmed slot allocation.',links:['scheduler']}]});
test('specified verification cases roundtrip and hand off exact inputs/expected evidence without claiming execution',()=>{
 const p=project();validateVerificationReferences(p);
 const source=JSON.stringify(toProjectFile(p));const reopened=parseProjectFile(source).project;
 assert.deepEqual(reopened.nodes[0].data.buildSpec.verificationCases,[caseRecord()]);
 const h=createBlockHandoff(source,'scheduler'),path=blockSpecPath('scheduler');
 const cases=JSON.parse(h.files[path+'/verification-cases.json']);assert.equal(cases.execution,'not_run');assert.equal(JSON.parse(h.files['handoff-readiness.json']).verificationPlan.specifiedCases,1);assert.deepEqual(cases.cases,[caseRecord()]);
 assert.ok(h.files[path+'/testing.md'].includes(caseRecord().expected));assert.ok(h.files[path+'/testing.md'].includes(caseRecord().evidence));
});
test('invalid case records reject and unresolved references survive saves for review',()=>{
 for(const mutate of [c=>delete c.expected,c=>c.setup=' ',c=>c.status='passed',c=>c.requirementIds=['exclusive','exclusive'],c=>c.category='deployment_pass']){const row=caseRecord();mutate(row);assert.throws(()=>validateVerificationCases([row]),/Verification/);}
 assert.throws(()=>validateVerificationCases([caseRecord(),caseRecord()]),/identity/);
 for(const mutate of [p=>p.nodes[0].data.buildSpec.verificationCases[0].requirementIds=['unknown'],p=>p.nodes[0].data.buildSpec.verificationCases[0].operationId='missing',p=>p.nodes[0].data.buildSpec.verificationCases[0].interfaceId='foreign']){const p=project();mutate(p);assert.throws(()=>validateVerificationReferences(p),/Verification/);const saved=parseProjectFile(JSON.stringify(toProjectFile(p))).project;assert.deepEqual(saved.nodes[0].data.buildSpec.verificationCases,p.nodes[0].data.buildSpec.verificationCases);assert.ok(architectureConsistency(saved).issues.some(issue=>issue.caseId==='race-last-slot'&&issue.severity==='error'));}
 const p=project();p.nodes[0].data.buildSpec.verificationCases[0].interfaceId='resource-check';assert.doesNotThrow(()=>validateVerificationReferences(p));
});
test('refining a module cannot silently remove a prior verification case',()=>{
 const p=project();assert.throws(()=>amendCanvasGraph(p,{addNodes:[],addEdges:[],updateNodes:[{id:'scheduler',data:{buildSpec:{verificationCases:[]}}}]}),/cannot silently remove/);
 const next=structuredClone(caseRecord());next.expected+=' Replaying the winner returns the same receipt.';
 const changed=amendCanvasGraph(p,{addNodes:[],addEdges:[],updateNodes:[{id:'scheduler',data:{buildSpec:{verificationCases:[next]}}}]});assert.equal(changed.nodes[0].data.buildSpec.verificationCases[0].expected,next.expected);
});
