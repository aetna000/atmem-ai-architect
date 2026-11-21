import {architectureQuality} from '../src/canvas-quality.mjs';
import {createBlockHandoff} from '../src/block-handoff.mjs';
import test from 'node:test';import assert from 'node:assert/strict';
import {architectureConsistency} from '../src/architecture-consistency.mjs';
import {scenarioDiagrams,validateScenarios} from '../src/block-spec.mjs';
import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';
const contract={transport:'RPC v1',input:'Request',output:'Receipt',authorization:'Operator',failure:'Read before retry',verification:'Duplicate request'};
function project(){
 const steps=[{sender:'Client role',receiver:'Journal role',action:'Record entry',messageKind:'command',senderBlockId:'client',receiverBlockId:'journal',interfaceId:'record',requirementIds:['once']},{sender:'Journal role',receiver:'Client role',action:'Entry receipt',messageKind:'result',senderBlockId:'journal',receiverBlockId:'client',interfaceId:'record',requirementIds:['once']}];
 return {id:'research',name:'Research journal',revision:1,version:1,provider:'tools',nodes:[{id:'client',type:'resource',position:{x:0,y:0},data:{label:'Portal',kind:'resource',provider:'tools',origin:'proposed'}},{id:'journal',type:'resource',position:{x:0,y:0},data:{label:'Journal',kind:'resource',provider:'tools',origin:'proposed',buildSpec:{behavior:'Record once',scenarios:[{name:'Record',steps}]}}}],edges:[{id:'record',source:'client',target:'journal',label:'Record',interfaceSpec:contract}],needs:[{id:'once',statement:'Record each request once.',links:['journal']}]};
}
test('explicit behavior bindings survive file round trip and requests/results share a directional contract',()=>{
 const raw=project(),reopened=fromProjectFile(toProjectFile(raw)).project;
 assert.deepEqual(reopened.nodes[1].data.buildSpec,raw.nodes[1].data.buildSpec);
 const report=architectureConsistency(reopened);assert.equal(report.status,'consistent_references');assert.equal(report.counts.interfaceBound,2);assert.equal(report.counts.explicitlyTracedRequirements,1);
 const diagrams=scenarioDiagrams(raw.nodes[1].data.buildSpec.scenarios[0]);assert.match(diagrams.sequence,/-->>/);assert.match(diagrams.sequence,/command#58; Record entry/);assert.doesNotMatch(diagrams.events,/\{\{/);
});
test('classification does not infer a completed event from a command or a legacy action name',()=>{
 const scenario={name:'Lab',steps:[{sender:'Lab',receiver:'Archive',action:'SpecimenAccepted'},{sender:'Lab',receiver:'Archive',action:'Archive specimen',messageKind:'command'},{sender:'Archive',receiver:'Lab',action:'Archived',messageKind:'event'}]};
 validateScenarios([scenario]);const diagram=scenarioDiagrams(scenario).events;
 assert.match(diagram,/event0\["Unclassified interaction#58; SpecimenAccepted"\]/);assert.match(diagram,/event1\["command#58; Archive specimen"\]/);assert.match(diagram,/event2\{\{"event#58; Archived"\}\}/);
 const legacy=project();delete legacy.nodes[1].data.buildSpec.scenarios[0].steps[0].messageKind;assert.ok(architectureConsistency(legacy).issues.some(row=>row.code==='message_unclassified'));
});
test('wrong interface direction, unknown participant and false requirement IDs remain actionable errors',()=>{
 for(const [change,code]of [[{senderBlockId:'journal'},'interface_direction_mismatch'],[{receiverBlockId:'missing'},'participant_block_missing'],[{interfaceId:'invented'},'interface_missing'],[{requirementIds:['fake']},'interaction_requirement_missing']]){
  const raw=project();Object.assign(raw.nodes[1].data.buildSpec.scenarios[0].steps[0],change);const report=architectureConsistency(raw);assert.equal(report.status,'inconsistent');assert.ok(report.issues.some(row=>row.code===code));
 }
});
test('legacy missing links and unreachable lifecycle state request review without inventing references',()=>{
 const raw=project();const step=raw.nodes[1].data.buildSpec.scenarios[0].steps[0];delete step.interfaceId;delete step.requirementIds;
 raw.extensions={systemSpec:{stateMachines:[{initial:'Open',states:['Open','Held','Lost'],transitions:[{from:'Open',to:'Held',event:'Held'}]}]}};
 const report=architectureConsistency(raw);assert.equal(report.status,'needs_review');assert.ok(report.issues.some(row=>row.code==='interaction_interface_unbound'));assert.ok(report.issues.some(row=>row.code==='state_unreachable'&&row.ref==='Lost'));
 assert.throws(()=>validateScenarios([{name:'Invalid',steps:[{...step,messageKind:'guess'}]}]),/message kind/);
 assert.throws(()=>validateScenarios([{name:'Invalid',steps:[{...step,requirementIds:['once','once']}]}]),/unique/);
});

test('contradictory behavior bindings block structural acceptance and remain explicit in external handoffs',()=>{
 const raw=project(),draft={addNodes:raw.nodes,addEdges:raw.edges,requirements:raw.needs};
 assert.equal(architectureQuality(draft,[],true).gates.behaviorReferencesConsistent,true);
 raw.nodes[1].data.buildSpec.scenarios[0].steps[0].receiverBlockId='client';
 const quality=architectureQuality(draft,[],true);assert.equal(quality.gates.behaviorReferencesConsistent,false);assert.equal(quality.ready,false);assert.ok(quality.behaviorConsistency.errors.some(row=>row.code==='interface_direction_mismatch'));
 const handoff=createBlockHandoff(JSON.stringify(toProjectFile(raw)),'journal');
 const readiness=JSON.parse(handoff.files['handoff-readiness.json']);assert.equal(readiness.status,'inconsistent_design');assert.equal(readiness.behaviorConsistency.counts.errors,1);
 assert.match(handoff.files['AGENT_PROMPT.md'],/Resolve contradictory references/);
});

function modeledProject(){
 const p=project();p.extensions={engineeringModel:{format:'atmem.engineering-model',version:1,id:'journal-model',name:'Journal model',elements:[{id:'journal-service',name:'JournalService',kind:'class',basis:'proposed',blockId:'journal',operations:[{id:'record-operation',name:'record',parameters:[]}]}],relationships:[],diagrams:[{id:'journal-classes',name:'Journal responsibilities',kind:'class',placements:[{elementId:'journal-service',x:0,y:0}],relationships:[]}]}};
 for(const step of p.nodes[1].data.buildSpec.scenarios[0].steps)step.operationId='record-operation';return p;
}
test('sequence calls and reverse results bind to the same canonical class operation through reopen and handoff',()=>{
 const p=modeledProject(),reopened=fromProjectFile(toProjectFile(p)).project;
 assert.equal(architectureConsistency(reopened).counts.operationBound,2);
 assert.equal(architectureConsistency(reopened).status,'consistent_references');
 const h=createBlockHandoff(JSON.stringify(toProjectFile(reopened)),'journal');
 const key=Object.keys(h.files).find(p=>p.endsWith('/scenarios.md')&&p.startsWith('spec-kit/blocks/'));
 assert.match(h.files[key],/Model operation bindings/);assert.match(h.files[key],/1\. record-operation/);assert.match(h.files[key],/2\. record-operation/);
});
test('unknown operations and contradictory call/result ownership block structural acceptance',()=>{
 for(const mutate of [p=>p.nodes[1].data.buildSpec.scenarios[0].steps[0].operationId='invented',p=>p.extensions.engineeringModel.elements[0].blockId='client']){
  const p=modeledProject();mutate(p);const report=architectureConsistency(p);assert.equal(report.status,'inconsistent');assert.ok(report.issues.some(r=>['operation_missing','operation_owner_mismatch'].includes(r.code)));
  const quality=architectureQuality({addNodes:p.nodes,addEdges:p.edges,requirements:p.needs,engineeringModel:p.extensions.engineeringModel},[],true);assert.equal(quality.gates.behaviorReferencesConsistent,false);
 }
});
test('unbound modeled calls request review without guessing class operations from display labels',()=>{
 const p=modeledProject(),step=p.nodes[1].data.buildSpec.scenarios[0].steps[0];delete step.operationId;
 const before=structuredClone(p),report=architectureConsistency(p);assert.ok(report.issues.some(row=>row.code==='journey_operations_unbound'));assert.equal(report.counts.operationBound,1);assert.deepEqual(p,before);
 delete p.extensions;delete p.nodes[1].data.buildSpec.scenarios[0].steps[1].operationId;
 assert.ok(!architectureConsistency(p).issues.some(row=>row.code==='journey_operations_unbound'));
});

import {appliedQualityBasis}from '../src/canvas-quality.mjs';
test('editing a class operation invalidates the applied review basis even when canvas blocks stay unchanged',()=>{
 const p=modeledProject(),before=appliedQualityBasis(p);p.extensions.engineeringModel.elements[0].operations[0].name='recordRevision';assert.notEqual(appliedQualityBasis(p),before);
});
