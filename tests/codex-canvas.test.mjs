import test from 'node:test';
import assert from 'node:assert/strict';
import {zipSync,strToU8} from 'fflate';
import {canvasProposal,canvasBasis,CANVAS_ARTIFACT} from '../src/codex-canvas.mjs';

const digest='9'.repeat(64);
const base={id:'ticketing',version:1,revision:2,name:'Ticketing',provider:'tools',nodes:[],edges:[],
  extensions:{designSources:[{name:'Theatre brief.txt',sha256:digest,text:'Section 1. Hold one seat at a time.'}]}};
const block=(id,data={})=>({id,type:'resource',position:{x:0,y:0},
  data:{label:id,kind:'resource',provider:'tools',origin:'proposed',...data}});
const draft={version:1,baseRevision:2,title:'Seat inventory',sourceDigests:[digest],
  addNodes:[block('inventory'),block('holds',{parentBlockId:'inventory',buildSpec:{tests:'Concurrent hold race.'}})],addEdges:[],
  requirements:[{id:'hold-once',statement:'Allocate at most one seat hold.',sourceSha256:digest,reference:'Section 1',links:['holds']}],
  questions:[{id:'q-timeout',question:'What happens if checkout runs past expiry?',links:['holds']}]};
const pack=(value)=>zipSync({[CANVAS_ARTIFACT]:strToU8(JSON.stringify(value))});

test('Codex output maps a captured nested design, source links and questions without mutating the board',()=>{
  const proposal=canvasProposal(base,pack(draft),'artifact');
  assert.equal(proposal.sourceBasis,canvasBasis(base));
  assert.equal(proposal.next.nodes[1].data.parentBlockId,'inventory');
  assert.match(proposal.sourceRequirements[0].basis,/Theatre brief.txt · Section 1/);
  assert.deepEqual(proposal.sourceQuestions[0].links,['holds']);
  assert.equal(base.nodes.length,0);
});

test('Codex canvas rejects stale, overlapping and untraced proposals',()=>{
  assert.throws(()=>canvasProposal({...base,revision:3},pack(draft),'artifact'),/changed/);
  assert.throws(()=>canvasProposal(base,pack({...draft,sourceDigests:['0'.repeat(64)]}),'artifact'),/changed/);
  assert.throws(()=>canvasProposal({...base,nodes:[block('inventory')]},pack(draft),'artifact'),/Invalid component/);
  assert.throws(()=>canvasProposal(base,pack({...draft,requirements:[{...draft.requirements[0],links:['missing']}]}),'artifact'),/responsible blocks/);
  assert.throws(()=>canvasProposal(base,zipSync({'README.md':strToU8('Design')}),'artifact'),/did not capture/);
});

