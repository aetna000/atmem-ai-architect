// Independent local native-contract transports. Original image modules are unchanged.
import assert from 'node:assert/strict';import fs from 'node:fs';import https from 'node:https';import http from 'node:http';
import {generateKeyPairSync,sign,createHash,randomUUID}from 'node:crypto';
import {createInterface}from 'node:readline';
import {configuration}from '/app/app/config.mjs';import {Identity}from '/app/app/identity.mjs';import {Azure}from '/app/app/azure.mjs';import {createApplication}from '/app/app/server.mjs';
const reader=createInterface({input:process.stdin});const line=await new Promise(resolve=>reader.once('line',resolve));reader.close();const input=JSON.parse(line),config=configuration(input.environment);
for(const[file,digest]of Object.entries(input.sourceHashes))assert.equal(createHash('sha256').update(fs.readFileSync('/app/'+file)).digest('hex'),digest,file);
assert.equal(process.version,'v26.13.0');assert.equal(process.arch,'x64');assert.equal(process.getuid(),1000);
const {privateKey,publicKey}=generateKeyPairSync('rsa',{modulusLength:2048}),jwk={...publicKey.export({format:'jwk'}),kid:'synthetic-key',use:'sig'};
const state={mode:'good',identity:'good',calls:0,unknownUrls:0,active:0,maxActive:0},codes=new Map(),barrier=[];
const reply=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
const suggestion=ticket=>({summary:'Reviewed '+ticket.slice(0,80),topic:'billing',urgency:'normal',uncertainty:{level:'high',reason:'Synthetic local provider response; human review required.'}});
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function signed(claims){const h=Buffer.from(JSON.stringify({alg:'RS256',kid:'synthetic-key'})).toString('base64url'),p=Buffer.from(JSON.stringify(claims)).toString('base64url');return h+'.'+p+'.'+sign('RSA-SHA256',Buffer.from(h+'.'+p),privateKey).toString('base64url');}
async function transport(target,options={}){
 const url=new URL(target),endpoint=config.endpoint,account='https://management.azure.com'+config.accountId;
 assert.equal(options.redirect,'error');assert(options.signal instanceof AbortSignal);
 if(url.href===`https://login.microsoftonline.com/${config.tenant}/discovery/v2.0/keys`)return reply({keys:[jwk]});
 if(url.href===`https://login.microsoftonline.com/${config.tenant}/oauth2/v2.0/token`){
  assert.equal(options.method,'POST');const body=options.body,flow=codes.get(body.get('code'));assert(flow);codes.delete(body.get('code'));
  assert.equal(body.get('client_id'),config.clientId);assert.equal(body.get('client_secret'),config.clientSecret);assert.equal(body.get('redirect_uri'),config.origin+'/auth/callback');
  assert.equal(createHash('sha256').update(body.get('code_verifier')).digest('base64url'),flow.challenge);
  const now=Math.floor(Date.now()/1000),claims={iss:`https://login.microsoftonline.com/${config.tenant}/v2.0`,tid:config.tenant,aud:config.clientId,nonce:flow.nonce,oid:flow.oid,sub:'synthetic-'+flow.oid,iat:now-1,nbf:now-1,exp:now+599,roles:['Reviewer']};
  if(state.identity==='nonce')claims.nonce='foreign';if(state.identity==='issuer')claims.iss='https://foreign.invalid';if(state.identity==='role')claims.roles=[];if(state.identity==='expired')claims.exp=now-60;if(state.identity==='audience')claims.aud='foreign';
  let token=signed(claims);
  if(state.identity==='signature'){const parts=token.split('.'),bytes=Buffer.from(parts[2],'base64url');bytes[0]^=1;parts[2]=bytes.toString('base64url');token=parts.join('.');}
  if(state.identity==='malformed')token='not.a.signed.token';
  return reply({id_token:token});
 }
 if(url.origin==='http://metadata.synthetic.invalid'){
  assert.equal(options.headers['X-IDENTITY-HEADER'],'synthetic-metadata-header');assert.equal(url.searchParams.get('client_id'),input.managedIdentityClientId);const resource=url.searchParams.get('resource');assert(['https://management.azure.com/','https://cognitiveservices.azure.com/'].includes(resource));
  return reply({access_token:'synthetic-token-'+resource,expires_on:Math.floor(Date.now()/1000)+3600});
 }
 if(url.href===account+'?api-version=2024-10-01'){
  assert.equal(options.headers.Authorization,'Bearer synthetic-token-https://management.azure.com/');
  return reply({location:state.mode==='foreign-region'?'westus':'australiaeast',properties:{capabilities:state.mode==='missing-logging'?[]:[{name:'ContentLogging',value:state.mode==='logging'?'true':'false'}],endpoint}});
 }
 if(url.href===account+'/deployments/'+config.deployment+'?api-version=2024-10-01')return reply({sku:{name:state.mode==='global-sku'?'GlobalStandard':'Standard'},properties:{model:{name:config.model,version:config.modelVersion},provisioningState:'Succeeded'}});
 if(url.href===`${endpoint}/openai/deployments/${config.deployment}/chat/completions?api-version=2024-10-21`){
  assert.equal(options.method,'POST');assert.equal(options.headers.Authorization,'Bearer synthetic-token-https://cognitiveservices.azure.com/');
  const request=JSON.parse(options.body);assert.equal(request.messages[0].role,'system');assert.equal(request.messages[1].role,'user');assert.equal(request.response_format.type,'json_schema');assert.equal(request.response_format.json_schema.strict,true);
  const ticket=request.messages[1].content,mode=state.mode;state.calls++;state.active++;state.maxActive=Math.max(state.maxActive,state.active);
  try{
   if(mode==='timeout')await new Promise((resolve,reject)=>{if(options.signal.aborted)return reject(options.signal.reason);options.signal.addEventListener('abort',()=>reject(options.signal.reason),{once:true});});
   if(mode==='barrier')await new Promise((resolve,reject)=>{barrier.push(resolve);options.signal.addEventListener('abort',()=>reject(options.signal.reason),{once:true});if(barrier.length===5)for(const done of barrier.splice(0))done();});
   else if(mode==='delay')await delay(700);else await delay(120);
   if(mode==='denial')return reply({error:{message:'PRIVATE-UPSTREAM-BODY '+ticket}},403);
   let result=suggestion(ticket);if(mode==='markup')result.summary='<img src=x onerror="globalThis.injected=true">';
   return reply({choices:[{finish_reason:mode==='truncated'?'length':'stop',message:{content:mode==='malformed'?'{':JSON.stringify(result),...(mode==='refusal'?{refusal:'Denied'}:{})}}]});
  }finally{state.active--;}
 }
 state.unknownUrls++;throw Error('Unrecognized native fixture destination');
}
const identity=new Identity(config,transport),azure=new Azure(config,transport,{IDENTITY_ENDPOINT:'http://metadata.synthetic.invalid/token',IDENTITY_HEADER:'synthetic-metadata-header',MANAGED_IDENTITY_CLIENT_ID:input.managedIdentityClientId});
const app=createApplication(config,{identity,azure});await new Promise(resolve=>app.server.listen(8080,'127.0.0.1',resolve));
const front=https.createServer({key:input.tlsKey,cert:input.tlsCert},(req,res)=>{
 const proxy=http.request({host:'127.0.0.1',port:8080,path:req.url,method:req.method,headers:req.headers},response=>{res.writeHead(response.statusCode,response.headers);response.pipe(res);});
 proxy.on('error',()=>{res.writeHead(502);res.end();});req.pipe(proxy);
});await new Promise(resolve=>front.listen(8443,'0.0.0.0',resolve));
// Native redirects are followed by Chromium before per-page route interception.
// Resolve this hostname only inside the isolated Docker network and serve an
// explicit synthetic authorization page over actual local TLS instead.
const authorization=https.createServer({key:input.tlsKey,cert:input.tlsCert},(req,res)=>{
 const url=new URL(req.url,'https://login.microsoftonline.com');
 assert.equal(url.pathname,`/${config.tenant}/oauth2/v2.0/authorize`);
 assert.equal(url.searchParams.get('client_id'),config.clientId);assert.equal(url.searchParams.get('code_challenge_method'),'S256');assert.equal(url.searchParams.get('redirect_uri'),config.origin+'/auth/callback');
 const code=randomUUID();codes.set(code,{oid:state.nextOid||config.reviewers[0],nonce:url.searchParams.get('nonce'),challenge:url.searchParams.get('code_challenge')});
 const callback=config.origin+'/auth/callback?'+new URLSearchParams({code,state:url.searchParams.get('state')});
 res.writeHead(200,{'Content-Type':'text/html'});res.end(`<a id="fixture-consent" href="${callback.replaceAll('&','&amp;')}">Synthetic sign-in</a>`);
});await new Promise(resolve=>authorization.listen(443,'0.0.0.0',resolve));
const control=http.createServer(async(req,res)=>{
 const chunks=[];for await(const chunk of req)chunks.push(chunk);const body=chunks.length?JSON.parse(Buffer.concat(chunks)):{};
 if(req.url==='/mode'){state.mode=body.mode||'good';state.identity=body.identity||'good';azure.checked=0;}
 else if(req.url==='/next-user')state.nextOid=body.oid;
 else if(req.url!=='/state'){res.writeHead(404);res.end();return;}
 res.setHeader('Content-Type','application/json');res.end(JSON.stringify(state));
});await new Promise(resolve=>control.listen(9090,'0.0.0.0',resolve));
console.log(JSON.stringify({ready:true,node:process.version,uid:process.getuid(),sourceUnchanged:true,cloudOperations:false}));
process.on('SIGTERM',()=>{control.close();authorization.close();front.close();app.server.close();});
