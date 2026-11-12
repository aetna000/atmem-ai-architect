import {InlineNote} from './HelpNote.jsx';
import {X,Volume2} from 'lucide-react';
import {BrainActivity} from './BrainActivity.jsx';
import React,{useEffect,useRef,useState} from 'react';
import {OpenAIVoice} from './openai-voice.mjs';

export function OpenAIVoicePanel({session,connection,transportRef,onTranscript,onStart,onConnections}){
 const [status,setStatus]=useState(null),[phase,setPhase]=useState('off'),[error,setError]=useState(''),[key,setKey]=useState(''),[saving,setSaving]=useState(false),[automatic,setAutomatic]=useState(false),[readReplies,setReadReplies]=useState(true),[open,setOpen]=useState(false);
 const props=useRef({onTranscript,onStart,automatic});props.current={onTranscript,onStart,automatic};
 const engine=useRef(null),live=useRef(true);
 const active=!['off','error'].includes(phase);
 async function refresh(){
  const response=await fetch('/api/voice/openai/status');
  if(!response.ok)throw Error('The voice service is unavailable. Check the Architect server.');
  const body=await response.json();if(live.current)setStatus(body);
 }
 useEffect(()=>{
  live.current=true;setPhase('off');void refresh().catch(e=>{if(live.current)setError(e.message)});
  return()=>{live.current=false;engine.current?.stop();if(transportRef.current===engine.current)transportRef.current=null;};
 },[session.token]);
 async function configure(){
  setSaving(true);setError('');
  try{
   const response=await fetch('/api/voice/openai/credentials',{method:'POST',headers:{Authorization:`Bearer ${session.token}`,'Content-Type':'application/json'},body:JSON.stringify({key})});
   if(!response.ok)throw Error('The voice key could not be configured. Check the server connection.');
   setKey('');await refresh();
  }catch(e){setError(e.message)}finally{setSaving(false)}
 }
 function start(){
  if(active||!status?.available||!connection)return;
  props.current.onStart?.();setError('');engine.current?.stop();
  const current=new OpenAIVoice({session,
   onState:value=>{if(live.current)setPhase(value)},onError:value=>{if(live.current)setError(value)},
   onTranscript:(text,meta)=>{
    if(props.current.automatic&&!meta.ordered){setAutomatic(false);setError('Automatic sending paused. Review the retained transcript in chat.');}
    props.current.onTranscript(text,props.current.automatic&&meta.ordered);
   }});
  current.readReplies=readReplies;engine.current=current;transportRef.current=current;void current.start().then(()=>{if(live.current&&current.channel?.readyState==='open')setOpen(false)});
 }
 const caption={off:'Off',connecting:'Connecting OpenAI audio…',listening:automatic?'Listening · auto-send':'Listening',speaking:'Speaking',error:'Stopped · retry'}[phase];
 return <>
  <div className="voice-status"><button type="button" className="icon" aria-label="Voice settings" title="Voice settings" onClick={()=>setOpen(true)}><Volume2 size={18}/></button>{active&&<button type="button" onClick={()=>engine.current?.stop({preservePending:true})}>Stop voice</button>}{active&&error.includes('playback')&&<button type="button" onClick={()=>void engine.current?.resumeAudio()}>Enable voice playback</button>}{(active||error)&&<span role="status">{error||caption}</span>}</div>
  {open&&<div className="backdrop" onMouseDown={event=>{if(event.target===event.currentTarget)setOpen(false)}}><section className="modal" role="dialog" aria-modal="true" aria-label="OpenAI voice" onKeyDown={event=>{if(event.key==='Escape'){event.stopPropagation();setOpen(false)}}}>
  <h2>Voice</h2><button type="button" className="icon modal-close" aria-label="Close voice settings" onClick={()=>setOpen(false)}><X size={18}/></button>
  <section aria-label="OpenAI voice settings">
   <small>AI audio · OpenAI</small><InlineNote>Audio and spoken replies go to OpenAI. Audio is not saved. Live verification pending.</InlineNote>
   {!connection&&<button type="button" className="btn" onClick={()=>{setOpen(false);onConnections()}}>Choose AI provider</button>}
   {status&&<details open={!status.available}><summary>API key</summary>

    <label className="dialog-field">OpenAI voice API key<input aria-label="OpenAI voice API key" type="password" autoComplete="off" value={key} onChange={event=>setKey(event.target.value)}/></label>
    <button type="button" className="btn" disabled={saving||active||!key.trim()} onClick={configure}>Use key</button>
   </details>}
   <button type="button" className="link" disabled={saving} onClick={()=>void refresh().catch(e=>setError(e.message))}>Refresh</button>
   <div className="record-row">
    <button type="button" className="btn" disabled={!status?.available||!connection} onClick={active?()=>engine.current?.stop({preservePending:true}):start}>{active?'Stop voice':'Start voice'}</button>
    {active&&<button type="button" className="btn" onClick={()=>engine.current?.interrupt()}>Stop speaking</button>}
    {active&&error.includes('playback')&&<button type="button" className="btn" onClick={()=>void engine.current?.resumeAudio()}>Enable voice playback</button>}
   </div>
   <p><label><input type="checkbox" checked={automatic} onChange={event=>setAutomatic(event.target.checked)}/> Auto-send</label></p>
   <p><label><input type="checkbox" checked={readReplies} onChange={event=>{setReadReplies(event.target.checked);if(engine.current){engine.current.readReplies=event.target.checked;if(!event.target.checked)engine.current.interrupt();}}}/> Read replies</label></p>
   <p role="status">{caption}</p>
   {error&&<p role="alert">{error}</p>}
  </section>
 </section></div>}
 </>;
}
