import assert from 'node:assert/strict';
import test from 'node:test';
import {zipSync,strToU8} from 'fflate';
import {CANVAS_ARTIFACT,DESIGN_WITH_CODEX,REFINE_CODEX_CANVAS,canvasProposal,canvasProposalRecords} from '../src/codex-canvas.mjs';
import {parseProjectFile,toProjectFile} from '../src/project-file.mjs';
import {blockSpecKit,blockSpecPath} from '../src/block-spec-kit.mjs';
import {reconcileSystemModel,validateSystemModel,systemModelOnBoard,removeModelRecord} from '../src/system-model.mjs';
import {reservationSystemModel} from './fixtures/system-model.mjs';

const digest='a'.repeat(64);
const base={id:'bookings',version:1,revision:1,name:'Bookings',provider:'tools',nodes:[],edges:[],
  extensions:{designSources:[{name:'brief.txt',sha256:digest,text:'Reserve each item at most once.',mime:'text/plain'}]}};
const block=id=>({id,type:'resource',position:{x:0,y:0},data:{label:id,kind:'resource',provider:'tools',origin:'proposed'}});
const draft={version:1,baseRevision:1,title:'Bookings',sourceSlots:[1],
  addNodes:[block('Ledger'),block('Reservations')],
  addEdges:[{id:'reserve',source:'Ledger',target:'Reservations',label:'Reserve'}],
  requirements:[{id:'unique-reservation',statement:'Reserve each item at most once.',sourceSlot:1,reference:'Paragraph 1',links:['Reservations']}],
};
const capture=systemModel=>canvasProposal(base,zipSync({[CANVAS_ARTIFACT]:strToU8(JSON.stringify({...draft,systemModel}))}),'artifact','b'.repeat(64));

test('initial design and refinement request native diagrams; captured model reopens and goes into the assigned module kit',()=>{
  for(const prompt of [DESIGN_WITH_CODEX,REFINE_CODEX_CANVAS])assert.match(prompt,/systemModel.*functional flow and sequence/);
  const model=reservationSystemModel();
  const result=capture(model);
  const applied={...result.next,...canvasProposalRecords(base,result),revision:2};
  assert.equal(result.quality.systemModel.status,'structurally_checked');
  const reloaded=parseProjectFile(JSON.stringify(toProjectFile(applied))).project;
  assert.deepEqual(reloaded.extensions.systemModel,model);
  const kit=blockSpecKit(reloaded,'fixture',[]);
  assert.deepEqual(JSON.parse(kit['spec-kit/system/system-model.json']),model);
  const scope=JSON.parse(kit[blockSpecPath('Reservations')+'/system-model-assignment.json']);
  assert.deepEqual(scope.elementIds,['allocator','allocate','allocator-in','allocate-in']);
  assert.deepEqual(scope.exchangeIds,['reserve-item','verified-request']);
  assert.deepEqual(scope.diagramIds,['logical','flow','scenario','retry']);
  assert.equal(capture(undefined).quality.systemModel.status,'missing');
});

test('capture rejects direction, ownership, trace, interface and sequence contradictions',()=>{
  for(const [edit,message] of [
    [m=>m.elements.find(row=>row.id==='allocate-in').direction='out',/incompatible port/],
    [m=>m.elements.find(row=>row.id==='allocate').allocatedTo='ledger',/disagree on function allocations/],
    [m=>m.exchanges.find(row=>row.id==='reserve-item').interfaceId='imaginary',/same allocated endpoints/],
    [m=>m.exchanges.find(row=>row.id==='reserve-item').requirementIds=['invented-id'],/unknown requirement/],
    [m=>m.diagrams.find(row=>row.id==='retry').elementIds=['ledger','clerk'],/visible, compatible participants/],
    [m=>m.elements.find(row=>row.id==='ledger').parentId='allocator',/cyclic nesting/],
    [m=>m.diagrams=m.diagrams.filter(row=>row.kind!=='sequence'),/include logical component, functional flow and sequence/],
  ]){
    const model=reservationSystemModel(); edit(model);
    assert.throws(()=>capture(model),message);
  }
});

test('refinement preserves record identity; views see a single shared exchange edit',()=>{
  const base=reservationSystemModel();
  const updated=structuredClone(base);
  updated.exchanges.find(row=>row.id==='reserve-item').name='Confirm hold';
  assert.equal(reconcileSystemModel(base,updated),updated);
  assert.equal(reconcileSystemModel(base,undefined),base);
  updated.elements=updated.elements.filter(row=>row.id!=='clerk-request');
  updated.exchanges=updated.exchanges.filter(row=>row.id!=='submit');
  for(const view of updated.diagrams)view.exchangeIds=view.exchangeIds.filter(id=>id!=='submit');
  assert.throws(()=>reconcileSystemModel(base,updated),/cannot remove or silently reassign/);
});

