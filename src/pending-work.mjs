// One shared lifecycle for visible work. Observing a job is not new work.
export function createPendingWork(){
 let sequence=0,snapshot=[];const entries=new Map(),listeners=new Set();
 const publish=()=>{snapshot=[...entries.values()];for(const listener of listeners)listener();};
 return{
  subscribe(listener){listeners.add(listener);return()=>listeners.delete(listener);},
  getSnapshot:()=>snapshot,
  begin(label){const id=++sequence;entries.set(id,{id,label});publish();let finished=false;return()=>{if(finished)return;finished=true;entries.delete(id);publish();};},
 };
}
export const pendingWork=createPendingWork();
let interaction=null;
const marked=new WeakMap();
function mark(element){
 if(!element?.setAttribute)return()=>{};
 let value=marked.get(element);
 if(value)value.count++;else{
  value={count:1,aria:element.getAttribute('aria-busy')};marked.set(element,value);
  element.setAttribute('data-waiting','true');if(value.aria===null)element.setAttribute('aria-busy','true');
 }
 let done=false;return()=>{if(done)return;done=true;if(--value.count)return;
  element.removeAttribute('data-waiting');if(value.aria===null&&element.getAttribute('aria-busy')==='true')element.removeAttribute('aria-busy');marked.delete(element);
 };
}
export function beginPendingWork(label,{associate=true}={}){
 const finish=pendingWork.begin(label),doc=globalThis.document;
 const target=associate&&interaction&&Date.now()-interaction.at<2000&&interaction.element.isConnected?interaction.element:null;
 const dialog=target?.closest('[role="dialog"],dialog')||[...doc?.querySelectorAll('[role="dialog"],dialog[open]')||[]].reverse().find(el=>el.getClientRects().length);
 const clearButton=mark(target),clearDialog=mark(dialog);let done=false;
 return()=>{if(done)return;done=true;clearButton();clearDialog();finish();};
}
export async function withPendingWork(label,operation){const finish=beginPendingWork(label);try{if(globalThis.requestAnimationFrame)await new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)));return await operation();}finally{finish();}}
export function pendingRequestLabel(input,options={}){
 let url;try{url=new URL(typeof input==='string'?input:input.url,'http://architect.local');}catch{return null;}
 const path=url.pathname;if(!path.startsWith('/api/'))return null;
 if(path==='/api/architect/activity'||/\/api\/engineering\/(?:list|events|state|recover|delivery|artifacts|finalizations|validators|validation\/(?:list|get|plan)|checkpoints\/(?:list|get))$/.test(path)||/\/(?:status|health|cli-ready)$/.test(path))return null;
 if(path==='/api/session')return 'Connecting…';
 if(path==='/api/architect')return 'Waiting for Architect…';
 if(path==='/api/diagram-authoring')return 'Generating diagrams…';
 if(path.includes('/projects/save'))return 'Saving project…';
 if(path.includes('/projects/list')||path.includes('/projects/get'))return 'Loading project…';
 if(path.includes('/memory/'))return path.endsWith('/sync')?'Saving memory…':'Loading memory…';
 if(path.includes('/design-sources'))return 'Reading specifications…';
 if(path.includes('/pricing/'))return 'Checking prices…';
 if(path.includes('/voice/'))return 'Processing voice…';
 if(path.includes('/models')||path.includes('/login')||path.includes('/credentials'))return 'Checking connection…';
 if(/\/(?:download|handoff|delivery|orca\/open)$/.test(path))return 'Preparing delivery…';
 if(/\/(?:validate|start|recheck|capture)$/.test(path))return path.includes('/engineering/')?'Starting project work…':'Running checks…';
 return 'Working…';
}
export function trackedFetch(fetcher,begin=beginPendingWork){
 return async function(input,options){
  const label=pendingRequestLabel(input,options);if(!label)return fetcher(input,options);
  const finish=begin(label,{associate:!/(?:\/projects\/save|\/memory\/sync)$/.test(typeof input==='string'?input:input.url)});
  try{return await fetcher(input,options);}finally{finish();}
 };
}
export function installPendingFeedback(host=globalThis){
 if(!host.document||!host.fetch)return()=>{};
 const doc=host.document,original=host.fetch,wrapped=trackedFetch(original.bind(host));
 const capture=event=>{
  let button=event.target?.closest?.('button,[role="button"],a[download]');
  if(event.type==='submit')button=event.submitter||event.target.querySelector('button[type="submit"]');
  if(event.type==='keydown'){
   if(event.key!=='Enter'||event.shiftKey)return;
   button=button||event.target.closest('form')?.querySelector('button[type="submit"]');
  }
  if(button)interaction={element:button,at:Date.now()};
 };
 for(const type of ['click','submit','keydown'])doc.addEventListener(type,capture,true);
 host.fetch=wrapped;
 return()=>{if(host.fetch===wrapped)host.fetch=original;for(const type of ['click','submit','keydown'])doc.removeEventListener(type,capture,true);};
}
