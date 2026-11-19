import {CANVAS_ARTIFACT,CANVAS_REVIEW,DESIGN_WITH_CODEX,REFINE_CODEX_CANVAS} from './codex-canvas.mjs';
import {BrainActivity} from './BrainActivity.jsx';
import React,{useEffect,useMemo,useRef,useState} from 'react';
import {engineeringCall,engineeringConversation,mergeEngineeringEvents,engineeringSelectionSupported} from './engineering-client.mjs';
import './engineering.css';
import {ArtifactChecks} from './ArtifactChecks.jsx';
import {verifyArtifactWork} from './artifact-work.mjs';
import {hasArchitectureDesign,buildIntent,blockBuildIntent,BUILD_AND_TEST_REQUEST} from './design-build-flow.mjs';
import {loadBlockOrder,saveBlockOrder,pendingBlockOrder,blockOrderPayload,verifyBlockOrderAcceptance} from './block-work-order-client.mjs';

export function EngineeringPanel({projectId,session,connection,saveProject,onConnections,project,onWorkModelChange,onIntentContext,onDesign,onDelivery,onCanvas,onAssessCanvas,buildRequest,onBuildRequestHandled,onRequestArchitecture,contextBusy=false,onBusyChange}){
  const draftKey=`atmem-engineering-draft-v1:${projectId}`;
  const [job,setJob]=useState(null),[events,setEvents]=useState([]),[draft,setDraft]=useState(()=>{try{return localStorage.getItem(draftKey)||'';}catch{return '';}}),
    [busy,setBusy]=useState(false),[error,setError]=useState(''),[loading,setLoading]=useState(true),[artifact,setArtifact]=useState(null);
  const [draftError,setDraftError]=useState(''),[mappingStatus,setMappingStatus]=useState('');
  const [retainedOrder,setRetainedOrder]=useState(()=>{try{return loadBlockOrder(localStorage,projectId);}catch{return {pending:null,error:'Browser storage is unavailable. Block requests cannot be retained.'};}});
  const [failedBuildRequest,setFailedBuildRequest]=useState(null);
  function retainOrder(value){saveBlockOrder(localStorage,projectId,value);setRetainedOrder({pending:value,error:''});}
  async function sendBlockOrder(order){
    const next=verifyBlockOrderAcceptance(order,await engineeringCall(session,'work-orders/block',blockOrderPayload(order)));
    retainOrder(null);
    if(live.current){setJob(next);setArtifact(null);onBuildRequestHandled?.(order.requestId);}
  }
 const mappedArtifacts=useRef(new Set());
  const [restoreBlocked,setRestoreBlocked]=useState(false),[restoreAttempt,setRestoreAttempt]=useState(0);
  useEffect(()=>{try{localStorage.setItem(draftKey,draft);setDraftError('');}catch{setDraftError('This draft could not be saved in your browser. Keep this view open or copy it before leaving.');}},[draftKey,draft]);
  const live=useRef(true),actionLock=useRef(false);
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
    const controller=new AbortController();let stopped=false,timer,cursor=0,interval=1000;
    setEvents([]);
    async function poll(){try{
      const result=await engineeringCall(session,'events',{projectId,sessionId:job.id,after:cursor},{signal:controller.signal});
      if(stopped)return;
      if(result.events.length){
        setEvents(current=>mergeEngineeringEvents(current,result.events));
        cursor=result.events.at(-1).sequence;
      }
      interval=result.events.length===200?25:1000;
      setJob(result.session);
    }catch(e){if(!stopped&&e.name!=='AbortError')setError(e.message);}finally{if(!stopped)timer=setTimeout(poll,interval);}}
    void poll();return()=>{stopped=true;clearTimeout(timer);controller.abort();};
  },[job?.id,projectId,session.token]);
  useEffect(()=>{if(job&&onIntentContext){try{onIntentContext(projectId,job.id,events);}catch(e){setError(e.message);}}},[job?.id,events,onIntentContext]);
  async function act(operation,onFailure){
    if(actionLock.current)return;
    actionLock.current=true;setBusy(true);setError('');
    try{await operation();}catch(e){if(live.current){setError(e.message);onFailure?.();}}finally{actionLock.current=false;if(live.current)setBusy(false);}
  }
  useEffect(()=>{onBusyChange?.(busy||loading||['running','starting'].includes(job?.state));return()=>onBusyChange?.(false);},[busy,loading,job?.state,onBusyChange]);
  const exactSelection=engineeringSelectionSupported(session,connection);
  const running=job?.state==='running',uncertain=job?.state==='starting';
  const lastProgress=events.filter(event=>event.runId===job?.run&&['progress','message'].includes(event.kind)).at(-1);
  const [lastReceived,setLastReceived]=useState(null),[now,setNow]=useState(Date.now());
  useEffect(()=>{if(lastProgress){const time=Date.now();setLastReceived(time);setNow(time);}},[lastProgress?.sequence]);
  useEffect(()=>{if(!running&&!uncertain)return;const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer);},[running,uncertain]);
  const activity=lastProgress?.kind==='message'?'Preparing an update':({reasoning:'Reasoning about the architecture',fileChange:'Updating project files',commandExecution:'Running a development command',mcpToolCall:'Using a development tool',webSearch:'Checking documentation'}[lastProgress?.text]||'Developing the architecture');
  const conversation=useMemo(()=>engineeringConversation(events),[events]);
  const visibleProgress=useMemo(()=>events.filter(event=>!['message','accepted','steering_submitted'].includes(event.kind)).slice(-200),[events]);
  const hasDesign=hasArchitectureDesign(project),hasSources=!!project.extensions?.designSources?.length;
  const architectureText=running?draft:`${DESIGN_WITH_CODEX}${draft.trim()?'\n\nAdditional architecture instructions:\n'+draft:''}`;
  const canSubmit=(running?!!draft.trim():hasSources)&&architectureText.length<=80000;
  const consumedBuild=useRef(null);
  function submitIntent(event,requestedText,designOnly=false,blockRequest=null){
    event?.preventDefault();
    const submitted=requestedText??architectureText;
    if(requestedText===undefined)designOnly=true;
    const sentDraft=requestedText===undefined?draft:submitted;
    if(!submitted||submitted.length>80000||loading||restoreBlocked||actionLock.current||uncertain||contextBusy||retainedOrder.pending||retainedOrder.error||(!job&&(!exactSelection||(!hasDesign&&!designOnly))))return false;
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
      if(blockRequest){
        const order=pendingBlockOrder(projectId,current.id,blockRequest.blockId,saved.sha256,blockRequest.id);
        retainOrder(order);await sendBlockOrder(order);return;
      }
      // The new session ID is explicit: React state may not have rendered yet.
      const next=await call(current.state==='running'?'steer':'start',{sessionId:current.id,text:submitted,contextSha256:saved.sha256});
      if(live.current){setJob(next);setArtifact(null);setDraft(value=>value===sentDraft?'':value);}
    },()=>{if(blockRequest)setFailedBuildRequest(blockRequest.id);});
    return true;
  }
  useEffect(()=>{
    if(!buildRequest||buildRequest.projectId!==projectId||consumedBuild.current===buildRequest.id||failedBuildRequest===buildRequest.id||loading||restoreBlocked||contextBusy||uncertain||busy||(!job&&!exactSelection)||((buildRequest.blockId||buildRequest.intent==='design')&&running))return;
    const designOnly=buildRequest.intent==='design';
    const intent=designOnly?DESIGN_WITH_CODEX:buildRequest.blockId?blockBuildIntent(project,buildRequest.blockId):buildRequest.intent==='test'?BUILD_AND_TEST_REQUEST:buildIntent(project,'');
    if(!intent||submitIntent(null,intent,designOnly,buildRequest.blockId?buildRequest:null)){
      consumedBuild.current=buildRequest.id;if(!buildRequest.blockId)onBuildRequestHandled?.(buildRequest.id);
    }
  },[buildRequest,projectId,loading,restoreBlocked,contextBusy,uncertain,busy,exactSelection,job?.id,project,running,failedBuildRequest]);
  const acceptedEvents=useMemo(()=>events.filter(event=>event.kind==='accepted'),[events]);
  const designStart=acceptedEvents.findLastIndex(event=>event.text?.startsWith('Design the full system described by the saved source documents.'));
  const reviewEvents=designStart<0?[]:acceptedEvents.slice(designStart+1).filter(event=>event.text?.startsWith('Review and refine the existing architecture.canvas.json'));
  const canvasTurn=!!artifact&&designStart>=0&&(acceptedEvents[designStart].runId===artifact.runId||reviewEvents.some(event=>event.runId===artifact.runId));
  const reviewCount=reviewEvents.length;
  // Captures can retain a proposal from earlier implementation work. Wait for
  // this run's intent before choosing automation; design assessment must not
  // race an import of those retained file mappings.
  const artifactIntentLoaded=!!artifact&&acceptedEvents.some(event=>event.runId===artifact.runId);
  const reviewKey=artifact?`atmem-canvas-reviewed-v1:${projectId}:${artifact.id}`:null;
  const [automaticReview,setAutomaticReview]=useState(null),[assessment,setAssessment]=useState(null);
  const assessedArtifact=useRef(null);
  const hasCanvas=artifact?.files.some(file=>file.kind==='file'&&file.path===CANVAS_ARTIFACT);
  const hasReview=artifact?.files.some(file=>file.kind==='file'&&file.path===CANVAS_REVIEW);
  const appliedQuality=project.extensions?.architectureDraftQuality,appliedDocuments=project.extensions?.architectureDocuments;
  const alreadyAppliedCanvas=!!artifact&&appliedQuality?.artifactId===artifact.id&&appliedDocuments?.artifactId===artifact.id
    &&/^[a-f0-9]{64}$/.test(appliedQuality.draftSha256||'')&&appliedQuality.draftSha256===appliedDocuments.draftSha256&&/^[a-f0-9]{64}$/.test(appliedQuality.appliedBasis||'');
  const assessable=onAssessCanvas&&canvasTurn&&hasCanvas&&!alreadyAppliedCanvas&&!running&&!uncertain&&!busy&&!contextBusy&&!buildRequest
    &&job?.last_status==='completed'&&job.run===artifact.runId;
  useEffect(()=>{
    if(!assessable||assessedArtifact.current===artifact.id)return;
    const key=artifact.id;
    assessedArtifact.current=key;
    onAssessCanvas(artifact,job.id).then(proposal=>{
      if(live.current)setAssessment({key,quality:proposal.quality});
    }).catch(error=>{
      if(live.current)setAssessment({key,error:error.message,diagnostic:error.canvasDiagnostic,repairable:error.canvasDraftInvalid});
    });
  },[assessable,artifact?.id,job?.id]);
  const currentAssessment=assessment?.key===artifact?.id?assessment:null;
  const nativeDiagramsMissing=currentAssessment?.quality?.systemModel?.status==='missing';
  const eligibleForReview=currentAssessment&&(currentAssessment.repairable||
    currentAssessment.quality&&(!currentAssessment.quality.ready||nativeDiagramsMissing));
  useEffect(()=>{
    if(!assessable||!eligibleForReview||reviewCount>=3||!reviewKey||automaticReview===artifact.id)return;
    try{if(localStorage.getItem(reviewKey))return;}catch{}
    const gaps=currentAssessment.quality?.measurements?.filter(row=>row.earned!==row.points)
      .map(row=>`${row.name} (${row.earned}/${row.points})`).join(', ');
    const gates=Object.entries(currentAssessment.quality?.gates||{}).filter(([,passed])=>!passed).map(([gate])=>gate).join(', ');
    const referenceErrors=currentAssessment.quality?.behaviorConsistency?.errors||[];
    const behavior=referenceErrors.length?`Behavior reference conflicts: ${referenceErrors.length}. First ${Math.min(20,referenceErrors.length)}: ${JSON.stringify(referenceErrors.slice(0,20))}. Check all scenario references against the exact block, interface and requirement IDs.`:'';
    const diagnostic=currentAssessment.diagnostic||currentAssessment.error||[gaps,gates&&`Required checks: ${gates}`,behavior,nativeDiagramsMissing&&'The native systemModel is missing. Add validated logical, functional and sequence views.'].filter(Boolean).join('. ');
    if(submitIntent(null,`${REFINE_CODEX_CANVAS}\n\nHost structural check: ${diagnostic}`,true)){
      setAutomaticReview(artifact.id);
      try{localStorage.setItem(reviewKey,'started');}catch{}
    }
  },[assessable,eligibleForReview,reviewCount,reviewKey,automaticReview,artifact?.id,currentAssessment]);
  const openedDraft=useRef(null);
  useEffect(()=>{
    if(!assessable||!currentAssessment?.quality?.ready||nativeDiagramsMissing||openedDraft.current===artifact.id)return;
    openedDraft.current=artifact.id;
    void act(()=>onCanvas(artifact,job.id));
  },[assessable,currentAssessment,nativeDiagramsMissing,artifact?.id,job?.id]);
  async function linkMappings(){
    const result=await call('reconciliation',{artifactId:artifact.id});
    if(result.status==='proposal_missing'){setMappingStatus('File links missing from package.');return;}
    const verified=await verifyArtifactWork(result);
    if(verified.payload.artifactId!==artifact.id||verified.payload.artifactSha256!==artifact.sha256||verified.payload.sessionId!==job.id)throw Error('The mapping receipt does not match this captured package.');
    onWorkModelChange({kind:'artifact',verified},projectId);setMappingStatus('Files connected to design blocks.');
  }
  useEffect(()=>{
    if(!onWorkModelChange||!artifact||!artifactIntentLoaded||canvasTurn||artifact.files.some(file=>file.path===CANVAS_ARTIFACT)&&!artifact.files.some(file=>file.path==='architecture-work-proposal.json')||running||uncertain||busy||contextBusy||job?.last_status!=='completed'||artifact.runId!==job.run||mappedArtifacts.current.has(artifact.id))return;
    mappedArtifacts.current.add(artifact.id);setMappingStatus('Connecting files to design blocks…');void act(linkMappings);
  },[artifact?.id,job?.run,job?.state,busy,contextBusy,artifactIntentLoaded,canvasTurn]);
  function downloadActivity(){
    const data=new Blob([JSON.stringify({projectId,sessionId:job.id,throughSequence:events.at(-1)?.sequence||0,events},null,2)],{type:'application/json'});
    const url=URL.createObjectURL(data),link=document.createElement('a');
    link.href=url;link.download='engineering-activity.json';link.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  return <div className="engineering-panel">
    <h2>Architecture workspace</h2>
    {onDesign&&<button onClick={onDesign}>Return to Design</button>}

    {retainedOrder.pending&&<section aria-label="Retained block request"><p role="status">Block request retained · {retainedOrder.pending.blockId}</p>
      <button disabled={busy||loading} onClick={()=>void act(()=>sendBlockOrder(retainedOrder.pending))}>Retry saved block request</button>
      <button disabled={busy||loading} onClick={()=>void act(async()=>{const request=retainedOrder.pending.requestId;retainOrder(null);onBuildRequestHandled?.(request);})}>Forget saved request</button>
      <p>Retry uses the original block and saved design. Forgetting this record does not stop agent work.</p>
    </section>}
    {retainedOrder.error&&<div><p role="alert">{retainedOrder.error}</p><button disabled={busy||loading} onClick={()=>void act(async()=>retainOrder(null))}>Clear unreadable request record</button></div>}

    {buildRequest?.projectId===projectId&&!retainedOrder.pending&&<p role="status">{failedBuildRequest===buildRequest.id?'Block request needs attention.':restoreBlocked?'Your request is waiting. Retry loading earlier work before starting.':uncertain?'Your request is waiting. Recover the existing request first to avoid duplicate work.':contextBusy?'Your request is waiting for the current design changes.':!job&&!exactSelection?'Your request is waiting here. Choose a model and reasoning level below; it will then start automatically.':'Your request is queued.'}
      {failedBuildRequest===buildRequest.id&&<button disabled={busy||loading} onClick={()=>{consumedBuild.current=null;setFailedBuildRequest(null);}}>Retry block preparation</button>}
      <button disabled={busy} onClick={()=>onBuildRequestHandled?.(buildRequest.id)}>Cancel queued request</button></p>}
    {restoreBlocked&&<button disabled={loading||busy} onClick={()=>{setError('');setRestoreAttempt(value=>value+1);}}>Retry loading earlier work</button>}
    {loading?<p role="status">Finding your project’s work…</p>:<>
      {job?<>
        {(running||uncertain)&&<div className="generation-progress" role="progressbar" aria-label="Project generation" aria-valuetext={activity}><span/></div>}
        {(running||uncertain)&&<p className="generation-activity" role="status">{activity}{lastReceived&&<> · Last update received {Math.max(0,Math.floor((now-lastReceived)/1000))}s ago</>}</p>}
        <p className="generation-status" role="status">{(running||uncertain||busy)&&<BrainActivity size={24}/>} {running?'Working':uncertain?'Recovering acceptance of your last request':finalization?.kind==='finalization_needs_attention'?'Files generated · Checks need attention':job.last_status?({completed:'Work completed',interrupted:'Work stopped',failed:'Work needs attention'}[job.last_status]||job.last_status):'Ready'} · {job.model} · {job.effort}</p>

      </>:<>
        <p>{exactSelection?`${connection.model} · ${connection.effort}`:'Choose a Codex model and reasoning level to start.'}</p>
        {!exactSelection&&<button onClick={onConnections}>Choose model</button>}
        {contextBusy&&<p role="status">Finish the current design changes before starting new work.</p>}
      </>}
      {!hasSources&&!running?<div><p>Add a specification to develop the architecture. Existing blocks can be exported individually.</p><button disabled={busy||contextBusy} onClick={onRequestArchitecture}>Add specification</button></div>:<form onSubmit={submitIntent}>
        <details open={running||undefined}><summary>{running?'Add an update':'Additional instructions (optional)'}</summary><label htmlFor="engineering-intent">{running?'Add an architecture update':'Additional instructions (optional)'}</label>
        <textarea id="engineering-intent" rows={2} value={draft} onChange={e=>setDraft(e.target.value)}/></details>
        {architectureText.length>80000&&<p role="alert">This update exceeds 80,000 characters. Edit it before sending; your draft is retained.</p>}
        <button disabled={busy||restoreBlocked||uncertain||contextBusy||!!retainedOrder.pending||!!retainedOrder.error||!canSubmit||architectureText.length>80000||(!job&&!exactSelection)}>{busy?<><BrainActivity size={22}/> Sending…</>:running?'Send update':'Refine architecture'}</button>
      </form>}
      {job&&<>
        {running&&<button disabled={busy} onClick={()=>act(async()=>{const next=await call('interrupt');if(live.current)setJob(next);})}>Stop generation</button>}

        <details className="engineering-actions"><summary>Connection and package details</summary>{finalization&&<p>{finalization.text}</p>}
          <button disabled={busy} onClick={()=>act(async()=>{const next=await call('recover');if(live.current)setJob(next);})}>Refresh connection status</button>
          {running&&<button disabled={busy} onClick={()=>act(async()=>{const next=await call('interrupt');if(live.current)setJob(next);})}>Stop work</button>}
          {!running&&!uncertain&&job.last_status&&<button disabled={busy} onClick={()=>act(async()=>{const captured=await call('capture');if(live.current)setArtifact(captured);})}>Refresh package snapshot</button>}
        </details>
        <details><summary>Engineering progress (<span key={events.length} className={`engineering-progress-count${running||uncertain?' updated':''}`}>{events.length}</span>)</summary><p>Latest {visibleProgress.length} progress entries.</p><button disabled={!events.length} onClick={downloadActivity}>Download loaded activity</button><ol>{visibleProgress.map(event=><li key={event.sequence}>{event.kind}{event.text?` · ${event.text}`:''}</li>)}</ol></details>
      </>}
      {artifact&&<div className="engineering-artifact"><p>{artifact.runId!==job?.run||running||uncertain?'Previous files':'Project files'} · {artifact.files.filter(file=>file.kind==='file').length} {artifact.files.filter(file=>file.kind==='file').length===1?'file':'files'}</p>
        {artifact.runId!==job?.run&&<p>{running||uncertain?'Generating updated files…':'Generate updated files to include your changes.'}</p>}
        {currentAssessment?.quality&&<p role="status">Structural coverage {currentAssessment.quality.score}% · {reviewCount} review passes · {currentAssessment.quality.ready?'Structure checked · content review pending':'Needs review'}</p>}
        {nativeDiagramsMissing&&<p role="status">Native system diagrams are missing from this draft.</p>}
        {currentAssessment?.error&&<p role="status">{currentAssessment.error}</p>}
        {eligibleForReview&&reviewCount>=3&&<p role="status">Three review passes used. The remaining checks need review.</p>}
        {hasCanvas&&onCanvas&&running&&<p role="status">Reviewing the architecture against your specification.</p>}
        {hasCanvas&&onCanvas&&!running&&!uncertain&&artifact.runId===job?.run&&!hasReview&&<button disabled={busy||contextBusy} onClick={()=>submitIntent(null,REFINE_CODEX_CANVAS,true)}>Refine from source</button>}
        {hasCanvas&&onCanvas&&artifact.runId===job?.run&&job.last_status==='completed'&&<button className="btn primary" disabled={busy||running||uncertain||contextBusy} onClick={()=>act(()=>onCanvas(artifact,job.id))}>Open architecture</button>}
        {onDelivery&&<button disabled={busy} onClick={onDelivery}>Review and download handoff</button>}

        {onWorkModelChange&&!hasCanvas&&<p className="muted small" role="status">{running||uncertain?'File links update when generation finishes.':artifact.runId!==job?.run?'File links belong to the previous snapshot.':mappingStatus||'Connecting files to design blocks…'}</p>}
        {!running&&!uncertain&&artifact.runId===job?.run&&mappingStatus==='File links missing from package.'&&<button disabled={busy||contextBusy} onClick={()=>submitIntent(null,'Add architecture-work-proposal.json binding the existing implementation files to the saved design blocks and requirements. Preserve the application and requirements. Run applicable local checks; retain failed or unexecuted checks explicitly.')}>Repair file links</button>}


      </div>}
    </>}
    {error&&<p role="alert">{error}</p>}
    {draftError&&<p role="alert">{draftError}</p>}
  </div>;
}
