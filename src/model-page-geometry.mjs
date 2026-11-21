import {routeDiagramWires} from './diagram-routing.mjs';
import dagre from 'dagre';
import {compactNodeLabel,numberConnections} from './diagram-labels.mjs';
import {drawioNodeStyle,drawioEdgeStyle} from './drawio-model.mjs';
import {architectureGraph} from './architecture-diagram-geometry.mjs';

const visibility={public:'+',private:'-',protected:'#',package:'~'};
const multi=m=>m?` [${m.lower}..${m.upper}]`:'';
const wrap=(text,limit=45)=>{const words=String(text).split(' '),lines=[''];for(const word of words){if((lines.at(-1)+' '+word).length>limit&&lines.at(-1))lines.push('');lines[lines.length-1]+=(lines.at(-1)?' ':'')+word;}return lines.flatMap(line=>{const chars=Array.from(line);return Array.from({length:Math.max(1,Math.ceil(chars.length/limit))},(_,i)=>chars.slice(i*limit,i*limit+limit).join(''));});};
function rows(element,index){const type=id=>index.get(id)?.element.name||id;
 if(['entity','table'].includes(element.kind))return(element.columns||[]).map(c=>({id:c.id,text:`${element.primaryKey?.includes(c.id)?'PK ':''}${c.name}: ${type(c.typeRef)}${c.nullable?' [nullable]':' [required]'}`}));
 return[...(element.attributes||[]).map(a=>({id:a.id,text:`${visibility[a.visibility]||''}${a.name}: ${type(a.typeRef)}${multi(a.multiplicity)}`})),...(element.operations||[]).map(o=>{const result=o.parameters.find(p=>p.direction==='return');return{id:o.id,operation:true,text:`${visibility[o.visibility]||''}${o.name}(${o.parameters.filter(p=>p.direction!=='return').map(p=>`${p.direction==='in'?'':p.direction+' '}${p.name}: ${type(p.typeRef)}${multi(p.multiplicity)}`).join(', ')}): ${result?type(result.typeRef)+multi(result.multiplicity):'result unspecified'}`};})];}
export function engineeringGraph(view,index){
 const vertices=view.elements.map(({element,placement})=>{
   const entries=placement.detail==='summary'?[]:rows(element,index).map(row=>row.text);
   const label=compactNodeLabel(element.name,element.kind+' · '+element.basis,{width:350,fields:entries.length?[entries.length+' members · see properties']:[]});
   return {id:element.id,name:element.name,record:element,detailBody:[element.name,element.description,...entries].filter(Boolean).join('\n'),...label,
     x:placement.x,y:placement.y,height:Math.max(label.height,view.connectors.reduce((sum,e)=>sum+Number(e.source===element.id)+Number(e.target===element.id),0)*12+32),
     style:drawioNodeStyle('rectangle')+'align=left;verticalAlign=top;',
   };
 });
 const wires=view.connectors.map(row=>{
   const source=[row.sourceEnd?.role,multi(row.sourceEnd?.multiplicity)].filter(Boolean).join(' ');
   const target=[row.targetEnd?.role,multi(row.targetEnd?.multiplicity)].filter(Boolean).join(' ');
   const style=drawioEdgeStyle+(['generalization','realization'].includes(row.kind)?'endFill=0;':'')+
      (['dependency','realization','mapping'].includes(row.kind)?'dashed=1;':'')+
      (['composition','aggregation'].includes(row.kind)?'startArrow=diamond;'+(row.kind==='aggregation'?'startFill=0;':''):'')+
      (row.kind==='association'&&row.targetEnd?.navigable!==true?'endArrow=none;':'');
   return {id:row.id,name:row.name,body:[source,row.name,target].filter(Boolean).join(' · '),source:row.source,target:row.target,style};
 });
 // Existing placements are retained when they fit the measured cells. Repair
 // collisions caused by generated fixed-height grids in the display projection.
 const overlap=vertices.some((a,i)=>vertices.slice(0,i).some(b=>a.x<b.x+b.width+24&&a.x+a.width+24>b.x&&a.y<b.y+b.height+24&&a.y+a.height+24>b.y));
 if(overlap){
  const g=new dagre.graphlib.Graph({multigraph:true}).setGraph({rankdir:'LR',nodesep:65,ranksep:120,marginx:40,marginy:40}).setDefaultEdgeLabel(()=>({}));
  vertices.forEach(v=>g.setNode(v.id,{width:v.width,height:v.height}));wires.forEach(w=>g.setEdge(w.source,w.target,{width:32,height:28},w.id));dagre.layout(g);
  vertices.forEach(v=>{const p=g.node(v.id);v.x=p.x-p.width/2;v.y=p.y-p.height/2;});
  wires.forEach(w=>{w.points=g.edge({v:w.source,w:w.target,name:w.id})?.points?.slice(1,-1);w.style+='noEdgeStyle=1;';});
 }
 return routeDiagramWires(numberConnections({vertices,wires}));
}

export function legacyGraph(diagram,index,step=-1){
  const timeline=diagram.kind==='sequence';
  const nodes=diagram.elementIds.map(id=>({...index.elements.get(id),details:[]}));
  const edges=diagram.exchangeIds.map(id=>{
    const exchange=index.exchanges.get(id);
    const [from,to]=index.participants(exchange);
    return {...exchange,kind:timeline?'call':exchange.kind,from,to,details:[]};
  });
  const graph=architectureGraph({type:{layout:timeline?'timeline':'graph'},nodes,edges,parentOf:node=>node.parentId},diagram);
  if(timeline&&graph.wires[step])graph.wires[step].style+='strokeColor=#873b50;strokeWidth=3;';
  return graph;
}
