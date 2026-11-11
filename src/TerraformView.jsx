import {moduleValidationCoverage} from './terraform-validation-coverage.mjs';
import {generationQuality} from './generation-quality.mjs';
import {BrainActivity} from "./BrainActivity.jsx";
import React, {useEffect, useMemo, useRef, useState} from 'react';
import {EmulationPanel} from './EmulationPanel.jsx';
import {terraformSketch} from './terraform.mjs';
import {resourcePlan} from './resources.mjs';
import {toProjectFile} from './project-file.mjs';

export function TerraformView({project,environment,session,onDownload,onBack,emulation,onDiscuss,discussionBusy}){
  const files=useMemo(()=>terraformSketch(project,environment),[project,environment]);
  const plan=useMemo(()=>resourcePlan(project),[project]);
  const [file,setFile]=useState('main.tf.json'),[step,setStep]=useState('code'),[result,setResult]=useState(null),[running,setRunning]=useState(false);
  const controller=useRef(null);
  const key=JSON.stringify(files);
  useEffect(()=>{setResult(null);setRunning(false);controller.current?.abort();controller.current=null;return ()=>{controller.current?.abort();controller.current=null;};},[key]);
  async function test(){
    if(running)return;
    const request=new AbortController();controller.current=request;setRunning(true);setResult(null);
    const timer=setTimeout(()=>request.abort(),500000);
    try{
      toProjectFile(project);
      if(!session?.token)throw Error('Connect the local service before running Terraform validation.');
      const response=await fetch('/api/terraform/validate',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({project,environment}),signal:request.signal});
      const body=await response.json();if(!response.ok)throw Error(typeof body.detail==='string'?body.detail:'Terraform validation failed.');
      if(!request.signal.aborted)setResult({...moduleValidationCoverage(body,quality.modules),filesKey:key});
    }catch(e){if(!request.signal.aborted)setResult({status:'failed',message:e.message,checks:[]});else if(controller.current===request)setResult({status:'failed',message:'Validation stopped or timed out; no success was recorded.',checks:[]});}
    finally{clearTimeout(timer);if(controller.current===request)setRunning(false);}
  }
  const quality=useMemo(()=>generationQuality(project,plan,files),[project,plan,files]);
  const gaps=JSON.parse(files['main.tf.json']).locals.unfinished_work;
  return <section className="doc terraform-view" aria-label="Terraform">
    <header className="doc-head"><h2>Terraform deployment draft</h2><p className="muted">Review generated resources, required integrations and the evidence for this configuration. Provider-specific capabilities and their limits are recorded in the export.</p></header>
    <div className="row"><button className="link" onClick={onBack}>Back to architecture</button><button className="btn" onClick={()=>onDownload(result?.filesKey===key?result:null)}>Download Terraform</button></div>
    <aside aria-label="Export quality"><strong>{quality.infrastructureComplete?'Infrastructure generated — validation required':'Implementation work remains'}</strong><p>{quality.providers.join(', ')||'No deployment provider selected'} · {quality.components.length} components · {quality.findings.length} coverage findings</p><p className="small">{result?.status==='passed'&&result.filesKey===key?'Current configuration checks passed. Matching evidence will accompany the Terraform download.':'No current validation receipt is attached. Run Terraform checks to generate evidence for these files.'} Application behavior and account deployment require their own tests.</p></aside>
    <EmulationPanel project={project} environment={environment} session={session} emulation={emulation} onDiscuss={onDiscuss} discussionBusy={discussionBusy}/>
    <div className="seg" role="tablist" aria-label="Terraform steps"><button role="tab" aria-selected={step==='code'} onClick={()=>setStep('code')}>1. Resources & code</button><button role="tab" aria-selected={step==='test'} onClick={()=>setStep('test')}>2. Test Terraform</button></div>
    {step==='code'?<>
      <h3>Resource coverage</h3>
      {plan.rows.map(r=><p key={r.id||r.address}><strong>{r.label||r.service}</strong> — {r.terraform}<br/><small>{r.provider} · {r.region}</small></p>)}
      {!!plan.gaps.length&&<details><summary>{plan.gaps.length} implementation gaps</summary><ul>{plan.gaps.map((g,i)=><li key={i}>{g}</li>)}</ul></details>}
      <div className="row" aria-label="Terraform files">{Object.keys(files).map(name=><button className="btn" key={name} aria-pressed={file===name} onClick={()=>setFile(name)}>{name}</button>)}</div>
      <pre className="terraform-code" aria-label={file}><code>{files[file]}</code></pre>
      <button className="btn primary" onClick={()=>setStep('test')}>Continue to Test Terraform →</button>
    </>:<>
      <h3>Test this Terraform draft</h3>
      <p>Checks the generated configuration against Terraform and the provider schema, then runs available generated application tests and mock-provider plans. Provider initialization downloads the official provider if needed; it uses a temporary directory with no cloud credentials or backend.</p>
      <p><strong>Resource and integration coverage: {gaps.length?'Incomplete':'No recorded gaps'}</strong>{gaps.length?` — ${gaps.length} unfinished tasks block a deployment plan.`:''}</p>
      <button className="btn primary" disabled={running} onClick={test}>{running?'Testing Terraform…':'Run Terraform checks'}</button>
      {running&&<p role="status"><BrainActivity/> Initializing providers, validating configuration and running generated local tests. This may take a few minutes.</p>}
      {result&&<div role="status"><h3>{result.status==='passed'?'Configuration validated':result.status==='unavailable'?'Terraform validation not run':result.status==='incomplete'?'Validation incomplete':'Validation failed'}</h3><p>{result.message}</p>{result.checks?.map((c,i)=><details key={i}><summary>{c.passed?'Passed':'Failed'}: {c.name}</summary><pre className="terraform-code">{c.output}</pre></details>)}</div>}
      <h3>Cloud deployment plan — not run</h3><p>A real plan must verify the selected account, region, permissions and proposed changes. Cloud access is not connected. Passing these checks does not prove a real deployment or live application behavior.</p>
      <button className="btn" disabled>Run cloud plan (under development)</button>
    </>}
  </section>;
}
