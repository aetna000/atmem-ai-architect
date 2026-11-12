import React,{useEffect,useState} from 'react';
import {engineeringCall,verifiedHandoffDownload} from './engineering-client.mjs';
import {ArtifactChecks} from './ArtifactChecks.jsx';

export function ImplementationDelivery({project,session,onBuild,onSave,contextBusy=false}){
 const [loaded,setLoaded]=useState(null),[error,setError]=useState(''),[retry,setRetry]=useState(0),[busy,setBusy]=useState(false);
 const report=loaded?.project===project?loaded.report:null;
 useEffect(()=>{
  const controller=new AbortController();setError('');setLoaded(null);
  engineeringCall(session,'delivery',{projectId:project.id},{signal:controller.signal}).then(value=>{
   if(!controller.signal.aborted)setLoaded({project,report:value});
  }).catch(e=>{if(!controller.signal.aborted)setError(e.message)});
  return()=>controller.abort();
 },[project,session.token,retry]);
 async function download(){
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
   const blob=await verifiedHandoffDownload(session,{...payload,savedDesignSha256:current.savedDesignSha256},current.artifact);
   const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;
   link.download=`architect-handoff-${report.artifact.id}.zip`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }
 return <section aria-label="Implementation delivery">
  <h3>Implementation package</h3>
  {!report&&!error&&<p role="status">Finding the captured implementation and its checks…</p>}
  {report&&!report.artifact&&<><p>No implementation package has been captured for this project yet. Next: generate the implementation and run its local checks. Then download the combined package here.</p>{onBuild&&<button className="btn primary" disabled={contextBusy} onClick={onBuild}>Implement and check</button>}</>}
  {report?.artifact&&<>
   <p>{report.relation==='matches_saved_design'?'This package used the latest saved design.':report.relation==='design_changed'?'The saved design has changed since this implementation. New or changed requirements need implementation and checks.':report.relation==='earlier_turn'?'This is an earlier package. A later implementation turn has not produced a completed package yet.':'The submitted design receipt is unavailable. Its relationship to the current design is unknown.'} Capture and local checks do not establish full project acceptance.</p>
   <p>{report.artifact.files.filter(file=>file.kind==='file').length} files · {report.artifact.model} · {report.artifact.effort}</p>
   {report.canPackage&&<button className="btn primary" disabled={busy||contextBusy} onClick={()=>download()}>Download handoff package (ZIP)</button>}
   {report.relation!=='matches_saved_design'&&onBuild&&<button className="btn" disabled={busy||contextBusy} onClick={onBuild}>Implement and check latest design</button>}
   <p>The handoff includes the captured files, their original ZIP, submitted and latest saved requirements/design, and recorded local checks. Missing implementation or Spec Kit content remains work to complete.</p>
   <ArtifactChecks key={report.artifact.id} session={session} projectId={project.id} sessionId={report.session.id} artifact={report.artifact}/>
   <details><summary>Package files and source receipt</summary><p>Artifact SHA-256: {report.artifact.sha256}</p><ul>{report.artifact.files.filter(file=>file.kind==='file').map(file=><li key={file.path}>{file.path}</li>)}</ul></details>
  </>}
  {busy&&<p role="status">Preparing and verifying your handoff download…</p>}
  {contextBusy&&<p role="status">Finish the current design changes before downloading a combined handoff.</p>}
  {error&&<p role="alert">{error}</p>}
  <button className="link" disabled={busy} onClick={()=>setRetry(value=>value+1)}>Refresh delivery</button>
 </section>;
}
