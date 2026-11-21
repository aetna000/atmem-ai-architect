// Synthetic browser speech + architect transport; never uses microphone, credentials or real memory.
import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
const provided = process.env.ATMEM_ARCHITECT_VOICE_TEST_URL;
let server;
let base = provided;
if (!base) {
 const probe=createServer();
 await new Promise(resolve=>probe.listen(0,'127.0.0.1',resolve));
 const port=probe.address().port; await new Promise(resolve=>probe.close(resolve));
 base=`http://127.0.0.1:${port}`;
 server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{cwd:new URL('..',import.meta.url),stdio:'ignore'});
}
let browser;
try {
 for(let n=0;n<100;n++){
  if(server && server.exitCode !== null) throw Error('Isolated voice test server exited');
  try {if((await fetch(base)).ok)break;}catch{}
  if(n===99)throw Error('Voice test server did not start');
  await new Promise(r=>setTimeout(r,100));
 }
 browser = await chromium.launch({headless:true});
 const context = await browser.newContext({viewport:{width:1440,height:1000}});
 const page = await context.newPage(); const errors=[], requests=[];
 page.on('pageerror',e=>errors.push(e.message));
 await context.addInitScript(()=>{
  localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'claude-code',model:'synthetic-dictation-test'}));
  window.__audio={stops:0,deny:false};
  const source=()=>({connect(){},disconnect(){}});
  Object.defineProperty(navigator,'mediaDevices',{value:{getUserMedia:async()=>{
   if(window.__audio.deny){const error=Error('denied');error.name='NotAllowedError';throw error;}
   return {getTracks:()=>[{stop:()=>window.__audio.stops++}]};
  }},configurable:true});
  class Audio {
   constructor(){this.state='running';this.sampleRate=16000;}
   resume(){return Promise.resolve();} close(){this.state='closed';return Promise.resolve();}
   createMediaStreamSource(){return source();} createGain(){return {...source(),gain:{value:0}};}
   createScriptProcessor(){const processor={...source()};window.__audio.feed=()=>processor.onaudioprocess?.({inputBuffer:{getChannelData:()=>new Float32Array(16000).fill(.1)}});return processor;}
  }
  Object.defineProperty(window,'AudioContext',{value:Audio,configurable:true});
  Object.defineProperty(window,'speechSynthesis',{get(){throw Error('Playback must not be used');},configurable:true});
  Object.defineProperty(window,'SpeechRecognition',{get(){throw Error('Browser speech service must not be used');},configurable:true});
 });
 let transcriptions=0;
 await context.route('**/api/**',async route=>{
  const url=new URL(route.request().url());
  let body={projects:[],bin:[],folder:'',enabled:false,records:[],preferences:[],skills:[]};
  if(url.pathname==='/api/session')body={status:'local-sidecar',token:'synthetic-no-provider-access',capabilities:{}};
  if(url.pathname==='/api/voice/prepare')body={ready:true};
  if(url.pathname==='/api/voice/transcribe'){
   assert.equal(route.request().headers()['content-type'],'audio/wav');
   assert.equal(route.request().postDataBuffer().subarray(0,4).toString(),'RIFF');
   transcriptions++;
   body={text:transcriptions===1?'Build a document assistant':transcriptions===2?'Build a document assistant using Azure':'Keep data in Australia',audioStored:false};
  }
  if(url.pathname==='/api/architect'){
   const request=route.request().postDataJSON();requests.push(request);
   const next={...request.project,nodes:[{id:'voice-assistant',type:'resource',position:{x:100,y:100},data:{label:'Azure document assistant',kind:'agent',provider:'azure',description:`Synthetic voice fixture ${requests.length}`,origin:'proposed',config:{region:'To be selected',classification:'Internal',timeout:5000}}}],edges:[]};
   body={message:'I updated the design.',proposal:{title:'Document assistant',body:'Synthetic architecture proposal',baseRevision:request.project.revision,next}};
  }
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
 });
 let confirmations=0;page.on('dialog',async d=>{confirmations++;await d.accept();});
 await page.goto(base);
 await page.getByRole('button',{name:'Start dictation',exact:true}).waitFor();await page.waitForTimeout(500);
 const initial=requests.length;
 await page.getByRole('button',{name:'Start dictation',exact:true}).click();
 await page.getByText('Dictating locally — review your words, then press Send.',{exact:true}).waitFor();
 await page.evaluate(()=>window.__audio.feed());
 await page.waitForFunction(()=>document.querySelector('textarea[aria-label="Your message"]').value==='Build a document assistant');
 assert.equal(requests.length,initial,'speaking does not submit to the model');
 await page.evaluate(()=>window.__audio.feed());
 await page.waitForFunction(()=>document.querySelector('textarea[aria-label="Your message"]').value==='Build a document assistant using Azure');
 assert.equal(requests.length,initial,'partial updates stay in the composer');
 await page.getByRole('button',{name:'Stop dictation',exact:true}).click();
 await page.getByRole('button',{name:'Start dictation',exact:true}).waitFor();
 await page.getByRole('button',{name:'Send message',exact:true}).click();
 await page.locator('.react-flow__node').filter({hasText:'Azure document assistant'}).waitFor();
 await page.locator('.react-flow__node.diagram-attention').waitFor();
 await page.waitForTimeout(850);
 const zoom = await page.locator('.react-flow__viewport').evaluate(el => new DOMMatrix(getComputedStyle(el).transform).a);
 assert.ok(zoom > 1.1, 'applied block is zoomed into view');
 await page.waitForFunction(() => !document.querySelector('.diagram-attention'));
 assert.equal(requests.length,initial+1);assert.equal(requests.at(-1).message,'Build a document assistant using Azure');
 await page.emulateMedia({reducedMotion:'reduce'});
 // Pressing Send during capture must finalise the pending words before posting once.
 await page.waitForFunction(()=>!document.querySelector('.msg.working'));
 await page.getByRole('button',{name:'Start dictation',exact:true}).click();
 await page.waitForFunction(()=>!!window.__audio.feed);await page.evaluate(()=>window.__audio.feed());
 await page.getByRole('button',{name:'Send message',exact:true}).click();
 await page.waitForFunction(()=>!document.querySelector('.msg.working'));
 await page.waitForTimeout(300);
 assert.equal(requests.length,initial+2);assert.ok(requests.at(-1).message.startsWith('Keep data in Australia'));
 const highlighted = page.locator('.react-flow__node.diagram-attention');
 await highlighted.waitFor();
 assert.equal(await highlighted.evaluate(el => getComputedStyle(el).animationName), 'none');
 assert.equal(confirmations,1);
 await page.evaluate(()=>{window.__audio.deny=true;});
 await page.getByRole('button',{name:'Start dictation',exact:true}).click();
 await page.getByText(/Microphone access is blocked/).waitFor();
 fs.mkdirSync('/private/tmp/atmem-architect-voice',{recursive:true});
 await page.screenshot({path:'/private/tmp/atmem-architect-voice/desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 const box=await page.locator('.voice-status').boundingBox();assert.ok(box&&box.x>=0&&box.x+box.width<=390);
 await page.screenshot({path:'/private/tmp/atmem-architect-voice/mobile.png',fullPage:true});
 assert.deepEqual(errors,[]);assert.ok(await page.evaluate(()=>window.__audio.stops>=2));
 console.log('Local dictation UI passed: live partial text, no automatic submission/playback/browser speech service, Stop, explicit Send, finalisation on Send, canvas proposal and microphone permission errors. Audio/model transports were fixtures.');
 await context.close();
} finally {await browser?.close();server?.kill("SIGTERM");}
