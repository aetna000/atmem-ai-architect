'use strict';
const byId=id=>document.getElementById(id),fields=['supplier','invoice_date','total','currency'];
const states={pending:'Queued for extraction',processing:'Reading the invoice',review:'Ready for human review',approved:'Approved — queued to send',dispatching:'Sending approved values',sent:'Sent',unknown:'Delivery needs reconciliation',dead:'Processing needs attention'};
let config,token=null,expires=0,epoch=0,roles=[],selected=null,dirty=false,busy=false,next=null,historyNext=null,polling=false,selection=0;
const requests=new Set(),rows=new Map();
const say=message=>{byId('status').textContent=message;};
const reviewer=()=>roles.some(r=>['reviewer','supervisor','owner'].includes(r));
const supervisor=()=>roles.some(r=>['supervisor','owner'].includes(r));
function clearSession(){
 epoch++;selection++;for(const controller of requests)controller.abort();requests.clear();token=null;expires=0;roles=[];rows.clear();selected=null;dirty=false;busy=false;next=null;
 sessionStorage.removeItem('invoice-oauth');byId('workspace').hidden=true;byId('detail').hidden=true;byId('sign-in').hidden=false;byId('sign-out').hidden=true;
 byId('invoices').replaceChildren();byId('history').replaceChildren();byId('evidence').replaceChildren();byId('file').value='';byId('review').reset();byId('model-notes').textContent='';byId('edit-status').textContent='';byId('state').textContent='';byId('progress').textContent='';
}
async function request(path,options={},binary=false){
 const generation=epoch,controller=new AbortController();requests.add(controller);const timeout=setTimeout(()=>controller.abort(),20000);
 try{
  if(config.mode==='oauth-pkce'&&(!token||Date.now()>=expires)){clearSession();throw Error('Your session expired. Sign in again.');}
  const response=await fetch(path,{...options,cache:'no-store',credentials:'same-origin',redirect:'error',signal:controller.signal,headers:{'X-Requested-With':'XMLHttpRequest',...options.headers,...(token?{Authorization:'Bearer '+token}:{})}});
  if(generation!==epoch)throw Error('Session changed.');
  if(response.status===401||response.status===403){clearSession();throw Error('Sign in with an authorized staff account to continue.');}
  if(response.status===409)throw Error('This invoice changed. Your edits are preserved. Reload the current version before saving or approving.');
  if(!response.ok)throw Error(response.status===400?'Check the invoice fields or PDF and try again.':'The service is temporarily unavailable. Your saved invoices are preserved.');
  const result=binary?await response.blob():await response.json();if(generation!==epoch)throw Error('Session changed.');return result;
 }finally{clearTimeout(timeout);requests.delete(controller);}
}
function controls(){
 byId('activity').hidden=!(busy||['pending','processing','approved','dispatching'].includes(selected?.state));
 const editable=selected?.state==='review'&&reviewer();byId('fields').disabled=!editable||busy;
 byId('save').disabled=!editable||!dirty||busy;byId('approve').disabled=!editable||dirty||busy;byId('reload').disabled=!selected||busy;
 byId('recover').hidden=selected?.state!=='dead'||!supervisor();byId('recover').disabled=busy;byId('original').disabled=!selected||busy;byId('upload-submit').disabled=busy;
 byId('progress').textContent=selected?.state==='unknown'?'The destination may already have received this invoice. An operator must check its receipt before another send.':selected?.state==='dead'?'A supervisor can retry extraction. Approved or uncertain deliveries are never replayed here.':selected?.state==='review'?'Compare the suggested values and evidence with the original. Approval sends exactly this saved revision.':'';
}
function renderList(){
 const fragment=document.createDocumentFragment();for(const row of rows.values()){
  const li=document.createElement('li'),button=document.createElement('button'),label=document.createElement('strong'),detail=document.createElement('span');button.type='button';
  label.textContent=row.result?.supplier||'Invoice '+row.id.slice(0,8);detail.textContent=(states[row.state]||'Status unavailable')+' · '+new Date(row.createdAt).toLocaleString();
  button.append(label,detail);button.setAttribute('aria-current',String(selected?.id===row.id));button.addEventListener('click',()=>openInvoice(row.id).catch(error=>say(error.message)));li.append(button);fragment.append(li);
 }byId('invoices').replaceChildren(fragment);byId('empty').hidden=rows.size>0;byId('more').hidden=!next;
}
function renderDetail(row){
 selected=row;dirty=false;byId('detail').hidden=false;byId('state').textContent=(states[row.state]||'Status unavailable')+' · Revision '+row.revision;
 byId('history').replaceChildren();historyNext=null;byId('history-more').hidden=true;
 for(const name of fields)byId(name).value=row.result?.[name]||'';byId('notes').value=row.result?.reviewerNotes||'';byId('edit-status').textContent='';
 byId('model-notes').textContent=row.result?.notes||'';const fragment=document.createDocumentFragment();
 for(const name of fields){const evidence=row.result?.fieldEvidence?.[name];if(!evidence)continue;const li=document.createElement('li');li.textContent=name.replaceAll('_',' ')+': '+(evidence.page?'Page '+evidence.page+' ('+evidence.channel+'): '+evidence.quote:'No reliable source value found.');fragment.append(li);}
 byId('evidence').replaceChildren(fragment);controls();renderList();
}
function discard(){return!dirty||confirm('Discard your unsaved corrections?');}
async function historyPage(append=false){
 if(!selected)return;const id=selected.id,generation=selection,data=await request('/api/invoices/'+id+'/history?after='+(append?historyNext:0));if(generation!==selection||selected?.id!==id)return;
 if(!append)byId('history').replaceChildren();for(const item of data.revisions){const li=document.createElement('li'),label=document.createElement('strong'),body=document.createElement('pre');label.textContent='Revision '+item.revision+' · '+item.actor+' · '+new Date(item.createdAt).toLocaleString();body.textContent=fields.map(name=>name.replaceAll('_',' ')+': '+(item.result?.[name]||'Unknown')).join('\n')+(item.result?.reviewerNotes?'\nNotes: '+item.result.reviewerNotes:'');li.append(label,body);byId('history').append(li);}historyNext=data.next;byId('history-more').hidden=!historyNext;
}
async function openInvoice(id,force=false){
 if(busy||(!force&&!discard()))return;busy=true;controls();const generation=++selection;
 try{const data=await request('/api/invoices/'+id);if(generation!==selection)return;renderDetail(data.invoice);await historyPage();}finally{busy=false;controls();}
}
async function listing(append=false){
 const data=await request('/api/invoices'+(append&&next?'?before='+encodeURIComponent(next):''));if(!append)rows.clear();for(const row of data.invoices)rows.set(row.id,row);next=data.next;renderList();
}
async function mutation(path,body){
 if(busy||!selected)return;const id=selected.id,generation=selection;busy=true;controls();
 try{const data=await request('/api/invoices/'+id+'/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(generation!==selection)return;rows.set(id,data.invoice);renderDetail(data.invoice);await historyPage();say(path==='approve'?'Approved values are queued to send.':path==='review'?'Corrections saved. Review this revision before approving.':'Extraction queued again.');}
 catch(error){say(error.message);}finally{busy=false;controls();}
}
const random=()=>Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');
async function signIn(){
 if(config.mode==='proxy'){location.assign(config.loginPath);return;}
 const verifier=random(),state=random();sessionStorage.setItem('invoice-oauth',JSON.stringify({verifier,state,created:Date.now()}));const digest=new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier))),challenge=btoa(String.fromCharCode(...digest)).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
 const url=new URL(config.authorizationEndpoint);url.search=new URLSearchParams({client_id:config.clientId,response_type:'code',scope:config.scopes,redirect_uri:location.origin+'/',state,code_challenge:challenge,code_challenge_method:'S256'});location.assign(url);
}
async function initialize(){
 const response=await fetch('/config.json',{cache:'no-store'});if(!response.ok)throw Error('Workspace configuration unavailable.');config=await response.json();
 const query=new URLSearchParams(location.search);
 if(query.has('error')){history.replaceState(null,'','/');sessionStorage.removeItem('invoice-oauth');throw Error('Sign-in was not completed. Try again.');}
 if(config.mode==='oauth-pkce'){
  if(!query.has('code')){clearSession();say('Sign in to upload and review your team’s invoices.');return;}
  const saved=JSON.parse(sessionStorage.getItem('invoice-oauth')||'null');sessionStorage.removeItem('invoice-oauth');history.replaceState(null,'','/');
  if(query.getAll('code').length!==1||query.getAll('state').length!==1||!saved||saved.state!==query.get('state')||!Number.isFinite(saved.created)||Date.now()-saved.created>600000||saved.created>Date.now()+5000)throw Error('Sign-in state expired or mismatched. Try again.');
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);let data;
  try{const response=await fetch(config.tokenEndpoint,{method:'POST',signal:controller.signal,credentials:'omit',redirect:'error',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({grant_type:'authorization_code',client_id:config.clientId,code:query.get('code'),redirect_uri:location.origin+'/',code_verifier:saved.verifier})});if(!response.ok)throw Error('Sign-in could not be completed.');data=await response.json();}finally{clearTimeout(timer);}
  if(typeof data.access_token!=='string'||!data.access_token||!Number.isFinite(data.expires_in)||data.expires_in<=0||data.expires_in>86400)throw Error('Sign-in could not be verified.');token=data.access_token;expires=Date.now()+data.expires_in*1000;
 }
 const session=await request('/api/session');roles=session.roles;byId('workspace').hidden=false;byId('sign-in').hidden=true;byId('sign-out').hidden=false;await listing();say('Upload an invoice or open one to review.');
}
byId('sign-in').addEventListener('click',()=>signIn().catch(()=>say('Sign-in could not be started. Try again.')));
byId('sign-out').addEventListener('click',()=>{const logout=config.mode==='proxy'?config.logoutPath:null;clearSession();say('Workspace cleared. Your identity-provider session may still be active. Close the browser on shared devices.');if(logout)location.assign(logout);});
byId('upload').addEventListener('submit',async event=>{
 event.preventDefault();if(busy)return;const file=byId('file').files[0];if(!file||file.size>10000000||!file.name.toLowerCase().endsWith('.pdf')){say('Choose a PDF invoice no larger than 10 MB.');return;}
 busy=true;controls();say('Uploading your invoice…');
 try{const data=await request('/api/invoices',{method:'POST',headers:{'Content-Type':'application/pdf'},body:file});rows.set(data.invoice.id,data.invoice);renderList();byId('file').value='';say('Invoice saved. Extraction is queued; you can upload another.');if(!dirty){++selection;renderDetail(data.invoice);await historyPage();}}
 catch(error){say(error.message);}finally{busy=false;controls();}
});
byId('review').addEventListener('input',()=>{dirty=true;byId('edit-status').textContent='Unsaved corrections. Save before approving.';controls();});
byId('review').addEventListener('submit',event=>{event.preventDefault();if(selected)mutation('review',{revision:selected.revision,fields:Object.fromEntries(fields.map(name=>[name,byId(name).value])),notes:byId('notes').value});});
byId('approve').addEventListener('click',()=>{if(selected&&!dirty)mutation('approve',{revision:selected.revision});});
byId('recover').addEventListener('click',()=>mutation('recover',{}));
byId('reload').addEventListener('click',()=>{if(selected)openInvoice(selected.id).catch(error=>say(error.message));});
byId('close-detail').addEventListener('click',()=>{if(!busy&&discard()){++selection;selected=null;dirty=false;byId('detail').hidden=true;renderList();}});
byId('more').addEventListener('click',()=>listing(true).catch(error=>say(error.message)));
byId('history-more').addEventListener('click',()=>historyPage(true).catch(error=>say(error.message)));
byId('original').addEventListener('click',async()=>{if(!selected)return;const id=selected.id,generation=epoch;try{const blob=await request('/api/invoices/'+id+'/original',{},true);if(generation!==epoch)return;const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='invoice.pdf';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(error){say(error.message);}});
addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
setInterval(async()=>{
 if(polling||busy||!roles.length||document.hidden)return;polling=true;
 try{
  const session=await request('/api/session');roles=session.roles;controls();
  if(selected){const id=selected.id,generation=selection,data=await request('/api/invoices/'+id);if(generation!==selection||selected?.id!==id)return;
   rows.set(id,data.invoice);renderList();if(data.invoice.revision!==selected.revision||data.invoice.state!==selected.state){if(dirty)byId('edit-status').textContent='A newer version is available. Your unsaved corrections are preserved; reload to compare.';else{renderDetail(data.invoice);await historyPage();}}
  }
 }catch(error){say(error.message);}finally{polling=false;}
},3000);
initialize().catch(error=>{clearSession();say(error.message);});
