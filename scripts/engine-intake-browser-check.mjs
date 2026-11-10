// Real browser intake/persistence; the model/session network is an explicit fixture.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
const out=path.resolve('specs/029-general-purpose-engine/evidence/20261111-engine-intake-recovery');fs.mkdirSync(out,{recursive:true});
const socket=createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));
const base=`http://127.0.0.1:${port}`,server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'ignore'});
let browser;const errors=[],checks=[];
try{
 let ready=false;for(let i=0;i<100;i++){try{if((await fetch(base)).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,100));}assert.ok(ready,'isolated UI server started');
 browser=await chromium.launch({headless:true});
 for(const kind of ['oversize','files']){
  const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));let sent=[];
  const original=kind==='oversize'?'Preserve every requirement. '.repeat(320):'Review all five original files before changing the design.';
  const files=kind==='files'?Array.from({length:5},(_,i)=>({id:`file-${i}`,name:`source-${i}.${i===0?'png':'txt'}`,mime:i===0?'image/png':'text/plain',originalNotSaved:true})):[];
  const project={id:`intake-recovery-${kind}`,version:1,revision:1,name:'Intake recovery',provider:'tools',nodes:[],edges:[],extensions:{conversation:{version:1,messages:[{role:'user',text:original,requestId:'saved-intent',workState:'queued',attachments:files}]}}};
  await page.addInitScript(p=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify(p));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'default'}));},project);
  await page.route('**/api/**',async route=>{
   if(route.request().url().endsWith('/api/architect')){sent.push(route.request().postDataJSON());return route.fulfill({json:{message:'The updated requirement is preserved.',proposal:null,followUp:null}});}
   return route.fulfill({json:route.request().url().endsWith('/api/session')?{token:'fixture',status:'local-sidecar',providers:{codex:{installed:true,available:true,signedIn:true}}}:{status:'disabled',enabled:false,projects:[],bin:[],saved:true}});
  });
  await page.goto(base);const input=page.getByLabel('Your message',{exact:true});await input.waitFor();await page.locator('.intake-status').filter({hasText:kind==='oversize'?'exceeds the message limit':'more than four files'}).waitFor();assert.equal(sent.length,0);
  await page.setViewportSize({width:390,height:900});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,`intake-blocked-${kind}-mobile.png`)});await page.setViewportSize({width:1440,height:1000});
  await input.fill('My current unsent draft');await page.getByRole('button',{name:'Edit update',exact:true}).click();assert.equal(await input.inputValue(),'My current unsent draft');assert.ok((await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')))).extensions.conversation.messages.some(m=>m.text===original&&m.workState==='queued'));
  await input.fill('');await page.getByRole('button',{name:'Edit update',exact:true}).click();assert.equal(await input.inputValue(),original);
  if(kind==='files'){
   assert.equal(await page.locator('.attachment-chip').count(),5);assert.equal(await page.locator('.attachment-chip img').count(),0,'missing image references do not become invalid data URLs');
   await page.getByRole('button',{name:'Send message',exact:true}).click();assert.equal(sent.length,0);
   for(const f of files)await page.getByRole('button',{name:`Remove ${f.name}`,exact:true}).click();
  }
  await input.fill('Keep the existing website and add a private worker.');await page.getByRole('button',{name:'Send message',exact:true}).click();await page.getByText('The updated requirement is preserved.',{exact:true}).waitFor();assert.equal(sent.length,1);assert.equal(sent[0].message,'Keep the existing website and add a private worker.');
  await page.reload();await page.getByText('The updated requirement is preserved.',{exact:true}).waitFor();const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));assert.ok(saved.extensions.conversation.messages.some(m=>m.text===original&&m.workState==='cancelled'));assert.equal(sent.length,1,'reload does not replay edited intent');
  await page.screenshot({path:path.join(out,`intake-${kind}.png`)});checks.push({kind,blockedWithoutCrash:true,draftPreserved:true,originalIntentRetained:true,editedRequestSentOnce:true,reloadDidNotReplay:true});await context.close();
 }
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify({passed:true,checks,errors,boundary:'Real browser UI, local persistence and queue dispatch; fixture model/session transport, no live model or cloud.'},null,2)+'\n');console.log('Passed real browser: saved oversized/multi-file queue recovery, protected draft, retained original intent, explicit edit/send and reload without replay.');
}finally{await browser?.close();server.kill('SIGTERM');}
