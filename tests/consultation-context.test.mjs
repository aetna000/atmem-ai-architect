import test from 'node:test';import assert from 'node:assert/strict';
import {consultationContext} from '../src/consultation-context.mjs';
import {agentContext,requestArchitect} from '../src/local-agent.mjs';import {structuredWebProject} from './fixtures/structured-web-project.mjs';
test('long authoritative records retain every Unicode code point in bounded context chunks',()=>{
 const value='Architecture 😀 '.repeat(120),records=consultationContext([{type:'requirement',id:'req-long',text:value}]);
 assert.ok(records.length>1);assert.equal(records[0].id,'req-long');assert.equal(records[1].type,'discovery');
 const restored=records.map((r,i)=>i?r.text.replace(/^Continuation of .*?part \d+\/\d+: /,''):r.text).join('');assert.equal(restored,value);
 for(const r of records)assert.ok(Array.from(r.text).length<=1000);
});
test('context retains all records beyond the former count limit and survives repeated preparation',()=>{
 const records=Array.from({length:1500},(_,i)=>({type:'requirement',id:'r'+i,text:'Required behavior '+i}));
 assert.deepEqual(consultationContext(records),records);
 assert.deepEqual(consultationContext(consultationContext(records)),records);
});
test('one long Unicode record may produce more than 300 chunks without dropping its tail',()=>{
 const text='患者 😀 café '.repeat(30000)+'FINAL REQUIRED BEHAVIOR';
 const records=consultationContext([{type:'requirement',id:'req-long',text}]);
 assert.ok(records.length>300);
 assert.equal(records.map((r,i)=>i?r.text.replace(/^Continuation of .*?part \d+\/\d+: /,''):r.text).join(''),text);
 assert.ok(records.every(r=>Array.from(r.text).length<=1000));
});
test('normal request serializes all project requirements and added consultation records',async()=>{
 const p=structuredWebProject();p.needs=Array.from({length:500},(_,i)=>({id:'req-'+i,statement:'Required behavior '+i,priority:'must',source:'user',kind:'functional',category:'other',status:'open',links:[]}));
 const extra=Array.from({length:700},(_,i)=>({type:'discovery',id:'extra-'+i,text:'Extra source evidence '+i}));
 const original=globalThis.fetch;let request;
 globalThis.fetch=async(url,options)=>{assert.equal(url,'/api/architect');request=JSON.parse(options.body);return Response.json({message:'Checked the full consultation.'});};
 try{await requestArchitect({session:{token:'synthetic-token'},connection:{provider:'codex',model:'default'},message:'Review every requirement',project:p,history:[],extra});}finally{globalThis.fetch=original;}
 assert.ok(request.context.length>1200);
 for(const requirement of p.needs)assert.ok(request.context.some(r=>r.type==='requirement'&&r.id===requirement.id&&r.text.includes(requirement.statement)));
 for(const record of extra)assert.ok(request.context.some(r=>r.id===record.id&&r.text===record.text));
});
test('model context refers to current capability catalogue and retains a long requirement tail',()=>{
 const p=structuredWebProject();p.needs=[{id:'req-long',statement:'Mandatory behavior. '.repeat(90)+'FINAL REQUIRED BEHAVIOR',priority:'Must',kind:'functional',category:'scope',status:'proposed'}];
 const c=agentContext(p);assert.ok(c.some(r=>r.text.includes('FINAL REQUIRED BEHAVIOR')));assert.ok(c.some(r=>r.id==='infrastructure-coverage'&&r.text.includes('current compiler capability catalogue')));
});