import {sha256} from '@noble/hashes/sha2.js';
import {systemSpecFiles} from '../src/canvas-quality.mjs';
test('readiness binds the review and renders operational behavior from the same model',()=>{
  const step={sender:'Box office',receiver:'Hold ledger',action:'Request numbered seat'};
  const spec={title:'Ticketing',decomposition:'Seat and queue components',infrastructure:'Portable site or cloud',
    operations:'Backups and restore',testing:'Concurrent hold and timeout',journeys:[{name:'Reserve',steps:[step]},{name:'Recover',steps:[step]}],
    stateMachines:[{name:'Hold',states:['Open','Held'],initial:'Open',transitions:[{from:'Open',to:'Held',event:'Seat held'}]}],
    deploymentUnits:[{name:'Local runtime',placement:'site',blocks:['holds','inventory']}]};
  const filled={inputs:'Stable request',outputs:'Hold receipt',behavior:'Single active hold',failures:'Recover existing outcome',
    implementation:'Hold ledger command',infrastructure:'Transactional store',operations:'Replay audit',tests:'Race the last seat',scenarios:spec.journeys};
  const value={...draft,systemSpec:spec,addNodes:[block('inventory',{buildSpec:filled}),block('holds',{buildSpec:filled,parentBlockId:'inventory'})],
    addEdges:[{id:'call',source:'inventory',target:'holds',interfaceSpec:{transport:'Local call',input:'Seat',output:'Hold',
      authorization:'Staff',failure:'Replay prior receipt',verification:'Simulate timeout'}}],
    requirements:[{...draft.requirements[0],kind:'nonfunctional',priority:'must',acceptance:'At most one winning hold'}]};
  const bytes=strToU8(JSON.stringify(value));
  const digest=Array.from(sha256(bytes),byte=>byte.toString(16).padStart(2,'0')).join('');
  const archive=review=>zipSync({[CANVAS_ARTIFACT]:bytes,'architecture.review.md':strToU8(review)});
  const proposal=canvasProposal(base,archive(`Draft SHA-256: ${digest}\nChecked original sections.`),'artifact');
  assert.equal(proposal.quality.score,100);
  assert.equal(proposal.quality.ready,true);
  assert.equal(canvasProposal(base,archive('Unbound review'),'artifact').quality.ready,false);
  const figureSource={...base.extensions.designSources[0],graphics:['diagram.png'],figureEvidence:{manifestSha256:'f'.repeat(64),figures:[{id:'figure-1',sha256:'e'.repeat(64),status:'available'}]}};
  const illustrated={...base,extensions:{designSources:[figureSource]}};
  const receipt={artifactId:'artifact',contextSha256:'b'.repeat(64),deliveries:[{
    sourceSha256:figureSource.sha256,manifestSha256:figureSource.figureEvidence.manifestSha256,figureId:'figure-1',sha256:'e'.repeat(64)}]};
  const reviewed=archive(`Draft SHA-256: ${digest}\nChecked original sections.`);
  assert.equal(canvasProposal(illustrated,reviewed,'artifact','b'.repeat(64)).quality.ready,false);
  assert.equal(canvasProposal(illustrated,reviewed,'artifact','b'.repeat(64),receipt).quality.ready,true);
  assert.equal(canvasProposal(illustrated,reviewed,'artifact','b'.repeat(64),{...receipt,artifactId:'other'}).quality.ready,false);
  assert.equal(canvasProposal(illustrated,reviewed,'artifact','b'.repeat(64),{...receipt,deliveries:[{...receipt.deliveries[0],sha256:'0'.repeat(64)}]}).quality.ready,false);
  assert.equal(canvasProposal({...base,extensions:{designSources:[{...figureSource,figureEvidence:undefined}]}},reviewed,'artifact','b'.repeat(64),receipt).quality.ready,false);
  const files=systemSpecFiles({...proposal.next,extensions:{systemSpec:proposal.systemSpec,architectureDraftQuality:proposal.quality}},'fixture');
  assert.match(files['spec-kit/system/lifecycle-1.mmd'],/state0 --> state1: Seat held/);
  assert.match(files['spec-kit/system/deployment.mmd'],/Local runtime/);
  assert.match(files['spec-kit/system/1-events.mmd'],/event0/);
});

test('native source slots require the verified capture context and receive exact host hashes',()=>{
 const {sourceDigests,requirements,...rest}=draft;
 const {sourceSha256,...requirement}=requirements[0];
 const value={...rest,sourceSlots:[1],requirements:[{...requirement,sourceSlot:1}]};
 assert.throws(()=>canvasProposal(base,pack(value),'artifact'),/source documents changed/);
 const proposal=canvasProposal(base,pack(value),'artifact','b'.repeat(64));
 assert.match(proposal.sourceRequirements[0].basis,new RegExp(digest));
 assert.equal(proposal.quality.contextSha256,'b'.repeat(64));
 assert.throws(()=>canvasProposal(base,pack({...value,requirements:[{...requirement,sourceSlot:2}]}),'artifact','b'.repeat(64)),/source reference/);
});

import {canvasProposalRecords} from '../src/codex-canvas.mjs';
import {toProjectFile,parseProjectFile} from '../src/project-file.mjs';
const seatModel=()=>({format:'atmem.engineering-model',version:1,id:'seat-model',name:'Seat hold model',elements:[
 {id:'seat-id',name:'SeatIdentifier',kind:'dataType',basis:'proposed'},
 {id:'hold',name:'SeatHold',kind:'class',basis:'proposed',blockId:'holds',requirementIds:['hold-once'],description:'Owns the exclusive hold of an identified seat.',attributes:[{id:'hold-seat',name:'seat',typeRef:'seat-id',visibility:'private'}]},
 {id:'hold-record',name:'HoldRecord',kind:'entity',basis:'proposed',blockId:'holds',columns:[{id:'record-seat',name:'seatId',typeRef:'seat-id',nullable:false}],primaryKey:['record-seat']}
 ],relationships:[{id:'hold-storage',name:'Persists exclusive identity',kind:'mapping',source:'hold',target:'hold-record'}],diagrams:[
 {id:'hold-class',name:'Hold responsibility',kind:'class',placements:[{elementId:'hold',x:0,y:0}],relationships:[]},
 {id:'hold-schema',name:'Hold data identity',kind:'schema',placements:[{elementId:'hold-record',x:0,y:0}],relationships:[]}
 ]});
