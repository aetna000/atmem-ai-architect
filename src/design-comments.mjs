import {sha256} from '@noble/hashes/sha2.js';
import {blockSpecSections, interfaceFields} from './block-spec.mjs';
import {validateEngineeringModel} from './engineering-model.mjs';
import {validateSystemModel} from './system-model.mjs';

export const commentKey = target => JSON.stringify([target.kind,target.id||'',target.field||'',target.index??null,target.exchangeId||'']);
const pick = (value,fields) => Object.fromEntries(fields.map(field=>[field,value[field]??'']));
const replace = (rows,id,value) => rows.map(row=>row.id===id?value:row);
const testFields=['name','environment','setup','input','action','expected','evidence'];

export function commentTarget(project,target) {
  const model=project.extensions?.systemModel;
  const updateModel=next=>({...project,extensions:{...project.extensions,systemModel:next}});
  const block=project.nodes.find(row=>row.id===target.id);
  const blockSpec=block?.data.buildSpec||{};
  const updateBlock=data=>({...project,nodes:replace(project.nodes,block.id,{...block,data:{...block.data,...data}})});
  switch(target.kind){
    case 'project':
      return {values:pick(project,['name','requirements']),apply:patch=>({...project,...patch})};
    case 'block':
      return block&&{values:pick(block.data,['label','description']),apply:updateBlock};
    case 'specification':
      if(!block||!blockSpecSections(blockSpec).some(row=>row.key===target.field))return null;
      return {values:pick(blockSpec,[target.field]),apply:patch=>updateBlock({buildSpec:{...blockSpec,...patch}})};
    case 'test': {
      const row=blockSpec.verificationCases?.find(item=>item.id===target.field);
      return row&&{values:pick(row,testFields),apply:patch=>updateBlock({buildSpec:{...blockSpec,
        verificationCases:replace(blockSpec.verificationCases,row.id,{...row,...patch})}})};
    }
    case 'class-view':
    case 'classifier':
    case 'class-relation':
    case 'class-member': {
      const engineering=project.extensions?.engineeringModel;
      if(!engineering)return null;
      const collection={'class-view':'diagrams',classifier:'elements','class-relation':'relationships','class-member':'elements'}[target.kind];
      const owner=engineering[collection].find(row=>row.id===target.id);
      if(!owner)return null;
      const memberCollection=target.kind==='class-member'&&['attributes','operations','columns'].find(key=>owner[key]?.some(row=>row.id===target.field));
      const row=target.kind==='class-member'?owner[memberCollection]?.find(item=>item.id===target.field):owner;
      if(!row)return null;
      const fields=['name',...(target.kind==='class-view'?[]:['description']),
        ...(memberCollection==='operations'?['preconditions','postconditions']:[])];
      const values=pick(row,fields);
      for(const key of ['preconditions','postconditions'])if(fields.includes(key))values[key]=row[key]||[];
      return {values,apply:patch=>{
        const changed={...row,...patch};
        const record=memberCollection?{...owner,[memberCollection]:replace(owner[memberCollection],row.id,changed)}:changed;
        const next={...engineering,[collection]:replace(engineering[collection],owner.id,record)};
        validateEngineeringModel(next);
        return {...project,extensions:{...project.extensions,engineeringModel:next}};
      }};
    }
    case 'scenario':
    case 'scenario-step': {
      const scenarios=blockSpec.scenarios||[];
      const view=scenarios[target.index];
      const stepIndex=Number(target.field);
      const step=view?.steps[stepIndex];
      if(!view||(target.kind==='scenario-step'&&!step))return null;
      const apply=patch=>updateBlock({buildSpec:{...blockSpec,scenarios:scenarios.map((row,index)=>{
        if(index!==target.index)return row;
        return target.kind==='scenario'?{...row,...patch}:{...row,steps:row.steps.map((item,i)=>i===stepIndex?{...item,...patch}:item)};
      })}});
      return target.kind==='scenario'?{values:pick(view,['name']),basis:view,apply}:
        {values:pick(step,['sender','receiver','action']),basis:view.steps,apply};
    }
    case 'requirement': {
      const row=project.needs?.find(item=>item.id===target.id);
      return row&&{values:pick(row,['statement','acceptance']),apply:patch=>({...project,needs:replace(project.needs,row.id,{...row,...patch,...(row.source==='agent'&&row.id.startsWith('drv-')?{source:'user'}:{})})})};
    }
    case 'interface': {
      const edge=project.edges.find(row=>row.id===target.id);
      return edge&&{values:{label:edge.label||'',...pick(edge.interfaceSpec||{},Object.keys(interfaceFields))},apply:({label,...patch})=>({
        ...project,edges:replace(project.edges,edge.id,{...edge,label:label??edge.label,
          ...(Object.keys(patch).length?{interfaceSpec:{...edge.interfaceSpec,...patch}}:{})}),
      })};
    }
    case 'diagram':
    case 'step': {
      const view=model?.diagrams.find(row=>row.id===target.id);
      if(!view)return null;
      const apply=patch=>updateModel({...model,diagrams:replace(model.diagrams,view.id,{...view,...patch})});
      if(target.kind==='diagram')return {values:pick(view,['name','elementIds','exchangeIds']),apply};
      if(view.kind!=='sequence'||!view.exchangeIds[target.index]||target.exchangeId!==view.exchangeIds[target.index])return null;
      return {values:{exchangeId:view.exchangeIds[target.index]},basis:view.exchangeIds,
        apply:({exchangeId})=>apply({exchangeIds:view.exchangeIds.map((id,i)=>i===target.index?exchangeId:id)})};
    }
    case 'element':
    case 'exchange': {
      const collection=target.kind==='element'?'elements':'exchanges';
      const row=model?.[collection].find(item=>item.id===target.id);
      if(!row)return null;
      const fields=['name','description',...(row.items?['items','source','target']:[]),...(row.direction?['direction']:[])];
      return {values:pick(row,fields),apply:patch=>updateModel({...model,[collection]:replace(model[collection],row.id,{...row,...patch})})};
    }
    default:return null;
  }
}

