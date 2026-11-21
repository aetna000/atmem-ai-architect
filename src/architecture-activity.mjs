export const ACTIVITY_KINDS=['context_started','context_ready','pass_started','model_started','model_message','model_checked','response_repair','tool_started','tool_finished','tool_cached','response_ready','failed','cancelled'];
export function architectureTurns(project){
 const value=project.extensions?.architectureActivity;
 if(value===undefined)return [];
 if(value.version!==1||!Array.isArray(value.turns)||value.turns.length>1000)throw Error('Unsupported or oversized architecture activity history. Keep the original project file.');
 const seen=new Set();
 for(const t of value.turns){if(t?.requestIds!==undefined&&(!Array.isArray(t.requestIds)||t.requestIds.length>1000||t.requestIds.some(id=>typeof id!=='string'||id.length>100)))throw Error('Invalid architecture request association.');if(!t||typeof t.id!=='string'||!/^[a-f0-9-]{36}$/.test(t.id)||seen.has(t.id)||typeof t.model!=='string'||typeof t.provider!=='string'||!['submitted','response_received','failed','cancelled'].includes(t.clientStatus))throw Error('Invalid architecture turn identity.');seen.add(t.id);}
 return value.turns;
}
export function recordArchitectureTurn(project,owner,turn){
 if(project.id!==owner)return project;
 const turns=architectureTurns(project);
 if(turns.some(t=>t.id===turn.id))throw Error('Architecture turn is already recorded; no request was replayed.');
 const value={version:1,turns:[...turns,{...turn,clientStatus:'submitted'}]};architectureTurns({extensions:{architectureActivity:value}});
 return {...project,extensions:{...project.extensions,architectureActivity:value}};
}
export function finishArchitectureTurn(project,owner,id,clientStatus,detailsAvailable){
 if(project.id!==owner)return project;
 const turns=architectureTurns(project);if(!turns.some(t=>t.id===id))return project;
 const value={version:1,turns:turns.map(t=>t.id===id?{...t,clientStatus,...(detailsAvailable===undefined?{}:{detailsAvailable})}:t)};architectureTurns({extensions:{architectureActivity:value}});
 return {...project,extensions:{...project.extensions,architectureActivity:value}};
}
// Exact request/reply associations keep activity inside the conversation. Older
// unbound records stay in turn order before the next associated turn; never guess
// that an unrelated reply belongs to them or discard historical activity.
export function architectureConversation(project,messages){
 let turns;try{turns=architectureTurns(project);}catch(error){return [...messages.map((message,index)=>({kind:'message',message,index})),{kind:'activity-error',error:error.message}];}
 const positions=turns.map(turn=>{
  const requests=messages.flatMap((m,i)=>m.role==='user'&&turn.requestIds?.includes(m.requestId)?[i]:[]);
  if(requests.length)return Math.max(...requests)+1;
  const reply=messages.findIndex(m=>m.activityId===turn.id);return reply<0?null:reply;
 });
 const slots=new Map();turns.forEach((turn,i)=>{
  const at=positions[i]??positions.slice(i+1).find(p=>p!==null)??messages.length;
  const entries=slots.get(at)||[];entries.push({kind:'activity',turn,number:i+1,unassociated:positions[i]===null});slots.set(at,entries);
 });
 return Array.from({length:messages.length+1},(_,i)=>[...(slots.get(i)||[]),...(i<messages.length?[{kind:'message',message:messages[i],index:i}]:[])]).flat();
}
export function mergeArchitectureActivity(current,incoming){
 const map=new Map(current.map(e=>[e.sequence,e]));
 for(const e of incoming){
  if(!Number.isSafeInteger(e.sequence)||e.sequence<1||!ACTIVITY_KINDS.includes(e.kind)||typeof e.text!=='string'||e.text.length>16000)throw Error('The service returned unsupported activity details.');
  if(map.has(e.sequence)&&JSON.stringify(map.get(e.sequence))!==JSON.stringify(e))throw Error('A recorded activity event changed identity.');
  map.set(e.sequence,e);
 }
 return [...map.values()].sort((a,b)=>a.sequence-b.sequence);
}
export async function readArchitectureActivity(session,projectId,id,after,signal,fetcher=fetch){
 const r=await fetcher('/api/architect/activity',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+session.token},body:JSON.stringify({projectId,activityId:id,after}),signal});
 if(!r.ok){const error=Error(r.status===404?'Detailed activity is not recorded in this service for this turn.':'Architecture activity could not be loaded.');error.status=r.status;throw error;}
 const value=await r.json();if(value.id!==id||value.projectId!==projectId||!Array.isArray(value.events))throw Error('Activity does not belong to this project and turn.');return value;
}

export function architectureChatEntries(project,messages){
 const entries=[];
 for(const entry of architectureConversation(project,messages)){
  if(entry.kind==='activity'&&entry.unassociated){
   const previous=entries.at(-1);if(previous?.kind==='legacy-activity')previous.entries.push(entry);
   else entries.push({kind:'legacy-activity',id:'legacy:'+entry.turn.id,entries:[entry]});
  }else entries.push(entry);
 }
 return entries;
}
