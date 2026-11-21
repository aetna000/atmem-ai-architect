import {drawioShapes} from './drawio-model.mjs';
import catalogue from '../agent-skills/specialists/architecture-diagrams/catalog.json' with {type:'json'};
import dagre from 'dagre';
import fields from '../agent-skills/specialists/architecture-diagrams/notation-fields.json' with {type:'json'};

export const {elementFields,relationFields} = fields;

export const diagramCatalogue = catalogue;
export const diagramTypes = new Map(catalogue.map(type=>[type.id,type]));
export const diagramGroups = [...new Set(catalogue.map(type=>type.group))];
const elementKinds = new Set(catalogue.flatMap(type=>type.elements));
const relationKinds = new Set(catalogue.flatMap(type=>type.relations));
const safeId = /^[a-z][a-z0-9_-]{0,95}$/i;
const text = (value,max) => typeof value==='string' && !!value.trim() && value.length<=max;
const fail = message => { throw Error(message); };
const keys = (row, required, optional=[]) => {
  if(!row || typeof row!=='object' || Array.isArray(row) || required.some(key=>!Object.hasOwn(row,key)) ||
    Object.keys(row).some(key=>!required.includes(key)&&!optional.includes(key))) fail('Invalid diagram record.');
};
const list = (value, max) => {
  if(!Array.isArray(value)||value.length>max)fail('Diagram collection exceeds its limit.');
  return value;
};
const checkLabels = (values,max,length) => {
  if(list(values,max).some(value=>!text(value,length)))fail('Invalid diagram text.');
};

export const emptyDiagramModel = () => ({version:1,elements:[],relations:[],views:[]});
export const kindLabel = kind => kind.replaceAll('-',' ').replace(/^./,first=>first.toUpperCase());
export const diagramId = () => 'd-'+crypto.randomUUID();

export function validateDiagramModel(model,{complete=false}={}) {
  keys(model,['version','elements','relations','views']);
  if(model.version!==1)fail('Unsupported diagram model version.');
  const ids=new Map();
  function identity(row,location) {
    if(typeof row.id!=='string'||!safeId.test(row.id)||Object.hasOwn(Object.prototype,row.id))fail(location+'.id must start with a letter and contain at most 96 letters, digits, underscores or hyphens.');
    if(ids.has(row.id))fail(location+'.id duplicates '+ids.get(row.id)+'.id; element, relationship and page IDs must be globally unique.');
    if(!text(row.name,180))fail(location+'.name needs 1–180 characters.');
    ids.set(row.id,location);
  }
  function common(row,location) {
    identity(row,location);
    if(!['specified','proposed','manual','example'].includes(row.basis)||typeof row.source!=='string'||
       row.source.length>500||(row.basis==='specified'&&!row.source.trim()))fail('Specified records need a source reference.');
    if(!Array.isArray(row.details)||row.details.length>16)fail('Invalid diagram details.');
    const names=new Set();
    for(const detail of row.details) {
      keys(detail,['name','value']);
      const name=typeof detail.name==='string'&&detail.name.trim().toLowerCase();
      if(!text(detail.name,48)||!text(detail.value,1600)||names.has(name))fail('Invalid or duplicate notation field.');
      names.add(name);
    }
  }
  const elements=new Map();
  for(const [index,row] of list(model.elements,650).entries()){
    keys(row,['id','name','kind','basis','source','details'],['parentId']);
    if(!elementKinds.has(row.kind))fail('Unknown element type.');
    common(row,'elements['+index+']');
    elements.set(row.id,row);
  }
  for(const row of elements.values()) {
    const visited=new Set([row.id]);
    for(let parent=row.parentId;parent;parent=elements.get(parent).parentId) {
      if(!elements.has(parent)||visited.has(parent))fail('Element ownership has a missing parent or a cycle.');
      visited.add(parent);
    }
  }
  const relations=new Map();
  for(const [index,row] of list(model.relations,900).entries()){
    keys(row,['id','name','kind','from','to','basis','source','details']);
    if(!relationKinds.has(row.kind)||!elements.has(row.from)||!elements.has(row.to))fail('A relationship needs two existing endpoints.');
    common(row,'relations['+index+']');
    relations.set(row.id,row);
  }
  for(const [index,view] of list(model.views,160).entries()){
    keys(view,['id','name','kind','elementIds','relationIds','gaps'],['scopeId','positions','groups','drawioShapes','mermaidDirection']);
    identity(view,'views['+index+']');
    const type=diagramTypes.get(view.kind);
    if(!type)fail('Unknown diagram type.');
    const visible=new Set(list(view.elementIds,80));
    if(visible.size!==view.elementIds.length||view.elementIds.some(id=>!type.elements.includes(elements.get(id)?.kind))) {
      fail(view.name+' contains an invalid or duplicate element.');
    }
    if(view.scopeId&&(!elements.has(view.scopeId)||!visible.has(view.scopeId)))fail(view.name+' needs a visible scope.');
    if(view.groups!==undefined){
      const owners=new Map();
      for(const row of list(view.groups,80)){
        keys(row,['elementId','groupId']);
        if(!visible.has(row.elementId)||!visible.has(row.groupId)||owners.has(row.elementId))fail('Invalid diagram group membership.');
        owners.set(row.elementId,row.groupId);
      }
      const parent=id=>owners.get(id)||elements.get(id).parentId;
      for(const id of owners.keys()){
        const visited=new Set();
        for(let node=id;visible.has(node);node=parent(node)){
          if(visited.has(node))fail('Diagram grouping contains a cycle.');
          visited.add(node);
        }
      }
    }
    list(view.relationIds,180);
    if(type.layout!=='timeline'&&new Set(view.relationIds).size!==view.relationIds.length)fail('Duplicate diagram relationship.');
    for(const id of view.relationIds){
      const row=relations.get(id);
      if(!row||!type.relations.includes(row.kind)||!visible.has(row.from)||!visible.has(row.to))fail(view.name+' has an incompatible relationship or hidden endpoint.');
    }
    checkLabels(view.gaps,600,500);
    if(view.mermaidDirection!==undefined&&!['TB','BT','LR','RL'].includes(view.mermaidDirection))fail('Invalid Mermaid layout direction.');
    if(view.drawioShapes!==undefined){
      if(!view.drawioShapes||typeof view.drawioShapes!=='object'||Array.isArray(view.drawioShapes))fail('Invalid diagram shapes.');
      for(const [id,shape] of Object.entries(view.drawioShapes)){
        if(!visible.has(id)||!Object.hasOwn(drawioShapes,shape))fail('Invalid diagram shape.');
      }
    }
    if(view.positions!==undefined){
      if(!view.positions||typeof view.positions!=='object'||Array.isArray(view.positions))fail('Invalid diagram layout.');
      for(const [id,point] of Object.entries(view.positions)) {
        keys(point,['x','y']);
        if(!visible.has(id)||![point.x,point.y].every(value=>Number.isInteger(value)&&value>=0&&value<=100000))fail('Invalid diagram pin.');
      }
    }
  }
  if(complete&&(model.views.length!==catalogue.length||new Set(model.views.map(view=>view.kind)).size!==catalogue.length||
    model.views.some(view=>!view.elementIds.length&&!view.gaps.length)))fail('AtMem must account for all 28 diagram types.');
  return model;
}

