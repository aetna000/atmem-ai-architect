import {emulationGuidance,emulationRepairTask} from './emulation-guidance.mjs';
import {toProjectFile} from './project-file.mjs';
import {BrainActivity} from "./BrainActivity.jsx";
import React,{useState} from 'react';
import {Play,Square,BrainCircuit,Repeat2,Download,ChevronDown,X,CheckCircle2,AlertCircle,HelpCircle,Sparkles} from 'lucide-react';
import {emulationFeedback,emulationEvidenceSummary} from './emulation-feedback.mjs';
export function EmulationPanel({project,session,emulation,onDiscuss,discussionBusy=false,onOpenComponent,onClose}){
 const {result,previous,running}=emulation;
 const [expanded,setExpanded]=useState(false),[taskError,setTaskError]=useState('');
 const guidance=emulationGuidance(project,result);
 const feedback=emulationFeedback(project,result),thinking=discussionBusy&&!!result;
 const title=running?'Testing this design…':thinking?'Architect is reviewing…':guidance?guidance.title:result?.status==='passed'?'Local emulation checks passed':result?'Let’s resolve the next step':previous?'Design changed — rerun needed.':'Ready to test your design';
 function saveReport(){const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`atmem-emulation-r${project.revision}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 function saveTask(){try{toProjectFile(project);const url=URL.createObjectURL(new Blob([emulationRepairTask(project,result)],{type:'text/markdown'}));const a=document.createElement('a');a.href=url;a.download='architect-repair-task.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);setTaskError('');}catch(error){setTaskError(error.message);}}
 const icon=(label,Icon,action,options={})=><button type="button" className={`emulation-icon ${options.active?'active':''}`} aria-label={label} title={label} onClick={action} disabled={options.disabled} aria-pressed={options.toggle?options.active:undefined}><Icon size={19}/></button>;
 return <aside className={`emulation-panel ${running||thinking?'is-working':''}`} aria-label="Cloud emulation">
  <div className="emulation-heading"><span className={`emulation-orb ${running||thinking?'working':''}`}><BrainActivity size={34} active={running||thinking}/></span><div><span className="emulation-eyebrow">EMULATE · IMPROVE</span><h3 aria-live="polite">{title}</h3></div>{onClose&&icon('Minimize emulation',X,onClose)}</div>
  <div className="emulation-controls">
   <button type="button" className="emulation-icon active" aria-label="Emulate locally" aria-busy={running||thinking} title={running?'Emulation running':thinking?'Architect is reviewing':'Emulate locally'} disabled={running||thinking||!session?.token} onClick={()=>emulation.run()}>{running||thinking?<BrainActivity size={24}/>:<Play size={19}/>}</button>
   {running&&icon('Stop waiting',Square,emulation.stop)}
   {icon('Architect mentoring',BrainCircuit,()=>emulation.setCoach(!emulation.coach),{toggle:true,active:emulation.coach})}
   {icon('Automatically retest corrections (up to two rounds)',Repeat2,()=>emulation.setAutoRetest(!emulation.autoRetest),{toggle:true,active:emulation.autoRetest})}
   {result&&icon('Discuss a correction with the architect',Sparkles,()=>onDiscuss?.(result,'correction'),{disabled:discussionBusy||running})}
   {result&&icon('Ask a focused question',HelpCircle,()=>onDiscuss?.(result,'question'),{disabled:discussionBusy||running})}
   {result?.artifactDigest&&icon('Download emulation report',Download,saveReport)}
   <button className="emulation-icon" title="Show test evidence and settings" aria-label="Show test evidence and settings" aria-expanded={expanded} onClick={()=>setExpanded(!expanded)}><ChevronDown size={18} style={{transform:expanded?'rotate(180deg)':undefined}}/></button>
  </div>
  <div className="emulation-track" aria-label="Emulation progress"><span className={running?'current':result?'complete':''}>Test</span><i/><span className={thinking?'current':''}>Review</span><i/><span>Improve</span><i/><span>Retest</span></div>
  {running&&<div className="emulation-progress" role="progressbar" aria-label="Running local checks"><span/></div>}
  <p className="emulation-caption">{running?'Checking the generated code. Keep exploring the diagram.':thinking?'Your architect is working through the evidence in chat.':guidance?guidance.reason:result?emulationEvidenceSummary(result):'Play runs local checks on this architecture. No cloud deployment.'}</p>
  {guidance&&!running&&!thinking&&<div className="emulation-next-step"><p><strong>Next:</strong> {guidance.next}</p>{guidance.owner==='engineering'?<button className="btn primary" onClick={saveTask}>Prepare repair task</button>:guidance.needsModel?<button className="btn primary" disabled={discussionBusy} onClick={()=>onDiscuss?.(result,'correction')}>Work through this with Architect</button>:<button className="btn ghost" onClick={()=>setExpanded(true)}>See test details</button>}{guidance.componentId&&onOpenComponent&&<button className="link" onClick={()=>onOpenComponent(guidance.componentId)}>Review affected block</button>}{taskError&&<p role="alert">{taskError}</p>}</div>}
  {emulation.retestLimitReached&&<p role="status">Two automatic retests are complete. Review the latest correction, then choose Emulate locally to continue.</p>}
  {expanded&&<div className="emulation-evidence">
   <p>Mentoring {emulation.coach?'on':'off'} · Automatic retests {emulation.autoRetest?'on':'off'}. Changes follow Draw as we talk and remain undoable.</p>
   {feedback&&<p>{feedback.question}</p>}{result?.message&&<p>{result.message}</p>}
   {result?.backend&&<p>{result.backend} {result.backendVersion} · r{result.designRevision} · {result.environment}</p>}
   {result?.checks?.map((c,i)=><div className="emulation-check" key={i}>{c.passed?<CheckCircle2 size={16}/>:<AlertCircle size={16}/>}<span>{c.name}{c.message&&<small>{c.message}</small>}</span></div>)}
   {result?.blockers?.map((b,i)=><p key={i}>{b}</p>)}
   {!!result?.capabilities?.length&&<details><summary>What was emulated</summary><ul>{result.capabilities.map((item,i)=><li key={i}>{item.service}: {item.mode}</li>)}</ul></details>}
   {!!result?.emulatorPatches?.length&&<details><summary>Emulator compatibility fixes</summary><ul>{result.emulatorPatches.map(item=><li key={item.id}>{item.id}: {item.reason}</li>)}</ul></details>}
   {!!result?.limitations?.length&&<details open><summary>Still requires cloud verification</summary><ul>{result.limitations.map((v,i)=><li key={i}>{v}</li>)}</ul></details>}
  </div>}
 </aside>;
}
