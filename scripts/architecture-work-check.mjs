// Actual browser/persistence/export; backend and model responses are fixtures.
import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import {spawn} from 'node:child_process';import {createServer} from 'node:net';import {chromium} from '@playwright/test';
import {validateImport} from '../src/core.mjs';import {architectureWork,proposeWorkRecords,reviewWorkContext} from '../src/architecture-work.mjs';import {toProjectFile,parseProjectFile} from '../src/project-file.mjs';import {deliveryPack} from '../src/delivery.mjs';
const out=path.resolve(process.env.ATMEM_ARCHITECT_WORK_EVIDENCE||'.local/engine-product/architecture-work-browser');if(fs.existsSync(out))throw Error('Preserve previous evidence; choose a new output directory.');fs.mkdirSync(out,{recursive:true});
const socket=createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));
const base='http://127.0.0.1:'+port,server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'ignore',env:{...process.env,ATMEM_ARCHITECT_VITE_CACHE_DIR:path.join(out,'vite-cache')}});
const node=(id,label,x)=>({id,position:{x,y:100},data:{kind:'resource',provider:'tools',origin:'existing',label,description:'Client-owned '+label+'. Preserve it.',config:{region:'Local'}}});
let project=validateImport({id:'library-work-ui',version:1,revision:1,name:'Library readings',provider:'tools',requirements:'Keep the public catalogue unchanged and display read-only readings.',nodes:[node('catalog','Public catalogue',0),node('viewer','Reading viewer',350)],edges:[{id:'lookup',source:'viewer',target:'catalog',label:'Read-only lookup'}],needs:[{id:'readings',kind:'functional',category:'other',priority:'must',status:'open',source:'user',statement:'Show readings in grams.',links:['viewer']}],decisions:[]});
const record=(id,kind,dependsOn,data)=>({id,kind,title:id,description:'A proposed mapping, not execution proof.',dependsOn,data});
project=proposeWorkRecords(project,[record('Reading files','implementation',['block:viewer'],{files:['viewer/read.mjs']}),record('Catalogue reference','implementation',['block:catalog'],{files:['reference/catalog.json']})]);
for(const id of ['work:Reading files','work:Catalogue reference'])project=reviewWorkContext(project,id);
let browser,page,job=null,events=[],modelCalls=0;const errors=[],nativeMutations=[],devReloads=[];
try{
 for(let i=0;i<100;i++){try{if((await fetch(base)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true});page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(15000);page.on('pageerror',e=>errors.push(e.message));page.on('websocket',socket=>socket.on('framereceived',frame=>{try{const value=JSON.parse(frame.payload);if(['update','full-reload'].includes(value.type))devReloads.push(value.type);}catch{}}));
 await page.addInitScript(p=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify(p));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'exact-model',effort:'high'}));},project);
 await page.route('**/api/**',async route=>{
  const url=route.request().url(),body=route.request().postDataJSON();
  if(url.includes('/engineering/')){
   const action=url.split('/engineering/').at(-1);
   if(['create','start','steer'].includes(action))nativeMutations.push(action);
   if(action==='list')return route.fulfill({json:{sessions:job?[job]:[]}});
   if(action==='create')job={id:'00000000-0000-0000-0000-000000000001',model:body.model,effort:body.effort,state:'idle',run:null};
   if(action==='start'){job={...job,state:'running',run:'00000000-0000-0000-0000-000000000002'};events.push({sequence:1,kind:'accepted',runId:job.run,text:body.text});}
   if(action==='events')return route.fulfill({json:{session:job,events:events.filter(e=>e.sequence>body.after)}});
   if(action==='artifacts')return route.fulfill({json:{artifacts:[]}});
   return route.fulfill({json:job});
  }
  if(url.endsWith('/api/architect')){modelCalls++;return route.fulfill({json:{message:'Requirement recorded. Existing graph retained.',phase:'Architecture Review',componentReview:{componentId:'viewer',summary:'Check dependent implementation against the updated requirement.',questions:[]}}});}
  return route.fulfill({json:url.endsWith('/api/session')?{token:'fixture',engineeringEnabled:true,status:'local-sidecar',providers:{codex:{installed:true,available:true,signedIn:true}}}:{status:'disabled',enabled:false,saved:true,projects:[],bin:[]}});
 });
 const state=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));
 const work=()=>page.locator('.architecture-work');
 await page.goto(base);await work().locator(':scope > summary').click();await work().getByText('Reading files',{exact:true}).waitFor();assert.match(await work().locator('li[data-work-ref="work:Reading files"]').innerText(),/Context current/);assert.deepEqual(nativeMutations,[]);
 const proposal={version:1,records:[record('Reported check','evidence',['work:Reading files'],{reportedStatus:'passed',level:'local-runtime'})]};
 await work().getByLabel('Import proposed work mappings').setInputFiles({name:'proposal.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(proposal))});
 await work().getByText('Reported check',{exact:true}).waitFor();assert.match(await work().locator('li[data-work-ref="work:Reported check"]').innerText(),/agent · proposed/);await work().getByRole('button',{name:'Record context review: Reported check',exact:true}).click();
 await page.getByRole('tab',{name:'Design',exact:true}).click();await page.getByRole('button',{name:/Review Reading viewer:/}).click();
 const req=page.getByRole('article',{name:'Requirement readings',exact:true});await req.getByRole('button',{name:'Edit requirement',exact:true}).click();await req.getByRole('textbox',{name:'Requirement text',exact:true}).fill('Show readings in milligrams.');await req.getByRole('button',{name:'Save & re-evaluate',exact:true}).click();
 await page.waitForFunction(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')).needs.some(r=>r.id==='readings'&&r.statement==='Show readings in milligrams.'));assert.equal(modelCalls,1);
 await page.getByRole('tab',{name:'Build',exact:true}).click();await work().locator(':scope > summary').click();
 for(const name of ['Reading files','Reported check'])assert.match(await work().locator('li[data-work-ref='+JSON.stringify('work:'+name)+']').innerText(),/Review again/);
 assert.match(await work().locator('li[data-work-ref="work:Catalogue reference"]').innerText(),/Context current/);
 assert.deepEqual((await state()).nodes.map(n=>n.data.origin),['existing','existing']);
 await page.reload();await work().locator(':scope > summary').click();assert.match(await work().locator('li[data-work-ref="work:Reported check"]').innerText(),/Review again/);
 await page.screenshot({path:path.join(out,'changed-desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'changed-mobile.png'),fullPage:true});
 await work().getByRole('button',{name:'Record context review: Reported check',exact:true}).click();const beforeNative=await state();assert.equal(beforeNative.extensions.architectureWork.history.length,1);
 const view=architectureWork(beforeNative),exported=deliveryPack(beforeNative);assert.deepEqual(JSON.parse(exported['architecture-work.json']),view);assert.deepEqual(architectureWork(parseProjectFile(exported['project.atmem-ai-architect.json']).project),view);
 fs.writeFileSync(path.join(out,'exported-architecture-work.json'),exported['architecture-work.json']);
 await page.getByLabel('What should we build or repair?',{exact:true}).fill('Retain the existing catalogue; add a local screen.');await page.getByRole('button',{name:'Start work',exact:true}).click();
 await page.waitForFunction(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')).extensions.architectureWork.intents.length===1);
 events.push({sequence:2,kind:'accepted',origin:'automatic_repair',runId:job.run,text:'Synthetic internal repair; not a client demand.'},{sequence:3,kind:'steering_submitted',requestId:'fixture-update',text:'Keep Unicode labels intact.'},{sequence:4,kind:'steering_accepted',requestId:'fixture-update'});
 await page.waitForFunction(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')).extensions.architectureWork.intents.length===2);
 const current=await state();assert.deepEqual(current.extensions.architectureWork.intents.map(i=>i.text),['Retain the existing catalogue; add a local screen.','Keep Unicode labels intact.']);
 await page.reload();await page.waitForFunction(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')).extensions.architectureWork.intents.length===2);assert.deepEqual(nativeMutations,['create','start']);assert.deepEqual(errors,[]);assert.deepEqual(devReloads,[]);
 fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({passed:true,checks:['unreviewed import remains proposed despite reported pass','scoped requirement edit invalidates transitive mappings/evidence','unrelated catalogue mapping remains current','graph ownership preserved','reload preserves stale context/history','UI/export/project round-trip agree','desktop/mobile','ordered native client intent persisted without internal repair prompts','reload does not replay native work'],modelBoundary:'Actual browser/UI/storage/export; explicit fixture model/backend. No live native generation, runtime evidence acceptance, cloud operation or completed GE-003 inferred.',errors,devReloads},null,2)+'\n');console.log('Architecture work browser checks passed.');
}catch(e){if(page){fs.writeFileSync(path.join(out,'failure.txt'),await page.locator('body').innerText());await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});}throw e;}finally{await browser?.close();server.kill('SIGTERM');}
