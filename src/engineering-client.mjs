// Backend-owned jobs: no native thread IDs, host paths or model credentials.
import {unzipSync} from 'fflate';
export async function engineeringCall(session, action, payload, {signal,fetcher=fetch}={}) {
  if(!session?.token)throw new Error('Connect to the session service first.');
  const response=await fetcher(`/api/engineering/${action}`,{method:'POST',signal,
    headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify(payload)});
  if(!response.ok){
    let detail;try{detail=(await response.json()).detail;}catch{}
    const error=new Error(typeof detail==='string'?detail:'The engineering request could not be accepted. Your draft is retained.');
    error.status=response.status;throw error;
  }
  if(action==='download'||action==='handoff')return response;
  return response.json();
}

export function mergeEngineeringEvents(current,incoming){
  const bySequence=new Map(current.map(event=>[event.sequence,event]));
  for(const event of incoming)bySequence.set(event.sequence,event);
  return [...bySequence.values()].sort((a,b)=>a.sequence-b.sequence);
}

export async function verifiedEngineeringDownload(session,payload,manifest,options){
  const response=await engineeringCall(session,'download',payload,options);
  const bytes=await response.arrayBuffer();
  const digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
  if(digest!==manifest.sha256 || response.headers.get('X-Artifact-Sha256')!==digest)
    throw new Error('The package digest did not match its capture receipt. Download was stopped.');
  return new Blob([bytes],{type:'application/zip'});
}

export async function verifiedHandoffDownload(session,payload,manifest,options){
  const response=await engineeringCall(session,'handoff',payload,options);
  const bytes=await response.arrayBuffer();
  const digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
  if(response.headers.get('X-Artifact-Sha256')!==digest||response.headers.get('X-Source-Artifact-Sha256')!==manifest.sha256)
    throw new Error('The handoff digest or source package did not match its receipt. Download was stopped.');
  let expanded=0;
  const files=unzipSync(new Uint8Array(bytes),{filter:entry=>{
    expanded+=entry.originalSize;
    if(expanded>150_000_000)throw new Error('The handoff exceeds its receiving size bound. Download was stopped.');
    return true;
  }});
  const sha=async value=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',value))].map(x=>x.toString(16).padStart(2,'0')).join('');
  const original=files['evidence/original-implementation.zip'];
  if(!original||await sha(original)!==manifest.sha256)
    throw new Error('The original implementation inside the handoff did not match its receipt. Download was stopped.');
  const expected=manifest.files.filter(file=>file.kind==='file');
  const receiving=Object.keys(files).filter(name=>name.startsWith('implementation/')&&!name.endsWith('/'));
  if(receiving.length!==expected.length)throw new Error('The handoff file inventory changed. Download was stopped.');
  for(const file of expected){
    const content=files['implementation/'+file.path];
    if(!content||content.byteLength!==file.bytes||await sha(content)!==file.sha256)
      throw new Error('An implementation file inside the handoff did not match its receipt. Download was stopped.');
  }
  return new Blob([bytes],{type:'application/zip'});
}


// User requests and model deltas remain separate from tool-progress/acceptance claims.
export function engineeringConversation(events){
  const ordered=mergeEngineeringEvents([],events),accepted=new Set(ordered.filter(e=>e.kind==='steering_accepted').map(e=>e.requestId)),uncertain=new Set(ordered.filter(e=>e.kind==='steering_delivery_uncertain').map(e=>e.requestId));
  const entries=[];
  for(const event of ordered){
    if(event.kind==='accepted'&&event.origin!=='automatic_repair'&&typeof event.text==='string')entries.push({id:event.sequence,role:'user',text:event.text,status:'accepted'});
    else if(event.kind==='steering_submitted'&&typeof event.text==='string')entries.push({id:event.sequence,role:'user',text:event.text,status:accepted.has(event.requestId)?'accepted':uncertain.has(event.requestId)?'uncertain':'pending'});
    else if(event.kind==='message'&&typeof event.text==='string'){
      const previous=entries.at(-1);
      if(previous?.role==='assistant'&&previous.runId===event.runId)previous.text+=event.text;
      else entries.push({id:event.sequence,role:'assistant',runId:event.runId,text:event.text});
    }
  }
  return entries;
}