test('the grammar also models circular measured feedback between equipment components',()=>{
  const record=(id,kind,attrs={})=>({id,name:id,kind,description:'Cooling process design.',basis:'proposed',requirementIds:[],...attrs});
  const elements=[
    record('controller','component'),record('actuator','component'),
    record('regulate','function',{allocatedTo:'controller'}),record('measure','function',{allocatedTo:'actuator'}),
    record('c-port','componentPort',{ownerId:'controller',direction:'inout'}),
    record('a-port','componentPort',{ownerId:'actuator',direction:'inout'}),
    record('r-port','functionPort',{ownerId:'regulate',direction:'inout'}),
    record('m-port','functionPort',{ownerId:'measure',direction:'inout'}),
  ];
  const exchange=(id,kind,source,target,item,attrs={})=>record(id,kind,{source,target,items:[item],...attrs});
  const exchanges=[
    exchange('setpoint','component','c-port','a-port','Target speed'),
    exchange('actual','component','a-port','c-port','Measured speed'),
    exchange('target-flow','functional','r-port','m-port','Target speed',{componentExchangeId:'setpoint'}),
    exchange('actual-flow','functional','m-port','r-port','Measured speed',{componentExchangeId:'actual'}),
  ];
  const diagram=(id,kind,elementIds,exchangeIds)=>({id,name:id,kind,elementIds,exchangeIds});
  const diagrams=[
    diagram('equipment','components',['controller','actuator'],['setpoint','actual']),
    diagram('feedback','functions',['regulate','measure'],['target-flow','actual-flow']),
    diagram('observe','sequence',['controller','actuator'],['setpoint','actual','actual']),
  ];
  assert.ok(validateSystemModel({format:'atmem.system-model',version:1,id:'cooling',elements,exchanges,diagrams}));
});

test('deleting a board block removes its symbols, allocated functions and incident messages from live diagrams',()=>{
  const model=reservationSystemModel();
  const project={nodes:[block('Ledger')],edges:[]};
  const view=systemModelOnBoard(model,project);
  assert.deepEqual(view.diagrams.find(row=>row.kind==='components').elementIds,['clerk','ledger']);
  assert.deepEqual(view.diagrams.find(row=>row.kind==='functions').elementIds,['receive']);
  assert.deepEqual(view.diagrams.find(row=>row.id==='scenario').exchangeIds,['submit']);
  assert.equal(view.diagrams.some(row=>row.id==='retry'),false);
  assert.equal(view.elements.some(row=>row.id==='allocate-in'),false);
  assert.ok(model.elements.some(row=>row.id==='allocator'));
  assert.equal(systemModelOnBoard(model,{nodes:draft.addNodes,edges:draft.addEdges}),model);
});

test('an empty manual diagram can be saved while generated models must meet completeness checks',()=>{
  const model={format:'atmem.system-model',version:1,id:'draft',authoring:'manual',elements:[],exchanges:[],diagrams:[
    {id:'first-diagram',name:'First diagram',kind:'components',elementIds:[],exchangeIds:[]},
  ]};
  const saved=parseProjectFile(JSON.stringify(toProjectFile({...base,extensions:{systemModel:model}}))).project;
  assert.deepEqual(saved.extensions.systemModel,model);
  assert.throws(()=>capture(model),/collection bounds/);
});

test('remove from one view preserves shared records, while explicit deletion removes incident ports and exchanges',()=>{
  const model={...reservationSystemModel(),authoring:'manual'};
  model.diagrams[0].positions={allocator:{x:100,y:90}};
  const hidden=validateSystemModel(removeModelRecord(model,'allocator','logical'));
  assert.equal(hidden.diagrams[0].elementIds.includes('allocator'),false);
  assert.deepEqual(hidden.diagrams[0].positions,{});
  assert.equal(hidden.diagrams[2].elementIds.includes('allocator'),true);
  assert.ok(hidden.exchanges.some(row=>row.id==='reserve-item'));
  const removed=validateSystemModel(removeModelRecord(model,'allocator'));
  assert.ok(removed.diagrams.every(row=>!row.elementIds.includes('allocator')&&!row.exchangeIds.includes('reserve-item')));
  assert.equal(removed.elements.some(row=>row.id==='allocator-in'),false);
  assert.equal(removed.elements.find(row=>row.id==='allocate').allocatedTo,undefined);
  assert.equal(removed.exchanges.find(row=>row.id==='verified-request').componentExchangeId,undefined);
});

test('AI refinement keeps manual placements in the matching view',()=>{
  const prior=reservationSystemModel();
  prior.diagrams[0].positions={allocator:{x:45,y:180}};
  const next=reservationSystemModel();
  next.diagrams[0].name='Refined components';
  const refined=reconcileSystemModel(prior,next);
  assert.deepEqual(refined.diagrams[0].positions,prior.diagrams[0].positions);
  assert.equal(refined.diagrams[0].name,'Refined components');
  assert.equal(next.diagrams[0].positions,undefined);
});
