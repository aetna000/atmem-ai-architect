import test from 'node:test';import assert from 'node:assert/strict';
import {recordArchitectureTurn,finishArchitectureTurn,architectureTurns,architectureConversation,mergeArchitectureActivity,readArchitectureActivity} from '../src/architecture-activity.mjs';
import {hasArchitectureDesign,buildIntent,BUILD_DESIGN_REQUEST} from '../src/design-build-flow.mjs';
const id='00000000-0000-4000-8000-000000000001',p={id:'project-001',extensions:{},nodes:[]},turn={id,provider:'codex',model:'exact-model',effort:'high'};
test('turn history is immutable and scoped to the latest owning project',()=>{
 const next=recordArchitectureTurn(p,p.id,turn);assert.deepEqual(architectureTurns(p),[]);assert.equal(architectureTurns(next)[0].clientStatus,'submitted');
 assert.equal(finishArchitectureTurn(next,'other-project',id,'failed'),next);
 const done=finishArchitectureTurn(next,p.id,id,'response_received',true);assert.equal(architectureTurns(done)[0].clientStatus,'response_received');assert.equal(architectureTurns(next)[0].clientStatus,'submitted');
 assert.throws(()=>recordArchitectureTurn(next,p.id,turn),/already recorded/);
});
test('timeline keeps exact public text, deduplicates and refuses private event types or changed receipts',()=>{
 const e={sequence:4,kind:'model_message',text:'Preserve café 🍊 and all ownership.\nNext step.'};
 assert.deepEqual(mergeArchitectureActivity([e],[e,{sequence:2,kind:'tool_started',text:'Lookup'}]).map(e=>e.sequence),[2,4]);
 assert.throws(()=>mergeArchitectureActivity([e],[{...e,text:'Changed'}]),/identity/);assert.throws(()=>mergeArchitectureActivity([],[{...e,kind:'reasoning'}]),/unsupported/);
});
test('activity reads bind exact project and turn without exposing native paths',async()=>{
 let sent;const fetcher=async(url,options)=>{sent={url,...options};return {ok:true,json:async()=>({id,projectId:p.id,events:[]})};};
 await readArchitectureActivity({token:'local'},p.id,id,0,undefined,fetcher);assert.deepEqual(JSON.parse(sent.body),{projectId:p.id,activityId:id,after:0});assert.equal(sent.headers.Authorization,'Bearer local');
 await assert.rejects(readArchitectureActivity({},p.id,id,0,undefined,async()=>({ok:true,json:async()=>({id,projectId:'other',events:[]})})),/belong/);
});
test('blank and annotation-only designs cannot create builds; design intent needs no repeated brief',()=>{
 assert.equal(hasArchitectureDesign(p),false);assert.equal(buildIntent(p,''),'');assert.equal(hasArchitectureDesign({...p,nodes:[{data:{kind:'note'}}]}),false);
 const design={...p,nodes:[{data:{kind:'resource'}}]};assert.equal(buildIntent(design,''),BUILD_DESIGN_REQUEST);assert.equal(buildIntent(design,'  Keep café 🍊 intact.  '),'  Keep café 🍊 intact.  ');
 assert.equal(hasArchitectureDesign({...p,extensions:{architectureWork:{records:[{kind:'responsibility'}]}}}),true);
});

test('activity stays under its exact user request and before its answer across queued updates and reload',()=>{
 const second='00000000-0000-4000-8000-000000000002';let project=recordArchitectureTurn(p,p.id,{...turn,requestIds:['first']});project=recordArchitectureTurn(project,p.id,{...turn,id:second,requestIds:['next','third']});
 const messages=[{role:'user',requestId:'first',text:'Original'},{role:'user',requestId:'next',text:'Queued'},{role:'assistant',activityId:id,text:'Original reply'},{role:'user',requestId:'third',text:'Third update'},{role:'assistant',activityId:second,text:'Combined reply'}];
 const entries=architectureConversation(project,messages);assert.deepEqual(entries.map(e=>e.kind==='activity'?e.turn.id:e.message.text),['Original',id,'Queued','Original reply','Third update',second,'Combined reply']);assert.deepEqual(architectureConversation(JSON.parse(JSON.stringify(project)),JSON.parse(JSON.stringify(messages))),entries);
});
test('old unbound activity remains ordered without assigning it to an unrelated response; malformed history preserves chat',()=>{
 const second='00000000-0000-4000-8000-000000000002';let project=recordArchitectureTurn(p,p.id,turn);project=recordArchitectureTurn(project,p.id,{...turn,id:second,requestIds:['new']});const messages=[{role:'assistant',text:'Legacy answer'},{role:'user',requestId:'new',text:'New request'}],entries=architectureConversation(project,messages);assert.deepEqual(entries.filter(e=>e.kind==='activity').map(e=>e.turn.id),[id,second]);assert.equal(entries.filter(e=>e.kind==='message').length,2);
 const broken=architectureConversation({...p,extensions:{architectureActivity:{version:999}}},messages);assert.equal(broken.at(-1).kind,'activity-error');assert.equal(broken[0].message,messages[0]);
});
