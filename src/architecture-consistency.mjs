import {systemModelIndex} from './system-model.mjs';
import {verificationReferenceIssues} from './verification-cases.mjs';
// Deterministic reference checks, independent of diagram rendering and model judgments.
// No label matching, protocol inference, domain routing or invented links.
export function architectureConsistency(project){
 const nodes=new Map(project.nodes.filter(node=>node.data.kind!=='note').map(node=>[node.id,node]));
 const edges=new Map(project.edges.map(edge=>[edge.id,edge]));
 const operations=new Map((project.extensions?.engineeringModel?.elements||[]).flatMap(element=>(element.operations||[]).map(operation=>[operation.id,{element,operation}])));
 const operationOwners=new Set([...operations.values()].map(row=>row.element.blockId).filter(Boolean));
 const requirements=new Map((project.needs||[]).map(row=>[row.id,row]));
 const issues=[],traced=new Set();let interactions=0,classified=0,bound=0,operationBound=0;
 const issue=(code,severity,location,message,ref)=>issues.push({code,severity,...location,message,...(ref?{ref}:{})});
 for(const element of project.extensions?.engineeringModel?.elements||[]){
  const location={modelElementId:element.id,blockId:element.blockId};
  if(element.blockId&&!nodes.has(element.blockId))issue('model_block_missing','error',location,'Engineering model element references a missing block.',element.blockId);
  for(const ref of element.requirementIds||[])if(!requirements.has(ref))issue('model_requirement_missing','error',location,'Engineering model element references a missing requirement.',ref);
 }
 const systemModel=project.extensions?.systemModel;
 if(systemModel){
  const index=systemModelIndex(systemModel);
  for(const record of [...systemModel.elements,...systemModel.exchanges]){
   const location={modelElementId:record.id,blockId:record.blockId};
   if(record.blockId&&!nodes.has(record.blockId))issue('model_block_missing','error',location,'System model component references a missing block.',record.blockId);
   for(const ref of record.requirementIds)if(!requirements.has(ref))issue('model_requirement_missing','error',location,'System model record references a missing requirement.',ref);
   if(record.interfaceId){
    const edge=edges.get(record.interfaceId);
    const [source,target]=index.participants(record).map(id=>index.elements.get(id).blockId);
    if(!edge||edge.source!==source||edge.target!==target)issue('model_interface_missing','error',location,'System model exchange needs a matching interface.',record.interfaceId);
   }
  }
 }
 issues.push(...verificationReferenceIssues(project));
 for(const [id,row]of requirements){
  if(!row.links?.length)issue('requirement_unallocated','review',{requirementId:id},'Allocate this requirement to responsible blocks.');
  for(const ref of row.links||[])if(!nodes.has(ref))issue('requirement_block_missing','error',{requirementId:id},'Requirement references an unknown block.',ref);
 }
 const journeys=[...project.nodes.flatMap(node=>(node.data.buildSpec?.scenarios||[]).map((scenario,index)=>({scenario,blockId:node.id,index}))),...(project.extensions?.systemSpec?.journeys||[]).map((scenario,index)=>({scenario,blockId:null,index}))];
 for(const {scenario,blockId,index}of journeys)for(const [stepIndex,step]of scenario.steps.entries()){
  interactions++;const location={blockId,journeyIndex:index,journey:scenario.name,stepIndex,participantBlockIds:[step.senderBlockId,step.receiverBlockId].filter(Boolean)};
  if(step.operationId){
   const target=operations.get(step.operationId),owner=step.messageKind==='result'?step.senderBlockId:step.receiverBlockId;
   if(!target)issue('operation_missing','error',location,'Interaction references an unknown model operation.',step.operationId);
   else if(!step.messageKind||!owner||!target.element.blockId)issue('operation_owner_unbound','review',location,'Bind the operation owner and interaction direction.',step.operationId);
   else if(owner!==target.element.blockId)issue('operation_owner_mismatch','error',location,'Operation owner contradicts the receiving module; results originate from the operation owner.',step.operationId);
   else operationBound++;
  }
  if(step.messageKind)classified++;else issue('message_unclassified','review',location,'Review whether this interaction is a command, event, query or result.');
  for(const key of ['senderBlockId','receiverBlockId'])if(step[key]&&!nodes.has(step[key]))issue('participant_block_missing','error',location,'Participant references an unknown block.',step[key]);
  if(!step.senderBlockId||!step.receiverBlockId)issue('participant_unbound','review',location,'Bind participants to blocks, or review the external actor boundary.');
  const edge=step.interfaceId?edges.get(step.interfaceId):null;
  if(step.interfaceId&&!edge)issue('interface_missing','error',location,'Interaction references an unknown interface.',step.interfaceId);
  if(edge){
   if(!edge.interfaceSpec)issue('interface_undeclared','review',location,'Define the referenced interface contract.',edge.id);
   if(step.senderBlockId&&step.receiverBlockId&&step.messageKind){
    const reverse=step.messageKind==='result',from=reverse?edge.target:edge.source,to=reverse?edge.source:edge.target;
    if(step.senderBlockId!==from||step.receiverBlockId!==to)issue('interface_direction_mismatch','error',location,'Participant direction contradicts this interface; results reverse its request direction.',edge.id);
    else bound++;
   }
  }else if(!step.interfaceId&&step.senderBlockId&&step.receiverBlockId&&step.senderBlockId!==step.receiverBlockId)issue('interaction_interface_unbound','review',location,'Bind this cross-block interaction to its declared interface.');
  if(!step.requirementIds?.length)issue('interaction_requirement_unbound','review',location,'Trace this interaction to its requirement IDs.');
  for(const ref of step.requirementIds||[])if(!requirements.has(ref))issue('interaction_requirement_missing','error',location,'Interaction references an unknown requirement.',ref);else traced.add(ref);
 }
 for(const {scenario,blockId,index}of journeys){
  const missing=scenario.steps.map((step,i)=>({step,i})).filter(({step})=>!step.operationId&&['command','query'].includes(step.messageKind)&&operationOwners.has(step.receiverBlockId));
  if(missing.length)issue('journey_operations_unbound','review',{blockId,journeyIndex:index,journey:scenario.name,stepIndices:missing.map(row=>row.i)},'Link modeled calls to their class operations; labels alone do not bind behavior.');
 }
 for(const id of requirements.keys())if(!traced.has(id))issue('requirement_journey_untraced','review',{requirementId:id},'No interaction explicitly traces this requirement; review behavior or nonfunctional acceptance coverage.');
 for(const [index,machine]of (project.extensions?.systemSpec?.stateMachines||[]).entries()){
  const reachable=new Set([machine.initial]);let changed=true;
  while(changed){changed=false;for(const step of machine.transitions)if(reachable.has(step.from)&&!reachable.has(step.to)){reachable.add(step.to);changed=true;}}
  for(const state of machine.states)if(!reachable.has(state))issue('state_unreachable','review',{stateMachine:index},'State is unreachable from the declared initial state.',state);
 }
 const counts={interactions,classified,interfaceBound:bound,operationBound,requirements:requirements.size,explicitlyTracedRequirements:traced.size,errors:issues.filter(row=>row.severity==='error').length,review:issues.filter(row=>row.severity==='review').length};
 return {version:1,status:counts.errors?'inconsistent':counts.review?'needs_review':'consistent_references',counts,issues,boundary:'Static reference and direction checks only. No proof of source interpretation, causal correctness, test execution or deployment.'};
}
