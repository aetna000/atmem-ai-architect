import {UserManager,WebStorageStateStore,InMemoryWebStorage} from 'oidc-client-ts';
const $=id=>document.getElementById(id),messages=$('messages');
let config,manager,csrf=null,epoch=0,busy=false,sessionTask=null,sessionSerial=0;
class WorkspaceError extends Error{}
class SessionChanged extends Error{}
const publicMessage=(error,fallback)=>error instanceof WorkspaceError?error.message:fallback;
const pending=new Set();
const say=text=>{$('status').textContent=text;};
function clearPrivate(){
 epoch++;csrf=null;busy=false;for(const controller of pending)controller.abort();pending.clear();messages.replaceChildren();$('question').value='';$('workspace').hidden=true;$('welcome').hidden=false;$('sign-out').hidden=true;$('new-answer').hidden=true;$('activity').hidden=true;$('sources').replaceChildren();
}
async function api(path,{method='GET',data,bootstrapToken}={}){
 const generation=epoch,controller=new AbortController();pending.add(controller);const timeout=setTimeout(()=>controller.abort(),45000);
 try{
  const response=await fetch(path,{method,cache:'no-store',credentials:'same-origin',redirect:'error',signal:controller.signal,headers:{'X-Workspace-Request':'session',...(data!==undefined?{'Content-Type':'application/json'}:{}),...(csrf?{'X-CSRF-Token':csrf}:{}),...(bootstrapToken?{'Authorization':'Bearer '+bootstrapToken}:{})},...(data!==undefined?{body:JSON.stringify(data)}:{})});
  if(generation!==epoch)throw new SessionChanged();
  let result=null;if(response.status!==204)result=await response.json();
  if(generation!==epoch)throw new SessionChanged();
  if(response.status===401||response.status===403){clearPrivate();throw new WorkspaceError(result?.error?.message||'Sign in with your company account to continue.');}
  if(!response.ok)throw new WorkspaceError(result?.error?.message||'The workspace is temporarily unavailable. Please try again.');
  return result;
 }finally{clearTimeout(timeout);pending.delete(controller);}
}
const statusText={connected:'Connected',refreshing:'Connection updating…',needs_reconnect:'Connect to search your sources.',revoked:'Disconnected',needs_setup:'Your workspace owner needs to enable access.'};
function renderSources(rows){
 $('sources').replaceChildren();let ready=true;
 for(const row of rows){
  const li=document.createElement('li'),label=document.createElement('strong'),state=document.createElement('p');label.textContent=row.name;state.textContent=statusText[row.status]||'Connection unavailable';li.append(label,state);
  const connect=document.createElement('button');connect.type='button';if(row.status==='connected')connect.className='quiet';connect.textContent=row.status==='connected'?'Reconnect':'Connect';connect.disabled=row.status==='needs_setup'||row.status==='refreshing';connect.addEventListener('click',()=>connectSource(row.id));li.append(connect);
  if(row.status==='connected'){
   const remove=document.createElement('button');remove.type='button';remove.textContent='Disconnect';remove.className='quiet disconnect';remove.addEventListener('click',async()=>{try{await api('/api/sources/'+encodeURIComponent(row.id),{method:'DELETE'});messages.replaceChildren();await session();say(row.name+' disconnected.');}catch{say('Could not disconnect the source. Refresh and try again.');}});li.append(remove);
  }else ready=false;
  $('sources').append(li);
 }
 if(rows.some(row=>['needs_reconnect','revoked','needs_setup'].includes(row.status)))messages.replaceChildren();$('send').disabled=!ready||busy;
}
async function session(fresh=false){
 if(!fresh&&sessionTask?.epoch===epoch)return sessionTask.promise;
 const task={epoch,serial:++sessionSerial};task.promise=(async()=>{const result=await api('/api/session');if(task.serial!==sessionSerial)return result;csrf=result.csrfToken;$('welcome').hidden=true;$('workspace').hidden=false;$('sign-out').hidden=false;renderSources(result.sources);return result;})();sessionTask=task;
 try{return await task.promise;}finally{if(sessionTask===task)sessionTask=null;}
}
function nearBottom(){return messages.scrollHeight-messages.scrollTop-messages.clientHeight<80;}
function append(role,text,citations=[]){
 const follow=nearBottom(),li=document.createElement('li'),label=document.createElement('span'),content=document.createElement('div');li.className=role;label.className='message-label';label.textContent=role==='user'?'You':'Company knowledge';content.textContent=text;li.append(label,content);
 for(const citation of citations){
  const block=document.createElement('div'),quote=document.createElement('blockquote');block.className='citation';quote.textContent=citation.quote;
  try{const url=new URL(citation.url);if(url.protocol!=='https:'||!config.citationHosts.includes(url.hostname)||url.username||url.password)throw Error();const link=document.createElement('a');link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';link.textContent=citation.title;block.append(link);}catch{const title=document.createElement('strong');title.textContent=citation.title;block.append(title);}
  block.append(quote);li.append(block);
 }
 messages.append(li);$('intro').hidden=true;if(follow)messages.scrollTop=messages.scrollHeight;else $('new-answer').hidden=false;
}
async function connectSource(alias){
 try{const result=await api('/api/sources/'+encodeURIComponent(alias)+'/connect',{method:'POST',data:{}}),url=new URL(result.authorizationUrl);if(!config.authorizationOrigins.includes(url.origin))throw Error();location.assign(url.href);}catch(error){if(!(error instanceof SessionChanged))say(publicMessage(error,'Could not open the source connection. Try again.'));}
}
$('sign-in').addEventListener('click',async()=>{try{await manager.clearStaleState();await manager.signinRedirect();}catch{say('Company sign-in is unavailable. Please try again shortly.');}});
$('sign-out').addEventListener('click',async()=>{let confirmed=false;try{await api('/api/session',{method:'DELETE'});confirmed=true;}catch{}finally{clearPrivate();await manager?.removeUser();say(confirmed?'Signed out of this workspace.':'Sign-out could not be confirmed. Reload this page and try again.');}});
$('new-answer').addEventListener('click',()=>{messages.scrollTop=messages.scrollHeight;$('new-answer').hidden=true;});
$('ask').addEventListener('submit',async event=>{
 event.preventDefault();if(busy)return;const generation=epoch,question=$('question').value.trim();if(!question)return;busy=true;$('send').disabled=true;$('activity').hidden=false;append('user',question);$('question').value='';say('');
 try{const result=await api('/api/ask',{method:'POST',data:{question}});append('assistant',result.answer,result.citations);}
 catch(error){if(generation===epoch)say(error.name==='AbortError'?'This request took too long. You can ask again.':publicMessage(error,'Could not verify an answer. Please try again.'));}
 finally{if(generation===epoch){busy=false;$('activity').hidden=true;if(csrf)try{await session(true);}catch(error){if(!(error instanceof SessionChanged)){clearPrivate();say(publicMessage(error,'We could not confirm access. Sign in again or retry shortly.'));}}}}
});
window.addEventListener('pagehide',clearPrivate);
window.addEventListener('pageshow',event=>{if(event.persisted)session().catch(()=>{clearPrivate();say('Sign in to reopen your workspace.');});});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&csrf)session().catch(error=>{if(!(error instanceof SessionChanged)){clearPrivate();say(publicMessage(error,'Access could not be confirmed. Sign in again.'));}});});
async function boot(){
 try{
  config=await(await fetch('/api/web-config',{cache:'no-store',credentials:'omit',redirect:'error'})).json();
  const metadata={issuer:config.company.issuer,authorization_endpoint:config.company.authorizationEndpoint,token_endpoint:config.company.tokenEndpoint};
  manager=new UserManager({authority:config.company.issuer,client_id:config.company.clientId,redirect_uri:location.origin+'/company-callback',response_type:'code',scope:config.company.scopes.join(' '),metadata,loadUserInfo:false,automaticSilentRenew:false,monitorSession:false,disablePKCE:false,requestTimeoutInSeconds:15,staleStateAgeInSeconds:300,userStore:new WebStorageStateStore({store:new InMemoryWebStorage()}),stateStore:new WebStorageStateStore({store:window.sessionStorage})});
  if(location.pathname==='/company-callback'){
   const callback=location.href;history.replaceState(null,'','/');let user;
   try{user=await manager.signinRedirectCallback(callback);await api('/api/session',{method:'POST',data:{},bootstrapToken:user.access_token});}finally{await manager.removeUser();user=null;}
  }else if(location.search){history.replaceState(null,'','/');}
  await session();say('');
 }catch(error){clearPrivate();say(publicMessage(error,'Sign in with your company account to open your workspace.'));}
}
setInterval(()=>{if(csrf&&!busy&&document.visibilityState==='visible')session().catch(error=>{if(!(error instanceof SessionChanged)){clearPrivate();say(publicMessage(error,'Access could not be confirmed. Sign in again or retry shortly.'));}});},15000);
boot();
