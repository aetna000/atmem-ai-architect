import React,{useEffect,useMemo,useRef,useState,useId}from'react';
import{BrainActivity}from'./BrainActivity.jsx';
import{engineeringCall}from'./engineering-client.mjs';
import{terraformSketch}from'./terraform.mjs';
import{verifiedReceipt}from'./validation-receipt.mjs';
export function ProjectChecks({project,environment,session,onReceipt,onBusy,receipt}){
 const [report,setReport]=useState(null),[catalogReady,setCatalogReady]=useState(false),[catalog,setCatalog]=useState([]),[checks,setChecks]=useState([]),[result,setResult]=useState(null),[working,setWorking]=useState(false),[error,setError]=useState('');
 const hintId=useId();
 const active=useRef(null),locked=useRef(false),files=useMemo(()=>terraformSketch(project,environment),[project,environment]),key=JSON.stringify(files);
 useEffect(()=>{let stopped=false;setResult(null);active.current?.abort();let previous=receipt;try{previous=previous||JSON.parse(localStorage.getItem('atmem-tf-receipt:'+project.id)||'null');}catch{}void verifiedReceipt(files,previous).then(value=>{if(!stopped){setResult(value);onReceipt?.(value);}});return()=>{stopped=true;active.current?.abort();};},[key]);
 useEffect(()=>{
  setReport(null);setCatalog([]);setChecks([]);setCatalogReady(false);
  if(!session?.engineeringEnabled)return;
  let stopped=false,timer;const controller=new AbortController();
  async function poll(){try{
   const value=await engineeringCall(session,'delivery',{projectId:project.id},{signal:controller.signal});if(stopped)return;setReport(value);
   if(value.artifact){const payload={projectId:project.id,sessionId:value.session.id};const [definitions,results]=await Promise.all([engineeringCall(session,'validators',payload,{signal:controller.signal}),engineeringCall(session,'validation/list',{...payload,artifactId:value.artifact.id},{signal:controller.signal})]);if(!stopped){setCatalog(definitions.validators||[]);setChecks(results.checks||[]);setCatalogReady(true);}}else{setCatalog([]);setChecks([]);setCatalogReady(false);}
  }catch(e){if(!stopped&&e.name!=='AbortError'&&e.status!==404)setError(e.message);}finally{if(!stopped)timer=setTimeout(poll,2000);}}
  void poll();return()=>{stopped=true;clearTimeout(timer);controller.abort();};
 },[project.id,session?.token,session?.engineeringEnabled]);
 const running=checks.some(c=>c.state!=='finished'&&c.state!=='recovery_required');
 useEffect(()=>{onBusy?.(!!working||running);return()=>onBusy?.(false);},[working,running,onBusy]);
 const available=catalog.filter(v=>v.available!==false);
 async function run(kind){
  if(locked.current||!session?.token||kind==='application'&&(!report?.artifact||!available.length))return;
  locked.current=true;setWorking(kind);setError('');const controller=new AbortController();active.current=controller;
  try{
   if(kind==='application'){
    const payload={projectId:project.id,sessionId:report.session.id,artifactId:report.artifact.id};
    await Promise.all(available.map(validator=>{
     const previous=checks.filter(c=>c.validatorId===validator.id&&c.contractSha256===validator.contractSha256).at(-1);
     if(previous&&previous.state!=='finished')return;
     return engineeringCall(session,'validation/start',{...payload,validatorId:validator.id,retry:!!previous},{signal:controller.signal});
    }));
    const results=await engineeringCall(session,'validation/list',payload,{signal:controller.signal});
    if(!controller.signal.aborted)setChecks(results.checks||[]);
   }else{
    const response=await fetch('/api/terraform/validate',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({project,environment}),signal:AbortSignal.any([controller.signal,AbortSignal.timeout(500000)])});const value=await response.json();
    if(!response.ok)throw Error(value.detail||'Terraform checks could not start.');
    const verified=await verifiedReceipt(files,value);if(!controller.signal.aborted){setResult(value);onReceipt?.(verified);try{if(verified)localStorage.setItem('atmem-tf-receipt:'+project.id,JSON.stringify(verified));else localStorage.removeItem('atmem-tf-receipt:'+project.id);}catch{}}
   }
  }catch(e){if(!controller.signal.aborted){if(kind==='terraform')setResult({status:'failed',message:e.message});setError(e.message);}}
  finally{locked.current=false;setWorking(false);}
 }
 const label=status=>({passed:'Passed',failed:'Failed',incomplete:'Incomplete',unavailable:'Not run'}[status]||'Not run');
 const applicationHint=!report?.artifact?'Generate project files first.':!catalogReady?'Loading available application tests.':!available.length?'No application tests are configured.':'Run the generated application tests.';
 const applicationStatus=!report?.artifact?'Generate files first':working==='application'||running?'Running…':checks.length?checks.every(c=>c.state==='finished'&&c.result?.status==='passed')?'Passed':'Needs attention':!catalogReady?'Loading…':available.length?'Not run':'Not configured';
 return <section className="project-checks" aria-label="Project checks"><div className="section-action"><h3>Checks</h3></div>
 <ul className="check-rows">
  <li><span>Terraform validation</span><strong className={result?.status==='passed'?'check-complete':'check-pending'}>{working==='terraform'?'Running…':label(result?.status)}</strong><span className="check-run-action" title="Validate the current Terraform files."><button className="btn" aria-label="Run Terraform validation" disabled={!session?.token||!!working||running} onClick={()=>run('terraform')}>{working==='terraform'?<><BrainActivity size={18}/> Running…</>:'Run'}</button></span></li>
  <li><span>Application tests</span><strong id={hintId} className={applicationStatus==='Passed'?'check-complete':'check-pending'}>{applicationStatus}</strong><span className="check-run-action" title={applicationHint} tabIndex={!report?.artifact||!available.length?0:undefined} aria-label={applicationHint}><button className="btn" aria-label="Run application tests" aria-describedby={hintId} title={applicationHint} disabled={!session?.token||!!working||running||!report?.artifact||!available.length} onClick={()=>run('application')}>{working==='application'||running?<><BrainActivity size={18}/> Running…</>:'Run'}</button></span></li>
 </ul>
 {(result||checks.length>0)&&<details><summary>Check details</summary>{result&&<><p>{result.message}</p>{result.checks?.map((c,i)=><details key={i}><summary>{c.name} · {c.passed?'Passed':'Failed'}</summary><pre>{c.output}</pre></details>)}</>}{checks.map(c=><details key={c.id}><summary>{c.label}</summary><pre>{c.result?.output||c.result?.reason||c.state}</pre></details>)}</details>}
 {error&&<p role="alert">{error}</p>}
 </section>;
}
