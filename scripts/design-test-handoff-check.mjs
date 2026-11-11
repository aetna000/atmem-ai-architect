// Browser handoff contract only. Explicit backend/native fixtures; no inference.
import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import {spawn} from 'node:child_process';import {createServer} from 'node:net';import {createHash} from 'node:crypto';import {chromium} from '@playwright/test';
import {BUILD_AND_TEST_REQUEST} from '../src/design-build-flow.mjs';
const out=process.env.ATMEM_HANDOFF_EVIDENCE;if(!out||fs.existsSync(out))throw Error('Choose a fresh evidence directory.');fs.mkdirSync(out,{recursive:true});
const socket=createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));
const base='http://127.0.0.1:'+port,server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'ignore',env:{...process.env,ATMEM_ARCHITECT_VITE_CACHE_DIR:path.resolve(out,'vite-cache')}});
const project={id:'public-handoff-project',version:1,revision:1,name:'Knowledge website',provider:'aws',requirements:'Retain the existing catalog portal, require staff access and preserve accepted placement. Advanced analytics stay deferred.',nodes:[{id:'website',position:{x:0,y:0},data:{label:'Existing website',kind:'resource',provider:'tools',origin:'existing',binding:'existing-service'}},{id:'application',position:{x:300,y:0},data:{label:'Website helper application',kind:'resource',provider:'aws',origin:'proposed'}}],edges:[{id:'web-api',source:'website',target:'application',label:'Required authenticated interface'}]};
let browser,page,job=null,starts=0,designCalls=0,emulationCalls=0,saved=null;const errors=[];
try{
 for(let i=0;i<100;i++){try{if((await fetch(base)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true});page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(20000);page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(p=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify(p));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.1-sol',effort:'high'}));},project);
 await page.route('**/api/**',async route=>{
  const url=route.request().url(),body=route.request().postDataJSON();
  if(url.endsWith('/api/architect')){designCalls++;return route.fulfill({status:500,json:{detail:'Unexpected design inference.'}});}
  if(url.endsWith('/api/projects/save')){saved=body.file;return route.fulfill({json:{saved:true,sha256:createHash('sha256').update(JSON.stringify(body.file)).digest('hex')}});}
  if(url.endsWith('/api/emulation/run')){emulationCalls++;return route.fulfill({json:{status:'blocked',checks:[],blockers:['resource-application'],designRevision:1,artifactDigest:'a'.repeat(64)}});}
  if(url.includes('/api/engineering/')){
   const action=url.split('/').at(-1);
   if(action==='list')return route.fulfill({json:{sessions:job?[job]:[]}});
   if(action==='create'){assert(saved);assert.equal(saved.discovery.problem,project.requirements);assert.equal(saved.design.nodes.length,2);assert.equal(saved.design.edges.length,1);assert.equal(body.model,'gpt-6.1-sol');assert.equal(body.effort,'high');job={id:'00000000-0000-4000-8000-000000000042',projectId:project.id,model:body.model,effort:body.effort,state:'idle',run:null};}
   if(action==='start'){starts++;assert.equal(body.text,BUILD_AND_TEST_REQUEST);job={...job,state:'running',run:'fixture-implementation-run'};}
   if(action==='events')return route.fulfill({json:{session:job,events:[]}});
   if(action==='artifacts')return route.fulfill({json:{artifacts:[]}});
   return route.fulfill({json:job});
  }
  return route.fulfill({json:url.endsWith('/api/session')?{token:'fixture',engineeringEnabled:true,architectureActivityEnabled:true,status:'local-sidecar',providers:{codex:{installed:true,available:true,signedIn:true}}}:{status:'disabled',enabled:false,projects:[],bin:[]}});
 });
 await page.goto(base);await page.locator('.react-flow').waitFor();await page.getByRole('button',{name:'Emulate & improve',exact:true}).click();
 const panel=page.getByRole('complementary',{name:'Cloud emulation',exact:true});await panel.getByRole('button',{name:'Build and test this design',exact:true}).waitFor();assert.equal(starts,0);assert.equal(designCalls,0);
 await panel.getByRole('button',{name:'Emulate locally',exact:true}).click();await page.waitForTimeout(250);assert.equal(emulationCalls,2);assert.equal(starts,0);assert.equal(await page.locator('.messages .msg.assistant').filter({hasText:'Build the implementation to run its tests'}).count(),1,'same empty blocker must not duplicate the automatic explanation');
 await panel.getByRole('button',{name:'Build and test this design',exact:true}).click();await page.getByRole('heading',{name:'Build outcome',exact:true}).waitFor();await page.getByText('Working · gpt-6.1-sol · high',{exact:true}).waitFor();assert.equal(starts,1);
 await page.screenshot({path:path.join(out,'build-handoff.png')});await page.reload();await page.locator('.react-flow').waitFor();assert.equal(starts,1,'reload must not repeat the build request');assert.equal(designCalls,0);assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({passed:true,starts,designCalls,emulationCalls,scopeAndOwnershipRetained:true,model:'gpt-6.1-sol',effort:'high',errors,boundary:'Real browser/UI/save/build handoff with explicit backend/native fixtures. No model inference, generated website application, application test pass or deployment claimed.'},null,2)+'\n');console.log('Design test-to-implementation handoff, no duplicate guidance and no replay passed.');
}catch(e){if(page){fs.writeFileSync(path.join(out,'failure.txt'),await page.locator('body').innerText());await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});}throw e;}finally{await browser?.close();server.kill('SIGTERM');}