const applied=(project,proposal)=>({...proposal.next,...canvasProposalRecords(project,proposal),revision:project.revision+1});
test('captured typed model applies with newly traced requirements and survives normal project reopen',()=>{
 const model=seatModel(),proposal=canvasProposal(base,pack({...draft,engineeringModel:model}),'typed-artifact');
 assert.deepEqual(proposal.engineeringModel,model);
 const current=applied(base,proposal);
 assert.deepEqual(parseProjectFile(JSON.stringify(toProjectFile(current))).project.extensions.engineeringModel,model);
 assert.ok(proposal.amendmentHistory.at(-1).changes.some(change=>change.kind==='engineeringModel'));
 assert.equal(base.extensions.engineeringModel,undefined);
 const changed=structuredClone(current);changed.extensions.engineeringModel.elements[1].description='Changed responsibility';
 assert.notEqual(canvasBasis(current),canvasBasis(changed));
});
test('captured model cannot invent block/requirement references, approval or clear existing detail',()=>{
 for(const mutate of [m=>m.elements[1].blockId='missing',m=>m.elements[1].requirementIds=['missing'],m=>m.elements[1].basis='accepted']){
  const model=seatModel();mutate(model);assert.throws(()=>canvasProposal(base,pack({...draft,engineeringModel:model}),'invalid'),/Engineering model:/);
 }
 const current=applied(base,canvasProposal(base,pack({...draft,engineeringModel:seatModel()}),'original'));
 const next={version:1,baseRevision:current.revision,title:current.name,sourceDigests:[digest],addNodes:[],addEdges:[],requirements:[],requirementCoverage:[{id:'hold-once',sourceSha256:digest,reference:'Section 1',links:['holds']}]};
 assert.deepEqual(canvasProposal(current,pack(next),'preserved').engineeringModel,current.extensions.engineeringModel);
 assert.throws(()=>canvasProposal(current,pack({...next,engineeringModel:null}),'cleared'),/cannot clear/);
 const removed=seatModel();removed.elements[1].attributes=[];
 assert.throws(()=>canvasProposal(current,pack({...next,engineeringModel:removed}),'dropped-member'),/cannot remove semantic identity/);
 const accepted=structuredClone(current);accepted.extensions.engineeringModel.elements[1].basis='accepted';
 const amended=structuredClone(accepted.extensions.engineeringModel);amended.elements[1].description='Rewrite accepted behavior';
 assert.throws(()=>canvasProposal(accepted,pack({...next,engineeringModel:amended}),'rewrite'),/accepted elements/);
 const reconnected=structuredClone(accepted.extensions.engineeringModel);reconnected.relationships[0].name='Changed storage obligation';
 assert.throws(()=>canvasProposal(accepted,pack({...next,engineeringModel:reconnected}),'rewrite-relation'),/relationships of accepted elements/);
});

test('captured behavior operation references use the proposed model when evaluating acceptance',()=>{
 const model=seatModel();model.elements[1].operations=[{id:'hold-request',name:'requestHold',parameters:[]}];
 const step={sender:'Inventory',receiver:'Hold owner',action:'Request hold',messageKind:'command',senderBlockId:'inventory',receiverBlockId:'holds',operationId:'hold-request',requirementIds:['hold-once']};
 const value={...draft,engineeringModel:model,addNodes:[draft.addNodes[0],{...draft.addNodes[1],data:{...draft.addNodes[1].data,buildSpec:{scenarios:[{name:'Hold request',steps:[step]}]}}}]};
 const valid=canvasProposal(base,pack(value),'bound');assert.equal(valid.quality.behaviorConsistency.errors.length,0);
 value.addNodes[1].data.buildSpec.scenarios[0].steps[0].operationId='invented';const invalid=canvasProposal(base,pack(value),'unbound');assert.equal(invalid.quality.ready,false);assert.ok(invalid.quality.behaviorConsistency.errors.some(r=>r.code==='operation_missing'));
});
