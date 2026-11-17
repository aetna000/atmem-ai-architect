import React,{useEffect,useRef,useState} from 'react';
import {Download,FolderOpen,LoaderCircle,RefreshCw,ShieldCheck,Square,ArrowRight} from 'lucide-react';
import {ACTIVE,progress,readSelection} from './model.mjs';
import './maintenance.css';
import CampaignPanel from './CampaignPanel.jsx';

function download(name,value){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function downloadPatch(changes){const url=URL.createObjectURL(new Blob([changes.map(c=>c.diff).join('\n')],{type:'text/x-patch'}));const a=document.createElement('a');a.href=url;a.download='atmem-infrastructure-upgrade.patch';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

export default function MaintenancePanel({session,project,onSection}) {
 const [mode,setMode]=useState('single');
 const [data,setData]=useState(null),[caps,setCaps]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[selected,setSelected]=useState(null),[inspected,setInspected]=useState(false);
 const folder=useRef(null),importer=useRef(null),current=useRef(null),mounted=useRef(true);
 const owner=useRef(project.id);owner.current=project.id;
 const aggregate=data?.aggregate,job=aggregate?.jobs.at(-1),state=progress(job),active=ACTIVE.has(job?.status);
 const request=async(path,body,headers={})=>{
  if(!session?.token)throw Error('Connect the local helper first.');
  const r=await fetch('/api/maintenance'+path,{method:body===undefined?'GET':'POST',signal:AbortSignal.timeout(20000),headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`,...headers},...(body===undefined?{}:{body:JSON.stringify(body)})});
  const value=await r.json();if(!r.ok)throw Error(typeof value.detail==='string'?value.detail:'Request failed. Reload and try again.');return value;
 };
 const accept=value=>{if(mounted.current&&owner.current===project.id){if(current.current?.aggregate?.projectId===value.aggregate?.projectId&&current.current.revision>value.revision)return;setData(value);current.current=value;}};
 const action=async(fn)=>{setBusy(true);setError('');try{await fn();}catch(e){if(mounted.current)setError(e.message);}finally{if(mounted.current)setBusy(false);}};
 useEffect(()=>{
  mounted.current=true;
  action(async()=>{
   setCaps(await request('/capabilities'));
   const existing=project.extensions?.maintenance;
   if(existing){
    if(project.extensions?.maintenanceNeedsImport)accept(await request('/projects/import',{projectId:crypto.randomUUID(),section:existing}));
    else {
     try{accept(await request('/projects/'+existing.aggregate.projectId));}
     catch{accept(await request('/projects/import',{projectId:crypto.randomUUID(),section:existing}));}
    }
   }
  });
  return()=>{mounted.current=false;};
 },[session?.token,project.id]);
 useEffect(()=>{
  if(!active||!aggregate)return;
  let stopped=false,timer;
  const poll=async()=>{try{const value=await request('/projects/'+aggregate.projectId);if(!stopped){accept(value);setError('');}}catch(e){if(!stopped)setError(e.message);}finally{if(!stopped)timer=setTimeout(poll,1500);}};
  timer=setTimeout(poll,500);return()=>{stopped=true;clearTimeout(timer);};
 },[active,aggregate?.projectId,session?.token]);
 const saveSection=async()=>{const section=await request('/projects/'+current.current.aggregate.projectId+'/export');if(mounted.current&&owner.current===project.id)onSection?.(section);return section;};
 useEffect(()=>{if(aggregate&&!active)action(async()=>{await saveSection();});},[aggregate?.revision,active]);
 const load=async(files)=>action(async()=>{const value=await readSelection(files);setSelected(value);setInspected(false);});
 const inspect=()=>action(async()=>{
  if(!selected)throw Error('Select Terraform source first.');
  const value=aggregate?await request('/projects/'+aggregate.projectId+'/inventory',{expectedProjectRevision:aggregate.revision,files:selected}):await request('/projects',{projectId:crypto.randomUUID(),name:project.name||'Infrastructure upgrade',files:selected});
  accept(value);setInspected(true);setSelected(null);
 });
 const start=()=>action(async()=>{accept(await request('/projects/'+aggregate.projectId+'/prepare',{expectedProjectRevision:aggregate.revision,sourceDigest:aggregate.snapshots.at(-1).treeDigest,recipeDigest:data.recipeDigest,computeConfirmed:true},{'Idempotency-Key':crypto.randomUUID()}));});
 const cancel=()=>action(async()=>{const fresh=await request('/projects/'+aggregate.projectId);accept(await request('/projects/'+aggregate.projectId+'/jobs/'+job.id+'/cancel',{expectedProjectRevision:fresh.revision}));});
 return <div className="maintenance-panel">
  <div className="maintenance-actions" aria-label="Maintenance workflow"><button className="btn" aria-pressed={mode==='single'} disabled={active} onClick={()=>setMode('single')}>Single repository</button><button className="btn" aria-pressed={mode==='campaign'} disabled={active} onClick={()=>setMode('campaign')}>Coordinated projects</button></div>
  {mode==='campaign'?<CampaignPanel session={session} project={project} available={caps?.status==='available'}/>:<>
  <header><span className="maintenance-eyebrow">INFRASTRUCTURE MAINTENANCE</span><h2>Prepare an AWS upgrade</h2><p>AWS provider 5.100.0 → 6.0.0 · Batch queue migration.</p></header>
  <div className="maintenance-boundary"><ShieldCheck size={18}/><span>Local schema checks. Original files stay unchanged. No deployment or AI calls.</span></div>
  {error&&<p role="alert" className="maintenance-error">{error}</p>}
  <div className="maintenance-actions">
   <input ref={folder} hidden type="file" webkitdirectory="" multiple onChange={e=>load(e.target.files)} aria-label="Select Terraform repository folder"/>
   <button className="btn" onClick={()=>folder.current.click()} disabled={busy||active}><FolderOpen size={16}/>Select repository folder</button>
   <input ref={importer} hidden type="file" accept="application/json,.json" aria-label="Import maintenance project" onChange={e=>{const file=e.target.files[0];if(file)action(async()=>{if(file.size>64_000_000)throw Error('Import exceeds 64 MB.');const section=JSON.parse(await file.text());accept(await request('/projects/import',{projectId:crypto.randomUUID(),section}));setInspected(true);});}}/>
   <button className="btn" disabled={busy||active} onClick={()=>importer.current.click()}>Import migration</button>
   {selected&&<button className="btn primary" onClick={inspect} disabled={busy}>Inspect {Object.keys(selected).length} {Object.keys(selected).length===1?'file':'files'} <ArrowRight size={16}/></button>}
  </div>
  <p className="muted">Secret files and installed dependencies are excluded. Review your selected source before continuing.</p>
  {caps?.status==='setup_required'&&<div className="maintenance-setup"><strong>Local worker setup required</strong><p>Install pinned tools and qualify Docker before preparing changes.</p><details><summary>Setup instructions</summary><p>See docs/INFRASTRUCTURE_MAINTENANCE.md for the qualified platform and command.</p></details></div>}
  {aggregate&&<>
   <div className="maintenance-source"><strong>{aggregate.snapshots.at(-1).files.length} {aggregate.snapshots.at(-1).files.length===1?'file':'files'} selected</strong><details><summary>Review selected paths</summary><ul>{aggregate.snapshots.at(-1).files.map(f=><li key={f.path}>{f.path}</li>)}</ul></details></div>
   {!active&&<div className="maintenance-actions"><button className="btn primary" disabled={busy||caps?.status!=='available'||!!selected} onClick={start}>{job?<RefreshCw size={16}/>:<ShieldCheck size={16}/>}Prepare migration</button><button className="btn" disabled={busy} onClick={()=>action(async()=>download('atmem-migration.json',await saveSection()))}><Download size={16}/>Export migration</button></div>}
   {job&&<section className="maintenance-progress" aria-label="Migration progress">
    <div className="maintenance-status" role="status">{active&&<LoaderCircle className="maintenance-spin" size={20}/>}<strong>{state.label}</strong>{active&&<button className="btn" disabled={busy} onClick={cancel}><Square size={14}/>Cancel</button>}</div>
    {active&&<div className="maintenance-track" role="progressbar" aria-label={state.label}><span/></div>}
    <ol className="maintenance-stages">{['Read source','Baseline','Breaking control','Patch','Candidate checks'].map((label,i)=><li key={label} className={job.status==='ready_for_review'||[...state.completed].some(k=>({baseline:1,control:2,patch:3}[k])>=i)?'done':''}>{label}</li>)}</ol>
    {job.findings.map((f,i)=><p className="maintenance-error" key={i}>{f.message}</p>)}
    {job.status==='ready_for_review'&&<p>Review the patch. State behavior and deployment still need destination-specific approval.</p>}
    {job.status==='ready_for_review'&&job.candidate&&<button className="btn" onClick={()=>downloadPatch(job.candidate.changes)}><Download size={16}/>Download patch</button>}
    {job.candidate&&<details open={job.status==='ready_for_review'}><summary>Review patch · {job.candidate.changes.length} files</summary>{job.candidate.changes.map(c=><div key={c.path}><h3>{c.path}</h3><pre tabIndex={0}>{c.diff}</pre></div>)}</details>}
    {!!job.receipts.length&&<details><summary>Check evidence · {job.receipts.length} receipts</summary><ul>{job.receipts.map(r=><li key={r.id}><strong>{r.kind}: {r.kind==='control'&&r.status==='failed'&&job.status==='ready_for_review'?'expected schema break':r.status}</strong> · {r.durationSeconds.toFixed(1)}s<details><summary>Diagnostics</summary><pre tabIndex={0}>{r.output}</pre></details></li>)}</ul></details>}
   </section>}
  </>}
 </>}
 </div>;
}
