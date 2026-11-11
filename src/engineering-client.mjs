// Backend-owned jobs: no native thread IDs, host paths or model credentials.
export async function engineeringCall(session, action, payload, {signal,fetcher=fetch}={}) {
  if(!session?.token)throw new Error('Connect to the session service first.');
  const response=await fetcher(`/api/engineering/${action}`,{method:'POST',signal,
    headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify(payload)});
  if(!response.ok){
    let detail;try{detail=(await response.json()).detail;}catch{}
    const error=new Error(typeof detail==='string'?detail:'The engineering request could not be accepted. Your draft is retained.');
    error.status=response.status;throw error;
  }
  if(action==='download')return response;
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
