import {html} from './handoff-presentation.mjs';
import {wrapDiagramText,diagramReferenceRows} from './diagram-labels.mjs';

const ink='#172033',accent='#873B50',pale='#FCECF0';
function linesAt(lines,x,y,{anchor='start',weight=500,size=15,color=ink}={}){
  return '<text x="'+x+'" y="'+y+'" text-anchor="'+anchor+'" font-size="'+size+'" font-weight="'+weight+'" fill="'+color+'">'+
    lines.map((line,i)=>'<tspan x="'+x+'" dy="'+(i?20:0)+'">'+html(line)+'</tspan>').join('')+'</text>';
}
const card=(x,y,w,h,fill=pale)=>'<rect x="'+x+'" y="'+y+'" width="'+w+'" height="'+h+'" rx="8" fill="'+fill+'" stroke="#7A8696"/>';
function figure(name,description,width,height,body){
  const svg='<svg xmlns="http://www.w3.org/2000/svg" role="img" width="'+width+'" height="'+height+'" viewBox="0 0 '+width+' '+height+'"><title>'+html(name)+'</title><desc>'+html(description)+'</desc>'+
    '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M1 1 9 5 1 9" fill="none" stroke="'+accent+'" stroke-width="1.5"/></marker></defs>'+
    '<rect width="100%" height="100%" fill="#FAFBF9"/><g font-family="DM Sans, Arial, Helvetica, sans-serif">'+body+'</g></svg>';
  return {svg,drawingSvg:svg,width,height};
}

export function sequenceFigure(scene){
  const actors=scene.vertices.filter(v=>v.selectable!==false);
  if(!actors.length)return connectionFigure(scene);
  const gap=242,pad=26,width=pad*2+actors.length*gap,headers=actors.map(v=>wrapDiagramText(v.name||v.body,20));
  const headerHeight=Math.max(...headers.map(lines=>lines.length))*20+32;
  const centers=new Map(actors.map((v,i)=>[v.id,pad+gap*(i+.5)]));
  const messages=[];let cursor=pad+headerHeight+32;
  for(const [i,w] of scene.wires.entries()){
    const from=centers.get(w.source),to=centers.get(w.target);
    if(from==null||to==null)return connectionFigure(scene);
    const label=wrapDiagramText((i+1)+'. '+(w.name||w.mermaidLabel||'Message'),Math.max(12,Math.floor(((from===to?gap*.8:Math.abs(to-from))-30)/9)));
    const lineY=cursor+label.length*20+8;
    messages.push(linesAt(label,from===to?from:((from+to)/2),cursor+13,{anchor:'middle',size:15,weight:550}),
      '<path data-message="'+(i+1)+'" d="'+(from===to?'M'+from+' '+lineY+'h48v16h-48':'M'+from+' '+lineY+'H'+to)+'" fill="none" stroke="'+accent+'" stroke-width="2" '+(w.kind==='return'?'stroke-dasharray="6 4" ':'')+'marker-end="url(#arrow)"/>');
    cursor=lineY+(from===to?52:40);
  }
  const height=cursor+12;
  const lifelines=actors.map((v,i)=>{
    const x=centers.get(v.id);
    return '<path d="M'+x+' '+(pad+headerHeight)+'V'+(height-18)+'" stroke="#7A8696" stroke-dasharray="4 5"/>'+card(x-gap/2+8,pad,gap-16,headerHeight)+linesAt(headers[i],x,pad+28,{anchor:'middle',weight:650});
  }).join('');
  return figure(scene.name,'Ordered messages between participants. Dashed arrows denote returns.',width,height,lifelines+messages.join(''));
}

// A directed record view needs no routing. Unconnected elements and repeated
// sequence steps remain visible when a saved drawing cannot pass native checks.
export function connectionFigure(scene){
  const width=820,rows=diagramReferenceRows(scene),connected=new Set(scene.wires.flatMap(w=>[w.source,w.target]));
  const others=scene.vertices.filter(v=>v.selectable!==false&&!connected.has(v.id));
  let cursor=22,body='';
  for(const r of rows){
    const a=wrapDiagramText(r.from,31),b=wrapDiagramText(r.to,31),caption=wrapDiagramText(r.description,80);
    const h=Math.max(a.length,b.length)*20+22,mid=cursor+h/2;
    body+=card(22,cursor,322,h)+card(476,cursor,322,h,'#FCF5F7')+linesAt(a,38,cursor+25)+linesAt(b,492,cursor+25)+
      '<path d="M352 '+mid+'H468" stroke="'+accent+'" stroke-width="2" marker-end="url(#arrow)"/>'+linesAt([r.number],410,mid-8,{anchor:'middle',size:13})+
      linesAt(caption,38,cursor+h+20,{size:14,color:accent});
    cursor+=h+caption.length*20+25;
  }
  for(const v of others){
    const label=wrapDiagramText(v.name||v.body,75),h=label.length*20+22;
    body+=card(22,cursor,776,h)+linesAt(label,38,cursor+25);cursor+=h+12;
  }
  if(!rows.length&&!others.length){body=linesAt(['No elements recorded'],24,45);cursor=65;}
  return figure(scene.name,'Directed connections in recorded order, followed by elements without a connection.',width,cursor+12,body);
}
