import test from 'node:test';import assert from 'node:assert/strict';
import {architectureSteps,architectureActivityLabel} from '../src/activity-presentation.mjs';
import {architectureChatEntries,recordArchitectureTurn} from '../src/architecture-activity.mjs';
const event=(sequence,kind,details={},text=kind)=>({sequence,kind,details,text});
test('public steps pair only an unambiguous same-tool action and retain source identities',()=>{
 const steps=architectureSteps([event(1,'tool_started',{tool:'knowledge.lookup'}),event(2,'tool_finished',{tool:'knowledge.lookup',success:false}),event(3,'model_message',{},'Exact public update')]);
 assert.equal(steps.length,2);assert.deepEqual(steps[0].sources,[1,2]);assert.match(steps[0].text,/evidence unavailable/);assert.equal(steps[1].text,'Exact public update');assert.equal(steps[1].message,true);
});
test('overlapping starts have no invented pairing or dropped events',()=>{
 const steps=architectureSteps([event(1,'tool_started',{tool:'memory.lookup'}),event(2,'tool_started',{tool:'memory.lookup'}),event(3,'tool_finished',{tool:'memory.lookup'}),event(4,'tool_finished',{tool:'memory.lookup'})]);assert.equal(steps.length,4);assert.deepEqual(steps.flatMap(s=>s.sources),[1,2,3,4]);
});
test('public state descriptions do not invent retry success, test passes or elapsed time',()=>{
 const turn={clientStatus:'submitted'};assert.equal(architectureActivityLabel(turn,'recovery_required',false),'Outcome unknown after restart');assert.equal(architectureActivityLabel(turn,null,false),'Awaiting details');assert.equal(architectureActivityLabel({...turn,clientStatus:'response_received'},'running',false),'Response received');
 assert.match(architectureSteps([event(1,'tool_cached',{tool:'memory.lookup'})])[0].text,/saved result/);
});
test('old unassociated turns form one honest history disclosure; associated requests remain inline',()=>{
 const project={id:'history-project'},id='00000000-0000-4000-8000-000000000001';let p=project;
 for(let i=0;i<7;i++)p=recordArchitectureTurn(p,p.id,{id:id.slice(0,-1)+String(i+1),provider:'codex',model:'exact',effort:'high'});
 const entries=architectureChatEntries(p,[{role:'assistant',text:'Earlier response'}]);assert.equal(entries.filter(e=>e.kind==='legacy-activity').length,1);assert.equal(entries.at(-1).entries.length,7);assert.equal(entries[0].message.text,'Earlier response');
});
