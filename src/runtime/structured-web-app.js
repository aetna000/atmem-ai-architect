'use strict';
const byId=id=>document.getElementById(id);
let config,accessToken=null,expiresAt=0,pending=null,sessionEpoch=0;
const status=text=>{byId('status').textContent=text;};
const signedIn=()=>!!accessToken&&Date.now()<expiresAt;
function ready(){
 const enabled=signedIn();byId('question').disabled=!enabled;byId('submit').disabled=!enabled||!!pending;
 byId('sign-in').hidden=enabled;byId('sign-out').hidden=!enabled;
}
function clearPrivateView(){byId('question').value='';byId('answer').replaceChildren();byId('citations').replaceChildren();}
function endSession(){sessionEpoch++;accessToken=null;expiresAt=0;if(pending)pending.abort();pending=null;sessionStorage.removeItem('atmem-oauth');clearPrivateView();ready();}
const random=()=>Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');
function endpoint(value,fallback){const result=new URL(value||fallback,config.authOrigin);if(result.protocol!=='https:')throw Error('Invalid sign-in endpoint');return result;}
async function signIn(){
 const verifier=random(),state=random();sessionStorage.setItem('atmem-oauth',JSON.stringify({verifier,state,created:Date.now()}));
 const digest=new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier)));
 const challenge=btoa(String.fromCharCode(...digest)).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
 const url=endpoint(config.authorizationEndpoint,'/oauth2/authorize');
 url.search=new URLSearchParams({client_id:config.clientId,response_type:'code',scope:config.scopes||'openid atmem/ask',redirect_uri:location.origin+'/',state,code_challenge:challenge,code_challenge_method:'S256'});location.assign(url);
}
async function initialize(){
 const response=await fetch('/config.json',{cache:'no-store'});if(!response.ok)throw Error('Configuration unavailable');config=await response.json();
 if(new URL(config.authOrigin).protocol!=='https:'||typeof config.clientId!=='string'||!Number.isInteger(config.maxInputBytes)||config.maxInputBytes<1||config.maxInputBytes>1000000)throw Error('Invalid configuration');
 config.fields=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(config.fieldsBase64),c=>c.charCodeAt(0))));
 if(!Array.isArray(config.fields)||!config.fields.length||config.fields.length>24||config.fields.some(f=>!f||typeof f.name!=='string'||typeof f.description!=='string'||!['string','boolean','number'].includes(f.type)))throw Error('Invalid result configuration');
 byId('question').maxLength=config.maxInputBytes;
 const query=new URLSearchParams(location.search),code=query.get('code');
 if(query.has('error')){history.replaceState(null,'','/');sessionStorage.removeItem('atmem-oauth');throw Error('Sign-in was not completed');}
 if(code){
  const saved=JSON.parse(sessionStorage.getItem('atmem-oauth')||'null');sessionStorage.removeItem('atmem-oauth');history.replaceState(null,'','/');
  if(!saved||saved.state!==query.get('state')||!Number.isFinite(saved.created)||Date.now()-saved.created>600000||saved.created>Date.now()+5000)throw Error('Sign-in state expired or mismatched');
  const tokenResponse=await fetch(endpoint(config.tokenEndpoint,'/oauth2/token'),{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({grant_type:'authorization_code',client_id:config.clientId,code,redirect_uri:location.origin+'/',code_verifier:saved.verifier})});
  if(!tokenResponse.ok)throw Error('Sign-in could not be completed');const tokens=await tokenResponse.json();
  if(typeof tokens.access_token!=='string'||!tokens.access_token||!Number.isFinite(tokens.expires_in)||tokens.expires_in<=0)throw Error('Invalid sign-in response');
  accessToken=tokens.access_token;expiresAt=Date.now()+tokens.expires_in*1000;sessionEpoch++;ready();status('Signed in. Submit input for a result you can review.');
 }else{ready();status('Sign in to use this workspace.');}
}
function renderResult(result){
 if(!result.result||typeof result.result!=='object'||Array.isArray(result.result)||result.requiresHumanReview!==true)throw Error('The result could not be verified.');
 const valid=Object.keys(result.result).length===config.fields.length&&config.fields.every(field=>{
  const value=result.result[field.name];return typeof value===field.type&&(field.type!=='number'||Number.isFinite(value))&&(field.type!=='string'||Array.from(value).length<=(field.maxLength||4096))&&(!field.values||field.values.includes(value));
 });
 if(!valid)throw Error('The result could not be verified.');
 const fragment=document.createDocumentFragment();
 for(const field of config.fields){const value=result.result[field.name],label=document.createElement('dt'),item=document.createElement('dd');label.textContent=field.description;item.textContent=typeof value==='boolean'?(value?'Yes':'No'):String(value);fragment.append(label,item);}
 byId('answer').replaceChildren(fragment);status('Result prepared. Review it before taking action.');
}
byId('sign-in').addEventListener('click',()=>signIn().catch(()=>status('Sign-in could not be started. Please retry.')));
byId('sign-out').addEventListener('click',()=>{
 endSession();
 if(config.localLogout===true){status('Workspace cleared. Your identity-provider session may still be active. Close this browser on a shared device.');return;}
 const url=endpoint(config.logoutEndpoint,'/logout');url.search=new URLSearchParams({client_id:config.clientId,[config.logoutParameter||'logout_uri']:location.origin+'/'});location.assign(url);
});
byId('ask').addEventListener('submit',async event=>{
 event.preventDefault();if(pending)return;
 if(!signedIn()){endSession();status('Your session expired. Sign in again.');return;}
 const text=byId('question').value.trim();if(!text||new TextEncoder().encode(text).length>config.maxInputBytes){status('Use input of at most '+config.maxInputBytes.toLocaleString()+' UTF-8 bytes.');return;}
 const epoch=sessionEpoch,token=accessToken,controller=new AbortController();pending=controller;ready();byId('answer').replaceChildren();status('Preparing a result…');
 const timer=setTimeout(()=>controller.abort(),config.requestDeadlineMs||28000);
 try{
  const response=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({text}),signal:controller.signal,cache:'no-store'});
  if(epoch!==sessionEpoch||accessToken!==token)return;
  if(response.status===401){endSession();status('Your session expired. Sign in again.');return;}
  if(response.status===403){endSession();status('Access is unavailable or permissions changed. Sign in again or contact the app owner.');return;}
  const result=await response.json();if(epoch!==sessionEpoch||accessToken!==token)return;
  if(!response.ok){if(result.error==='data_retention_unverified')throw Error('This workspace needs its data-handling setup checked by the app owner. Your input was not sent to the AI.');throw Error('The AI result is unavailable or could not be verified. Please try again later.');}
  renderResult(result);
 }catch(error){if(epoch===sessionEpoch&&accessToken===token)status(error.name==='AbortError'?'The request timed out. Please try again later.':error.message);}
 finally{clearTimeout(timer);if(pending===controller)pending=null;ready();}
});
initialize().catch(()=>{endSession();status('Sign-in or configuration could not be verified. Please retry sign-in.');});
