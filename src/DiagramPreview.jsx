import React,{useMemo,useState} from 'react';
import {scenarioDiagrams} from './block-spec.mjs';
import {DrawioCanvas} from './DrawioCanvas.jsx';
import {DiagramMermaid} from './DiagramMermaid.jsx';
import {architectureGraph} from './architecture-diagram-geometry.mjs';
import {graphMermaid} from './drawio-model.mjs';
import {renderDiagramSvg} from './drawio-render.mjs';

function scenarioGraph(scenario,view){
  const actors=[...new Set(scenario.steps.flatMap(step=>[step.sender,step.receiver]))];
  const byName=new Map(actors.map((name,index)=>[name,'participant-'+index]));
  const participantNodes=actors.map(name=>({id:byName.get(name),name,kind:'component',details:[]}));
  const stepNodes=scenario.steps.map((row,index)=>({id:'step-'+index,name:row.action,kind:'activity',details:[]}));
  const edges=scenario.steps.flatMap((row,index)=>{
    if(view==='sequence')return [{id:'message-'+index,name:row.action,kind:row.messageKind==='result'?'return':'call',
      from:byName.get(row.sender),to:byName.get(row.receiver),details:[]}];
    if(view==='functional')return index?[{id:'next-'+index,name:'Next',kind:'control-flow',from:stepNodes[index-1].id,to:stepNodes[index].id,details:[]}]:[];
    return [{id:'send-'+index,name:row.messageKind||'Interaction',kind:'publishes',from:byName.get(row.sender),to:stepNodes[index].id,details:[]},
      {id:'receive-'+index,name:'Receive',kind:'delivers',from:stepNodes[index].id,to:byName.get(row.receiver),details:[]}];
  });
  const nodes=view==='sequence'?participantNodes:view==='functional'?stepNodes:[...participantNodes,...stepNodes];
  return architectureGraph({nodes,edges,type:{layout:view==='sequence'?'timeline':'graph'},parentOf:()=>undefined},{kind:view});
}

export default function DiagramPreview({scenario}) {
  const [view,setView]=useState('sequence'),[selected,setSelected]=useState(null),[error,setError]=useState('');
  const scene=useMemo(()=>scenarioGraph(scenario,view),[scenario,view]);
  async function download(){
    try{
      const {svg}=await renderDiagramSvg(scene,{name:scenario.name});
      const url=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'}));
      const anchor=document.createElement('a');anchor.href=url;anchor.download=view+'.svg';anchor.click();
      setTimeout(()=>URL.revokeObjectURL(url),1000);
    }catch(failure){setError(failure.message);}
  }
  return <section className="scenario-diagram" aria-label={scenario.name+' diagram'}>
    <label>Diagram view<select value={view} onChange={event=>{setView(event.target.value);setSelected(null);}}>
      <option value="sequence">Sequence</option>
      <option value="functional">Functional flow</option>
      <option value="events">Events and messages</option>
    </select></label>
    <div className="scenario-diagram-scroll drawio-engineering"><DrawioCanvas key={view} scene={scene}
      label={scenario.name+' '+view+' diagram'} selected={selected} onSelect={setSelected}/></div>
    <button className="btn" onClick={download}>Download SVG</button>
    {error&&<p role="alert">{error}</p>}
    <DiagramMermaid code={selected?graphMermaid(scene,{selected,timeline:view==='sequence'}):scenarioDiagrams(scenario)[view]}/>
  </section>;
}