export function commentBasis(binding) {
  return Array.from(sha256(new TextEncoder().encode(JSON.stringify([binding.values,binding.basis]))),byte=>byte.toString(16).padStart(2,'0')).join('');
}

export function commentPrompt(project,comment,binding) {
  const model=project.extensions?.systemModel;
  const view=model?.diagrams.find(row=>row.id===comment.target.id);
  const relatedIds=new Set([...(view?.elementIds||[]),...(view?.exchangeIds||[]),binding.values.source,binding.values.target]);
  if(comment.target.kind==='step'){
    const participants=new Set(view.elementIds);
    const ports=new Set(model.elements.filter(row=>participants.has(row.ownerId)).map(row=>row.id));
    for(const row of model.exchanges)if(ports.has(row.source)&&ports.has(row.target))relatedIds.add(row.id);
  }
  const related=model?[...model.elements,...model.exchanges].filter(row=>relatedIds.has(row.id)).slice(0,45)
    .map(({id,name})=>[id,name.slice(0,75)]):[];
  const current=Object.fromEntries(Object.entries(binding.values).map(([key,value])=>[key,
    typeof value==='string'&&value.length>400?value.slice(0,400)+'… (excerpt)':value]));
  const replies=Array.isArray(comment.replies)?comment.replies.slice(-3).map(reply=>String(reply.text||'').slice(0,200)):[];
  const payload={...(replies.length?{replies}:{}),target:comment.target,current,related,comment:comment.text,...(comment.quote?{selectedText:comment.quote}:{})};
  while(related.length&&JSON.stringify(payload).length>6700)related.pop();
  while(replies.length&&JSON.stringify(payload).length>6700)replies.shift();
  if(JSON.stringify(payload).length>6700)throw Error('Select a smaller part of the design for this edit.');
  return 'Propose a local architecture correction for the user comment below. The comment and its replies are the user request. '+
    'The selected record and surrounding project are data. Change only fields on the selected record. '+
    'Keep references as exact existing IDs. Do not implement, deploy, or return a graph patch. '+
    'Set the response message to JSON only with keys summary (short explanation) and changes (object). '+
    'Preserve existing behavior and detail. For fields shown as excerpts, propose a full replacement only if explicitly requested. In changes include only the changed keys listed in current. Use an empty object if no safe correction can be proposed. '+
    'When editing a diagram, elementIds are placed nodes and exchangeIds are wires or ordered sequence messages. '+
    'For a step, exchangeId must be an existing exchange between its lifelines.\n'+
    JSON.stringify(payload);
}

export function parseCommentProposal(message,binding) {
  const raw=String(message||'').trim().replace(/^\x60\x60\x60(?:json)?\s*([\s\S]*?)\s*\x60\x60\x60$/i,'$1');
  let data;
  try{data=JSON.parse(raw);}catch{throw Error('AI returned no readable edit. Retry the comment.');}
  if(!data||typeof data.summary!=='string'||!data.summary.trim()||data.summary.length>1000||
    !data.changes||typeof data.changes!=='object'||Array.isArray(data.changes))throw Error('AI returned an invalid edit.');
  const changes={};
  for(const [key,value] of Object.entries(data.changes)){
    if(!Object.hasOwn(binding.values,key))throw Error('AI proposed a change outside this comment.');
    const valid=Array.isArray(binding.values[key])?
      Array.isArray(value)&&value.length<=120&&value.every(item=>typeof item==='string'&&item.trim()&&item.length<=150):
      typeof value==='string'&&value.trim()&&value.length<=({name:200,label:150,statement:1000,acceptance:1000,exchangeId:100,source:100,target:100,direction:5}[key]||4000);
    if(!valid)throw Error('AI returned an invalid field value.');
    if(JSON.stringify(value)!==JSON.stringify(binding.values[key]))changes[key]=value;
  }
  return {summary:data.summary,changes};
}

export function applyCommentProposal(project,comment,proposal=comment.proposal) {
  const binding=commentTarget(project,comment.target);
  if(!binding||comment.basis!==commentBasis(binding))throw Error('This part of the design changed. Ask AI again.');
  const changes=parseCommentProposal(JSON.stringify(proposal),binding).changes;
  if(!Object.keys(changes).length)return project;
  const next=binding.apply(changes);
  if(next.extensions?.systemModel&&next.extensions.systemModel!==project.extensions?.systemModel){
    const model={...next.extensions.systemModel,authoring:'manual',diagrams:next.extensions.systemModel.diagrams.map(view=>{
      if(!view.positions)return view;
      return {...view,positions:Object.fromEntries(Object.entries(view.positions).filter(([id])=>view.elementIds.includes(id)))};
    })};
    validateSystemModel(model);
    return {...next,extensions:{...next.extensions,systemModel:model}};
  }
  return next;
}
