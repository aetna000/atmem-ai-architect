import {wrapDiagramText} from './diagram-labels.mjs';
// Containment is a presentation of existing semantic ownership, never a new record.
// Scene coordinates remain absolute for saved layouts, routing and exports.
export function containerDescendants(vertices,id){
 const ids=new Set([id]);let changed=true;
 while(changed){changed=false;for(const v of vertices)if(v.containerParentId&&ids.has(v.containerParentId)&&!ids.has(v.id)){ids.add(v.id);changed=true;}}
 ids.delete(id);return vertices.filter(v=>ids.has(v.id));
}
export function nestDrawingScene(scene,parentOf){
 const rows=scene.vertices.filter(v=>v.selectable!==false),byId=new Map(rows.map(v=>[v.id,{...v}]));
 for(const v of byId.values()){
  const parent=parentOf(v.id);if(parent===v.id)throw Error('A component cannot contain itself.');
  if(byId.has(parent))v.containerParentId=parent;
 }
 if(![...byId.values()].some(v=>v.containerParentId))return scene;
 for(const v of byId.values()){
  const seen=new Set([v.id]);let parent=byId.get(v.containerParentId);
  while(parent){if(seen.has(parent.id))throw Error('Component nesting cannot contain a cycle.');seen.add(parent.id);parent=byId.get(parent.containerParentId);}
 }
 const children=id=>[...byId.values()].filter(v=>v.containerParentId===id);
 const ordered=[];
 function pack(items,x,y){
  const cols=Math.min(3,Math.ceil(Math.sqrt(items.length)));let col=0,atX=x,atY=y,rowHeight=0,right=x;
  for(const v of items){
   if(col===cols){col=0;atX=x;atY+=rowHeight+70;rowHeight=0;}
   place(v,atX,atY);right=Math.max(right,atX+v.width);rowHeight=Math.max(rowHeight,v.height);atX+=v.width+80;col++;
  }
  return{width:right-x,height:items.length?atY-y+rowHeight:0};
 }
 function place(v,x,y){
  v.x=x;v.y=y;ordered.push(v);const inside=children(v.id);
  if(!inside.length)return;
  v.container=true;v.rotation=0;v.body=wrapDiagramText(v.name||v.body.split('\n')[0],Math.max(12,Math.floor((v.width-40)/8))).join('\n');v.headerHeight=Math.max(48,v.body.split('\n').length*19+20);
  v.style+='shape=swimlane;rounded=1;startSize='+v.headerHeight+';horizontal=1;align=left;verticalAlign=middle;spacingLeft=16;spacingTop=0;swimlaneFillColor=#fcf5f7;fillColor=#faeaf0;strokeColor=#873b50;rotation=0;';
  const size=pack(inside,x+28,y+v.headerHeight+28);
  v.width=Math.max(v.width,size.width+56);v.height=Math.max(v.height,size.height+v.headerHeight+56);
 }
 pack([...byId.values()].filter(v=>!v.containerParentId),40,40);
 return{...scene,vertices:ordered};
}
// Keep every child inside its parent after manual resizing or movement.
export function fitContainerBounds(scene){
 const vertices=scene.vertices.map(v=>({...v})),byId=new Map(vertices.map(v=>[v.id,v]));
 for(const v of [...vertices].reverse()){
  const p=byId.get(v.containerParentId);if(!p)continue;
  if(v.x<p.x+20)v.x=p.x+20;if(v.y<p.y+(p.headerHeight||48)+20)v.y=p.y+(p.headerHeight||48)+20;
  p.width=Math.max(p.width,v.x+v.width-p.x+28);p.height=Math.max(p.height,v.y+v.height-p.y+28);
 }
 return{...scene,vertices};
}
// Persist absolute positions for all descendants when a native container moves.
export function nativeLayoutChanges(model,cells){
 const rows=new Map();
 const absolute=cell=>{const g=model.getGeometry(cell),p=model.getParent(cell);const offset=p&&model.isVertex(p)?absolute(p):{x:0,y:0};return{x:g.x+offset.x,y:g.y+offset.y};};
 function visit(cell){
  if(!model.isVertex(cell)||!cell.atmem)return;
  const row=cell.atmem,g=model.getGeometry(cell),p=absolute(cell);
  rows.set(row.recordId||row.id,{id:row.recordId||row.id,x:Math.round(p.x),y:Math.round(p.y),width:Math.round(g.width),height:Math.round(g.height)});
  for(let i=0;i<model.getChildCount(cell);i++)visit(model.getChildAt(cell,i));
 }
 cells.forEach(visit);return[...rows.values()];
}
