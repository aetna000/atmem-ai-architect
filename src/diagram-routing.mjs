// Rectilinear routing around every visible node. Coordinates come from obstacle
// boundaries, not a pixel grid, so sparse and detailed models use the same rules.
const inset=18;
const inside=(x,y,r)=>x>r.x+.01&&x<r.x+r.width-.01&&y>r.y+.01&&y<r.y+r.height-.01;
function clear(a,b,rects){
 return !rects.some(r=>a.x===b.x?a.x>r.x+.01&&a.x<r.x+r.width-.01&&Math.max(a.y,b.y)>r.y+.01&&Math.min(a.y,b.y)<r.y+r.height-.01:
  a.y>r.y+.01&&a.y<r.y+r.height-.01&&Math.max(a.x,b.x)>r.x+.01&&Math.min(a.x,b.x)<r.x+r.width-.01);
}
class Heap{
 rows=[];
 push(row){let i=this.rows.length;this.rows.push(row);while(i){const p=(i-1)>>1;if(this.rows[p].f<=row.f)break;this.rows[i]=this.rows[p];i=p;}this.rows[i]=row;}
 pop(){const first=this.rows[0],last=this.rows.pop();if(this.rows.length){let i=0;while(i*2+1<this.rows.length){let c=i*2+1;if(c+1<this.rows.length&&this.rows[c+1].f<this.rows[c].f)c++;if(this.rows[c].f>=last.f)break;this.rows[i]=this.rows[c];i=c;}this.rows[i]=last;}return first;}
}
export function routeDiagramWires(scene){
 if(scene.timeline||!scene.wires.length)return scene;
 const nodes=scene.vertices.filter(v=>v.selectable!==false),byId=new Map(nodes.map(v=>[v.id,v]));
 const bounds=v=>{const angle=(v.rotation||0)*Math.PI/180,c=Math.abs(Math.cos(angle)),s=Math.abs(Math.sin(angle)),width=v.width*c+v.height*s,height=v.width*s+v.height*c;return{x:v.x+v.width/2-width/2,y:v.y+v.height/2-height/2,width,height};};
 const obstacles=nodes.map(v=>{const b=bounds(v);return{x:b.x-inset,y:b.y-inset,width:b.width+inset*2,height:b.height+inset*2};});
 const allocations=new Map(),selfCounts=new Map();
 const baseStyles=scene.wires.map(w=>w.routingBaseStyle??w.style??'');
 const endpoints=scene.wires.map((w,index)=>{
  if(w.start||w.end)return null;
  const a=byId.get(w.source),b=byId.get(w.target);if(!a||!b)return null;
  const dx=b.x+b.width/2-a.x-a.width/2,dy=b.y+b.height/2-a.y-a.height/2;
  let source,target;
  if(w.source===w.target){const count=selfCounts.get(w.source)||0;selfCounts.set(w.source,count+1);[source,target]=[[[1,.25],[1,.75]],[[.25,0],[.75,0]],[[0,.75],[0,.25]],[[.75,1],[.25,1]]][count%4];}
  else if(Math.abs(dy)>Math.abs(dx)*1.5){source=[.5,dy>0?1:0];target=[.5,dy>0?0:1];}
  else{source=[dx>=0?1:0,.5];target=[dx>=0?0:1,.5];}
  const existing=(prefix,fallback)=>{const x=baseStyles[index].match(new RegExp('(?:^|;)'+prefix+'X=([0-9.]+)')),y=baseStyles[index].match(new RegExp('(?:^|;)'+prefix+'Y=([0-9.]+)'));return x&&y?[Number(x[1]),Number(y[1])]:fallback;};
  const fixedSource=/(?:^|;)exitX=/.test(baseStyles[index]),fixedTarget=/(?:^|;)entryX=/.test(baseStyles[index]);
  source=existing('exit',source);target=existing('entry',target);
  const allocate=(id,side,fixed)=>{const key=id+':'+(side[0]===0?'left':side[0]===1?'right':side[1]===0?'top':'bottom');if(!allocations.has(key))allocations.set(key,[]);const value={side:[...side],fixed};allocations.get(key).push(value);return value;};
  const sourceSlot=allocate(w.source,source,Boolean(w.lockPorts||w.source===w.target)),targetSlot=allocate(w.target,target,Boolean(w.lockPorts||w.source===w.target));
  const port=(node,[x,y])=>{
   const angle=(node.rotation||0)*Math.PI/180,c=Math.cos(angle),s=Math.sin(angle),cx=node.x+node.width/2,cy=node.y+node.height/2;
   const dx=(x-.5)*node.width,dy=(y-.5)*node.height,nx=x===0?-1:x===1?1:0,ny=y===0?-1:y===1?1:0;
   const p={x:cx+dx*c-dy*s,y:cy+dx*s+dy*c},normal={x:nx*c-ny*s,y:nx*s+ny*c},b=bounds(node);
   if(Math.abs(normal.x)>=Math.abs(normal.y))p.x=normal.x>=0?b.x+b.width+inset:b.x-inset;
   else p.y=normal.y>=0?b.y+b.height+inset:b.y-inset;
   return p;
  };
  return{a,b,sourceNode:a,targetNode:b,port,sourceSlot,targetSlot};
 });
 for(const slots of allocations.values())slots.forEach((slot,index)=>{if(!slot.fixed&&slots.length>1){const axis=slot.side[0]===0||slot.side[0]===1?1:0;slot.side[axis]=.15+.7*(index+1)/(slots.length+1);}});
 for(const p of endpoints.filter(Boolean)){p.source=p.sourceSlot.side;p.target=p.targetSlot.side;const a=p.a,b=p.b;p.a=p.port(a,p.source);p.b=p.port(b,p.target);}
 const channels=values=>values.flatMap(v=>[v-12,v,v+12]);
 const xs=[...new Set([...obstacles.flatMap(r=>channels([r.x,r.x+r.width])),...endpoints.filter(Boolean).flatMap(p=>[p.a.x,p.b.x])])].sort((a,b)=>a-b);
 const ys=[...new Set([...obstacles.flatMap(r=>channels([r.y,r.y+r.height])),...endpoints.filter(Boolean).flatMap(p=>[p.a.y,p.b.y])])].sort((a,b)=>a-b);
 const count=xs.length*ys.length;
 if(count>150000)return{...scene,wires:scene.wires.map(w=>({...w,routingIssue:'This page exceeds the routing limit. Split it into smaller views.'}))};
 const reserved=new Set(),segmentKey=(a,b)=>a<b?a+':'+b:b+':'+a;
 const valid=new Int8Array(count),links=new Map();
 const id=(x,y)=>y*xs.length+x,point=i=>({x:xs[i%xs.length],y:ys[Math.floor(i/xs.length)]});
 const allowed=i=>{if(!valid[i]){const p=point(i);valid[i]=obstacles.some(r=>inside(p.x,p.y,r))?-1:1;}return valid[i]===1;};
 function neighbors(i){
  if(links.has(i))return links.get(i);
  const x=i%xs.length,y=Math.floor(i/xs.length),a=point(i);
  const list=[[x-1,y],[x+1,y],[x,y-1],[x,y+1]].filter(([x,y])=>x>=0&&y>=0&&x<xs.length&&y<ys.length).map(([x,y])=>id(x,y))
   .filter(j=>allowed(j)&&clear(a,point(j),obstacles));links.set(i,list);return list;
 }
 const drawn=[];
 const overlap=(a,b,c,d)=>a.x===b.x&&c.x===d.x&&Math.abs(a.x-c.x)<12?Math.max(0,Math.min(Math.max(a.y,b.y),Math.max(c.y,d.y))-Math.max(Math.min(a.y,b.y),Math.min(c.y,d.y))):a.y===b.y&&c.y===d.y&&Math.abs(a.y-c.y)<12?Math.max(0,Math.min(Math.max(a.x,b.x),Math.max(c.x,d.x))-Math.max(Math.min(a.x,b.x),Math.min(c.x,d.x))):0;
 const sharedScore=path=>path.slice(1).reduce((sum,b,i)=>sum+drawn.reduce((total,old)=>total+old.slice(1).reduce((part,d,j)=>{const n=overlap(path[i],b,old[j],d);return part+(n>24?n:0);},0),0),0);
 const shared=(a,b)=>drawn.some(path=>path.slice(1).some((d,j)=>overlap(a,b,path[j],d)>24));
 const wires=scene.wires.map((wire,i)=>{
  const ports=endpoints[i];if(!ports)return wire.start&&wire.end?wire:{...wire,routingIssue:'A connector endpoint is missing.'};
  const start=id(xs.indexOf(ports.a.x),ys.indexOf(ports.a.y)),goal=id(xs.indexOf(ports.b.x),ys.indexOf(ports.b.y));
  const dist=new Float64Array(count).fill(Infinity),prev=new Int32Array(count).fill(-1),heap=new Heap(),target=ports.b;
  dist[start]=0;heap.push({id:start,f:0,g:0});
  while(heap.rows.length){
   const current=heap.pop();if(current.g!==dist[current.id])continue;if(current.id===goal)break;
   const a=point(current.id);
   for(const next of neighbors(current.id)){
    const b=point(next),cost=current.g+(Math.abs(a.x-b.x)+Math.abs(a.y-b.y))*(reserved.has(segmentKey(current.id,next))?25:1);
    if(cost>=dist[next])continue;dist[next]=cost;prev[next]=current.id;heap.push({id:next,g:cost,f:cost+Math.abs(b.x-target.x)+Math.abs(b.y-target.y)});
   }
  }
  if(!Number.isFinite(dist[goal]))return{...wire,routingIssue:'No clear route between these overlapping or obstructed ports.'};
  const path=[];for(let at=goal;at!==-1;at=prev[at]){path.push(point(at));if(prev[at]!==-1)reserved.add(segmentKey(at,prev[at]));}path.reverse();
  let points=path.filter((p,j)=>!j||j===path.length-1||!((path[j-1].x===p.x&&p.x===path[j+1].x)||(path[j-1].y===p.y&&p.y===path[j+1].y)));
  if(wire.source===wire.target){
    for(const offset of [12,24,36,48,60,84,108,144]){
      const vertical=ports.source[0]===0||ports.source[0]===1,sign=(vertical?ports.source[0]:ports.source[1])===1?1:-1;
      const candidate=vertical?[ports.a,{x:ports.a.x+offset*sign,y:ports.a.y},{x:ports.a.x+offset*sign,y:ports.b.y},ports.b]:[ports.a,{x:ports.a.x,y:ports.a.y+offset*sign},{x:ports.b.x,y:ports.a.y+offset*sign},ports.b];
      if(candidate.slice(1).every((p,k)=>clear(candidate[k],p,obstacles)&&!shared(candidate[k],p))){points=candidate;break;}
    }
  }
  const terminal=(node,side)=>{const angle=(node.rotation||0)*Math.PI/180,c=Math.cos(angle),s=Math.sin(angle),dx=(side[0]-.5)*node.width,dy=(side[1]-.5)*node.height;return{x:node.x+node.width/2+dx*c-dy*s,y:node.y+node.height/2+dx*s+dy*c};};
  const fullPath=route=>{
    const path=[terminal(ports.sourceNode,ports.source),...route,terminal(ports.targetNode,ports.target)];
    return path.filter((p,j)=>!j||j===path.length-1||!((path[j-1].x===p.x&&p.x===path[j+1].x&&(p.y-path[j-1].y)*(path[j+1].y-p.y)>=0)||(path[j-1].y===p.y&&p.y===path[j+1].y&&(p.x-path[j-1].x)*(path[j+1].x-p.x)>=0)));
  };
  const score=route=>sharedScore(fullPath(route));
  // Separate coincident trunks into nearby clear lanes without moving terminals.
  for(let pass=0;pass<3;pass++)for(let j=0;j<points.length-1;j++){
   const a=points[j],b=points[j+1];if(!shared(a,b)&&!((j===0||j===points.length-2)&&score(points)>0))continue;
   for(const offset of [12,-12,24,-24,36,-36,48,-48,72,-72,96,-96]){
    const candidate=points.map(p=>({...p}));
    const axis=a.x===b.x?'x':'y';candidate[j][axis]+=offset;candidate[j+1][axis]+=offset;
    if(j===0)candidate.unshift({...points[0]});
    if(j===points.length-2)candidate.push({...points.at(-1)});
    const at=j===0?1:j;
    if(candidate.slice(1).every((p,k)=>clear(candidate[k],p,obstacles))&&score(candidate)+1<score(points)){points=candidate;break;}
   }
  }
  drawn.push(fullPath(points));
  return{...wire,points,routingIssue:undefined,routingBaseStyle:baseStyles[i],style:baseStyles[i].split(';').filter(part=>part&&!/^(?:noEdgeStyle|exitX|exitY|entryX|entryY)=/.test(part)).join(';')+';noEdgeStyle=1;exitX='+ports.source[0]+';exitY='+ports.source[1]+';entryX='+ports.target[0]+';entryY='+ports.target[1]+';'};
 });
 return{...scene,wires};
}
