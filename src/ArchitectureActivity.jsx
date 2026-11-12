import {BrainActivity} from './BrainActivity.jsx';
import React,{useEffect,useRef,useState,useId} from 'react';
import {mergeArchitectureActivity,readArchitectureActivity} from './architecture-activity.mjs';
import {architectureSteps,architectureActivityLabel} from './activity-presentation.mjs';
import {ChatMessage} from './ChatMessage.jsx';
import './architecture-activity.css';
// A view of observed work, never a completion claim about the client's system.
function TurnActivity({label,latest,steps=[],model,effort,working=false,failed=false,open,onOpenChange,onStop,children}){
 const [expanded,setExpanded]=useState(false),id=useId();const shown=open??expanded;
 const change=value=>{setExpanded(value);onOpenChange?.(value);};
 useEffect(()=>{if(failed)change(true);},[failed]);
 return <div className={'turn-activity'+(failed?' has-error':'')}>
  <div className="turn-activity-row">
   <button type="button" className="turn-activity-toggle" aria-expanded={shown} aria-controls={id} title={[model,effort].filter(Boolean).join(' · ')} onClick={()=>{change(!shown);}}>
    <span aria-hidden="true" className={'turn-state-icon'+(working?' has-brain':'')}>{working?<BrainActivity size={22}/>:failed?'!':'›'}</span>
    <span className="turn-activity-label" role="status" aria-live="polite">{label}</span>{latest&&<span className="turn-latest"> · {latest}</span>}
    <span className="turn-chevron" aria-hidden="true">{shown?'⌄':'›'}</span>
   </button>
   {onStop&&working&&<button type="button" className="turn-inline-action" onClick={onStop}>Stop</button>}
  </div>
  <div id={id} hidden={!shown} className="turn-activity-details">
   {(model||effort)&&<p className="turn-selection">{[model,effort].filter(Boolean).join(' · ')}</p>}
   <ol>{steps.map(step=><li key={step.id} data-step={step.id}>{step.message?<ChatMessage text={step.text}/>:<p>{step.text}</p>}{step.detail&&<small>{step.detail}</small>}</li>)}</ol>
   {children}
  </div>
 </div>;
}

export function ArchitectureTurn({turn,projectId,session,active,working,onStop,historyNumber}){
 const [open,setOpen]=useState(false),[events,setEvents]=useState([]),[status,setStatus]=useState(null),[error,setError]=useState('');const cursor=useRef(0),observed=useRef([]);
 useEffect(()=>{
  if((!open&&!active)||!session?.architectureActivityEnabled)return;
  let stopped=false,timer;const controller=new AbortController();
  async function poll(){try{
   const value=await readArchitectureActivity(session,projectId,turn.id,cursor.current,controller.signal);
   if(stopped)return;const merged=mergeArchitectureActivity(observed.current,value.events);observed.current=merged;setEvents(merged);setStatus(value.state);setError('');
   if(value.events.length)cursor.current=value.events.at(-1).sequence;
   if(value.state==='running'||value.events.length===200)timer=setTimeout(poll,value.events.length===200?0:700);
  }catch(e){if(!stopped&&e.name!=='AbortError'){setError(e.status===404?'Details not recorded for this turn.':e.message);if(e.status===404&&working)timer=setTimeout(poll,1000);}}}
  void poll();return()=>{stopped=true;controller.abort();clearTimeout(timer);};
 },[open,active,projectId,turn.id,turn.clientStatus,session?.token,session?.architectureActivityEnabled,working]);
 const steps=architectureSteps(events),label=architectureActivityLabel(turn,status,active),failed=status==='failed'||turn.clientStatus==='failed';
 return <div className="conversation-activity" data-turn={turn.id}><TurnActivity label={historyNumber?'Activity '+historyNumber+' · '+label:label} latest={active?steps.at(-1)?.text:undefined} steps={steps} model={turn.model} effort={turn.effort} working={active} failed={failed} open={open} onOpenChange={setOpen} onStop={active?onStop:undefined}>
  {error&&<p role="status">{error}</p>}
  {!session?.architectureActivityEnabled&&<p>Live details are unavailable from this service. The reply remains in chat.</p>}
  {turn.detailsAvailable===false&&<p>Some activity details were not recorded. The returned response remains in chat.</p>}
 </TurnActivity></div>;
}
export function EarlierArchitectureActivity({entries,projectId,session}){
 const [open,setOpen]=useState(false);
 return <details className="legacy-activity" open={open} onToggle={e=>setOpen(e.currentTarget.open)}><summary>{entries.length} earlier {entries.length===1?'turn':'turns'} · activity history</summary>
  {open&&<><p>Recorded before activity was linked to individual replies.</p>{entries.toReversed().map(({turn,number})=><ArchitectureTurn key={projectId+':'+turn.id} turn={turn} projectId={projectId} session={session} active={false} working={false} historyNumber={number}/>)}</>}
 </details>;
}
