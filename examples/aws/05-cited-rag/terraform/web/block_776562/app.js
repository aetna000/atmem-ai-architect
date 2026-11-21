'use strict';
const byId=id=>document.getElementById(id);
let config,accessToken=null,expiresAt=0;
const status=text=>{byId('status').textContent=text;};
const ready=enabled=>{byId('question').disabled=!enabled;byId('submit').disabled=!enabled;byId('sign-in').hidden=enabled;byId('sign-out').hidden=!enabled;};
const random=()=>Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');
async function signIn(){
 const verifier=random(),state=random();sessionStorage.setItem('atmem-oauth',JSON.stringify({verifier,state,created:Date.now()}));
 const digest=new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier)));
 const challenge=btoa(String.fromCharCode(...digest)).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
 const url=new URL('/oauth2/authorize',config.authOrigin);url.search=new URLSearchParams({client_id:config.clientId,response_type:'code',scope:'openid atmem/ask',redirect_uri:location.origin+'/',state,code_challenge:challenge,code_challenge_method:'S256'});location.assign(url);
}
async function initialize(){
 const response=await fetch('/config.json',{cache:'no-store'});if(!response.ok)throw Error('Configuration unavailable');config=await response.json();
 if(new URL(config.authOrigin).protocol!=='https:'||typeof config.clientId!=='string')throw Error('Invalid sign-in configuration');
 const query=new URLSearchParams(location.search),code=query.get('code');
 if(query.has('error')){history.replaceState(null,'','/');sessionStorage.removeItem('atmem-oauth');throw Error('Sign-in was not completed');}
 if(code){
  const saved=JSON.parse(sessionStorage.getItem('atmem-oauth')||'null');sessionStorage.removeItem('atmem-oauth');history.replaceState(null,'','/');
  if(!saved||saved.state!==query.get('state')||Date.now()-saved.created>600000)throw Error('Sign-in state expired or mismatched');
  const tokenResponse=await fetch(new URL('/oauth2/token',config.authOrigin),{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({grant_type:'authorization_code',client_id:config.clientId,code,redirect_uri:location.origin+'/',code_verifier:saved.verifier})});
  if(!tokenResponse.ok)throw Error('Sign-in could not be completed');const tokens=await tokenResponse.json();
  if(typeof tokens.access_token!=='string'||!Number.isFinite(tokens.expires_in)||tokens.expires_in<=0)throw Error('Invalid sign-in response');
  accessToken=tokens.access_token;expiresAt=Date.now()+tokens.expires_in*1000;ready(true);status('Signed in. Ask a question about your documents.');
 }else{ready(false);status('Sign in to access your documents.');}
}
byId('sign-in').addEventListener('click',()=>signIn().catch(()=>status('Sign-in could not be started. Please retry.')));
byId('sign-out').addEventListener('click',()=>{
 accessToken=null;expiresAt=0;sessionStorage.removeItem('atmem-oauth');ready(false);byId('answer').textContent='';byId('citations').replaceChildren();
 const url=new URL('/logout',config.authOrigin);url.search=new URLSearchParams({client_id:config.clientId,logout_uri:location.origin+'/'});location.assign(url);
});
byId('ask').addEventListener('submit',async event=>{
 event.preventDefault();if(!accessToken||Date.now()>=expiresAt){ready(false);status('Your session expired. Sign in again.');return;}
 const question=byId('question').value.trim();if(!question||new TextEncoder().encode(question).length>2000){status('Use a question of at most 2,000 UTF-8 bytes.');return;}
 byId('submit').disabled=true;byId('answer').textContent='';byId('citations').replaceChildren();status('Checking your permitted documents…');
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),25000);
 try{
  const response=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+accessToken},body:JSON.stringify({question}),signal:controller.signal,cache:'no-store'});
  if(response.status===401){accessToken=null;ready(false);throw Error('Your session expired. Sign in again.');}
  if(response.status===403)throw Error('Access is unavailable or permissions changed.');
  if(!response.ok)throw Error('The answer is temporarily unavailable. Please retry.');
  const result=await response.json();if(typeof result.answer!=='string'||!Array.isArray(result.citations))throw Error('The answer could not be verified.');
  byId('answer').textContent=result.answer;
  for(const source of result.citations){const item=document.createElement('li');item.textContent=String(source.title)+' — revision '+String(source.revision);byId('citations').append(item);}
  status(result.abstained?'No sufficient evidence was found.':'Answered from your permitted sources.');
 }catch(error){status(error.name==='AbortError'?'The request timed out. Please retry.':error.message);}
 finally{clearTimeout(timer);byId('submit').disabled=!accessToken;}
});
initialize().catch(()=>{ready(false);status('Sign-in or configuration could not be verified. Please retry sign-in.');});
