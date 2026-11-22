import {segmentCrossesRect} from './diagram-geometry.mjs';
// Runtime guard over the rendered native cells. Browser audits separately inspect
// SVG glyphs and sample painted paths; schema completeness is not a visual pass.
export function inspectDiagramReadability(graph,scene){
 const model=graph.getModel(),issues=[],nodes=[];
 const byId=new Map(scene.vertices.map(v=>[v.id,v]));
 const ancestor=(parent,id)=>{const seen=new Set();for(let v=byId.get(id);v&&!seen.has(v.id);v=byId.get(v.containerParentId)){if(v.containerParentId===parent)return true;seen.add(v.id);}return false;};
 if(!graph.container.getClientRects().length||!graph.container.clientWidth||!graph.container.clientHeight)return{version:1,passed:false,deferred:true,issues:[],nodes:0,connections:0};
 const rect=n=>{const r=n.getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height};};
 const hits=(a,b)=>a.x<b.x+b.width-1&&a.x+a.width>b.x+1&&a.y<b.y+b.height-1&&a.y+a.height>b.y+1;
 for(const v of scene.vertices.filter(v=>v.selectable!==false)){
  const state=graph.view.getState(model.getCell(v.id));if(!state?.shape?.node){issues.push({kind:'missing-node',id:v.id});continue;}
  const box=rect(state.shape.node);nodes.push({id:v.id,box,container:v.container,visualGroup:v.visualGroup,overlapBox:v.visualGroup?{...box,height:(v.headerHeight||48)*graph.view.scale}:box});
  for(const t of state.text?.node?.querySelectorAll('text')||[]){const r=rect(t);if(r.x<box.x-2||r.x+r.width>box.x+box.width+2||r.y<box.y-2||r.y+r.height>box.y+box.height+2){issues.push({kind:'text-overflow',id:v.id});break;}}
 }
 for(let i=0;i<nodes.length;i++)for(let j=0;j<i;j++)if(!ancestor(nodes[i].id,nodes[j].id)&&!ancestor(nodes[j].id,nodes[i].id)&&hits(nodes[i].overlapBox,nodes[j].overlapBox))issues.push({kind:'node-overlap',id:nodes[i].id,other:nodes[j].id});
 const labels=[],painted=paintedConnectorPaths(graph,scene),paths=new Map(painted.map(path=>[path.id,path]));
 for(const wire of scene.wires){
  if(wire.routingIssue)issues.push({kind:'blocked-route',id:wire.id});
  const cell=model.getCell(wire.id),state=graph.view.getState(cell);
  if(!state?.shape?.node||!state.absolutePoints?.filter(Boolean).length)issues.push({kind:'missing-connector',id:wire.id});
  if(!scene.vertices.some(v=>v.id===wire.source)||!scene.vertices.some(v=>v.id===wire.target))issues.push({kind:'missing-endpoint',id:wire.id});
  if(cell?.numberPlacementIssue)issues.push({kind:'ambiguous-number',id:wire.id});
  if(wire.reference&&wire.body!==wire.reference)issues.push({kind:'wrong-reference',id:wire.id});
  const crossed=new Set();
  for(const segment of paths.get(wire.id)?.segments||[])for(const node of nodes){
   if(node.container||[wire.source,wire.target].includes(node.id)||crossed.has(node.id))continue;
   if(segmentCrossesRect(segment[0],segment[1],node.box,3))crossed.add(node.id);
  }
  for(const other of crossed)issues.push({kind:'line-through-node',id:wire.id,other});
  for(const t of state?.text?.node?.querySelectorAll('text')||[]){const box=rect(t);for(const node of nodes)if(!node.container&&hits(box,node.box))issues.push({kind:'number-on-node',id:wire.id,other:node.id});for(const old of labels)if(hits(box,old.box))issues.push({kind:'number-overlap',id:wire.id,other:old.id});labels.push({id:wire.id,box});}
 }
 issues.push(...connectorOverlapFindings(painted,graph.view.scale));
 return{version:1,passed:!issues.length,issues,nodes:nodes.length,connections:scene.wires.length};
}

