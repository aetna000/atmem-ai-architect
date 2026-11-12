import {emulationGuidance,emulationRepairTask} from './emulation-guidance.mjs';
import {toProjectFile} from './project-file.mjs';
import {BrainActivity} from "./BrainActivity.jsx";
import React,{useState} from 'react';
import {Play,X,CheckCircle2,AlertCircle} from 'lucide-react';
import {emulationFeedback,emulationEvidenceSummary} from './emulation-feedback.mjs';
export function EmulationPanel({project,session,emulation,onDiscuss,discussionBusy=false,onOpenComponent,onClose,onBuild}){
 const {result,previous,running}=emulation;
 const [expanded,setExpanded]=useState(false),[taskError,setTaskError]=useState('');
 const readiness=emulationGuidance(project,result)||emulation.preflight;
 const guidance=readiness?.action==='build-and-test'&&!onBuild?{...readiness,next:'Application implementation is unavailable in this session. Download the repair task for the missing code and tests; testing can resume once that implementation is available.'}:readiness;
 const feedback=emulationFeedback(project,result),thinking=discussionBusy&&!!result;
 const title=running?'Testing this design…':thinking?'Architect is reviewing…':guidance?guidance.title:result?.status==='passed'?'Local checks passed':result?'Let’s resolve the next step':previous?'Design changed — rerun needed.':'Local implementation checks';
 function saveReport(){const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`atmem-local-checks-r${project.revision}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 function saveTask(){try{toProjectFile(project);const url=URL.createObjectURL(new Blob([emulationRepairTask(project,result)],{type:'text/markdown'}));const a=document.createElement('a');a.href=url;a.download='architect-repair-task.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);setTaskError('');}catch(error){setTaskError(error.message);}}
 const icon=(label,Icon,action,options={})=><button type="button" className={`emulation-icon ${options.active?'active':''}`} aria-label={label} title={label} onClick={action} disabled={options.disabled} aria-pressed={options.toggle?options.active:undefined}><Icon size={19}/></button>;
 return <aside className={`emulation-panel ${running||thinking?'is-working':''}`} aria-label="Local checks">
  <div className="emulation-heading"><span className={`emulation-orb ${running||thinking?'working':''}`}><BrainActivity size={34} active={running||thinking}/></span><div><span className="emulation-eyebrow">LOCAL CHECKS</span><h3 aria-live="polite">{title}</h3></div>{onClose&&icon('Close local checks',X,onClose)}</div>
  <div className="emulation-controls row">
   <button type="button" className="btn primary" aria-label="Run local checks" aria-busy={running||thinking} title={running?'Local checks running':thinking?'Architect is reviewing':emulation.preflight?'Complete the next step below before testing':'Run local checks'} disabled={running||thinking||!session?.token||!!emulation.preflight} onClick={()=>emulation.run()}>{running||thinking?<BrainActivity size={24}/>:<Play size={19}/>} Run local checks</button>
   {running&&<button type="button" className="btn" onClick={emulation.stop}>Stop waiting</button>}
   {result&&onDiscuss&&<button type="button" className="btn" disabled={discussionBusy||running} onClick={()=>onDiscuss(result,'question')}>Ask Architect about these results</button>}
   <button type="button" className="btn" aria-expanded={expanded} onClick={()=>setExpanded(!expanded)}>{expanded?'Hide details':'Check details and settings'}</button>
  </div>
  <div className="emulation-track" aria-label="Local check progress"><span className={running?'current':result?'complete':''}>Test</span><i/><span className={thinking?'current':''}>Review</span><i/><span>Improve</span><i/><span>Retest</span></div>
  {running&&<div className="emulation-progress" role="progressbar" aria-label="Running local checks"><span/></div>}
  <p className="emulation-caption">{running?'Checking the generated code. Keep exploring the diagram.':thinking?'Your architect is working through the evidence in chat.':guidance?guidance.reason:result?emulationEvidenceSummary(result):'Runs local checks on the generated implementation and shows the results here. Monitoring needs its own implementation and configuration.'}</p>
  {guidance&&!running&&!thinking&&<div className="emulation-next-step"><p><strong>Next:</strong> {guidance.next}</p>{guidance.action==='build-and-test'&&onBuild?<button className="btn primary" disabled={discussionBusy} onClick={onBuild}>Implement and check</button>:guidance.owner==='engineering'?<button className="btn primary" onClick={saveTask}>Download repair task</button>:guidance.needsModel?<button className="btn primary" disabled={discussionBusy} onClick={()=>onDiscuss?.(result,'correction')}>Work through this with Architect</button>:<button className="btn ghost" onClick={()=>setExpanded(true)}>See test details</button>}{guidance.componentId&&onOpenComponent&&<button className="link" onClick={()=>onOpenComponent(guidance.componentId)}>Review affected block</button>}{taskError&&<p role="alert">{taskError}</p>}</div>}
  {emulation.retestLimitReached&&<p role="status">Two automatic retests are complete. Review the latest correction, then choose Run local checks to continue.</p>}
  {expanded&&<div className="emulation-evidence">
   <label><input type="checkbox" checked={emulation.coach} onChange={event=>emulation.setCoach(event.target.checked)}/> Ask Architect to explain new check results automatically</label>
   <label><input type="checkbox" checked={emulation.autoRetest} onChange={event=>emulation.setAutoRetest(event.target.checked)}/> Rerun checks after an accepted correction (up to two attempts)</label>
   <p>Corrections follow Draw as we talk and remain undoable. Stop waiting ends your wait; server work can continue until its time limit.</p>
   {result?.artifactDigest&&<button type="button" className="btn" onClick={saveReport}>Download check report (JSON)</button>}
   {feedback&&<p>{feedback.question}</p>}{result?.message&&<p>{result.message}</p>}
   {result?.backend&&<p>{result.backend} {result.backendVersion} · r{result.designRevision} · {result.environment}</p>}
   {result?.checks?.map((c,i)=><div className="emulation-check" key={i}>{c.passed?<CheckCircle2 size={16}/>:<AlertCircle size={16}/>}<span>{c.name}{c.message&&<small>{c.message}</small>}</span></div>)}
   {result?.blockers?.map((b,i)=><p key={i}>{b}</p>)}
   {!!result?.capabilities?.length&&<details><summary>What was checked</summary><ul>{result.capabilities.map((item,i)=><li key={i}>{item.service}: {item.mode}</li>)}</ul></details>}
   {!!result?.emulatorPatches?.length&&<details><summary>Emulator compatibility fixes</summary><ul>{result.emulatorPatches.map(item=><li key={item.id}>{item.id}: {item.reason}</li>)}</ul></details>}
   {!!result?.limitations?.length&&<details open><summary>Still requires cloud verification</summary><ul>{result.limitations.map((v,i)=><li key={i}>{v}</li>)}</ul></details>}
  </div>}
 </aside>;
}
