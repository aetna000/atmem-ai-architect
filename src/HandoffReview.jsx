import React,{useMemo,useState} from 'react';
import {ArrowUpRight,CheckCheck,FileText,GitFork,Search} from 'lucide-react';
import {buildReview,designReadiness,reviewDecisions} from './build-review.mjs';
import {diagramCatalogue,diagramGroups} from './architecture-diagrams.mjs';
import './handoff-review.css';

export function PageExplorer({project,onOpen,onCreate,onGenerate}){
 const [search,setSearch]=useState('');
 const model=project.extensions?.architectureDiagrams;
 const pages=[{id:'board',name:'Architecture board',group:'Overview',count:project.nodes.filter(n=>n.data.kind!=='note').length},
  ...(model?.views||[]).map(v=>({id:'view/'+v.id,name:v.name,group:diagramCatalogue.find(t=>t.id===v.kind)?.group,count:v.elementIds.length})),
  ...(project.extensions?.systemModel?.diagrams||[]).map(v=>({id:'system/'+v.id,name:v.name,group:'System behaviour',kind:v.kind,count:v.elementIds.length})),
  ...(project.extensions?.engineeringModel?.diagrams||[]).map(v=>({id:'engineering/'+v.id,name:v.name,group:'Detailed engineering',kind:v.kind,count:v.placements.length}))];
 return <section className="page-explorer" aria-label="Saved drawing pages">
  <header><h3>Project pages</h3><span>{pages.length}</span></header>
  <label className="page-search"><Search size={15}/><input aria-label="Search saved pages" placeholder="Find a page…" value={search} onChange={e=>setSearch(e.target.value)}/></label>
  <div className="page-explorer-list">{['Overview',...diagramGroups,'System behaviour','Detailed engineering'].map(group=>{
   const rows=pages.filter(p=>p.group===group&&[p.name,p.group,p.kind||''].join(' ').toLowerCase().includes(search.toLowerCase()));
   return rows.length>0&&<section key={group}><h4>{group}</h4>{rows.map(p=><button key={p.id} onClick={()=>onOpen(p.id)}><GitFork size={14}/><span>{p.name}<small>{p.count?p.count+' elements':'Empty page'}</small></span><ArrowUpRight size={12}/></button>)}</section>;
  })}</div>
  <footer><button className="btn primary" onClick={onGenerate}>Generate from spec</button><button className="btn" onClick={onCreate}>New page</button></footer>
 </section>;
}
export function HandoffReview({project,onOpen,onDelivery,busy=false}){
 const review=useMemo(()=>buildReview(project),[project]);
 const [tab,setTab]=useState('Diagrams'),[query,setQuery]=useState('');
 const catalogueRequested=!!project.extensions?.diagramCatalogueRequired;
 const savedPages=(project.nodes.some(n=>n.data.kind!=='note')?1:0)+(project.extensions?.architectureDiagrams?.views.length||0)+(project.extensions?.systemModel?.diagrams.length||0)+(project.extensions?.engineeringModel?.diagrams.length||0);
 const decisions=reviewDecisions(project,review),readiness=designReadiness(review,catalogueRequested);
 const rows={Diagrams:review.diagrams.filter(type=>catalogueRequested||type.pages.length),Decisions:decisions,Interfaces:review.interfaces,Acceptance:review.cases}[tab];
 const shown=rows.filter(row=>JSON.stringify(row).toLowerCase().includes(query.toLowerCase()));
 return <section className="handoff-review" aria-label="Developer handoff review">
  <header><div><span className="handoff-eyebrow">Developer handoff</span><h2>Review the build package</h2></div>{onDelivery&&<button className="btn" onClick={onDelivery}><FileText size={15}/> Open handoff</button>}</header>
  <aside className="handoff-verdict"><strong>{readiness.title}</strong>{readiness.gaps.length>0&&<ul>{readiness.gaps.map(g=><li key={g}>{g}</li>)}</ul>}</aside>
  {review.counts.contractReviews>0&&<details><summary>Contracts requiring review · {review.counts.contractReviews}</summary>{review.interfaces.filter(row=>row.missing.length||row.pending.length).map(row=><button className="link" key={row.id} onClick={event=>{event.currentTarget.closest('details')?.removeAttribute('open');setTab('Interfaces');setQuery(row.id);}}>{row.name} · {row.id}</button>)}</details>}
  <h3>Inspect details</h3>
  <div className="handoff-metrics">
   {[['Diagrams',catalogueRequested?review.counts.types+'/28':savedPages,catalogueRequested?'catalogue types with content':'saved drawing pages; catalogue optional'],['Decisions',decisions.length,review.counts.open+' awaiting an owner'],['Interfaces',review.interfaces.length,review.counts.contractReviews+' need qualification'],['Acceptance',review.cases.length,review.counts.dedicatedCovered+'/'+review.requirements.length+' dedicated · '+review.counts.covered+'/'+review.requirements.length+' linked']].map(([name,value,label])=><button key={name} aria-pressed={tab===name} onClick={()=>{setTab(name);setQuery('');}}><strong>{value}</strong><span>{name==='Acceptance'?'Test definitions':name}</span><small>{label}</small>{name==='Acceptance'&&<small>Execution not recorded</small>}</button>)}
  </div>
  <label className="page-search"><Search size={16}/><input aria-label="Search handoff records" placeholder={'Search '+tab.toLowerCase()} value={query} onChange={e=>setQuery(e.target.value)}/></label>
  <div className="handoff-records">{shown.map(row=><details key={row.id}><summary><span>{row.name||row.question}</span><small>{tab==='Diagrams'?(row.pages.some(p=>p.populated&&!p.exampleOnly)?row.pages.length+(row.pages.length===1?' page':' pages'):'Missing content'):tab==='Decisions'?row.status:tab==='Acceptance'?'Defined · execution required':row.missing.length?'Needs definition':row.pending.length?'Blocked · owner input':'Documented'}</small></summary>
   {tab==='Diagrams'?<><p>{row.check}</p>{row.pages.map(page=><div className="handoff-page" key={page.id}><button className="link" disabled={busy} onClick={()=>onOpen('view/'+page.id)}>{page.name} <ArrowUpRight size={13}/></button>{page.findings.length>0&&<details><summary>{page.findings.length} review items</summary><ul>{page.findings.map((v,i)=><li key={i}>{v}</li>)}</ul></details>}</div>)}</>:
    tab==='Decisions'?<><p>{row.owner||'Owner needed'}</p><p>{row.answer||'Decision pending'}</p>{row.requirementIds?.length>0&&<p>Blocked requirements: {row.requirementIds.join(', ')}</p>}{row.interfaceIds?.length>0&&<p>Blocked interfaces: {row.interfaceIds.join(', ')}</p>}{row.decisionBy&&<p>Needed before: {row.decisionBy}</p>}{row.interim&&<p>Interim: {row.interim}</p>}<small>{row.blocks.join(' · ')}</small></>:
    tab==='Interfaces'?<><p>{row.from} → {row.to}</p><dl>{Object.entries(row.contract).map(([k,v])=><React.Fragment key={k}><dt>{k}</dt><dd>{v}</dd></React.Fragment>)}</dl></>:
    <><p>{row.blockName} · {row.requirementIds.join(', ')}</p><dl>{['environment','setup','input','action','expected','evidence'].map(key=><React.Fragment key={key}><dt>{key}</dt><dd>{row[key]}</dd></React.Fragment>)}</dl></>}
  </details>)}
  {!shown.length&&<p>{query?'No matching '+tab.toLowerCase()+'.':tab==='Diagrams'&&!catalogueRequested?'The 28-type catalogue has not been requested for this project. Open saved pages from the Board.':'No '+tab.toLowerCase()+' recorded.'}</p>}</div>
  <footer><CheckCheck size={16}/><span>Test definitions and owner decisions need recorded results before release.</span></footer>
 </section>;
}
