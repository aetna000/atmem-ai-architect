import {inspectDiagramReadability,paintedConnectorOverlaps} from './diagram-readability.mjs';
import {wrapDiagramText,diagramReferenceRows} from './diagram-labels.mjs';
import {drawioRuntime} from './drawio-runtime.mjs';
import {drawioEdgeStyle} from './drawio-model.mjs';

export function populateDrawioGraph(mx,graph,scene){
  scene={...scene,vertices:scene.vertices.map(v=>({...v})),wires:scene.wires.map(w=>({...w,points:w.points?.map(p=>({...p}))}))};
  const model=graph.getModel(),parent=graph.getDefaultParent();
  const cells=new Map();
  model.beginUpdate();
  try{
    graph.removeCells(graph.getChildCells(parent),true);
    for(const row of scene.vertices){
      const owner=cells.get(row.containerParentId),offset=owner?.atmem;
      const cell=graph.insertVertex(owner||parent,row.id,row.body,row.x-(offset?.x||0),row.y-(offset?.y||0),row.width,row.height,row.style);
      cell.atmem=row;
      cells.set(row.id,cell);
    }
    for(const row of scene.wires){
      const cell=graph.insertEdge(parent,row.id,row.body,cells.get(row.start?null:row.source),
        cells.get(row.end?null:row.target),row.style||drawioEdgeStyle);
      cell.atmem=row;
      if(row.start||row.end||row.points||row.labelOffset){
        const geometry=model.getGeometry(cell).clone();
        if(row.start)geometry.setTerminalPoint(new mx.mxPoint(row.start.x,row.start.y),true);
        if(row.end)geometry.setTerminalPoint(new mx.mxPoint(row.end.x,row.end.y),false);
        if(row.labelOffset)geometry.offset=new mx.mxPoint(row.labelOffset.x,row.labelOffset.y);
        if(row.points)geometry.points=row.points.map(({x,y})=>new mx.mxPoint(x,y));
        model.setGeometry(cell,geometry);
      }
    }
  }finally{model.endUpdate();}
  repairPaintedConnectorRoutes(mx,graph,scene);
  placeConnectionNumbers(mx,graph,scene);
  for(const row of [...scene.vertices,...scene.wires]){
    const cell=model.getCell(row.id),state=graph.view.getState(cell),shape=state?.shape?.node;
    if(state?.text?.node){state.text.node.setAttribute('data-record-id',row.recordId||row.id);state.text.node.setAttribute('data-cell-label','true');}
    if(shape){shape.setAttribute('data-record-id',row.recordId||row.id);shape.setAttribute('data-cell-kind',model.isVertex(cell)?'vertex':'edge');}
  }
  graph.atmemRenderedScene=scene;
  return [...cells.values(),...scene.wires.map(w=>model.getCell(w.id))];
}

