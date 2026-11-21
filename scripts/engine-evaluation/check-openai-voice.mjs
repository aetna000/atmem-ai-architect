// Real frontend, synthetic transport/project only. Never writes owner projects or calls a model.
import fs from 'node:fs';import assert from 'node:assert/strict';import {chromium}from '@playwright/test';import {toProjectFile}from '../../src/project-file.mjs';
const base=process.argv[2]||'http://127.0.0.1:5297',out=process.argv[3]||'.local/external-artifacts/openai-voice/v1/browser';fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'}),errors=[],calls=[];let emulationCalls=0,enabled=true,voiceAvailable=false,keysConfigured=0;
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.1-sol',effort:'high'}));localStorage.setItem('atforma-draw-live','off')});
 const memory=()=>({enabled,status:enabled?'ready':'disabled',pending:0,rejected:0,engine:'AtMem 2.3.10 core SDK',policy:'Synthetic fixture transport',profile:[],project:[],knowledge:[],skills:[],activity:[],events:[]});
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  if(path==='/api/voice/openai/status')return route.fulfill({json:{available:voiceAvailable,model:'gpt-realtime-2.1-mini',voice:'marin'}});
  if(path==='/api/voice/openai/credentials'){const body=route.request().postDataJSON();assert.equal(body.provider,undefined);assert.equal(body.key,'synthetic-not-a-real-key');keysConfigured++;voiceAvailable=true;return route.fulfill({json:{configuredInMemory:true}})}
  if(path==='/api/voice/openai/session')return route.fulfill({json:{value:'ek_synthetic',expires_at:Date.now()/1000+60,model:'gpt-realtime-2.1-mini'}});
  if(path==='/api/session')return route.fulfill({json:{token:'fixture',status:'local-sidecar',engineeringEnabled:true,providers:{codex:{available:true,installed:true,signedIn:true}}}});
  if(path==='/api/projects/save')return route.fulfill({json:{saved:true,sha256:'a'.repeat(64),memory:memory()}});
  if(path==='/api/memory/settings'){enabled=route.request().postDataJSON().enabled;return route.fulfill({json:memory()})}
  if(path.startsWith('/api/memory/'))return route.fulfill({json:memory()});
  if(path==='/api/emulation/run'){emulationCalls++;return route.fulfill({status:500,json:{detail:'Known missing implementation should not run'}})}
  if(path==='/api/architect'){const body=route.request().postDataJSON();calls.push(body);return route.fulfill({json:{message:'The existing service stays unchanged. I will add the requested tests.',phase:'Architecture',followUp:null}})}
  if(path==='/api/engineering/list')return route.fulfill({json:{sessions:[]}});
  return route.fulfill({json:{projects:[],bin:[],models:[],saved:true,status:'disabled'}});
 });
 await page.route('https://api.openai.com/**',route=>{assert.equal(route.request().url(),'https://api.openai.com/v1/realtime/calls');if(route.request().method()!=='OPTIONS')assert.equal(route.request().headers().authorization,'Bearer ek_synthetic');return route.fulfill({body:'synthetic-answer',contentType:'application/sdp',headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'authorization,content-type','Access-Control-Allow-Methods':'POST,OPTIONS'}})});
 await page.addInitScript(()=>{
  window.__oai={events:[],closed:0,stopped:0};
  Object.defineProperty(navigator,'mediaDevices',{value:{getUserMedia:async()=>({getTracks:()=>[{stop:()=>window.__oai.stopped++}]})},configurable:true});
  window.Audio=class{play(){return Promise.resolve()}pause(){}};
  window.RTCPeerConnection=class{
   constructor(){window.__oai.peer=this;this.connectionState='new'}addTrack(){}
   createDataChannel(){this.channel={readyState:'connecting',send:raw=>{const value=JSON.parse(raw);window.__oai.events.push(value)},close(){this.readyState='closed'}};return this.channel}
   async createOffer(){return {sdp:'synthetic-offer'}}async setLocalDescription(){}
   async setRemoteDescription(){this.channel.readyState='open';this.channel.onopen?.()}
   close(){window.__oai.closed++}
  };
  window.__oai.emit=(id,text)=>{const channel=window.__oai.peer.channel;for(const value of [{type:'input_audio_buffer.committed',item_id:id},{type:'conversation.item.input_audio_transcription.completed',item_id:id,transcript:text}])channel.onmessage?.({data:JSON.stringify(value)})};
 });
 const project={id:'voice-fixture',version:1,revision:1,name:'Voice fixture',provider:'tools',requirements:'Preserve the existing service.',nodes:[{id:'client',type:'resource',position:{x:0,y:0},data:{label:'Existing service',description:'Keep current ownership.',kind:'resource',provider:'tools',origin:'existing',config:{}}}],edges:[]};
 await page.goto(base+'/');await page.locator('#project-file-input').setInputFiles({name:'voice.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(toProjectFile(project)))});
 await page.getByRole('button',{name:'OpenAI voice',exact:true}).click();const panel=page.getByRole('region',{name:'OpenAI voice settings',exact:true});
 assert.equal(await panel.getByRole('button',{name:'Start OpenAI voice',exact:true}).isDisabled(),true);
 await panel.getByLabel('OpenAI voice API key',{exact:true}).fill('synthetic-not-a-real-key');await panel.getByRole('button',{name:'Configure voice key',exact:true}).click();await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='Start OpenAI voice'&&!b.disabled));
 assert.equal(keysConfigured,1);assert.equal(calls.length,0);assert.deepEqual(await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-connection-v1'))),{provider:'codex',model:'gpt-6.1-sol',effort:'high'});
 await panel.getByRole('button',{name:'Start OpenAI voice',exact:true}).click();await page.getByRole('status').filter({hasText:'Listening — review the transcript'}).waitFor();
 const input=page.getByRole('textbox',{name:'Your message',exact:true});await page.evaluate(()=>window.__oai.emit('manual','Keep the existing service and add tests.'));assert.equal(await input.inputValue(),'Keep the existing service and add tests.');assert.equal(calls.length,0);
 await page.getByRole('button',{name:'Send message',exact:true}).click();await page.getByText('The existing service stays unchanged. I will add the requested tests.',{exact:true}).waitFor();await page.waitForFunction(()=>window.__oai.events.some(e=>e.type==='response.create'));
 const readout=await page.evaluate(()=>window.__oai.events.find(e=>e.type==='response.create'));assert.equal(readout.response.input[0].content[0].text,'The existing service stays unchanged. I will add the requested tests.');assert.equal(readout.response.conversation,'none');
 await page.getByRole('button',{name:'OpenAI voice',exact:true}).click();await panel.getByRole('checkbox',{name:'Send spoken turns automatically',exact:true}).check();await page.getByRole('button',{name:'Close voice settings',exact:true}).click();await page.evaluate(()=>window.__oai.emit('automatic','Also preserve the accepted provider.'));await page.waitForFunction(()=>document.querySelectorAll('.msg.assistant').length>=3);await page.waitForTimeout(100);assert.equal(calls.length,2);
 for(const call of calls){assert.equal(call.provider,'codex');assert.equal(call.model,'gpt-6.1-sol');assert.equal(call.effort,'high')}
 await input.fill('An unsent requirement.');await page.evaluate(()=>window.__oai.emit('retain','Add drift alerts.'));assert.equal(await input.inputValue(),'An unsent requirement. Add drift alerts.');assert.equal(calls.length,2);
 await page.evaluate(()=>window.__oai.late=window.__oai.peer.channel.onmessage);await page.getByRole('button',{name:'Stop OpenAI voice',exact:true}).click();await page.evaluate(()=>window.__oai.late({data:JSON.stringify({type:'conversation.item.input_audio_transcription.completed',item_id:'late',transcript:'Must not leak after stop.'})}));assert.equal(await input.inputValue(),'An unsent requirement. Add drift alerts.');assert.deepEqual(await page.evaluate(()=>({closed:window.__oai.closed,stopped:window.__oai.stopped})),{closed:1,stopped:1});
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'OpenAI voice',exact:true}).click();await panel.getByRole('button',{name:'Start OpenAI voice',exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:out+'/voice-mobile.png'});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);assert.deepEqual(errors,[]);
 const receipt={base,missingKeyHasSetup:true,keyDoesNotChangeArchitect:true,manualTranscriptDefault:true,automaticSendingOptIn:true,exactArchitectModelEffortPreserved:true,writtenAnswerReadout:true,unsentDraftPreserved:true,stopClosesMicAndPeer:true,lateTranscriptIgnored:true,ownerProjectWrites:0,realOpenAICalls:0,transport:'Synthetic API/WebRTC/audio transport; actual UI events and selected Architect routing; no listening or live audio quality claim'};fs.writeFileSync(out+'/receipt.json',JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
}finally{await browser.close()}
