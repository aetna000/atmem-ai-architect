import {fitDiagramFrames} from './diagram-frames.mjs';
import dagre from 'dagre';
import {routeDiagramWires} from './diagram-routing.mjs';

// Presentation only: keep every record, connector, parent and individual rotation.
export function arrangeDrawingScene(scene,{spacing=1,direction='LR'}={}){
 if(!Number.isFinite(spacing)||spacing<.5||spacing>8||!['LR','TB'].includes(direction))throw Error('Invalid arrangement spacing or direction.');
 if(scene.timeline||scene.ordered)throw Error('Ordered diagrams keep their chronological layout.');
 const vertices=scene.vertices.map(v=>({...v})),byId=new Map(vertices.map(v=>[v.id,v]));
 const children=new Map();
 for(const v of vertices.filter(v=>v.selectable!==false)){
  const parent=byId.has(v.containerParentId)&&byId.get(v.containerParentId).selectable!==false?v.containerParentId:null;
  if(!children.has(parent))children.set(parent,[]);children.get(parent).push(v);
 }
 const seen=new Set(),active=new Set();
 const move=(v,dx,dy)=>{v.x+=dx;v.y+=dy;for(const child of children.get(v.id)||[])move(child,dx,dy);};
 function pack(parent){
  if(active.has(parent))throw Error('Drawing nesting cannot contain a cycle.');
  if(seen.has(parent))return;active.add(parent);
  const items=children.get(parent)||[];
  for(const v of items)pack(v.id);
  if(items.length){
   const ids=new Set(items.map(v=>v.id)),owner=id=>{
    let v=byId.get(id);const path=new Set();
    while(v&&!ids.has(v.id)&&!path.has(v.id)){path.add(v.id);v=byId.get(v.containerParentId);}return v?.id;
   };
   const graph=new dagre.graphlib.Graph({multigraph:true}).setGraph({rankdir:direction,nodesep:100*spacing,ranksep:180*spacing,edgesep:32*spacing,marginx:32,marginy:32}).setDefaultEdgeLabel(()=>({}));
   for(const v of items){
    const angle=(v.rotation||0)*Math.PI/180,c=Math.abs(Math.cos(angle)),s=Math.abs(Math.sin(angle));
    graph.setNode(v.id,{width:v.width*c+v.height*s,height:v.width*s+v.height*c});
   }
   for(const w of scene.wires){const a=owner(w.source),b=owner(w.target);if(a&&b&&a!==b)graph.setEdge(a,b,{width:32,height:24},w.id);}
   dagre.layout(graph);
   const header=parent?(byId.get(parent)?.headerHeight||48):0;
   for(const v of items){const p=graph.node(v.id);move(v,p.x-v.width/2-v.x,p.y-v.height/2+header-v.y);}
   if(parent){
    const v=byId.get(parent),bounds=graph.graph();
    v.x=0;v.y=0;v.width=Math.max(180,bounds.width);v.height=Math.max(header+80,bounds.height+header);
   }
  }
  active.delete(parent);seen.add(parent);
 }
 pack(null);
 if([...children.values()].flat().some(v=>!seen.has(v.id)))throw Error('Drawing nesting cannot contain a cycle.');
 return routeDiagramWires(fitDiagramFrames({...scene,vertices,wires:scene.wires.map(w=>({...w,labelOffset:undefined}))}));
}
export function arrangementChanges(scene){
 return scene.vertices.filter(v=>v.selectable!==false).map(v=>({id:v.recordId||v.id,x:Math.round(v.x),y:Math.round(v.y),width:Math.round(v.width),height:Math.round(v.height),...(v.rotation?{rotation:v.rotation}:{})}));
}
export function layoutConflictScore(issues){
 const severity={'missing-node':1000,'missing-connector':1000,'missing-endpoint':1000,'node-overlap':100,'line-through-node':30,'text-overflow':30,'blocked-route':30,'wrong-reference':30,'connector-overlap':3,'ambiguous-number':2,'number-on-node':2,'number-overlap':2};
 return issues.reduce((n,issue)=>n+(severity[issue.kind]||1),0);
}