// A bounded native pass resolves differences between abstract routes and actual
// shape perimeters. These waypoints are emitted with the same SVG/native page.
export function repairPaintedConnectorRoutes(mx,graph,scene){
 if(!graph.container.clientWidth||!graph.container.clientHeight)return 0;
 const model=graph.getModel(),scale=graph.view.scale,{translate}=graph.view;
 const score=id=>paintedConnectorOverlaps(graph,scene,id?[id]:undefined).reduce((sum,r)=>sum+r.pixels,0);
 const crosses=wire=>{
  const s=graph.view.getState(model.getCell(wire.id)),points=s?.absolutePoints?.filter(Boolean)||[];
  const rectangles=scene.vertices.filter(v=>v.selectable!==false&&!v.container&&![wire.source,wire.target].includes(v.id)).map(v=>graph.view.getState(model.getCell(v.id))?.shape?.boundingBox).filter(Boolean);
  return points.slice(1).some((b,i)=>rectangles.some(r=>{
   const a=points[i],dx=b.x-a.x,dy=b.y-a.y;let lo=0,hi=1;
   for(const[p,q]of [[-dx,a.x-r.x-2],[dx,r.x+r.width-2-a.x],[-dy,a.y-r.y-2],[dy,r.y+r.height-2-a.y]]){if(p===0){if(q<0)return false;}else{const t=q/p;if(p<0)lo=Math.max(lo,t);else hi=Math.min(hi,t);}}
   return lo<hi;
  }));
 };
 // Interactive repair is best effort. Exhaustive diagnostics still run below;
 // unresolved overlaps remain visible and continue to block verified exports.
 const started=performance.now();let repairs=0,totalAttempts=0;
 repair:for(let pass=0;pass<12;pass++){
  if(totalAttempts>=48||performance.now()-started>160)break;
  const issues=paintedConnectorOverlaps(graph,scene);if(!issues.length)break;
  let changed=false;
  for(const issue of issues){
   for(const id of [issue.id,issue.other]){
   if(totalAttempts>=48||performance.now()-started>160)break repair;
   const row=scene.wires.find(w=>w.id===id),cell=model.getCell(id),state=graph.view.getState(cell),original=model.getGeometry(cell).clone(),before=score(id);
   const full=state.absolutePoints.filter(Boolean).map(p=>({x:p.x/scale-translate.x,y:p.y/scale-translate.y}));
   const host=graph.container.getBoundingClientRect(),shared=(id===issue.id?issue.shared.slice(0,2):issue.shared.slice(2)).map(p=>({x:(p.x-host.left+graph.container.scrollLeft)/scale-translate.x,y:(p.y-host.top+graph.container.scrollTop)/scale-translate.y}));
   let attempts=0;
   for(let at=1;at<full.length&&!changed&&attempts<24;at++){
    const a=full[at-1],b=full[at],axis=Math.abs(a.x-b.x)<.1?'x':Math.abs(a.y-b.y)<.1?'y':null;if(!axis)continue;
    const along=axis==='x'?'y':'x';
    if(Math.abs(a[axis]-(shared[0][axis]+shared[1][axis])/2)>24/scale||Math.min(Math.max(a[along],b[along])+20/scale,Math.max(shared[0][along],shared[1][along]))-Math.max(Math.min(a[along],b[along])-20/scale,Math.min(shared[0][along],shared[1][along]))<0)continue;
    for(const delta of [12,-12,24,-24,36,-36,48,-48,72,-72,96,-96]){
     if(totalAttempts>=48||performance.now()-started>160)break repair;
     totalAttempts++;attempts++;const points=full.map(p=>({...p}));
     if(at-1>0)points[at-1][axis]+=delta;if(at<points.length-1)points[at][axis]+=delta;
     if(at===1&&points.length===2){points.splice(1,0,{x:a.x+(b.x-a.x)*.3+(axis==='x'?delta:0),y:a.y+(b.y-a.y)*.3+(axis==='y'?delta:0)},{x:a.x+(b.x-a.x)*.7+(axis==='x'?delta:0),y:a.y+(b.y-a.y)*.7+(axis==='y'?delta:0)});}
     const geometry=original.clone();geometry.points=points.slice(1,-1).map(p=>new mx.mxPoint(p.x,p.y));model.setGeometry(cell,geometry);
     if(!crosses(row)&&score(id)<before){row.points=points.slice(1,-1);repairs++;changed=true;break;}
     model.setGeometry(cell,original.clone());
    }
   }
   if(changed)break;
   }
   if(changed)break;
  }
  if(!changed)break;
 }
 scene.nativeRoutingRepairs=repairs;
 return repairs;
}

// Measure native text after rendering. Numbers stay near their own line and
// outside node bodies and previously placed numbers, including parallel edges.
export function placeConnectionNumbers(mx,graph,scene){
 if(!graph.container.clientWidth||!graph.container.clientHeight)return;
 const model=graph.getModel(),scale=graph.view.scale;
 const boxes=scene.vertices.filter(v=>v.selectable!==false&&!v.container).map(v=>graph.view.getState(model.getCell(v.id))).filter(Boolean)
  .map(s=>({x:s.x-7*scale,y:s.y-7*scale,width:s.width+14*scale,height:s.height+14*scale}));
 const occupied=[...boxes];
 const wireStates=scene.wires.map(w=>({id:w.id,points:graph.view.getState(model.getCell(w.id))?.absolutePoints?.filter(Boolean)||[]}));
 const distance=(p,points)=>Math.min(...points.slice(1).map((b,i)=>{const a=points[i],dx=b.x-a.x,dy=b.y-a.y,t=Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/(dx*dx+dy*dy||1)));return Math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy);}));
 const hits=(a,b)=>a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y;
 // Label offsets do not change connector paths. Commit them together instead
 // of forcing a full native graph validation for every individual number.
 model.beginUpdate();
 try{
 for(const wire of scene.wires){
  if(!wire.reference)continue;
  const cell=model.getCell(wire.id),state=graph.view.getState(cell),box=state?.text?.boundingBox;
  if(cell)cell.numberPlacementIssue=false;
  if(!box)continue;
  const points=state.absolutePoints?.filter(Boolean)||[];
  const segments=points.slice(1).map((b,i)=>({a:points[i],b,length:Math.hypot(b.x-points[i].x,b.y-points[i].y)})).sort((a,b)=>b.length-a.length);
  const candidates=[];
  for(const {a,b,length}of segments){
   if(length<24*scale)continue;
   for(const t of [...new Set([.5,.3,.7,.15,.85,...Array.from({length:Math.max(0,Math.floor(length/(18*scale))-1)},(_,i)=>(i+1)*18*scale/length)])])for(const off of [0,8,-8,16,-16,30,-30]){
    const x=a.x+(b.x-a.x)*t-(b.y-a.y)/length*off*scale,y=a.y+(b.y-a.y)*t+(b.x-a.x)/length*off*scale;
    candidates.push({x:x-box.width/2-2*scale,y:y-box.height/2-.4*scale,width:box.width+4*scale,height:box.height+.8*scale});
   }
  }
  const own=wireStates.find(s=>s.id===wire.id);
  const candidate=candidates.find(c=>{if(occupied.some(b=>hits(c,b)))return false;const center={x:c.x+c.width/2,y:c.y+c.height/2},d=distance(center,own.points);return wireStates.every(other=>other.id===wire.id||distance(center,other.points)>d+4*scale);});
  if(!candidate){cell.numberPlacementIssue=true;occupied.push(box);continue;}
  const geometry=model.getGeometry(cell).clone(),offset=geometry.offset||new mx.mxPoint(0,0);
  geometry.offset=new mx.mxPoint(offset.x+(candidate.x+candidate.width/2-box.x-box.width/2)/scale,
   offset.y+(candidate.y+candidate.height/2-box.y-box.height/2)/scale);
  model.setGeometry(cell,geometry);
  wire.labelOffset={x:geometry.offset.x,y:geometry.offset.y};
  occupied.push(candidate);
 }
 }finally{model.endUpdate();}
}

