import {ArchitectureWorkPanel} from './ArchitectureWorkPanel.jsx';
import React,{useEffect,useRef,useState} from 'react';
import {engineeringCall,engineeringConversation,mergeEngineeringEvents,verifiedEngineeringDownload} from './engineering-client.mjs';
import './engineering.css';
import {ArtifactChecks} from './ArtifactChecks.jsx';
import {verifyArtifactWork} from './artifact-work.mjs';
import {hasArchitectureDesign,buildIntent,BUILD_AND_TEST_REQUEST} from './design-build-flow.mjs';

export function EngineeringPanel({projectId,session,connection,saveProject,onConnections,project,onWorkModelChange,onIntentContext,onDesign,buildRequest,onBuildRequestHandled,contextBusy=false}){
  const draftKey=`atmem-engineering-draft-v1:${projectId}`;
  const [job,setJob]=useState(null),[events,setEvents]=useState([]),[draft,setDraft]=useState(()=>{try{return localStorage.getItem(draftKey)||'';}catch{return '';}}),
    [busy,setBusy]=useState(false),[error,setError]=useState(''),[loading,setLoading]=useState(true),[artifact,setArtifact]=useState(null);
  const [draftError,setDraftError]=useState('');
  const [restoreBlocked,setRestoreBlocked]=useState(false),[restoreAttempt,setRestoreAttempt]=useState(0);
  useEffect(()=>{try{localStorage.setItem(draftKey,draft);setDraftError('');}catch{setDraftError('This draft could not be saved in your browser. Keep this view open or copy it before leaving.');}},[draftKey,draft]);
  const live=useRef(true),cursor=useRef(0),actionLock=useRef(false);
  const finalization=events.filter(event=>event.runId===job?.run&&event.kind.startsWith('finalization_')).at(-1);
  useEffect(()=>{live.current=true;return()=>{live.current=false;};},[]);
  const call=(action,payload={},options)=>engineeringCall(session,action,{projectId,...(job?{sessionId:job.id}:{}),...payload},options);
  useEffect(()=>{
    if(!job)return;
    const controller=new AbortController();let stopped=false;
    engineeringCall(session,'artifacts',{projectId,sessionId:job.id},{signal:controller.signal}).then(result=>{
      if(!stopped)setArtifact(result.artifacts.find(item=>item.runId===job.run)||result.artifacts[0]||null);
    }).catch(e=>{if(!stopped&&e.name!=='AbortError')setError(e.message);});
    return()=>{stopped=true;controller.abort();};
  },[job?.id,job?.run,finalization?.artifactId,projectId,session.token]);
  useEffect(()=>{
    const controller=new AbortController();let stopped=false;
    setLoading(true);setRestoreBlocked(false);
    (async()=>{let restored=false;try{
      const result=await engineeringCall(session,'list',{projectId},{signal:controller.signal});
      const previous=result.sessions.at(-1);
      if(previous){
        restored=true;
        if(!stopped)setJob(previous);
        const recovered=await engineeringCall(session,'recover',{projectId,sessionId:previous.id},{signal:controller.signal});
        if(!stopped)setJob(recovered);
      }
    }catch(e){if(!stopped&&e.name!=='AbortError'&&(e.status!==404||restored)){setError(e.message);setRestoreBlocked(true);}}finally{if(!stopped)setLoading(false);}})();
    return()=>{stopped=true;controller.abort();};
  },[projectId,session.token,restoreAttempt]);
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
  useEffect(()=>{if(job&&onIntentContext){try{onIntentContext(projectId,job.id,events);}catch(e){setError(e.message);}}},[job?.id,events,onIntentContext]);
  async function act(operation){
    if(actionLock.current)return;
    actionLock.current=true;setBusy(true);setError('');
    try{await operation();}catch(e){if(live.current)setError(e.message);}finally{actionLock.current=false;if(live.current)setBusy(false);}
  }
  const exactSelection=connection?.provider==='codex'&&connection.model&&connection.model!=='default'&&connection.effort;
  const running=job?.state==='running',uncertain=job?.state==='starting';
  const conversation=engineeringConversation(events);
  const hasDesign=hasArchitectureDesign(project),canSubmit=running?!!draft.trim():!!buildIntent(project,draft);
  const consumedBuild=useRef(null);
  function submitIntent(event,requestedText){
    event?.preventDefault();
    const submitted=requestedText??(running?draft:buildIntent(project,draft));
    if(!submitted||submitted.length>80000||loading||restoreBlocked||actionLock.current||uncertain||contextBusy||(!job&&(!exactSelection||!hasDesign)))return false;
    void act(async()=>{
      let current=job;
      let saved=await saveProject();
      if(!/^[a-f0-9]{64}$/.test(saved?.sha256||''))throw Error('The server did not confirm the saved design context. Your draft is retained.');
      if(!current){
        current=await call('create',{model:connection.model,effort:connection.effort});
        if(live.current)setJob(current);
        // Native session creation can outlast pending autosaves. Confirm the
        // context immediately before submitting, without replaying any intent.
        saved=await saveProject();
        if(!/^[a-f0-9]{64}$/.test(saved?.sha256||''))throw Error('The server did not confirm the saved design context. Your draft is retained.');
      }
      // The new session ID is explicit: React state may not have rendered yet.
      const next=await call(current.state==='running'?'steer':'start',{sessionId:current.id,text:submitted,contextSha256:saved.sha256});
      if(live.current){setJob(next);setArtifact(null);setDraft(value=>value===submitted?'':value);}
    });
    return true;
  }
  useEffect(()=>{
    if(!buildRequest||buildRequest.projectId!==projectId||consumedBuild.current===buildRequest.id||loading||restoreBlocked||contextBusy||uncertain||busy||(!job&&!exactSelection))return;
    if(submitIntent(null,buildRequest.intent==='test'?BUILD_AND_TEST_REQUEST:buildIntent(project,''))){
      consumedBuild.current=buildRequest.id;onBuildRequestHandled?.(buildRequest.id);
    }
  },[buildRequest,projectId,loading,restoreBlocked,contextBusy,uncertain,busy,exactSelection,job?.id]);
  async function linkMappings(){
    const result=await call('reconciliation',{artifactId:artifact.id});
    if(result.status==='proposal_missing')throw Error(result.message);
    const verified=await verifyArtifactWork(result);
    if(verified.payload.artifactId!==artifact.id||verified.payload.artifactSha256!==artifact.sha256||verified.payload.sessionId!==job.id)throw Error('The mapping receipt does not match this captured package.');
    onWorkModelChange({kind:'artifact',verified},projectId);
  }
  return <div className="engineering-panel">
    <h2>{artifact?'Handoff package':'Implementation'}</h2>
    <p>Architect implements your saved design, runs applicable local checks and prepares a downloadable package. Follow its progress below.</p>
    {onDesign&&<button onClick={onDesign}>Return to Design</button>}

    {buildRequest?.projectId===projectId&&<p role="status">{restoreBlocked?'Your implementation request is waiting. Retry loading earlier work before starting.':uncertain?'Your implementation request is waiting. Recover the existing request first to avoid duplicate work.':contextBusy?'Your implementation request is waiting for the current design changes.':!job&&!exactSelection?'Your implementation request is waiting here. Choose a model and reasoning level below; it will then start automatically.':'Your implementation request is queued.'} <button onClick={()=>onBuildRequestHandled?.(buildRequest.id)}>Cancel queued request</button></p>}
    {restoreBlocked&&<button disabled={loading||busy} onClick={()=>{setError('');setRestoreAttempt(value=>value+1);}}>Retry loading earlier work</button>}
    {loading?<p role="status">Finding your project’s work…</p>:<>
      {job?<>
        <p role="status">{running?'Working':uncertain?'Recovering acceptance of your last request':job.last_status?({completed:'Work completed',interrupted:'Work stopped',failed:'Work needs attention'}[job.last_status]||job.last_status):'Ready'} · {job.model} · {job.effort}</p>
        <p className="muted">Each request includes your saved design. Earlier versions remain in the work history.</p>
      </>:<>
        <p>{exactSelection?`${connection.model} · ${connection.effort}`:'Choose a Codex model and reasoning level to start.'}</p>
        {!exactSelection&&<button onClick={onConnections}>Choose model</button>}
        {contextBusy&&<p role="status">Finish the current design changes before starting new work.</p>}
      </>}
      {conversation.length>0&&<section className="engineering-conversation" role="log" aria-label="Project conversation" aria-live="polite">{conversation.map(entry=><article key={entry.id} className={`engineering-entry ${entry.role}`}>
        <strong>{entry.role==='user'?'You':'Architect'}</strong>
        {entry.status==='pending'&&<span> · Sending update</span>}
        {entry.status==='uncertain'&&<span> · Delivery uncertain; recover before resending</span>}
        <pre>{entry.text}</pre>
      </article>)}</section>}
      {!hasDesign&&!job?<p>Start with the architecture in Design. Add the components or responsibilities before building an implementation.</p>:<form onSubmit={submitIntent}>
        <label htmlFor="engineering-intent">{running?'Add an implementation update':hasDesign?'Additional instructions (optional)':'Continue implementation'}</label>
        <textarea id="engineering-intent" rows={4} value={draft} onChange={e=>setDraft(e.target.value)}/>
        {draft.length>80000&&<p role="alert">This update exceeds 80,000 characters. Edit it before sending; your draft is retained.</p>}
        <button disabled={busy||restoreBlocked||uncertain||contextBusy||!canSubmit||draft.length>80000||(!job&&!exactSelection)}>{running?'Send update':hasDesign?'Implement and check':'Continue implementation'}</button>
      </form>}
      {job&&<>
        {finalization&&<p role="status"><strong>Recorded verification update: </strong>{finalization.text}</p>}
        <div className="engineering-actions">
          <button disabled={busy} onClick={()=>act(async()=>{const next=await call('recover');if(live.current)setJob(next);})}>Refresh connection status</button>
          {running&&<button disabled={busy} onClick={()=>act(async()=>{const next=await call('interrupt');if(live.current)setJob(next);})}>Stop work</button>}
          {!running&&!uncertain&&job.last_status&&<button disabled={busy} onClick={()=>act(async()=>{const captured=await call('capture');if(live.current)setArtifact(captured);})}>Refresh package snapshot</button>}
        </div>
        <details><summary>Engineering progress ({events.length})</summary><ol>{events.filter(event=>!['message','accepted','steering_submitted'].includes(event.kind)).map(event=><li key={event.sequence}>{event.kind}{event.text?` · ${event.text}`:''}</li>)}</ol></details>
      </>}
      {artifact&&<div className="engineering-artifact"><p>Implementation draft · {artifact.files.filter(file=>file.kind==='file').length} {artifact.files.filter(file=>file.kind==='file').length===1?'file':'files'} · work {artifact.turnStatus}. Checks are not independently verified.</p>
        {artifact.runId!==job?.run&&<p>This package is from an earlier turn. It does not cover the current work.</p>}
        <button disabled={busy} onClick={()=>act(async()=>{const blob=await verifiedEngineeringDownload(session,{projectId,sessionId:job.id,artifactId:artifact.id},artifact);const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=`engineering-${artifact.id}.zip`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);})}>Download handoff package (ZIP)</button>
        {!running&&!uncertain&&job?.last_status==='completed'&&artifact.runId===job.run&&<button disabled={busy} onClick={()=>act(async()=>{await call('recheck',{runId:job.run,artifactId:artifact.id});const next=await call('state');if(live.current)setJob(next);})}>Recheck and repair</button>}
        {onWorkModelChange&&!running&&!uncertain&&job?.last_status==='completed'&&artifact.runId===job.run&&<button disabled={busy||contextBusy} onClick={()=>act(linkMappings)}>Link proposed mappings</button>}
        <ArtifactChecks key={artifact.id} session={session} projectId={projectId} sessionId={job.id} artifact={artifact}/>
      </div>}
    </>}
    {(hasDesign||job)&&<ArchitectureWorkPanel project={project} onChange={onWorkModelChange} busy={busy||contextBusy}/>}
    {error&&<p role="alert">{error}</p>}
    {draftError&&<p role="alert">{draftError}</p>}
  </div>;
}
