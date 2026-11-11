import React,{useEffect,useRef,useState} from 'react';
import {architectureTurns,mergeArchitectureActivity,readArchitectureActivity} from './architecture-activity.mjs';
import {ChatMessage} from './ChatMessage.jsx';
import './architecture-activity.css';
const states={running:'Working',response_ready:'Response ready',failed:'Could not finish',cancelled:'Stopped',recovery_required:'Outcome unknown after service restart',details_unavailable:'Some details unavailable'};
const tools={'project.read':'Current design','memory.lookup':'Project memory','knowledge.lookup':'Engineering sources','skills.lookup':'Engineering guidance','pricing.lookup':'Provider prices','pricing.aws_s3':'Provider prices'};
function Turn({turn,number,projectId,session,active,working}){
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
 return <details className="architecture-turn" open={open} onToggle={e=>setOpen(e.currentTarget.open)}>
  <summary><strong>Turn {number}</strong><span>{turn.model}{turn.effort?' · '+turn.effort:''}</span><em>{states[status]||({submitted:active?'Preparing':'Awaiting details',response_received:'Response received',failed:'Request failed',cancelled:'Stopped'}[turn.clientStatus])}</em></summary>
  <div className="architecture-turn-body">
   {attempts>0&&<p className="activity-count">{attempts} model {attempts===1?'attempt':'attempts'} recorded</p>}
   {session?.architectureActivityEnabled?<>{error&&<p role="status">{error}</p>}<ol aria-label={'Activity for turn '+number}>{events.map(e=><li key={e.sequence} className={'activity-'+e.kind}>
    <div className="activity-event-heading"><span className="activity-dot"/><strong>{e.kind==='model_started'?`Model attempt ${e.details?.attempt||''}${e.details?.round?' · pass '+e.details.round:''}`:e.kind==='model_message'?'Architect update':e.details?.tool?tools[e.details.tool]||e.details.tool:e.text}</strong><time dateTime={e.at}>{e.at?new Date(e.at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'}):''}</time></div>
    {e.kind==='model_message'?<ChatMessage text={e.text}/>:e.details?.tool&&<p>{e.kind==='tool_finished'&&e.details.success===false?'Evidence was unavailable.':e.text}</p>}
    {!!e.details?.skillIds?.length&&<p>Guidance: {e.details.skillIds.join(', ')}</p>}
    {e.details?.recordCount!==undefined&&<p>{e.details.recordCount} relevant memory references</p>}
   </li>)}</ol></>:<p>This service provides conversation replies; detailed live activity is not available here.</p>}
   {turn.detailsAvailable===false&&<p>Some progress details could not be recorded. The conversation contains the returned response.</p>}
  </div>
 </details>;
}
export function ArchitectureActivity({project,session,busy=false}){
 const [expanded,setExpanded]=useState(false);let turns,error;try{turns=architectureTurns(project);}catch(e){turns=[];error=e.message;}
 useEffect(()=>{if(busy)setExpanded(true);},[busy]);
 if(!turns.length&&!busy&&!error)return null;
 return <details className="architecture-activity" open={expanded} onToggle={e=>setExpanded(e.currentTarget.open)}>
  <summary>Architecture activity <span role="status">{busy?'Working…':`${turns.length} ${turns.length===1?'turn':'turns'}`}</span></summary>
  <p className="activity-caption">Visible architect updates, evidence lookups and response checks.</p>
  {error&&<p role="alert">{error}</p>}
  {!turns.length&&busy&&!session?.architectureActivityEnabled&&<p className="activity-caption">Live details are unavailable from this service. The reply will appear in the conversation.</p>}
  <div className="architecture-turns">{turns.map((turn,i)=><Turn key={project.id+':'+turn.id} turn={turn} number={i+1} projectId={project.id} session={session} active={i===turns.length-1&&(busy||expanded)} working={busy&&turn.clientStatus==='submitted'}/>)}</div>
 </details>;
}