const ns='http://www.w3.org/2000/svg';
function element(type,attributes){
  const node=document.createElementNS(ns,type);
  for(const [name,value] of Object.entries(attributes))node.setAttribute(name,value);
  return node;
}

export async function renderDiagramSvg(scene,{name,revision}={}){
  const mx=await drawioRuntime();
  const host=document.createElement('div');
  host.setAttribute('aria-hidden','true');
  host.style.cssText='position:fixed;left:-20000px;top:0;width:800px;height:600px;pointer-events:none;';
  document.body.append(host);
  const graph=new mx.mxGraph(host);
  try{
    graph.setHtmlLabels(false);
    graph.setEnabled(false);
    populateDrawioGraph(mx,graph,scene);
    scene=graph.atmemRenderedScene;
    const readability=inspectDiagramReadability(graph,scene);
    if(!readability.passed)throw Error((name||'Diagram')+' has '+readability.issues.length+' layout issues ('+readability.issues.slice(0,4).map(r=>r.kind+': '+r.id).join(', ')+'). Reset its layout or adjust its elements before exporting.');
    const bounds=graph.getGraphBounds(),x=Math.floor(bounds.x)-24,y=Math.floor(bounds.y)-24;
    const width=Math.max(800,Math.ceil(bounds.width)+50),drawingHeight=Math.max(180,Math.ceil(bounds.height)+50);
    const referenceLines=[['Connections',true],...diagramReferenceRows(scene).flatMap(row=>
      wrapDiagramText(row.number+'. '+row.from+' → '+row.to+' — '+row.description,Math.floor((width-56)/8)).map(line=>[line,false,{number:row.number,id:row.id,from:row.from,to:row.to}])),
      ['Element properties',true],...scene.vertices.filter(v=>v.selectable!==false).flatMap(v=>
       wrapDiagramText(v.detailBody||v.body,Math.floor((width-56)/8)).map(line=>[line,false]))];
    const height=drawingHeight+60+referenceLines.length*22;
    const svg=element('svg',{width,height,viewBox:`${x} ${y} ${width} ${height}`});
    svg.setAttributeNS('http://www.w3.org/2000/xmlns/','xmlns:xlink','http://www.w3.org/1999/xlink');
    const title=element('title',{});title.textContent=name||'Architecture diagram';
    const desc=element('desc',{});desc.textContent=scene.vertices.filter(row=>row.selectable!==false)
      .map(row=>row.name).concat(scene.wires.map(row=>row.name)).join('. ');
    const metadata=element('metadata',{});metadata.textContent=JSON.stringify({name,revision,readability});
    svg.append(title,desc,metadata,element('rect',{x,y,width,height,fill:'#fafbf9'}));
    const draw=graph.view.getDrawPane();
    const defs=draw.ownerSVGElement?.querySelector('defs');
    if(defs)svg.append(defs.cloneNode(true));
    svg.append(draw.cloneNode(true));
    const legend=element('g',{'data-diagram-references':'true','font-family':'Arial, Helvetica','font-size':14,fill:'#172033'});
    const groups=new Map();
    referenceLines.forEach(([line,heading,reference],i)=>{
      const text=element('text',{x:x+24,y:y+drawingHeight+38+i*22,...(heading?{'font-weight':700}:{})});text.textContent=line;
      if(reference){if(!groups.has(reference.id)){const group=element('g',{'data-connection-reference':reference.number,'data-record-id':reference.id,'data-from':reference.from,'data-to':reference.to});groups.set(reference.id,group);legend.append(group);}groups.get(reference.id).append(text);}else legend.append(text);
    });
    svg.append(legend);
    return {svg:new XMLSerializer().serializeToString(svg),width,height,scene,readability};
  }finally{graph.destroy();host.remove();}
}