export const detailValue = (record,name) => record.details.find(detail=>detail.name===name)?.value;
export function diagramProjection(model,view){
  const type=diagramTypes.get(view.kind);
  const elements=new Map(model.elements.map(row=>[row.id,row]));
  const relations=new Map(model.relations.map(row=>[row.id,row]));
  const nodes=view.elementIds.map(id=>elements.get(id));
  const edges=view.relationIds.map(id=>relations.get(id));
  const diagnostics=[...view.gaps];
  const groups=new Map((view.groups||[]).map(row=>[row.elementId,row.groupId]));
  const parentOf=node=>groups.get(node.id)||node.parentId;
  if(view.kind==='context' && nodes.filter(node=>node.kind==='system').length!==1)diagnostics.push('Choose exactly one system.');
  if(view.kind==='state'&&!nodes.some(node=>node.kind==='start'))diagnostics.push('Add an initial state marker.');
  if(view.kind==='workflow'&&!['start','end'].every(kind=>nodes.some(node=>node.kind===kind)))diagnostics.push('Add the workflow start and end.');
  const cycles=new dagre.graphlib.Graph();
  for(const node of nodes)cycles.setNode(node.id);
  for(const edge of edges){
    const from=elements.get(edge.from),to=elements.get(edge.to);
    const property=name=>detailValue(edge,name);
    if(['dependency','prerequisite','decomposition'].includes(edge.kind))cycles.setEdge(edge.from,edge.to);
    if(view.kind==='data-flow'&&from.kind!=='process'&&to.kind!=='process')diagnostics.push(edge.name+' must connect through a process.');
    if(view.kind==='workflow'&&from.kind==='decision'&&!property('Guard'))diagnostics.push(edge.name+' needs a branch guard or default.');
    if(view.kind==='erd'){
      const columns=record=>new Set((detailValue(record,'Columns')||'').split('\n').map(line=>line.trim().split(/\s+/)[0]));
      const pair=name=>(property(name)||'').split(',').map(value=>value.trim()).filter(Boolean);
      const a=pair('From columns'),b=pair('To columns');
      if(!a.length||a.length!==b.length||a.some(id=>!columns(from).has(id))||b.some(id=>!columns(to).has(id))) {
        diagnostics.push(edge.name+' needs matching, existing foreign-key columns.');
      }
    }
    if(view.kind==='trust'&&parentOf(from)!==parentOf(to)&&!property('Controls'))diagnostics.push(edge.name+' needs a boundary control.');
    if(view.kind==='network'&&(!property('Protocol')||!property('Port')))diagnostics.push(edge.name+' needs a protocol and port.');
    if(view.kind==='api'&&edge.kind==='routes-to'){
      const method=detailValue(from,'Method'), targetMethod=detailValue(to,'Method');
      const path=property('Rewrite')||detailValue(from,'Path'), targetPath=detailValue(to,'Path');
      if(!method||!targetMethod||!path||!targetPath||method.toUpperCase()!==targetMethod.toUpperCase()||path!==targetPath) {
        diagnostics.push(edge.name+' needs a matching route method and path.');
      }
    }
    if(view.kind==='layer'&&from.parentId&&to.parentId&&from.parentId!==to.parentId){
      const allowed=detailValue(elements.get(from.parentId),'Allowed layers');
      if(allowed&&!allowed.split(',').map(name=>name.trim()).includes(to.parentId))diagnostics.push(edge.name+' violates the layer dependency policy.');
    }
  }
  if(['package','pipeline','functional','capability'].includes(view.kind)){
    for(const cycle of dagre.graphlib.alg.findCycles(cycles))diagnostics.push('Cycle: '+cycle.map(id=>elements.get(id).name).join(' → '));
  }
  return {type,nodes,edges,parentOf,diagnostics:[...new Set(diagnostics)]};
}

