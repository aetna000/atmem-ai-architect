import React,{useEffect,useRef,useState} from 'react';
import {engineeringCall} from './engineering-client.mjs';

export function ArtifactChecks({session,projectId,sessionId,artifact,readOnly=false}){
  const [catalog,setCatalog]=useState([]),[available,setAvailable]=useState(false),[checks,setChecks]=useState([]),
    [error,setError]=useState(''),[busy,setBusy]=useState(false);
  const live=useRef(true),locked=useRef(false);
  const payload={projectId,sessionId,artifactId:artifact.id};
  useEffect(()=>{live.current=true;return()=>{live.current=false;};},[]);
  useEffect(()=>{
    const controller=new AbortController();let stopped=false,timer;
    async function poll(){try{
      const [configuration,result]=await Promise.all([
        engineeringCall(session,'validators',{projectId,sessionId},{signal:controller.signal}),
        engineeringCall(session,'validation/list',payload,{signal:controller.signal})]);
      if(stopped)return;
      setCatalog(configuration.validators);setAvailable(configuration.available);setChecks(result.checks);
    }catch(e){if(!stopped&&e.name!=='AbortError')setError(e.message);}
    finally{if(!stopped)timer=setTimeout(poll,1200);}}
    void poll();return()=>{stopped=true;clearTimeout(timer);controller.abort();};
  },[projectId,sessionId,artifact.id,session.token]);
  async function act(action,values){
    if(locked.current)return;locked.current=true;setBusy(true);setError('');
    try{const body=action==='validation/recover'?{projectId,sessionId,...values}:{...payload,...values};const result=await engineeringCall(session,action,body);if(live.current)setChecks(current=>[...current.filter(check=>check.id!==result.id),result]);}
    catch(e){if(live.current)setError(e.message);}finally{locked.current=false;if(live.current)setBusy(false);}
  }
  return <section className="artifact-checks" aria-label="Captured package checks">
    <h3>Check results</h3>
    {!available&&<p>Independent checks have not run: no check runner is configured.</p>}
    {!readOnly&&catalog.map(validator=>{
      const previous=checks.filter(check=>check.validatorId===validator.id&&check.contractSha256===validator.contractSha256).at(-1);
      const active=previous&&previous.state!=='finished';
      return <button key={validator.id} disabled={busy||!available||validator.available===false||active} onClick={()=>void act('validation/start',{validatorId:validator.id,retry:!!previous})}>
        {previous?.state==='finished'?'Run again: ':''}{validator.label}{validator.available===false?' · unavailable':''}{active?' · '+previous.state:''}
      </button>;
    })}
    <ol>{checks.map(check=>{
      const definition=catalog.find(validator=>validator.id===check.validatorId),outdated=!definition||(definition.contractSha256!=null&&definition.contractSha256!==check.contractSha256);
      return <li key={check.id}>
        <strong>{check.label} · {check.state==='finished'?check.result?.status||'incomplete':check.state.replaceAll('_',' ')}</strong>
        {outdated&&<p>From a previous check definition; retained as historical evidence.</p>}
        {check.result?.testsReported!=null&&<p>{check.result.testsReported} tests reported · {check.result.skipped||0} skipped</p>}
        {!readOnly&&check.state==='recovery_required'&&<button disabled={busy} onClick={()=>void act('validation/recover',{checkId:check.id})}>Recover check</button>}
        {check.result&&<><details><summary>Check output</summary><pre>{check.result.output||check.result.reason||'No output reported.'}</pre></details></>}
      </li>;
    })}</ol>
    {error&&<p role="alert">{error}</p>}
  </section>;
}
