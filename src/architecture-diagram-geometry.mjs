import {fitDiagramFrames} from './diagram-frames.mjs';
import {routeDiagramWires} from './diagram-routing.mjs';
import dagre from 'dagre';
import {compactNodeLabel,numberConnections} from './diagram-labels.mjs';
import {detailValue,kindLabel} from './architecture-diagrams.mjs';
import {architectureShape,drawioNodeStyle,drawioEdgeStyle} from './drawio-model.mjs';

export const W=280, H=96, PAD=40;

export function nodeLines(node,type){
  return (node.details||[]).flatMap(({name,value})=>type.layout==='compartments'
    ?value.split('\n').filter(Boolean).map(line=>[name,line]):[[name,value]]);
}
export const labelParts=(edge,view)=>{
  const specific = view.kind==='state'?['Event','Guard','Action']:
    view.kind==='network'?['Protocol','Port']:view.kind==='integration'?['Transport','Version']:
    view.kind==='trust'?['Controls']:view.kind==='workflow'?['Guard']:view.kind==='observability'?['Signal type']:[];
  return [edge.name,...specific.map(name=>detailValue(edge,name)).filter(Boolean)];
};

export function layoutDiagram({type,nodes,edges,parentOf},view){
  const timeline=type.layout==='timeline';
  const stages=type.layout==='stages';
  const ordered=timeline||stages?nodes:[...nodes].sort((a,b)=>a.id.localeCompare(b.id));
  function labelFor(node){
    const shape=view.drawioShapes?.[node.id]||architectureShape(node.kind),width=timeline?220:W;
    const inset=['actor','umlActor'].includes(shape)?55:['ellipse','rhombus'].includes(shape)?70:0;
    const label=compactNodeLabel(node.name,kindLabel(node.kind),{width:width-inset,
      fields:type.layout==='compartments'&&nodeLines(node,type).length?[nodeLines(node,type).length+' properties · see details']:[]});
    const degree=edges.reduce((n,e)=>n+Number(e.from===node.id)+Number(e.to===node.id),0);
    return {...label,body:label.body+(degree>8?'\n'+degree+' connections':''),width,height:Math.max(label.height+(['ellipse','rhombus','cylinder'].includes(shape)?24:0),timeline?0:degree*12+32)};
  }
  const size=new Map(ordered.map(node=>[node.id,labelFor(node)]));
  const positions=new Map();
  const groups=[];
  if(timeline||stages){
    ordered.forEach((node,index)=>positions.set(node.id,{x:PAD+index*(W+85),y:PAD,...size.get(node.id)}));
  }else if(ordered.length){
    const graph=new dagre.graphlib.Graph({multigraph:true,compound:true}).setGraph({
      rankdir:view.mermaidDirection||(type.layout==='tree'?'TB':'LR'),marginx:PAD,marginy:PAD,nodesep:64,ranksep:100,edgesep:26,
    }).setDefaultEdgeLabel(()=>({}));
    for(const node of ordered)graph.setNode(node.id,{...size.get(node.id)});
    const ids=new Set(nodes.map(n=>n.id));
    const groupParents=new Set(['groups','bands','tiles'].includes(type.layout)?nodes.map(parentOf).filter(id=>ids.has(id)):[]);
    for(const id of groupParents)graph.setNode('@cluster/'+id,{});
    for(const node of ordered){
      const parent=parentOf(node);
      if(groupParents.has(node.id)){
        graph.setParent(node.id,'@cluster/'+node.id);
        if(groupParents.has(parent))graph.setParent('@cluster/'+node.id,'@cluster/'+parent);
      }else if(groupParents.has(parent))graph.setParent(node.id,'@cluster/'+parent);
    }
    for(const edge of [...edges].sort((a,b)=>a.id.localeCompare(b.id)))graph.setEdge(edge.from,edge.to,{width:32,height:28},edge.id);
    dagre.layout(graph);
    for(const node of ordered){
      const placed=graph.node(node.id);
      positions.set(node.id,{x:placed.x-placed.width/2,y:placed.y-placed.height/2,...size.get(node.id)});
    }
    for(const id of groupParents){const p=graph.node('@cluster/'+id);groups.push({id,x:p.x-p.width/2,y:p.y-p.height/2,width:p.width,height:p.height,memberIds:nodes.filter(node=>{let parent=node;const seen=new Set();while(parent&&!seen.has(parent.id)){if(parent.id===id)return true;seen.add(parent.id);parent=nodes.find(n=>n.id===parentOf(parent));}return false;}).map(n=>n.id)});}
    for(const key of graph.edges()){
      const edge=graph.edge(key);
      if(edge.points) edge.route=edge.points;
    }
    return {positions,groups,graph};
  }
  return {positions,groups};
}


