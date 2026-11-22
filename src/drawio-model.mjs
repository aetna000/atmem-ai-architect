import {nestDrawingScene} from './drawing-containment.mjs';
import {routeDiagramWires} from './diagram-routing.mjs';
import {wrapDiagramText,numberConnections} from './diagram-labels.mjs';
import {blockSpecSections} from './block-spec.mjs';
import libraries from './drawing-libraries.json' with {type:'json'};
const xml=value=>String(value??'').replace(/[<>&"'\r\n]/g,char=>({
  '<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&apos;','\r':'','\n':'&#10;',
})[char]);
const attr=(name,value)=>value==null?'':` ${name}="${xml(value)}"`;

const general={
  rectangle:'Rectangle', rounded:'Rounded', ellipse:'Ellipse', rhombus:'Decision', cylinder:'Database',
  actor:'Actor', cloud:'Cloud', parallelogram:'Input/output', hexagon:'Hexagon', triangle:'Triangle',
  note:'Note', swimlane:'Lane', text:'Text',
};
const er={erEntity:'Entity',erTable:'Table',erAttribute:'Attribute',erKey:'Key attribute',erDerived:'Derived attribute',erMultivalue:'Multivalued attribute',erRelationship:'Relationship'};
const uml={umlClass:'Class',umlActor:'Use case actor',umlUseCase:'Use case',umlComponent:'Component',umlState:'State',umlDecision:'Choice',umlActivity:'Activity'};
export const shapeLibraries={General:general,Flowchart:libraries.Flowchart,Basic:libraries.Basic,Arrows:libraries.Arrows,BPMN:libraries.BPMN,'Entity relationship':er,UML:uml};
export const drawioShapes=Object.assign({},...Object.values(shapeLibraries));
const actorImage='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="72" viewBox="0 0 48 72"><g fill="none" stroke="#7a8696" stroke-width="1.5"><circle cx="24" cy="12" r="9"/><path d="M24 21v27M7 31h34M24 48L7 68M24 48l17 20"/></g></svg>');
const actorStyle='shape=label;image='+actorImage+';imageWidth=44;imageHeight=64;imageAlign=left;imageVerticalAlign=middle;spacingLeft=66';
const shapeStyle={rounded:'rounded=1',rectangle:'rounded=0',cylinder:'shape=cylinder',
  erEntity:'shape=rectangle',erTable:'shape=swimlane;startSize=24',erAttribute:'shape=ellipse',erKey:'shape=ellipse;fontStyle=4',
  erDerived:'shape=ellipse;dashed=1',erMultivalue:'shape=doubleEllipse',erRelationship:'shape=rhombus',
  actor:actorStyle,umlClass:'shape=swimlane;startSize=24',umlActor:actorStyle,umlUseCase:'shape=ellipse',umlComponent:'shape=mxgraph.flowchart.predefined_process',
  umlState:'shape=rectangle;rounded=1;arcSize=40',umlDecision:'shape=rhombus',umlActivity:'shape=rectangle;rounded=1',
  text:'shape=label;fillColor=none;strokeColor=none'};

export function drawioNodeStyle(shape,{fill='#ffffff',stroke='#7a8696',font='#172033'}={}){
  const safe=Object.hasOwn(drawioShapes,shape)?shape:'rectangle';
  return `whiteSpace=wrap;html=0;overflow=hidden;align=center;verticalAlign=middle;fontSize=14;fontColor=${font};strokeColor=${stroke};fillColor=${fill};spacing=7;${shapeStyle[safe]||'shape='+safe};`;
}
export const drawioEdgeStyle='edgeStyle=orthogonalEdgeStyle;rounded=1;html=0;strokeColor=#536477;fontColor=#172033;labelBackgroundColor=#fafbf9;endArrow=block;endFill=1;';
export function architectureShape(kind){
  if(['actor','persona'].includes(kind))return 'actor';
  if(['use-case','state','start','end','outcome'].includes(kind))return 'ellipse';
  if(kind==='decision')return 'rhombus';
  if(['store','dataset','telemetry-store'].includes(kind))return 'cylinder';
  if(kind==='rule')return 'note';
  return 'rounded';
}
function boardDisplayPositions(nodes){
  const byId=new Map(nodes.map(row=>[row.id,row]));
  const positions=new Map();
  function get(row,parents=new Set()){
    if(positions.has(row.id))return positions.get(row.id);
    if(parents.has(row.id))return {x:0,y:0};
    parents.add(row.id);
    const owner=byId.get(row.parentId);
    const offset=owner?get(owner,parents):{x:0,y:0};
    const point={x:offset.x+(row.position?.x||0),y:offset.y+(row.position?.y||0)};
    positions.set(row.id,point);
    return point;
  }
  nodes.forEach(row=>get(row));
  return positions;
}

