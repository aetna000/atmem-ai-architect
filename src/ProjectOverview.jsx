import {recordedOutcome} from './source-scope.mjs';
import {isDiagramRevision} from './records.mjs';
import React,{useMemo,useState} from 'react';
import {ArrowUpRight,Search,Workflow,FileText,GitFork}from'lucide-react';
import{buildReview}from'./build-review.mjs';
import{requirementNumber}from'./derive.mjs';
import'./project-overview.css';

export function ProjectOverview({project,onDrawings,onRequirements,onReview,onBlock}){
 const report=useMemo(()=>buildReview(project),[project]),[tab,setTab]=useState('Overview'),[query,setQuery]=useState('');
 const decisions=(project.decisions||[]).filter(d=>d.status==='Accepted'&&!isDiagramRevision(d)),history=(project.decisions||[]).filter(isDiagramRevision),scenarios=project.nodes.flatMap(n=>(n.data.buildSpec?.scenarios||[]).map((s,i)=>({...s,id:n.id+'-'+i,block:n.id,blockName:n.data.label})));
 const groups=[...Map.groupBy(scenarios,s=>s.name.replace(/\s*[—–-]\s*part\s+\d+$/i,''))];
 const names=new Map(project.nodes.map(n=>[n.id,n.data.label]));
 const required=!!project.extensions?.diagramCatalogueRequired;
 const open=report.decisions.filter(d=>d.status==='open');
 return <section className="project-overview" aria-label="Project overview">
  <header><div><span className="handoff-eyebrow">Board · project overview · revision {project.revision}</span><h1>{project.name}</h1><details className="overview-scope"><summary>Project scope</summary><p>{recordedOutcome(project)||'Inspect the scope, architecture and work remaining.'}</p></details></div><button className="btn" onClick={onDrawings}><GitFork size={16}/> Open drawings</button></header>
  <nav aria-label="Project summary sections">{['Overview','Traceability','Scenarios'].map(t=><button aria-pressed={tab===t} key={t} onClick={()=>setTab(t)}>{t}</button>)}</nav>
  {tab==='Overview'&&<>
   <div className="overview-metrics"><span><strong>{project.nodes.filter(n=>n.data.kind!=='note').length}</strong> components</span><span><strong>{report.interfaces.length}</strong> interfaces<small>{report.counts.contractReviews} need qualification</small></span><span><strong>{report.requirements.length}</strong> requirements</span><span><strong>{report.counts.dedicatedCovered}/{report.requirements.length}</strong> dedicated case definitions<small>Execution not recorded</small></span></div>
   <div className="overview-columns"><section><h2>First five requirements</h2>{report.requirements.slice(0,5).map(r=><p key={r.id}><strong>{requirementNumber(project,r.id)} <small>· {r.id}</small></strong> {r.statement}</p>)}<button className="link" onClick={onRequirements}>Read all requirements <ArrowUpRight size={14}/></button></section>
    <section><h2>Recorded decisions</h2>{decisions.slice(-5).map(d=><p key={d.id}><strong>{d.title||d.subject}</strong><br/>{d.decision}</p>)}{!decisions.length&&<p>No accepted decisions recorded.</p>}{!!history.length&&<details><summary>Diagram change history · {history.length} revisions</summary>{history.map(d=><p key={d.id}>{d.title} · {d.decision}</p>)}</details>}</section>
    <section><h2>Owner decisions</h2>{open.map(d=><details key={d.id}><summary>{d.question}</summary><p>{d.owner||'Owner needed'}</p><p>{d.blocks.join(' · ')}</p>{d.decisionBy&&<p>Needed before: {d.decisionBy}</p>}{d.interim&&<p>Interim: {d.interim}</p>}</details>)}{!open.length&&<p>No open owner questions recorded.</p>}</section>
    <section><h2>Work remaining</h2><ul><li>{report.requirements.length-report.counts.covered} requirements without linked case definitions</li><li>{report.counts.contractReviews} contracts need definition or owner input</li><li>{required?report.counts.types+' of 28 catalogue types have content':'The 28-type catalogue has not been requested'}</li><li>Defined tests need recorded execution evidence.</li></ul><button className="link" onClick={onReview}>Open handoff review <ArrowUpRight size={14}/></button></section></div>
  </>}
  {tab==='Traceability'&&<><label className="page-search"><Search size={15}/><input aria-label="Search traceability" placeholder="Find a requirement…" value={query} onChange={e=>setQuery(e.target.value)}/></label>
   <div className="traceability-scroll"><table><thead><tr><th>Requirement</th><th>Components</th><th>Linked interfaces</th><th>Case definitions</th></tr></thead><tbody>{report.requirements.filter(r=>(r.id+' '+r.statement).toLowerCase().includes(query.toLowerCase())).map(r=>{
    const blocks=r.links||[];const edges=report.interfaces.filter(e=>r.interfaceIds.includes(e.id));
    return <tr key={r.id}><td><strong>{requirementNumber(project,r.id)} <small>· {r.id}</small></strong><p>{r.statement}</p>{report.decisions.filter(q=>q.status==='open'&&q.requirementIds?.includes(r.id)).map(q=><details key={q.id}><summary className="trace-gap">Blocked · {q.id}</summary><p>{q.question}</p><p>{q.owner} · {q.decisionBy}</p><p>{q.interim}</p></details>)}</td><td>{blocks.map(id=><button key={id} className="link" onClick={()=>onBlock(id)}>{names.get(id)||id}</button>)}{!blocks.length&&<strong>Allocation missing</strong>}</td><td><details><summary>{edges.length} scenario-linked interfaces</summary>{edges.map(e=><p key={e.id}>{e.name} · {e.from} → {e.to}</p>)}</details>{!edges.length&&<strong className="trace-gap">Interface links missing</strong>}</td><td>{r.cases.map(c=><button key={c.blockId+'/'+c.id} className="link" onClick={()=>onBlock(c.blockId)}>{c.id}</button>)}{!r.cases.length&&<strong className="trace-gap">Cases missing</strong>}</td></tr>;
   })}</tbody></table></div></>}
  {tab==='Scenarios'&&<><p>Operational walkthroughs from the saved component specifications.</p>{groups.map(([name,lanes])=><details key={name}><summary>{name} · {new Set(lanes.map(s=>s.block)).size} components</summary>{lanes.map(s=><section className="scenario-lane" key={s.id}><h3>{s.name} · {s.blockName}</h3><button className="link" onClick={()=>onBlock(s.block)}>Open component and diagrams <ArrowUpRight size={14}/></button><ol className="scenario-steps">{(s.steps||[]).map((step,i)=><li key={i}>{typeof step==='string'?step:<><strong>{step.sender||'Sender'} → {step.receiver||'Receiver'}</strong><p>{step.action||step.description||step.name}</p>{step.interfaceId&&<small>{step.interfaceId} · {(step.requirementIds||[]).join(', ')}</small>}</>}</li>)}</ol></section>)}</details>)}{!scenarios.length&&<p>No structured operational scenarios recorded. Add a specification to develop them.</p>}</>}
 </section>;
}
