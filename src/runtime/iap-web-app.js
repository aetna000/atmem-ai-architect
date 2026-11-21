'use strict';
const byId=id=>document.getElementById(id);
let config,pending=null,epoch=0;
const status=text=>{byId('status').textContent=text;};
function clear(){epoch++;if(pending)pending.abort();pending=null;byId('question').value='';byId('answer').replaceChildren();byId('citations').replaceChildren();byId('submit').disabled=!config;}
byId('clear').addEventListener('click',()=>{clear();status('Input and result cleared. Your company sign-in is managed by Identity-Aware Proxy.');});
function render(data){
 if(data.requiresHumanReview!==true||!data.result||typeof data.result!=='object'||Array.isArray(data.result)||Object.keys(data.result).length!==config.fields.length)throw Error('The result could not be verified.');
 const valid=config.fields.every(f=>{const v=data.result[f.name];return typeof v===f.type&&(f.type!=='number'||Number.isFinite(v))&&(f.type!=='string'||Array.from(v).length<=(f.maxLength||4096))&&(!f.values||f.values.includes(v));});
 if(!valid)throw Error('The result could not be verified.');
 const fragment=document.createDocumentFragment();
 for(const f of config.fields){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=f.description;dd.textContent=typeof data.result[f.name]==='boolean'?(data.result[f.name]?'Yes':'No'):String(data.result[f.name]);fragment.append(dt,dd);}
 byId('answer').replaceChildren(fragment);status('Result prepared. Review it before taking action.');
}
byId('ask').addEventListener('submit',async event=>{
 event.preventDefault();if(!config||pending)return;
 const text=byId('question').value.trim();if(!text||new TextEncoder().encode(text).length>config.maxInputBytes){status('Use at most '+config.maxInputBytes.toLocaleString()+' UTF-8 bytes.');return;}
 const controller=new AbortController(),started=epoch;pending=controller;byId('submit').disabled=true;byId('answer').replaceChildren();status('Preparing a result…');
 const timer=setTimeout(()=>controller.abort(),config.requestDeadlineMs||28000);
 try{
  const response=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({text}),signal:controller.signal,cache:'no-store',redirect:'error'});
  if(started!==epoch)return;
  if(response.status===401||response.status===403){config=null;clear();byId('question').disabled=true;status('Your company session or access needs checking. Reopen this workspace to sign in.');return;}
  const data=await response.json();if(started!==epoch)return;
  if(!response.ok){if(data.error==='data_retention_unverified')throw Error('The app owner needs to verify its data-handling setup. Your input was not sent to the AI.');if(response.status===429)throw Error('The workspace is busy. Try again shortly.');throw Error('The AI result is unavailable or could not be verified.');}
  render(data);
 }catch(error){if(started===epoch)status(error.name==='AbortError'?'The request timed out. Try again later.':error.message);}
 finally{clearTimeout(timer);if(pending===controller)pending=null;byId('submit').disabled=!config||!!pending;}
});
async function initialize(){
 const response=await fetch('/config.json',{cache:'no-store',credentials:'same-origin',redirect:'error'});if(!response.ok)throw Error('Configuration unavailable');
 const value=await response.json(),fields=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(value.fieldsBase64),c=>c.charCodeAt(0))));
 if(!Number.isInteger(value.maxInputBytes)||value.maxInputBytes<1||value.maxInputBytes>20000||!Array.isArray(fields)||!fields.length||fields.length>24||fields.some(f=>typeof f.name!=='string'||typeof f.description!=='string'||!['string','boolean','number'].includes(f.type)))throw Error('Invalid configuration');
 config={...value,fields};byId('question').maxLength=value.maxInputBytes;byId('question').disabled=false;byId('submit').disabled=false;status('Company sign-in protects this workspace. Submit input for a result you can review.');
}
initialize().catch(()=>status('Access or configuration could not be verified. Reopen this workspace to sign in.'));