const paintedCache=new WeakMap();
function paintedConnectorPaths(graph,scene){
 const model=graph.getModel(),paths=[];
 for(const wire of scene.wires){
  const node=graph.view.getState(model.getCell(wire.id))?.shape?.node;
  const path=[...node?.querySelectorAll('path')||[]].find(p=>p.getAttribute('fill')==='none'&&p.getAttribute('visibility')!=='hidden');
  if(!path)continue;
  const currentMatrix=path.getScreenCTM();if(!currentMatrix)continue;
  const matrixKey=[currentMatrix.a,currentMatrix.b,currentMatrix.c,currentMatrix.d,currentMatrix.e,currentMatrix.f].join(',')+'|'+graph.view.scale+'|'+graph.view.translate.x+'|'+graph.view.translate.y;
  const cached=paintedCache.get(path);if(cached?.d===path.getAttribute('d')&&cached.matrixKey===matrixKey){paths.push({id:wire.id,segments:cached.segments,bounds:cached.bounds});continue;}
  const tokens=path.getAttribute('d').match(/[MLQCZ]|-?\d+(?:\.\d+)?(?:e[-+]?\d+)?/gi)||[],matrix=currentMatrix,segments=[];let at=0,current;
  const point=()=>({x:Number(tokens[at++]),y:Number(tokens[at++])});
  const screen=p=>new DOMPoint(p.x,p.y).matrixTransform(matrix);
  while(at<tokens.length){const cmd=tokens[at++];if(cmd==='M')current=point();else if(cmd==='L'){const next=point();if(current)segments.push([screen(current),screen(next)]);current=next;}else if(cmd==='Q'){const control=point(),end=point(),start=current;let last=start;for(let k=1;k<=8;k++){const t=k/8,u=1-t,next={x:u*u*start.x+2*u*t*control.x+t*t*end.x,y:u*u*start.y+2*u*t*control.y+t*t*end.y};segments.push([screen(last),screen(next)]);last=next;}current=end;}else if(cmd==='C'){const c1=point(),c2=point(),end=point(),start=current;let last=start;for(let k=1;k<=8;k++){const t=k/8,u=1-t,next={x:u*u*u*start.x+3*u*u*t*c1.x+3*u*t*t*c2.x+t*t*t*end.x,y:u*u*u*start.y+3*u*u*t*c1.y+3*u*t*t*c2.y+t*t*t*end.y};segments.push([screen(last),screen(next)]);last=next;}current=end;}else if(cmd!=='Z')break;}
  for(const segment of segments){const[a,b]=segment;segment.box={left:Math.min(a.x,b.x),right:Math.max(a.x,b.x),top:Math.min(a.y,b.y),bottom:Math.max(a.y,b.y)};segment.dx=b.x-a.x;segment.dy=b.y-a.y;segment.magnitude=Math.hypot(segment.dx,segment.dy);}
  const bounds={left:Math.min(...segments.map(s=>s.box.left)),right:Math.max(...segments.map(s=>s.box.right)),top:Math.min(...segments.map(s=>s.box.top)),bottom:Math.max(...segments.map(s=>s.box.bottom))};
  paintedCache.set(path,{d:path.getAttribute('d'),matrixKey,segments,bounds});paths.push({id:wire.id,segments,bounds});
 }
 return paths;
}
export function paintedConnectorOverlaps(graph,scene,onlyIds){
 return connectorOverlapFindings(paintedConnectorPaths(graph,scene),graph.view.scale,onlyIds);
}
function connectorOverlapFindings(paths,scale,onlyIds){
 const selected=onlyIds?new Set(onlyIds):null,findings=[],padding=.6*scale;
 // Compare nearby painted segments once. Rounded corners otherwise multiply
 // every connector pair into thousands of irrelevant segment comparisons.
 const grid=new Map(),all=[],large=[],cellSize=Math.max(16,128*scale);
 const cells=(box,extra=0)=>({left:Math.floor((box.left-extra)/cellSize),right:Math.floor((box.right+extra)/cellSize),top:Math.floor((box.top-extra)/cellSize),bottom:Math.floor((box.bottom+extra)/cellSize)});
 const oversized=r=>(r.right-r.left+1)*(r.bottom-r.top+1)>64;
 for(let i=0;i<paths.length;i++){
  const totals=new Map();
  for(const first of paths[i].segments){
   const area=cells(first.box,padding),candidates=new Set(large);
   if(oversized(area)){for(const entry of all)candidates.add(entry);}
   else for(let x=area.left;x<=area.right;x++)for(let y=area.top;y<=area.bottom;y++)for(const entry of grid.get(x+':'+y)||[])candidates.add(entry);
   for(const {owner,segment:second}of candidates){
    if(selected&&!selected.has(paths[i].id)&&!selected.has(paths[owner].id))continue;
    if(first.box.right<second.box.left-padding||second.box.right<first.box.left-padding||first.box.bottom<second.box.top-padding||second.box.bottom<first.box.top-padding)continue;
    const[a,b]=first,[c,d]=second,dx=first.dx,dy=first.dy,lengthA=first.magnitude,ex=second.dx,ey=second.dy,lengthB=second.magnitude;if(!lengthA||!lengthB)continue;
    if(Math.abs(dx*ey-dy*ex)/(lengthA*lengthB)>.25)continue;
    if(Math.abs((c.x-a.x)*dy-(c.y-a.y)*dx)/lengthA>padding||Math.abs((d.x-a.x)*dy-(d.y-a.y)*dx)/lengthA>padding)continue;
    const p=((c.x-a.x)*dx+(c.y-a.y)*dy)/lengthA,q=((d.x-a.x)*dx+(d.y-a.y)*dy)/lengthA;
    const length=Math.max(0,Math.min(lengthA,Math.max(p,q))-Math.max(0,Math.min(p,q)));
    if(!length)continue;
    const value=totals.get(owner)||{total:0,longest:0};value.total+=length;
    if(length>value.longest){value.longest=length;value.shared=[a,b,c,d].map(p=>({x:p.x,y:p.y}));}
    totals.set(owner,value);
   }
  }
  for(const [owner,value]of [...totals].sort((a,b)=>a[0]-b[0]))if(value.total>24*scale)findings.push({kind:'connector-overlap',id:paths[i].id,other:paths[owner].id,pixels:Math.round(value.total),shared:value.shared});
  for(const segment of paths[i].segments){
   const entry={owner:i,segment},area=cells(segment.box);all.push(entry);
   if(oversized(area)){large.push(entry);continue;}
   for(let x=area.left;x<=area.right;x++)for(let y=area.top;y<=area.bottom;y++){
    const key=x+':'+y;if(!grid.has(key))grid.set(key,[]);grid.get(key).push(entry);
   }
  }
 }
 return findings;
}