export function addDiagram(model,kind,name,example=false){
  const type=diagramTypes.get(kind);
  const view={id:diagramId(),kind,name,elementIds:[],relationIds:[],gaps:[]};
  if(!example)return {model:{...model,views:[...model.views,view]},view};
  const exampleNames={
    'use-case':['Support agent','Resolve a ticket'], functional:['Manage requests','Triage request'],
    capability:['Customer support','Case management'], sequence:['Customer','Support desk'],
    workflow:['Review request','Approved?'], state:['Awaiting review','Approved'], journey:['Submit a request','Track progress'],
    erd:['Ticket','Customer'], migration:['Parallel operation','Switch traffic'],
  };
  const added=type.starter.map((kind,index)=>({id:diagramId(),kind,name:exampleNames[type.id]?.[index]||kindLabel(kind)+(type.starter[0]===type.starter[1]?' '+(index+1):''),basis:'example',source:'',details:[]}));
  if(kind==='capability')added[1].parentId=added[0].id;
  const relation={id:diagramId(),kind:type.relations[0],name:kindLabel(type.relations[0]),
    from:added[0].id,to:added[1].id,basis:'example',source:'',details:[]};
  view.elementIds=added.map(row=>row.id);
  view.relationIds=[relation.id];
  return {model:{...model,elements:[...model.elements,...added],relations:[...model.relations,relation],views:[...model.views,view]},view};
}

// Append a reviewed suggestion and reconcile against the current shared records.
// Existing records and manually arranged views are preserved.
export function appendDiagramProposal(model,proposal,{complete=true}={}){
  validateDiagramModel(proposal,{complete});
  const merge = (current,incoming) => {
    const existing=new Map(current.map(row=>[row.id,row]));
    const added=incoming.filter(row=>{
      const original=existing.get(row.id);
      if(!original)return true;
      for(const key of ['kind','from','to','parentId']){
        if(original[key]!==row[key])fail('AtMem changed the meaning of an existing record. Regenerate from the current model.');
      }
      return false;
    });
    return [...current,...added];
  };
  return validateDiagramModel({...model,elements:merge(model.elements,proposal.elements),relations:merge(model.relations,proposal.relations),
    views:[...model.views,...proposal.views.map(view=>({...view,id:diagramId()}))]});
}

export function diagramFromSelection(model,kind,name,starting,scope){
    const result=addDiagram(model,kind,name,starting==='example');
    if(starting==='model'){
      const type=diagramTypes.get(kind);
      const byId=new Map(model.elements.map(row=>[row.id,row]));
      const inScope=row=>{
        for(let id=row.id;id;id=byId.get(id)?.parentId)if(id===scope)return true;
        return false;
      };
      const scoped=new Set(scope?[scope,...model.elements.filter(inScope).map(row=>row.id)]:byId.keys());
      for(const relation of model.relations){
        if(relation.from===scope)scoped.add(relation.to);
        if(relation.to===scope)scoped.add(relation.from);
      }
      const matches=model.elements.filter(row=>row.id!==scope&&scoped.has(row.id)&&type.elements.includes(row.kind)).map(row=>row.id);
      result.view.elementIds=(scope?[scope,...matches]:matches).slice(0,80);
      if(scope)result.view.scopeId=scope;
      const ids=new Set(result.view.elementIds);
      result.view.relationIds=model.relations.filter(row=>type.relations.includes(row.kind)&&ids.has(row.from)&&ids.has(row.to)).slice(0,180).map(row=>row.id);
    }
  return result;
}
