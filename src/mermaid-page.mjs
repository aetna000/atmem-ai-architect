import {addDiagram,diagramId,diagramTypes,validateDiagramModel} from './architecture-diagrams.mjs';

let parser;
const fail=message=>{throw Error(message);};
const shapes={square:'rectangle',round:'rounded',circle:'ellipse',ellipse:'ellipse',diamond:'rhombus',
  cylinder:'cylinder',hexagon:'hexagon',lean_right:'parallelogram',lean_left:'parallelogram',stadium:'ellipse'};
function clean(value){
  return String(value??'').replace(/#(\d+);/g,(_,digits)=>{
    const code=Number(digits);
    return code>0&&code<=0x10ffff?String.fromCodePoint(code):'';
  }).trim();
}

export async function parseMermaidPage(source){
  if(typeof source!=='string'||!source.trim()||source.length>60_000)fail('Enter up to 60,000 characters of Mermaid.');
  if(/%%\{|^\s*(?:click|classDef|class|style|linkStyle|subgraph)\b/im.test(source)){
    fail('Use plain flowchart or sequence syntax. Remove styling, links, directives or subgraphs.');
  }
  const first=source.split('\n').map(line=>line.trim()).find(line=>line&&!line.startsWith('%%'))||'';
  const timeline=/^sequenceDiagram\s*$/.test(first);
  const direction=/^(?:graph|flowchart)\s+(TB|TD|BT|RL|LR)\b/i.exec(first)?.[1].toUpperCase();
  if(!timeline&&!direction)fail('Use a Mermaid flowchart or sequence diagram.');
  parser??=import('mermaid').then(({default:mermaid})=>{
    mermaid.initialize({startOnLoad:false,securityLevel:'strict',suppressErrorRendering:true});
    return mermaid.mermaidAPI;
  });
  let db;
  try{db=(await (await parser).getDiagramFromText(source)).db;}
  catch{fail('Mermaid could not read the diagram. Check the syntax and try again.');}
  let nodes,edges;
  if(timeline){
    nodes=[...db.getActors()].map(([id,row])=>({id,name:clean(row.description||row.name||id),actor:row.type==='actor'}));
    const messages=db.getMessages();
    if(messages.some(row=>!row.from||!row.to||typeof row.message!=='string'))fail('Use ordered messages. Add sequence fragments in the diagram workspace.');
    const returns=new Set(Object.entries(db.LINETYPE).filter(([kind])=>kind.startsWith('DOTTED')).map(([,value])=>value));
    edges=messages.map(row=>({from:row.from,to:row.to,name:clean(row.message),kind:returns.has(row.type)?'return':'call'}));
  }else{
    nodes=[...db.getVertices()].map(([id,row])=>({id,name:clean(row.text||id),shape:shapes[row.type]}));
    edges=db.getEdges().map(row=>({from:row.start,to:row.end,name:clean(row.text),kind:row.type==='arrow_open'?'association':undefined}));
  }
  if(!nodes.length||nodes.length>80||edges.length>180)fail('A Mermaid page supports 1–80 elements and up to 180 connections.');
  if([...nodes,...edges].some(row=>row.name.length>180))fail('Keep diagram labels to 180 characters. Put longer text in record details.');
  return {timeline,nodes,edges,direction:direction==='TD'?'TB':direction};
}

export function applyMermaidPage(model,parsed,{view,scene}={}){
  if(!view){
    const result=addDiagram(model,parsed.timeline?'sequence':'workflow',parsed.timeline?'Mermaid sequence':'Mermaid flowchart');
    model=result.model;view=result.view;
  }
  const type=diagramTypes.get(view.kind);
  if(parsed.timeline!==(type.layout==='timeline'))fail('Match the Mermaid source to the current page type.');
  const aliases=new Map((scene?.vertices||[]).filter(row=>row.selectable!==false).map((row,index)=>['n'+(index+1),row.id]));
  const byId=new Map(model.elements.map(row=>[row.id,row])),relations=new Map(model.relations.map(row=>[row.id,row]));
  const elements=new Map(byId),newIds=new Map(),drawioShapes={};
  for(const node of parsed.nodes){
    const existing=byId.get(aliases.get(node.id));
    const id=existing?.id||diagramId();
    const preferred=parsed.timeline?(node.actor?'actor':'component'):node.shape==='rhombus'?'decision':'activity';
    const kind=type.elements.includes(preferred)?preferred:type.elements[0];
    elements.set(id,existing?{...existing,name:node.name}:{id,kind,name:node.name,basis:'manual',source:'',details:[]});
    newIds.set(node.id,id);
    const shape=view.drawioShapes?.[id]||node.shape;
    if(shape)drawioShapes[id]=shape;
  }
  const byTerminals=new Map();
  for(const id of view.relationIds){
    const row=relations.get(id);
    const key=JSON.stringify([row.from,row.to]);
    if(!byTerminals.has(key))byTerminals.set(key,[]);
    byTerminals.get(key).push(row);
  }
  const relationIds=parsed.edges.map(edge=>{
    const from=newIds.get(edge.from),to=newIds.get(edge.to);
    if(!from||!to)fail('Every Mermaid connection needs two elements.');
    const existing=byTerminals.get(JSON.stringify([from,to]))?.shift();
    const id=existing?.id||diagramId();
    const name=edge.name||existing?.name||'Connection';
    const kind=type.relations.includes(edge.kind)?edge.kind:existing?.kind||type.relations[0];
    relations.set(id,existing?{...existing,name,kind}:{id,kind,name,from,to,basis:'manual',source:'',details:[]});
    return id;
  });
  const elementIds=[...newIds.values()],visible=new Set(elementIds);
  const {scopeId,groups,positions,...original}=view;
  const next={...original,elementIds,relationIds,drawioShapes,
    ...(parsed.direction?{mermaidDirection:parsed.direction}:{}),
    ...(visible.has(scopeId)?{scopeId}:{}),
    ...(groups?{groups:groups.filter(row=>visible.has(row.elementId)&&visible.has(row.groupId))}:{}),
    ...(positions?{positions:Object.fromEntries(Object.entries(positions).filter(([id])=>visible.has(id)))}:{})};
  return {view:next,model:validateDiagramModel({...model,elements:[...elements.values()],relations:[...relations.values()],
    views:model.views.map(row=>row.id===view.id?next:row)})};
}
