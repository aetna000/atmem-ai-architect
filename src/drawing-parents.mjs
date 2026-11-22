import {containerDescendants,fitContainerBounds} from './drawing-containment.mjs';
import {wrapDiagramText} from './diagram-labels.mjs';
export function validateDrawingParents(pages){
 if(pages===undefined)return;
 if(!pages||typeof pages!=='object'||Array.isArray(pages)||Object.keys(pages).length>600)throw Error('Invalid drawing nesting.');
 for(const [page,parents]of Object.entries(pages)){
  if(!page||page.length>240||!parents||typeof parents!=='object'||Array.isArray(parents)||Object.keys(parents).length>500)throw Error('Invalid drawing nesting.');
  for(const [id,parent]of Object.entries(parents)){
   if(!id||id.length>240||parent!==null&&(typeof parent!=='string'||!parent||parent.length>240))throw Error('Invalid drawing parent.');
   const seen=new Set([id]);for(let p=parent;p;p=parents[p]){if(seen.has(p))throw Error('Drawing nesting cannot contain a cycle.');seen.add(p);}
  }
 }
}
export function applyDrawingParents(scene,parents){
 const vertices=scene.vertices.map(v=>({...v})),byId=new Map(vertices.map(v=>[v.id,v]));
 for(const v of vertices)if(parents&&Object.hasOwn(parents,v.id))v.containerParentId=parents[v.id]&&byId.has(parents[v.id])?parents[v.id]:undefined;
 for(const v of vertices){const seen=new Set([v.id]);for(let p=byId.get(v.containerParentId);p;p=byId.get(p.containerParentId)){if(seen.has(p.id))throw Error('Drawing nesting cannot contain a cycle.');seen.add(p.id);}}
 for(const v of vertices){
  const count=vertices.filter(child=>child.containerParentId===v.id).length;
  if(!count&&!v.container)continue;
  v.container=true;v.headerHeight=v.headerHeight||48;v.rotation=0;v.childCount=count;
  v.body=wrapDiagramText(v.name+(count?' · '+count+(count===1?' item':' items'):''),Math.max(18,Math.floor((v.width-40)/8))).join('\n');
  v.headerHeight=Math.max(v.headerHeight,v.body.split('\n').length*19+18);
  v.style+='shape=swimlane;rounded=1;horizontal=1;startSize='+v.headerHeight+';align=left;spacingLeft=16;swimlaneFillColor=none;fillColor=#faeaf0;strokeColor=#873b50;rotation=0;';
 }
 const sorted=[],seen=new Set();function visit(v){if(seen.has(v.id))return;const p=byId.get(v.containerParentId);if(p)visit(p);seen.add(v.id);sorted.push(v);}vertices.forEach(visit);
 return fitContainerBounds({...scene,vertices:sorted});
}
export function drawingInterior(scene,scope){
 if(!scope)return scene;
 const ids=new Set(containerDescendants(scene.vertices,scope).map(v=>v.id));
 return{...scene,vertices:scene.vertices.filter(v=>ids.has(v.id)),wires:scene.wires.filter(w=>ids.has(w.source)&&ids.has(w.target))};
}
export function updateDrawingPlacement(layout,page,changes,options={}){
 const parents={...layout?.parents?.[page],...options.parents},groups=(layout?.groups?.[page]||[]).map(g=>({...g,memberIds:g.memberIds.filter(id=>!Object.hasOwn(options.parents||{},id))}));
 for(const [id,parent]of Object.entries(options.parents||{})){const group=groups.find(g=>g.id===parent);if(group&&!group.memberIds.includes(id))group.memberIds.push(id);}
 const next={...layout,version:1,pages:layout?.pages||{},parents:{...layout?.parents,[page]:parents},groups:{...layout?.groups,[page]:groups}};
 validateDrawingParents(next.parents);return next;
}
// Default insertions use free space in the open interior, preserving existing geometry.
export function interiorInsertGeometry(scene,scope,id,position,{width=232,height=100}={}){
 const parent=scene.vertices.find(v=>v.id===scope),siblings=scene.vertices.filter(v=>v.containerParentId===scope);
 let point=position;
 if(!point){
  const start={x:(parent?.x||0)+28,y:(parent?.y||0)+(parent?.headerHeight||48)+28},cols=Math.max(1,Math.min(3,Math.floor(((parent?.width||width+56)-56)/(width+32))));
  outer:for(let row=0;row<=siblings.length+1;row++)for(let col=0;col<cols;col++){
   const p={x:start.x+col*(width+32),y:start.y+row*(height+32)};
   if(siblings.every(v=>p.x+width+16<=v.x||p.x>=v.x+v.width+16||p.y+height+16<=v.y||p.y>=v.y+v.height+16)){point=p;break outer;}
  }
  point??={x:start.x,y:Math.max(start.y,...siblings.map(v=>v.y+v.height+32))};
 }
 return [...scene.vertices.filter(v=>v.selectable!==false).map(v=>({id:v.id,x:Math.round(v.x),y:Math.round(v.y),width:Math.round(v.width),height:Math.round(v.height)})),{id,x:Math.round(point.x),y:Math.round(point.y)}];
}
