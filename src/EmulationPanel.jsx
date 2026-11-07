import React,{useEffect,useMemo,useRef,useState} from 'react';
import {terraformSketch} from './terraform.mjs';
import {toProjectFile} from './project-file.mjs';

// API-only UI: worker location, credentials, filesystem and emulator setup stay server-side.
export function EmulationPanel({project,environment,session}){
 const [result,setResult]=useState(null),[running,setRunning]=useState(false);
 const controller=useRef(null);
 const snapshot=useMemo(()=>JSON.stringify(terraformSketch(project,environment)),[project,environment]);
 useEffect(()=>{
  controller.current?.abort();controller.current=null;setResult(null);setRunning(false);
  return ()=>{controller.current?.abort();controller.current=null;};
 },[snapshot]);
 async function emulate(){
  if(running)return;
  const request=new AbortController();controller.current=request;setRunning(true);setResult(null);
  const timer=setTimeout(()=>request.abort(),115000);
  try{
   toProjectFile(project);
   if(!session?.token)throw Error('Connect to the architect service before emulating.');
   const response=await fetch('/api/emulation/run',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({project,environment}),signal:request.signal});
   const body=await response.json();if(!response.ok)throw Error(typeof body.detail==='string'?body.detail:'Emulation failed.');
   if(controller.current===request&&!request.signal.aborted)setResult(body);
  }catch(error){
   if(controller.current===request)setResult({status:'failed',checks:[],message:request.signal.aborted?'Stopped waiting for emulation; no pass was recorded. The isolated worker will stop at its time limit.':error.message});
  }finally{clearTimeout(timer);if(controller.current===request)setRunning(false);}
 }
 function saveReport(){
  const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)+'\n'],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download=`atmem-emulation-r${project.revision}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 const title=result?.status==='passed'?'Local emulation checks passed':result?.status==='blocked'?'Emulation blocked':result?.status==='unavailable'?'Emulation unavailable':'Emulation failed';
 return <aside className="emulation-panel" aria-label="AWS emulation">
  <h3>Emulate before download</h3>
  <p>Exercise generated application code with synthetic data and stateful local AWS service emulation. Model answers and authenticated request envelopes are simulated. This does not deploy to AWS or run Terraform apply.</p>
  <div className="row"><button className="btn primary" onClick={emulate} disabled={running}>{running?'Emulating locally…':'Emulate locally'}</button>{running&&<button className="btn" onClick={()=>controller.current?.abort()}>Stop waiting</button>}{result?.artifactDigest&&<button className="btn" onClick={saveReport}>Download emulation report</button>}</div>
  {running&&<p role="status">Running an isolated worker for this design. Results will be cleared if the generated files change.</p>}
  {result&&<div role="status"><h4>{title}</h4><p>{result.message}</p>
   {result.backend&&<p className="muted small">{result.backend} {result.backendVersion} · design r{result.designRevision} · {result.environment} · no cloud operations</p>}
   {!!result.blockers?.length&&<ul>{result.blockers.map((item,i)=><li key={i}>{item}</li>)}</ul>}
   {!!result.checks?.length&&<ul>{result.checks.map((check,i)=><li key={i}><strong>{check.passed?'Passed':'Failed'}:</strong> {check.name}{check.message&&<p>{check.message}</p>}</li>)}</ul>}
   {!!result.capabilities?.length&&<details><summary>What was emulated</summary><ul>{result.capabilities.map((item,i)=><li key={i}>{item.service}: {item.mode}</li>)}</ul></details>}
   {!!result.emulatorPatches?.length&&<details><summary>Emulator compatibility fixes</summary><ul>{result.emulatorPatches.map(item=><li key={item.id}>{item.id}: {item.reason}</li>)}</ul></details>}
   {!!result.limitations?.length&&<details open><summary>Still requires AWS verification</summary><ul>{result.limitations.map((item,i)=><li key={i}>{item}</li>)}</ul></details>}
  </div>}
 </aside>;
}