export function architectureGraph(projection,view){
  const layout=layoutDiagram(projection,view);
  const {type,nodes,edges}=projection;
  const timeline=type.layout==='timeline';
  const location=id=>({...layout.positions.get(id),...view.positions?.[id]});
  const vertices=layout.groups.map(group=>({...group,id:'@frame-'+group.id,body:'',selectable:false,connectable:false,movable:false,
    style:'rounded=1;dashed=1;fillColor=#fcf5f7;strokeColor=#a78994;opacity=60;'}));
  for(const node of nodes){
    const point=location(node.id),shape=view.drawioShapes?.[node.id]||architectureShape(node.kind);
    const details=nodeLines(node,type).map(([name,text])=>name+' · '+text);
    const label=point;
    vertices.push({id:node.id,name:node.name,record:node,body:label.body,detailBody:[node.name,kindLabel(node.kind),...details].join('\n'),
      ...point,selectable:true,connectable:!timeline,movable:!timeline,
      style:drawioNodeStyle(shape,{fill:node.kind==='decision'?'#f7edd9':'#ffffff'})+'align=left;verticalAlign=middle;spacingLeft='+(['actor','umlActor'].includes(shape)?66:18)+';spacingRight=18;'});
  }
  const y0=Math.max(165,...nodes.map(node=>{const point=location(node.id);return point.y+point.height+40;}));
  const bottom=y0+(edges.length+1)*54;
  if(timeline)for(const node of nodes){
    const point=location(node.id);
    vertices.push({id:'@lifeline-'+node.id,body:'',x:point.x+point.width/2,y:point.y+point.height,
      width:1,height:bottom-point.y-point.height,selectable:false,connectable:false,movable:false,
      style:'fillColor=#aeb7c5;strokeColor=none;'});
  }
  const wires=edges.map((row,index)=>{
    const foreign=row.kind==='foreign-key';
    const optional=detailValue(row,'Nullable')?.toLowerCase()==='true';
    const unique=detailValue(row,'Unique')?.toLowerCase()==='true';
    const cardinality=foreign?'['+(optional?'0..1':'1')+' parent / '+(unique?'0..1':'0..*')+' children]':'';
    const label=[...labelParts(row,view),cardinality].filter(Boolean).join(' · ');
    const style=drawioEdgeStyle+(foreign?'startArrow=ER'+(unique?'one':'many')+';endArrow=ER'+(optional?'zeroToOne':'one')+';':'')+(row.kind==='association'?'endArrow=none;':'')+
      (['return','async','include','extend','implements','rollback'].includes(row.kind)?'dashed=1;':'')+
      (['inheritance','generalization','implements'].includes(row.kind)?'endArrow=block;endFill=0;':'')+
      (row.kind==='composition'?'startArrow=diamond;':'');
    const wire={id:timeline?row.id+'-step-'+index:row.id,recordId:row.id,kind:row.kind,
      name:row.name,record:row,mermaidLabel:label,body:(timeline?(index+1)+'. ':'')+label,source:row.from,target:row.to,style,selectable:true};
    if(timeline){
      const from=location(row.from),to=location(row.to),y=y0+index*54;
      wire.start={x:from.x+from.width/2,y};
      wire.end={x:to.x+to.width/2,y};
      if(row.from===row.to){wire.points=[{x:wire.start.x+45,y},{x:wire.start.x+45,y:y+20}];wire.end.y=y+20;}
      wire.style=style+'noEdgeStyle=1;';
    }
    if(!timeline&&layout.graph&&!view.positions?.[row.from]&&!view.positions?.[row.to]){
      const route=layout.graph.edge({v:row.from,w:row.to,name:row.id})?.points;
      if(route?.length>2){wire.points=route.slice(1,-1);wire.style+='noEdgeStyle=1;';}
    }
    return wire;
  });
  return routeDiagramWires(fitDiagramFrames(numberConnections({vertices,wires,timeline,direction:view.mermaidDirection||(type.layout==='tree'?'TB':'LR')})));
}
