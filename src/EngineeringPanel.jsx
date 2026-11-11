import React,{useEffect,useRef,useState} from 'react';
import {engineeringCall,mergeEngineeringEvents,verifiedEngineeringDownload} from './engineering-client.mjs';
import './engineering.css';

export function EngineeringPanel({projectId,session,connection,saveProject,onConnections}){
  const draftKey=`atmem-engineering-draft-v1:${projectId}`;
  const [job,setJob]=useState(null),[events,setEvents]=useState([]),[draft,setDraft]=useState(()=>{try{return localStorage.getItem(draftKey)||'';}catch{return '';}}),
    [busy,setBusy]=useState(false),[error,setError]=useState(''),[loading,setLoading]=useState(true),[artifact,setArtifact]=useState(null);
  const [draftError,setDraftError]=useState('');
  useEffect(()=>{try{localStorage.setItem(draftKey,draft);setDraftError('');}catch{setDraftError('This draft could not be saved in your browser. Keep this view open or copy it before leaving.');}},[draftKey,draft]);
  const live=useRef(true),cursor=useRef(0),actionLock=useRef(false);
  useEffect(()=>{live.current=true;return()=>{live.current=false;};},[]);
  const call=(action,payload={},options)=>engineeringCall(session,action,{projectId,...(job?{sessionId:job.id}:{}),...payload},options);
  useEffect(()=>{
    const controller=new AbortController();let stopped=false;
    (async()=>{try{
      const result=await engineeringCall(session,'list',{projectId},{signal:controller.signal});
      const previous=result.sessions.at(-1);
      if(previous){
        if(!stopped)setJob(previous);
        const recovered=await engineeringCall(session,'recover',{projectId,sessionId:previous.id},{signal:controller.signal});
        if(!stopped)setJob(recovered);
      }
    }catch(e){if(!stopped&&e.name!=='AbortError')setError(e.message);}finally{if(!stopped)setLoading(false);}})();
    return()=>{stopped=true;controller.abort();};
  },[projectId,session.token]);
  useEffect(()=>{
    if(!job)return;
    const controller=new AbortController();let stopped=false,timer;
    async function poll(){try{
      const result=await engineeringCall(session,'events',{projectId,sessionId:job.id,after:cursor.current},{signal:controller.signal});
      if(stopped)return;
      setEvents(current=>mergeEngineeringEvents(current,result.events));
      if(result.events.length)cursor.current=result.events.at(-1).sequence;
      setJob(result.session);
    }catch(e){if(!stopped&&e.name!=='AbortError')setError(e.message);}finally{if(!stopped)timer=setTimeout(poll,1000);}}
    void poll();return()=>{stopped=true;clearTimeout(timer);controller.abort();};
  },[job?.id,projectId,session.token]);
  async function act(operation){
    if(actionLock.current)return;
    actionLock.current=true;setBusy(true);setError('');
    try{await operation();}catch(e){if(live.current)setError(e.message);}finally{actionLock.current=false;if(live.current)setBusy(false);}
  }
  const exactSelection=connection?.provider==='codex'&&connection.model&&connection.model!=='default'&&connection.effort;
  const running=job?.state==='running',uncertain=job?.state==='starting';
  const messages=events.filter(event=>event.kind==='message').map(event=>event.text).join('');
  return <div className="engineering-panel">
    <h2>Engineering workspace</h2>
    <p>Build implementation files and local tests from your saved project. Work continues when you close this view.</p>
    {loading?<p role="status">Finding your project’s work…</p>:!job?<>
      <p>{exactSelection?`${connection.model} · ${connection.effort}`:'Choose a Codex model and reasoning level to start.'}</p>
      {!exactSelection&&<button onClick={onConnections}>Choose model</button>}
      <button disabled={busy||!exactSelection} onClick={()=>act(async()=>{await saveProject();const created=await call('create',{model:connection.model,effort:connection.effort});if(live.current)setJob(created);})}>Open engineering job</button>
    </>:<>
      <p role="status">{running?'Working':uncertain?'Recovering acceptance of your last request':job.last_status?`Turn ${job.last_status}`:'Ready'} · {job.model} · {job.effort}</p>
      <p className="muted">This job uses the project snapshot from when it was opened. Send later changes below.</p>
      <form onSubmit={e=>{e.preventDefault();if(!draft.trim()||uncertain)return;const submitted=draft;void act(async()=>{const next=await call(running?'steer':'start',{text:submitted});if(live.current){setJob(next);setArtifact(null);setDraft(current=>current===submitted?'':current);}});}}>
        <label htmlFor="engineering-intent">{running?'Add an update':'What should we build or repair?'}</label>
        <textarea id="engineering-intent" rows={4} value={draft} onChange={e=>setDraft(e.target.value)}/>
        {draft.length>80000&&<p role="alert">This update exceeds 80,000 characters. Edit it before sending; your draft is retained.</p>}
        <button disabled={busy||uncertain||!draft.trim()||draft.length>80000}>{running?'Send update':'Start work'}</button>
      </form>
      <div className="engineering-actions">
        <button disabled={busy} onClick={()=>act(async()=>{const next=await call('recover');if(live.current)setJob(next);})}>Recover connection</button>
        {running&&<button disabled={busy} onClick={()=>act(async()=>{const next=await call('interrupt');if(live.current)setJob(next);})}>Stop work</button>}
        {!running&&!uncertain&&job.last_status&&<button disabled={busy} onClick={()=>act(async()=>{const captured=await call('capture');if(live.current)setArtifact(captured);})}>Capture package</button>}
      </div>
      {messages&&<pre className="engineering-message">{messages}</pre>}
      <details><summary>Engineering progress ({events.length})</summary><ol>{events.filter(event=>event.kind!=='message').map(event=><li key={event.sequence}>{event.kind}{event.text?` · ${event.text}`:''}</li>)}</ol></details>
      {artifact&&<div className="engineering-artifact"><p>Implementation draft · {artifact.files.filter(file=>file.kind==='file').length} files · turn {artifact.turnStatus}. Checks are not independently verified.</p>
        <button disabled={busy} onClick={()=>act(async()=>{const blob=await verifiedEngineeringDownload(session,{projectId,sessionId:job.id,artifactId:artifact.id},artifact);const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=`engineering-${artifact.id}.zip`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);})}>Download package</button>
      </div>}
    </>}
    {error&&<p role="alert">{error}</p>}
    {draftError&&<p role="alert">{draftError}</p>}
  </div>;
}
