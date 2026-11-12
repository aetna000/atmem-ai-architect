import dagre from 'dagre';
import {layerOf} from './levels.mjs';
const key=p=>'atmem-canvas-view-v1:'+encodeURIComponent(p.id||'unsaved');
export function readCanvasView(project,storage){
 const fallback={level:'flow',focus:null,selected:null,positions:{}};
 try{
  storage=storage||globalThis.localStorage;
  const value=JSON.parse(storage.getItem(key(project))||'null');if(!value)return fallback;
  const selected=project.nodes.some(n=>n.id===value.selected)?value.selected:null;
  // Older overview preferences reopen as components, without changing the graph.
  const level=value.level==='block'&&selected?'block':'flow';
  const focus=project.nodes.some(n=>layerOf(n).id===value.focus)?value.focus:null;
  const positions=Object.fromEntries(Object.entries(value.positions||{}).filter(([,p])=>Number.isFinite(p?.x)&&Number.isFinite(p?.y)));
  return {level,focus,selected,positions};
 }catch{return fallback;}
}
export function saveCanvasView(project,view,storage){
 try{storage=storage||globalThis.localStorage;storage.setItem(key(project),JSON.stringify(view));return true;}catch{return false;}
}
// Arrange only the overview projection. Component positions and project semantics stay intact.
export function arrangeOverview(view,sizes={}){
 const graph=new dagre.graphlib.Graph();graph.setDefaultEdgeLabel(()=>({}));
 graph.setGraph({rankdir:'LR',nodesep:80,ranksep:170,marginx:40,marginy:40});
 for(const n of view.nodes)graph.setNode(n.id,{width:sizes[n.id]?.width||240,height:sizes[n.id]?.height||190});
 for(const e of view.edges)graph.setEdge(e.source,e.target,{width:Math.min(240,String(e.label||'').length*6),height:24});
 dagre.layout(graph);
 return Object.fromEntries(view.nodes.map(n=>{const g=graph.node(n.id);return [n.id,{x:g.x-g.width/2,y:g.y-g.height/2}];}));
}
