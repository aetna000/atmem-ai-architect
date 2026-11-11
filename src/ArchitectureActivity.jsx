import React,{useEffect,useRef,useState} from 'react';
import {mergeArchitectureActivity,readArchitectureActivity} from './architecture-activity.mjs';
import {ChatMessage} from './ChatMessage.jsx';
import './architecture-activity.css';
const states={running:'Working',response_ready:'Response ready',failed:'Could not finish',cancelled:'Stopped',recovery_required:'Outcome unknown after service restart',details_unavailable:'Some details unavailable'};
const tools={'project.read':'Current design','memory.lookup':'Project memory','knowledge.lookup':'Engineering sources','skills.lookup':'Engineering guidance','pricing.lookup':'Provider prices','pricing.aws_s3':'Provider prices'};
export function ArchitectureTurn({turn,number,projectId,session,active,working}){
 const [open,setOpen]=useState(active),[events,setEvents]=useState([]),[status,setStatus]=useState(null),[error,setError]=useState('');const cursor=useRef(0),observed=useRef([]);
 useEffect(()=>{if(active)setOpen(true);},[active]);
 useEffect(()=>{
  if(!open||!session?.architectureActivityEnabled)return;
  let stopped=false,timer;const controller=new AbortController();
  async function poll(){try{
   const value=await readArchitectureActivity(session,projectId,turn.id,cursor.current,controller.signal);
   if(stopped)return;const merged=mergeArchitectureActivity(observed.current,value.events);observed.current=merged;setEvents(merged);setStatus(value.state);setError('');
   if(value.events.length)cursor.current=value.events.at(-1).sequence;
   if(value.state==='running'||value.events.length===200)timer=setTimeout(poll,value.events.length===200?0:700);
  }catch(e){if(!stopped&&e.name!=='AbortError'){setError(e.message);if(e.status===404&&working)timer=setTimeout(poll,1000);}}}
  void poll();return()=>{stopped=true;controller.abort();clearTimeout(timer);};
 },[open,projectId,turn.id,turn.clientStatus,session?.token,session?.architectureActivityEnabled,working]);
 const attempts=events.filter(e=>e.kind==='model_started').length;
 return <details className="architecture-turn conversation-activity" open={open} onToggle={e=>setOpen(e.currentTarget.open)}>
  <summary><strong>Architect activity · turn {number}</strong><span>{turn.model}{turn.effort?' · '+turn.effort:''}</span><em>{states[status]||({submitted:active?'Preparing':'Awaiting details',response_received:'Response received',failed:'Request failed',cancelled:'Stopped'}[turn.clientStatus])}</em></summary>
  <div className="architecture-turn-body">
   {attempts>0&&<p className="activity-count">{attempts} model {attempts===1?'attempt':'attempts'} recorded</p>}
   {session?.architectureActivityEnabled?<>{error&&<p role="status">{error}</p>}<ol aria-label={'Activity for turn '+number}>{events.toReversed().map(e=><li data-sequence={e.sequence} key={e.sequence} className={'activity-'+e.kind}>
    <div className="activity-event-heading"><span className="activity-dot"/><strong>{e.kind==='model_started'?`Model attempt ${e.details?.attempt||''}${e.details?.round?' · pass '+e.details.round:''}`:e.kind==='model_message'?'Architect update':e.details?.tool?tools[e.details.tool]||e.details.tool:e.text}</strong><time dateTime={e.at}>{e.at?new Date(e.at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'}):''}</time></div>
    {e.kind==='model_message'?<ChatMessage text={e.text}/>:e.details?.tool&&<p>{e.kind==='tool_finished'&&e.details.success===false?'Evidence was unavailable.':e.text}</p>}
    {!!e.details?.skillIds?.length&&<p>Guidance: {e.details.skillIds.join(', ')}</p>}
    {e.details?.recordCount!==undefined&&<p>{e.details.recordCount} relevant memory references</p>}
   </li>)}</ol></>:<p>This service provides conversation replies; detailed live activity is not available here.</p>}
   {turn.detailsAvailable===false&&<p>Some progress details could not be recorded. The conversation contains the returned response.</p>}
  </div>
 </details>;
}
