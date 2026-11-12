import React,{useEffect,useMemo,useRef,useState}from'react';
import{BrainActivity}from'./BrainActivity.jsx';
import{engineeringCall}from'./engineering-client.mjs';
import{terraformSketch}from'./terraform.mjs';
import{verifiedReceipt}from'./validation-receipt.mjs';
export function ProjectChecks({project,environment,session,onReceipt,onBusy,receipt}){
 const [report,setReport]=useState(null),[catalog,setCatalog]=useState([]),[checks,setChecks]=useState([]),[result,setResult]=useState(null),[working,setWorking]=useState(false),[error,setError]=useState('');
 const active=useRef(null),locked=useRef(false),files=useMemo(()=>terraformSketch(project,environment),[project,environment]),key=JSON.stringify(files);
 useEffect(()=>{let stopped=false;setResult(null);active.current?.abort();let previous=receipt;try{previous=previous||JSON.parse(localStorage.getItem('atmem-tf-receipt:'+project.id)||'null');}catch{}void verifiedReceipt(files,previous).then(value=>{if(!stopped){setResult(value);onReceipt?.(value);}});return()=>{stopped=true;active.current?.abort();};},[key]);
 useEffect(()=>{
  if(!session?.engineeringEnabled)return;
  let stopped=false,timer;const controller=new AbortController();
  async function poll(){try{
   const value=await engineeringCall(session,'delivery',{projectId:project.id},{signal:controller.signal});if(stopped)return;setReport(value);
   if(value.artifact){const payload={projectId:project.id,sessionId:value.session.id};const [definitions,results]=await Promise.all([engineeringCall(session,'validators',payload,{signal:controller.signal}),engineeringCall(session,'validation/list',{...payload,artifactId:value.artifact.id},{signal:controller.signal})]);if(!stopped){setCatalog(definitions.validators||[]);setChecks(results.checks||[]);}}
  }catch(e){if(!stopped&&e.name!=='AbortError'&&e.status!==404)setError(e.message);}finally{if(!stopped)timer=setTimeout(poll,2000);}}
  void poll();return()=>{stopped=true;clearTimeout(timer);controller.abort();};
 },[project.id,session?.token,session?.engineeringEnabled]);
 const running=checks.some(c=>c.state!=='finished'&&c.state!=='recovery_required');
 useEffect(()=>{onBusy?.(working||running);return()=>onBusy?.(false);},[working,running,onBusy]);
 async function run(){
  if(locked.current)return;locked.current=true;setWorking(true);setError('');const controller=new AbortController();active.current=controller;
  try{
   const jobs=[];
   if(report?.artifact)for(const validator of catalog.filter(v=>v.available!==false)){
    const previous=checks.filter(c=>c.validatorId===validator.id&&c.contractSha256===validator.contractSha256).at(-1);
    if(previous&&previous.state!=='finished')continue;
    jobs.push(engineeringCall(session,'validation/start',{projectId:project.id,sessionId:report.session.id,artifactId:report.artifact.id,validatorId:validator.id,retry:!!previous},{signal:controller.signal}));
   }
   const outcomesPending=Promise.allSettled(jobs);
   const response=await fetch('/api/terraform/validate',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({project,environment}),signal:AbortSignal.any([controller.signal,AbortSignal.timeout(500000)])});const value=await response.json();
   if(!response.ok)throw Error(value.detail||'Terraform checks could not start.');
   const verified=await verifiedReceipt(files,value);if(!controller.signal.aborted){setResult(value);onReceipt?.(verified);try{if(verified)localStorage.setItem('atmem-tf-receipt:'+project.id,JSON.stringify(verified));else localStorage.removeItem('atmem-tf-receipt:'+project.id);}catch{}}
   const outcomes=await outcomesPending;const failed=outcomes.find(o=>o.status==='rejected');if(failed)throw failed.reason;
  }catch(e){if(!controller.signal.aborted){setResult({status:'failed',message:e.message});setError(e.message);}}
  finally{locked.current=false;setWorking(false);}
 }
 const label=status=>({passed:'Passed',failed:'Failed',incomplete:'Incomplete',unavailable:'Not run'}[status]||'Not run');
 return <section className="project-checks" aria-label="Project checks"><div className="section-action"><h3>Checks</h3><button className="btn" disabled={!session?.token||working||running} onClick={run}>{working||running?<><BrainActivity size={22}/> Checking…</>:'Run checks'}</button></div>
 <ul className="check-rows"><li><span>Terraform</span><strong className={result?.status==='passed'?'check-complete':'check-pending'}>{working?'Running…':label(result?.status)}</strong></li>{checks.map(c=><li key={c.id}><span>{c.label}</span><strong className={c.result?.status==='passed'?'check-complete':'check-pending'}>{c.state==='finished'?label(c.result?.status):c.state==='recovery_required'?'Needs recovery':'Running…'}</strong></li>)}{!checks.length&&<li><span>Application checks</span><strong className="check-pending">{report?.artifact?'Not configured':'Generate files first'}</strong></li>}</ul>
 {(result||checks.length>0)&&<details><summary>Check details</summary>{result&&<><p>{result.message}</p>{result.checks?.map((c,i)=><details key={i}><summary>{c.name} · {c.passed?'Passed':'Failed'}</summary><pre>{c.output}</pre></details>)}</>}{checks.map(c=><details key={c.id}><summary>{c.label}</summary><pre>{c.result?.output||c.result?.reason||c.state}</pre></details>)}</details>}
 {error&&<p role="alert">{error}</p>}
 </section>;
}
