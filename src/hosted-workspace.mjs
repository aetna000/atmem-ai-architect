// Same-origin parent owns Firebase identity; the workspace never receives a token or provider key.
export const HOSTED=import.meta.env?.VITE_ARCHITECT_HOSTED==='1';
let initial=null,port=null,sequence=0;const waiting=new Map(),versions=new Map();let changeSequence=0;
export function hostedRevision(id){return versions.get(id)||0;}
export function noteHostedChange(projectId){const version=++changeSequence;versions.set(projectId,version);return hostedCall('changed',{projectId,version});}
export function hostedInitial(){if(!initial)throw Error('Hosted workspace is not connected.');return initial;}
export function hostedCall(action,payload={},signal){
 if(!port)return Promise.reject(Error('Return to Architect and reopen your project.'));
 if(signal?.aborted)return Promise.reject(new DOMException('Aborted','AbortError'));
 const id=++sequence;
 return new Promise((resolve,reject)=>{
  const timeout=setTimeout(()=>finish(Error('The workspace request timed out. Your draft remains open.')),10*60*1000);
  const abort=()=>{port.postMessage({type:'abort',id});finish(new DOMException('Aborted','AbortError'));};
  function finish(error,value){clearTimeout(timeout);signal?.removeEventListener('abort',abort);waiting.delete(id);error?reject(error):resolve(value);}
  waiting.set(id,finish);signal?.addEventListener('abort',abort,{once:true});port.postMessage({type:'request',id,action,payload});
 });
}
export async function connectHostedWorkspace(){
 if(!HOSTED)return;
 if(window.parent===window)throw Error('Open your project from atmem.ai/architect.');
 initial=await new Promise((resolve,reject)=>{
  const timeout=setTimeout(()=>{window.removeEventListener('message',receive);reject(Error('Return to Architect and reopen your project.'));},15000);
  function receive(event){
   if(event.origin!==location.origin||event.source!==parent||event.data?.type!=='atmem.workspace.initialize'||event.ports.length!==1)return;
   clearTimeout(timeout);window.removeEventListener('message',receive);port=event.ports[0];
   port.onmessage=({data})=>{if(data?.type==='response')waiting.get(data.id)?.(data.error?Error(data.error):null,data.value);};port.start();resolve(event.data.initial);
  }
  window.addEventListener('message',receive);window.parent.postMessage({type:'atmem.workspace.ready'},location.origin);
 });
 // Do not leave project drafts, conversations or profile state in a shared browser's local storage.
 const values=new Map([['atmem-architect-theme',initial.theme||'light']]);
 const transient={getItem:key=>values.get(String(key))??null,setItem:(key,value)=>values.set(String(key),String(value)),removeItem:key=>values.delete(String(key)),clear:()=>values.clear(),key:index=>[...values.keys()][index]??null,get length(){return values.size;}};
 Object.defineProperty(window,'localStorage',{value:transient,configurable:true});
 const network=window.fetch.bind(window);
 window.fetch=async(input,options={})=>{
  const url=new URL(typeof input==='string'?input:input.url,location.href);
  if(url.origin!==location.origin||!url.pathname.startsWith('/api/'))return network(input,options);
  let body=null;
  if(options.body){
   if(typeof options.body==='string')body=JSON.parse(options.body);
   else{
    const bytes=new Uint8Array(options.body instanceof Blob?await options.body.arrayBuffer():options.body);
    let binary='';for(let start=0;start<bytes.length;start+=8192)binary+=String.fromCharCode(...bytes.subarray(start,start+8192));
    body={__workspaceBinary:btoa(binary)};
   }
  }
  if(url.pathname==='/api/projects/save'&&body)body.bridgeVersion??=hostedRevision(body.id);
  const result=await hostedCall('fetch',{path:url.pathname,method:options.method||'GET',body},options.signal);
  const content=result.base64?Uint8Array.from(atob(result.base64),character=>character.charCodeAt(0)):result.bytes?new Uint8Array(result.bytes):JSON.stringify(result.body);
  return new Response(content,{status:result.status,headers:result.headers||{'Content-Type':'application/json'}});
 };
}
