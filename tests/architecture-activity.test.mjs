import test from 'node:test';import assert from 'node:assert/strict';
import {recordArchitectureTurn,finishArchitectureTurn,architectureTurns,mergeArchitectureActivity,readArchitectureActivity} from '../src/architecture-activity.mjs';
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