const sides={left:[0,.5],right:[1,.5],top:[.5,0],bottom:[.5,1]};
function terminalSide(prefix,side){
  const point=sides[String(side||'').toLowerCase()];
  return point?prefix+'X='+point[0]+';'+prefix+'Y='+point[1]+';':'';
}

// Native selection is controlled separately; changing it must not reroute the diagram.
export function boardSceneKey(nodes,edges){
 return JSON.stringify({nodes:nodes.map(({selected,...node})=>node),edges});
}
export function boardGraph(nodes,edges){
  const records=new Map(nodes.map(row=>[row.id,row.data]));
  const positions=boardDisplayPositions(nodes);
  const vertices=nodes.map(row=>{
    const data=row.data;
    const note=data.kind==='note';
    const shape=Object.hasOwn(drawioShapes,data.drawingShape)?data.drawingShape:note?'note':data.kind==='source'?'parallelogram':data.kind==='storage'?'cylinder':'rounded';
    const warning=data.runState==='failed'||data.status==='failed';
    const external=data.origin==='existing';
    const lines=[data.label,data.service,external?'Existing system':data.provider&&data.provider!=='tools'?data.provider.toUpperCase():'',
      data.blocks?.length?`${data.blocks.length} components`:'',data.childCount?`${data.childCount} subsystems`:'',
      data.blockReview?.statusLabel,
      data.reviewSummary&&data.blocks?.length?`${data.reviewSummary.reviewed}/${data.blocks.length} designs reviewed`:'',
      data.runState&&data.runState!=='idle'?data.runState[0].toUpperCase()+data.runState.slice(1):warning?'Check failed':'',
      data.runCount?`${data.runCount} live resources`:''].filter(Boolean);
    const point=positions.get(row.id);
    const parent=positions.get(row.parentId);
    const display=lines.flatMap(line=>wrapDiagramText(line,Math.max(12,Math.floor(((row.width||232)-38)/8)))) ;
    const properties=Object.fromEntries(blockSpecSections(data.buildSpec).filter(field=>field.content).map(field=>[field.key,field.content]));
    return {id:row.id,body:display.join('\n'),detailBody:lines.join('\n'),name:data.label||(note?'Comment':'Component'),...point,width:row.width||232,height:Math.max(row.height||0,note?92:85,display.length*19+30,edges.reduce((sum,e)=>sum+Number(e.source===row.id)+Number(e.target===row.id),0)*12+32),
      offset:parent,properties,initialFocus:!note&&!external&&!data.parentBlockId,selectable:true,connectable:true,canSend:data.kind!=='output',canReceive:data.kind!=='source',
      style:drawioNodeStyle(shape,{fill:data.drawingFill||(data.drawingShape?'#ffffff':note?'#fff4c8':external?'#edf3fb':'#fcf5f7'),stroke:warning?'#a62531':data.drawingStroke||'#7a8696'})+
        (external?'dashed=1;':'')+(data.dim?'opacity=48;':'')+(row.className?.includes('diagram-attention')?'strokeColor=#873b50;strokeWidth=3;':'')};
  });
  const visible=new Set(vertices.map(row=>row.id));
  const wires=edges.filter(edge=>visible.has(edge.source)&&visible.has(edge.target)).map(edge=>({
    id:edge.id,source:edge.source,target:edge.target,interfaceIds:edge.data?.sourceEdgeIds||[edge.id],record:edge,body:edge.label||'',name:edge.label||'Interface',selectable:true,
    style:drawioEdgeStyle+terminalSide('exit',records.get(edge.source)?.outputPosition)+
      terminalSide('entry',records.get(edge.target)?.inputPosition)+(edge.animated?'dashed=1;':'')+
      (edge.className?.includes('wire-failed')?'strokeColor=#a62531;':edge.className?.includes('diagram-attention')?'strokeWidth=3;strokeColor=#873b50;':''),
  }));
  return routeDiagramWires(nestDrawingScene(numberConnections({vertices,wires}),id=>records.get(id)?.parentBlockId));
}
const idFor=id=>'atmem-'+encodeURIComponent(id);
export function drawioFile(pages){
  return `<mxfile host="AtMem Architect">${pages.map(({id,name,vertices,wires})=>{
    const cells=vertices.map(row=>{
      const fields=blockSpecSections(row.properties).filter(field=>field.content);
      const id=attr('id',idFor(row.id));
      const hasDetails=row.detailBody&&row.detailBody!==row.body;
      const value=fields.length||row.record||hasDetails?'':id+attr('value',row.body);
      const parent=vertices.find(v=>v.id===row.containerParentId);
      const cell=`<mxCell${value}${attr('style',row.style)} vertex="1" parent="${parent?idFor(parent.id):'1'}"><mxGeometry x="${row.x-(parent?.x||0)}" y="${row.y-(parent?.y||0)}" width="${row.width}" height="${row.height}" as="geometry"/></mxCell>`;
      if(!fields.length&&!row.record&&!hasDetails)return cell;
      return `<object${id}${attr('label',row.body)}${row.record?attr('atmemRecord',JSON.stringify(row.record)):''}${hasDetails?attr('atmemDescription',row.detailBody):''}${fields.map(field=>attr(field.key,field.content)).join('')}>${cell}</object>`;
    });
    const edges=wires.map(row=>{
      const terminal=key=>row[key]==null||(key==='source'?row.start:row.end)?null:idFor(row[key]);
      const point=(value,name)=>value?`<mxPoint x="${value.x}" y="${value.y}" as="${name}"/>`:'';
      return `<mxCell${attr('id',idFor(row.id))}${attr('value',row.body)}${attr('atmemDescription',row.detailBody)}${attr('atmemRecord',row.record?JSON.stringify(row.record):null)}${attr('style',row.style)} edge="1" parent="1"${attr('source',terminal('source'))}${attr('target',terminal('target'))}><mxGeometry relative="1" as="geometry">${point(row.start,'sourcePoint')}${point(row.end,'targetPoint')}${point(row.labelOffset,'offset')}${row.points?.length?`<Array as="points">${row.points.map(p=>`<mxPoint x="${p.x}" y="${p.y}"/>`).join('')}</Array>`:''}</mxGeometry></mxCell>`;
    });
    return `<diagram${attr('id',id)}${attr('name',name)}><mxGraphModel grid="1" gridSize="10" page="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>${cells.join('')}${edges.join('')}</root></mxGraphModel></diagram>`;
  }).join('')}</mxfile>\n`;
}

const safeLabel=value=>String(value||'').replace(/[&"<>\x60#|;{}\[\]]/g,char=>`#${char.charCodeAt(0)};`).replace(/\s+/g,' ').trim();
export function graphMermaid({vertices,wires,direction='LR'},{selected,timeline=false}={}){
  const cells=new Map(vertices.filter(row=>row.selectable!==false&&!row.visualGroup).map(row=>[row.id,row]));
  const aliases=new Map([...cells.keys()].map((id,index)=>[id,'n'+(index+1)]));
  const incident=wires.filter(row=>cells.has(row.source)&&cells.has(row.target)&&
    (!selected||[row.id,row.recordId,row.source,row.target].includes(selected)));
  const shown=new Set(incident.flatMap(row=>[row.source,row.target]));
  if(!selected)for(const id of cells.keys())shown.add(id);
  else if(cells.has(selected))shown.add(selected);
  const lines=[timeline?'sequenceDiagram':'flowchart '+direction];
  for(const [id,row] of cells){
    if(!shown.has(id))continue;
    const label=safeLabel(row.name||row.body);
    if(timeline)lines.push(`  participant ${aliases.get(id)} as ${label.replace(/:/g,'#58;')}`);
    else lines.push(`  ${aliases.get(id)}["${label}"]`);
  }
  for(const wire of incident){
    const from=aliases.get(wire.source),to=aliases.get(wire.target),label=safeLabel(wire.mermaidLabel??wire.name??wire.body);
    if(timeline)lines.push(`  ${from}${wire.kind==='return'?'-->>':'->>'}${to}: ${label}`);
    else lines.push(`  ${from}${wire.kind==='association'?' ---':' -->'}${label?`|"${label}"| `:''}${to}`);
  }
  return lines.join('\n')+'\n';
}
