import test from 'node:test';import assert from 'node:assert/strict';
import {consultationContext} from '../src/consultation-context.mjs';
import {agentContext} from '../src/local-agent.mjs';import {structuredWebProject} from './fixtures/structured-web-project.mjs';
test('long authoritative records retain every Unicode code point in bounded context chunks',()=>{
 const value='Architecture 😀 '.repeat(120),records=consultationContext([{type:'requirement',id:'req-long',text:value}]);
 assert.ok(records.length>1);assert.equal(records[0].id,'req-long');assert.equal(records[1].type,'discovery');
 const restored=records.map((r,i)=>i?r.text.replace(/^Continuation of .*?part \d+\/\d+: /,''):r.text).join('');assert.equal(restored,value);
 for(const r of records)assert.ok(Array.from(r.text).length<=1000);
});
test('oversized context is rejected explicitly rather than silently losing project records',()=>{
 assert.throws(()=>consultationContext(Array.from({length:301},(_,i)=>({type:'requirement',id:'r'+i,text:'A required behavior'}))),/no records were truncated/);
});
test('model context refers to current capability catalogue and retains a long requirement tail',()=>{
 const p=structuredWebProject();p.needs=[{id:'req-long',statement:'Mandatory behavior. '.repeat(90)+'FINAL REQUIRED BEHAVIOR',priority:'Must',kind:'functional',category:'scope',status:'proposed'}];
 const c=agentContext(p);assert.ok(c.some(r=>r.text.includes('FINAL REQUIRED BEHAVIOR')));assert.ok(c.some(r=>r.id==='infrastructure-coverage'&&r.text.includes('current compiler capability catalogue')));
});
