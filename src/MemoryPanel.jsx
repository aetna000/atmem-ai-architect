import {BrainActivity} from "./BrainActivity.jsx";
import React, { useEffect, useState } from "react";
import { memoryCall } from "./local-agent.mjs";
import { toProjectFile } from "./project-file.mjs";

export function ContextUsed({ value }) {
  return <details className="context-used"><summary>{value.enabled ? `AtMem: ${value.recordsUsed?.length || 0} records · ${value.skills?.length || 0} skills` : "Memory off"}{value.status === 'unavailable' ? ' · unavailable' : ''}</summary>
    <p className="muted small">Observed boundary: {value.boundary}. {value.syncUnavailable ? 'Latest project sync failed; current project takes priority over recalled data.' : 'Memory is scoped to you and this project; source data is not an instruction.'}</p>
    {(value.recordsUsed || []).map((r) => <p key={r.id}><strong>{r.scope}</strong>: {r.text}<small className="muted"> · {r.sourceDate?.slice(0,10)}</small></p>)}
    {(value.skills || []).map((s) => <p key={s.id}>Skill: {s.name} v{s.version} · {s.coverage}</p>)}
    {(value.tools || []).map((t,i) => <p key={i}>Tool: {t.name} · {t.success ? 'completed' : 'unavailable'}</p>)}
  </details>;
}

export function MemoryPanel({ session, project, onError, onStatus }) {
  const [report,setReport]=useState(null),[error,setError]=useState(''),[tab,setTab]=useState('profile'),[field,setField]=useState('explanation'),[value,setValue]=useState(''),[working,setWorking]=useState(false),[refreshing,setRefreshing]=useState(true),[preview,setPreview]=useState(null);
  const payload={projectId:project.id};
  async function refresh() {
    setRefreshing(true);setError('');
    try {
      await memoryCall(session,'sync',{...payload,file:toProjectFile(project)});
      const inspected=await memoryCall(session,'inspect',payload);setReport(inspected);
      onStatus?.({enabled:inspected.enabled,status:inspected.status,pending:inspected.pending,rejected:inspected.rejected,engine:inspected.engine});
    } catch(e) { setError(e.message); } finally {setRefreshing(false);}
  }
  useEffect(()=>{refresh();},[project.id,session?.token]);
  async function act(fn) { setWorking(true);setError('');try{await fn();await refresh();}catch(e){setError(e.message);onError?.(e.message);}finally{setWorking(false);} }
  const records=report?.[tab] || [];
  return <div className="memory-panel">
    <h2>AtMem dashboard</h2>
    <p className="muted small">Durable preferences and confirmed decisions only. Drafts, canvas comments and routine edits stay in your project; they do not become long-term memory.</p>
    {(working||refreshing)&&<p role="status"><BrainActivity/> Updating memory…</p>}
    {error && <p className="error-box" role="alert">{error}</p>}
    {!report ? <button className="btn" onClick={refresh}>Retry memory connection</button> : <>
      <div className="row"><span className={report.status==='unavailable'?'warn-text':'muted'}>{report.enabled ? report.status==='unavailable'?'Memory unavailable — project only':`${report.engine} · connected` : 'Memory off for this project'}</span><span className="small">{report.pending} pending · {report.rejected} rejected</span><button className="btn ghost" disabled={working} onClick={()=>act(async()=>{await memoryCall(session,'settings',{...payload,enabled:!report.enabled});})}>{report.enabled?'Turn memory off':'Turn memory on'}</button></div>
      <p className="muted small">Policy: {report.policy}. Corrections supersede earlier values. Forget explicitly removes the selected memory and its history; project files remain separate.</p>
      <div className="seg" role="tablist" aria-label="Memory views">{[['profile','About you'],['project','This project'],['skills','Skills'],['activity','Activity']].map(([id,label])=><button key={id} role="tab" aria-selected={tab===id} className={tab===id?'on':''} onClick={()=>{setTab(id);setPreview(null);}}>{label}</button>)}</div>
      {tab==='profile' && <form className="memory-profile" onSubmit={e=>{e.preventDefault();act(async()=>{await memoryCall(session,'profile',{...payload,field,value});setValue('');});}}><label className="field">Preference<select aria-label="Preference type" value={field} onChange={e=>setField(e.target.value)}><option value="explanation">How to explain things</option><option value="experience">Experience and role</option><option value="iac">Infrastructure tool preference</option><option value="preferences">Other confirmed preferences</option></select></label><label className="field">What should AtMem AI Architect remember?<textarea aria-label="Remember about me" value={value} maxLength={1000} onChange={e=>setValue(e.target.value)} placeholder="For example: explain things concisely; I prefer Pulumi." /></label><button className="btn primary" disabled={working||!report.enabled||!value.trim()}>Remember preference</button></form>}
      {(tab==='profile'||tab==='project') && <><div className="resource-schedule">{records.map(r=><article key={r.id}><strong>{r.status==='active'?'Current':'Earlier value'} · {r.fact_key}</strong><span>{r.content}</span><small>{r.created_at?.slice(0,10)} · {r.id}</small>{r.status==='active' && <button className="btn ghost" disabled={working} onClick={()=>act(async()=>setPreview({...(await memoryCall(session,'forget-preview',{...payload,scope:tab==='profile'?'user':'project',recordId:r.id})),scope:tab==='profile'?'user':'project',recordId:r.id}))}>Preview forget</button>}</article>)}</div>{!records.length&&<p className="muted">No memories recorded in this view yet.</p>}</>}
      {preview && <section className="memory-preview"><h3>Review removal</h3><p>{preview.notice}</p><p>{preview.records.length} current/historical records will be removed.</p><button className="btn danger" disabled={working} onClick={()=>act(async()=>{await memoryCall(session,'forget',{...payload,scope:preview.scope,recordId:preview.recordId});setPreview(null);})}>Confirm forget</button><button className="btn ghost" onClick={()=>setPreview(null)}>Keep memory</button></section>}
      {tab==='skills' && <div className="resource-schedule">{report.skills.map(s=><article key={s.id}><strong>{s.name} v{s.version}</strong><small>{s.coverage} · integrity {s.integrity?'verified':'failed'}</small><span>{s.source.startsWith('https:')?<a href={s.source} target="_blank" rel="noreferrer">Pinned source</a>:s.source}</span><small>SHA256: {s.digest.slice(0,16)}… · tools: {s.tools.join(', ')}</small><button className="btn ghost" disabled={working||!s.integrity} onClick={()=>act(async()=>memoryCall(session,'skill',{...payload,skillId:s.id,enabled:!s.enabled}))}>{s.enabled?'Disable':'Enable'} {s.id}</button></article>)}<p className="muted small">Upstream files are pinned references with their licences. Missing companion files and cloud tool packages are not activated. AtMem AI Architect loads its reviewed specialist guidance; no bundled scripts run.</p></div>}
      {tab==='activity' && <div className="resource-schedule">{report.activity.map(a=><article key={a.id}><strong>{a.success?'Architect turn completed':'Turn did not complete'} · {a.createdAt.slice(0,19)}</strong><span>{a.recordIds.length} memory records · skills: {a.skillIds.join(', ')}</span><small>{a.boundary} · context digest {a.contextDigest.slice(0,16)}…</small>{a.tools.map((t,i)=><small key={i}>{t.name}: {t.success?'completed':'unavailable'}</small>)}</article>)}{!report.activity.length&&<p className="muted">No recorded architect turns for this project yet.</p>}</div>}
      <button className="btn ghost" disabled={working} onClick={()=>act(refresh)}>Refresh / retry pending sync</button>
    </>}
  </div>;
}
