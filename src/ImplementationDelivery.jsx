import {unzipSync,zipSync,strToU8} from 'fflate';
import {FinalChecklist} from './FinalChecklist.jsx';
import {BrainActivity} from './BrainActivity.jsx';
import {completeProjectZip} from './final-package.mjs';
import React,{useEffect,useState} from 'react';
import {engineeringCall,verifiedHandoffDownload} from './engineering-client.mjs';
import {ArtifactChecks} from './ArtifactChecks.jsx';

export function ImplementationDelivery({project,session,onBuild,onSave,contextBusy=false,designBundle,onDesignDownload,onDownloaded,checkReceipt,onExplore,onNavigate}){
 const [orcaResult,setOrcaResult]=useState(null);
 const [prepared,setPrepared]=useState(null),[preparing,setPreparing]=useState(false);
 const [loaded,setLoaded]=useState(null),[error,setError]=useState(''),[retry,setRetry]=useState(0),[busy,setBusy]=useState(false);
 const report=loaded?.project===project?loaded.report:null;
 useEffect(()=>{
  const controller=new AbortController();setError('');setLoaded(null);
  engineeringCall(session,'delivery',{projectId:project.id},{signal:controller.signal}).then(value=>{
   if(!controller.signal.aborted)setLoaded({project,report:value});
  }).catch(e=>{if(!controller.signal.aborted){if(e.status===404&&e.message.startsWith('Save or restore this project'))setLoaded({project,report:{artifact:null}});else setError(e.message);}});
  return()=>controller.abort();
 },[project,session.token,retry]);
 useEffect(()=>{
  if(!report?.canPackage||designBundle?.project!==project){setPrepared(null);return;}
  let stopped=false;const controller=new AbortController();setPreparing(true);setError('');
  (async()=>{try{
    const captured=await verifiedHandoffDownload(session,{projectId:project.id,sessionId:report.session.id,artifactId:report.artifact.id,savedDesignSha256:report.savedDesignSha256},report.artifact,{signal:controller.signal});
    const blob=await completeProjectZip(captured,designBundle);
    const files=unzipSync(new Uint8Array(await blob.arrayBuffer()));
    if(!stopped){setPrepared({artifactId:report.artifact.id,designSha256:report.savedDesignSha256,blob});onExplore?.({project,files});}
  }catch(e){if(!stopped&&e.name!=='AbortError')setError(e.message);}finally{if(!stopped)setPreparing(false);}})();
  return()=>{stopped=true;controller.abort();};
 },[report?.artifact?.id,report?.savedDesignSha256,designBundle,project,session.token,retry]);
 async function launchOrca(blob){
  if(blob.size>32000000)throw Error('Orca handoff supports ZIPs up to 32 MB. Download ZIP instead.');
  const zipBase64=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(Error('Could not prepare the project ZIP.'));reader.readAsDataURL(blob);});
  const result=await engineeringCall(session,'orca/open',{projectId:project.id,zipBase64});setOrcaResult(result);if(!result.opened)throw Error(result.message);
 }
 async function openOrca(){
  if(busy||contextBusy)return;
  setOrcaResult(null);
  if(report?.artifact)return download(true);
  setBusy(true);setError('');try{if(!designBundle||designBundle.project!==project)throw Error('Project files are still preparing.');if(onSave)await onSave(project);await launchOrca(new Blob([zipSync(Object.fromEntries(Object.entries(designBundle.files).map(([name,value])=>[name,typeof value==='string'?strToU8(value):value])))]));}catch(error){setError(error.message);}finally{setBusy(false);}
 }
 async function download(openInOrca=false){
  if(!report?.artifact||busy||contextBusy)return;
  setBusy(true);setError('');
  try{
   let current=report;
   if(onSave){
    const saved=await onSave(project);
    if(!/^[a-f0-9]{64}$/.test(saved?.sha256||''))throw Error('The current design save was not confirmed. Nothing was downloaded.');
    current=await engineeringCall(session,'delivery',{projectId:project.id});
    setLoaded({project,report:current});
    if(current.savedFileSha256!==saved.sha256)
      throw Error('The saved design changed after confirmation. Review the refreshed Delivery information before downloading.');
    const confirmedSameDesign=current.relation==='matches_saved_design'&&current.savedFileSha256===saved.sha256;
    if(current.artifact?.id!==report.artifact.id||current.session?.id!==report.session.id||(current.savedDesignSha256!==report.savedDesignSha256&&!confirmedSameDesign))
      throw Error('The saved design or package changed. Review the refreshed Delivery information before downloading.');
   }
   const payload={projectId:project.id,sessionId:current.session.id,artifactId:current.artifact.id};
   const captured=await verifiedHandoffDownload(session,{...payload,savedDesignSha256:current.savedDesignSha256},current.artifact);
   if(designBundle?.project!==project)throw Error('The design documents are refreshing. Try downloading again when preparation finishes.');
   const blob=await completeProjectZip(captured,designBundle);
   if(openInOrca){await launchOrca(blob);return;}
   const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;
   link.download=`architect-handoff-${report.artifact.id}.zip`;link.click();onDownloaded?.();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }
 return <section aria-label="Implementation delivery">
  <h3>Your project ZIP</h3>
  {!report&&!error&&<p role="status">Preparing package…</p>}
  {report&&!report.artifact&&<p>Design package · implementation not generated.</p>}
  {report&&!report.canPackage&&<button className="btn primary" disabled={!designBundle||designBundle.project!==project||contextBusy} onClick={()=>onDesignDownload?.(designBundle)}>Download project ZIP</button>}
  {report?.artifact&&<>
   <p className="delivery-state">{report.relation==='matches_saved_design'?'✓ Current design':report.relation==='design_changed'?'! Design changed since generation':'! Earlier or unverified implementation'}</p>

   <p>{report.artifact.files.filter(file=>file.kind==='file').length} files · {report.artifact.model} · {report.artifact.effort}</p>
   {report.canPackage&&<button className="btn primary" disabled={busy||preparing||!prepared||contextBusy||!designBundle||designBundle.project!==project} onClick={()=>download()}>Download project ZIP</button>}




  </>}
  <button className="btn" disabled={busy||preparing||contextBusy||!report||!designBundle||(!!report?.artifact&&!prepared)} onClick={openOrca}>Open in Orca ↗</button> <a className="link orca-website" href="https://orca.dev" target="_blank" rel="noopener noreferrer">Orca website ↗</a>
  {orcaResult&&<p role="status">{orcaResult.opened?'Opened in Orca':''} <code>{orcaResult.path}</code></p>}
  <FinalChecklist project={project} implementation={report?.canPackage&&report?.artifact} checks={report?.checks} terraform={checkReceipt} onNavigate={onNavigate}/>
  {(busy||preparing)&&<p role="status"><BrainActivity/> Preparing ZIP…</p>}
  {contextBusy&&<p role="status">Waiting for current changes…</p>}
  {error&&<p role="alert">{error}</p>}
  <button className="icon" aria-label="Refresh package" title="Refresh package" disabled={busy||preparing} onClick={()=>setRetry(value=>value+1)}>↻</button>
 </section>;
}
