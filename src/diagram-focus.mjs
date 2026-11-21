// Choose a useful connected neighbourhood at readable scale, rather than an
// isolated first record. This changes only the viewport, never model geometry.
export function readableDiagramFocus(scene,width,height,zoom=1){
 const nodes=scene.vertices.filter(v=>v.selectable!==false);
 if(!nodes.length)return null;
 if(scene.timeline)return nodes[0];
 let best=nodes[0],highest=-Infinity;
 for(const candidate of nodes){
  const cx=candidate.x+candidate.width/2,cy=candidate.y+candidate.height/2;
  const shown=new Set(nodes.filter(n=>Math.abs(n.x+n.width/2-cx)*zoom+n.width*zoom/2<=width/2&&Math.abs(n.y+n.height/2-cy)*zoom+n.height*zoom/2<=height/2).map(n=>n.id));
  const connections=scene.wires.filter(w=>shown.has(w.source)&&shown.has(w.target)).length;
  const degree=scene.wires.filter(w=>w.source===candidate.id||w.target===candidate.id).length;
  const score=shown.size+connections*5+Math.min(degree,10)*.1+(candidate.initialFocus?.15:0);
  if(score>highest){highest=score;best=candidate;}
 }
 return best;
}
