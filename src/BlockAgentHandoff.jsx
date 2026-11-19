import React,{useState} from 'react';
import {zipSync,strToU8} from 'fflate';
import {toProjectFile} from './project-file.mjs';

export function BlockAgentHandoff({project,node,busy,session,onPrepareSources}){
 const [working,setWorking]=useState(false),[error,setError]=useState(''),[status,setStatus]=useState('');
 async function prepare(withFigures=false){
  const snapshot=structuredClone(project),now=new Date();
  let sourceSession=session;
  if(withFigures&&(snapshot.extensions?.architectureDocuments||snapshot.extensions?.designSources?.some(source=>source.figureEvidence?.figures?.length))&&onPrepareSources)sourceSession=await onPrepareSources(project);
  const {createBlockHandoff,blockHandoffExportFiles}=await import('./block-handoff.mjs');
  let handoff=createBlockHandoff(JSON.stringify(toProjectFile(snapshot,now)),node.id,{generatedAt:now.toISOString()});
  if(withFigures){const {attachReviewedDraftFiles}=await import('./reviewed-draft.mjs');const evidence=await attachReviewedDraftFiles(snapshot,handoff.files,{session:sourceSession});const {attachCapturedEvidenceFiles}=await import('./capture-download.mjs');const captured=await attachCapturedEvidenceFiles(snapshot,evidence.files,{session:sourceSession});handoff={...handoff,files:captured.files};const {attachHandoffSourceFigures}=await import('./source-handoff.mjs');return attachHandoffSourceFigures(handoff,{session:sourceSession});}
  return {handoff,files:blockHandoffExportFiles(handoff)};
 }
 async function run(action){if(working)return;setWorking(true);setError('');setStatus('');try{await action();}catch(error){setError(error.message);}finally{setWorking(false);}}
 async function download(){
  const {files}=await prepare(true),archive=zipSync(Object.fromEntries(Object.entries(files).map(([name,text])=>[name,typeof text==='string'?strToU8(text):text])));
  const url=URL.createObjectURL(new Blob([archive],{type:'application/zip'}));const link=document.createElement('a');
  const slug=text=>text.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,60)||'module';
  link.href=url;link.download=`${slug(project.name)}-${slug(node.data.label)}-r${project.revision}-agent-handoff.zip`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);const ready=JSON.parse(files['handoff-readiness.json']),evidence=ready.sourceEvidence;setStatus(ready.capturedEvidence?.status==='unavailable'?'Handoff downloaded with unavailable capture evidence. See captured-evidence.json.':ready.reviewedDraft?.status==='unavailable'?'Handoff downloaded with unavailable draft evidence. See design-evidence.json.':evidence?.referenced?`Handoff downloaded. ${evidence.embedded}/${evidence.referenced} source images included.${evidence.complete?'':' See missing evidence in the package.'}`:'Agent handoff downloaded. Implementation and tests remain external.');
 }
 async function copy(){const {files}=await prepare();await navigator.clipboard.writeText(files['AGENT_PROMPT.md']);setStatus('Agent prompt copied. Give it the handoff ZIP.');}
 return <section aria-label="External agent handoff" className="module-agent-handoff">
  <h4>Hand off this module</h4><p>Download its specifications, contracts, diagrams, tasks and operating requirements for an external team or coding agent.</p>
  <div className="row"><button className="btn primary" disabled={busy||working} onClick={()=>void run(download)}>{working?'Preparing handoff…':'Download agent handoff'}</button>
   <button className="btn" disabled={busy||working} onClick={()=>void run(copy)}>Copy agent prompt</button></div>
  <p className="muted">Includes the full project context and assigned descendant modules. This does not authorize deployment.</p>
  {status&&<p role="status">{status}</p>}{error&&<p role="alert">{error}</p>}
 </section>;
}
