import React,{useState,useEffect}from'react';
import{newDecision}from'./engagement.mjs';import{reviseDecision}from'./records.mjs';
const latest=(project,subject)=>[...(project.decisions||[])].reverse().find(d=>d.subject===subject&&d.status==='Accepted');
export function LocationChoices({project,onChange,onDiscuss}){
 const cloud=latest(project,'platform.cloud')?.decision,country=latest(project,'data.country')?.decision,current=latest(project,'cloud.region');
 const [region,setRegion]=useState(current?.decision||''),[error,setError]=useState('');
 useEffect(()=>setRegion(current?.decision||''),[project.id,current?.decision]);
 function apply(event){event.preventDefault();const value=region.trim();if(!cloud||!value)return;if(!/^[a-z][a-z0-9-]{2,39}$/.test(value)){setError('Enter a region code.');return;}if(cloud==='gcp'&&/^(usa|us|united states)$/i.test(country||'')&&!value.startsWith('us-')){setError('Choose a US region for USA residency.');return;}
 const fields={title:'Cloud region',decision:value,status:'Accepted',owner:'user',reason:'Selected in Choices.'};let next=current?reviseDecision(project,current.id,fields,fields.reason):{...project,decisions:[...(project.decisions||[]),newDecision(project,{...fields,subject:'cloud.region'})]};
 next={...next,nodes:next.nodes.map(node=>{const previous=node.data.config?.region;return node.data.provider===cloud&&node.data.origin!=='existing'&&(!previous||/select|unknown|tbd/i.test(previous)||previous===current?.decision)?{...node,data:{...node.data,config:{...node.data.config,region:value}}}:node;})};onChange(next);setError('');}
 return <section className="doc location-choices" aria-label="Country and region"><header className="doc-head"><h2>Country &amp; region</h2></header><p><strong>Data country:</strong> {country||'Not selected'}</p><form className="location-region-form" onSubmit={apply}><label>Cloud region<input aria-label="Cloud region" value={region} maxLength={40} placeholder={cloud==='gcp'?'e.g. us-central1':'Region code'} onChange={event=>setRegion(event.target.value)}/></label><button className="btn primary" disabled={!cloud||!region.trim()||region.trim()===current?.decision}>Apply</button></form>{current&&<p className="ok-text" role="status">✓ {current.decision}</p>}{error&&<p role="alert">{error}</p>}<button className="link" onClick={onDiscuss}>Discuss location</button></section>;
}
