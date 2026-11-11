// Real browser interactions; explicitly fixture backend/model, not native qualification.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
import {createHash} from 'node:crypto';
const out=path.resolve(process.env.ATMEM_ENGINEERING_EVIDENCE_DIR||'specs/029-general-purpose-engine/evidence/20261111-engineering-jobs');fs.mkdirSync(out,{recursive:true});
const socket=createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));
const base=`http://127.0.0.1:${port}`,server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'ignore',env:{...process.env,ATMEM_ARCHITECT_VITE_CACHE_DIR:path.join(out,'vite-cache')}});
const project={id:'engineering-project-123',version:1,revision:1,name:'Sensor processing',provider:'tools',requirements:'Keep the existing sensor service.',nodes:[],edges:[]};
const archive=Buffer.from('fixture immutable archive'),digest=createHash('sha256').update(archive).digest('hex');
let browser;const errors=[],requests=[];let saved=false,rejectSave=false,engineeringEnabled=true;let job=null,events=[],rejectUpdate=false,captured=null,validations=[],definition='definition-one';
try{
 for(let i=0;i<100;i++){try{if((await fetch(base)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(project=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify(project));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'exact-model',effort:'high'}));},project);
 await page.route('**/api/**',async route=>{
  const url=route.request().url(),payload=route.request().postDataJSON();
  if(url.includes('/engineering/')){
   const action=url.split('/engineering/').at(-1);requests.push({action,payload});
   assert.equal(payload.projectId,project.id);assert.equal(payload.workspace,undefined);assert.equal(payload.handle,undefined);
   if(action==='list')return saved?route.fulfill({json:{sessions:job?[job]:[]}}):route.fulfill({status:404,json:{detail:'Save this project before looking up work.'}});
   if(action==='create'){assert(saved,'project context must save before native creation');assert.equal(payload.model,'exact-model');assert.equal(payload.effort,'high');job={id:'00000000-0000-0000-0000-000000000001',model:payload.model,effort:payload.effort,state:'idle',run:null,last_status:null};}
   if(action==='start'){job={...job,state:'running',run:'public-run'};events.push({sequence:events.length+1,kind:'accepted',text:payload.text});}
   if(action==='steer'&&rejectUpdate)return route.fulfill({status:409,json:{detail:'Recover this job before submitting more work.'}});
   if(action==='steer')events.push({sequence:events.length+1,kind:'steering_submitted',requestId:'update-one',text:payload.text},{sequence:events.length+2,kind:'steering_accepted',requestId:'update-one'});
   if(action==='events')return route.fulfill({json:{session:job,events:events.filter(e=>e.sequence>payload.after)}});
   if(action==='artifacts')return route.fulfill({json:{artifacts:captured?[captured]:[]}});
   if(action==='recheck'){assert.equal(payload.runId,job.run);assert.equal(payload.artifactId,captured.id);assert.equal(payload.command,undefined);return route.fulfill({json:{state:'checking'}});}
   if(action==='capture'){captured={id:'artifact-fixture',runId:job.run,sha256:digest,turnStatus:'completed',files:[{path:'main.tf',kind:'file'}]};return route.fulfill({json:captured});}
   if(action==='validators')return route.fulfill({json:{available:true,validators:[{id:'python-tests',label:'Local Python tests',contractSha256:definition},{id:'browser-tests',label:'Isolated browser tests',available:false,contractSha256:'unavailable-definition'}]}});
   if(action==='validation/list')return route.fulfill({json:{checks:validations}});
   if(action==='validation/start'){
    assert.equal(payload.command,undefined);assert.equal(payload.image,undefined);
    const check={id:`check-${validations.length+1}`,artifactId:captured.id,artifactSha256:digest,validatorId:'python-tests',label:'Local Python tests',contractSha256:definition,state:'running',result:null};
    validations.push(check);return route.fulfill({json:check});
   }
   if(action==='validation/recover'){
    assert.equal(payload.artifactId,undefined);
    const index=validations.findIndex(check=>check.id===payload.checkId);assert.ok(index>=0);
    validations[index]={...validations[index],state:'finished',result:{status:'failed',reason:'supervisor_restart',output:'Prior cleanup confirmed; no work replayed.'}};
    return route.fulfill({json:validations[index]});
   }
   if(action==='download')return route.fulfill({body:archive,contentType:'application/zip',headers:{'X-Artifact-Sha256':digest}});
   return route.fulfill({json:job});
  }
  if(url.endsWith('/api/projects/save')){if(rejectSave)return route.fulfill({status:503,json:{detail:'Synthetic save unavailable'}});saved=true;}
  return route.fulfill({json:url.endsWith('/api/session')?{token:'fixture',engineeringEnabled,status:'local-sidecar',providers:{codex:{installed:true,available:true,signedIn:true}}}:{status:'disabled',enabled:false,projects:[],bin:[],saved:true}});
 });
 await page.goto(base);await page.getByRole('heading',{name:'Build your project',exact:true}).waitFor();assert.equal(await page.getByRole('tab',{name:'Build',exact:true}).getAttribute('aria-selected'),'true');
 assert.equal(requests.filter(r=>r.action==='create'||r.action==='start').length,0,'opening Build does not start inference');
 const input=page.getByLabel('What should we build or repair?',{exact:true});await input.fill('Keep the existing sensor API. Build a converter and tests.');
 await page.screenshot({path:path.join(out,'build-start-desktop.png')});await page.setViewportSize({width:390,height:900});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'build-start-mobile.png')});await page.setViewportSize({width:1440,height:1000});
 rejectSave=true;await page.getByRole('button',{name:'Start work',exact:true}).click();await page.getByRole('alert').filter({hasText:'Synthetic save unavailable'}).waitFor();assert.equal(await input.inputValue(),'Keep the existing sensor API. Build a converter and tests.');assert.equal(requests.filter(r=>r.action==='create'||r.action==='start').length,0);rejectSave=false;
 await page.getByRole('button',{name:'Start work',exact:true}).click();await page.getByText('Working · exact-model · high',{exact:true}).waitFor();await page.getByRole('log',{name:'Project conversation',exact:true}).getByText('Keep the existing sensor API. Build a converter and tests.',{exact:true}).waitFor();
 const update=page.getByLabel('Add an update',{exact:true});await update.fill('Retain tenant boundaries.');rejectUpdate=true;await page.getByRole('button',{name:'Send update',exact:true}).click();await page.getByRole('alert').filter({hasText:'Recover this job'}).waitFor();assert.equal(await update.inputValue(),'Retain tenant boundaries.');
 rejectUpdate=false;await page.getByRole('button',{name:'Send update',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#engineering-intent').value==='');
 await update.fill('My next unsent requirement must survive reload.');
 await page.getByRole('tab',{name:'Design',exact:true}).click();await page.reload();await page.getByRole('tab',{name:'Build',exact:true}).click();await page.getByText('Working · exact-model · high',{exact:true}).waitFor();
 assert.equal(await page.getByLabel('Add an update',{exact:true}).inputValue(),'My next unsent requirement must survive reload.');
 assert.equal(requests.filter(r=>r.action==='start').length,1,'reload never resubmits original intent');assert.equal(requests.filter(r=>r.action==='create').length,1,'reload reuses the job');
 job={...job,state:'idle',last_status:'completed'};events.push({sequence:events.length+1,kind:'message',text:'Implementation files created. Independent validation remains pending.'},{sequence:events.length+2,kind:'completed'});
 captured={id:'artifact-fixture',runId:job.run,sha256:digest,turnStatus:'completed',files:[{path:'main.tf',kind:'file'}]};
 const finalizationText='Selected local checks passed for the saved package. Requirements and full-system acceptance still need independent verification.';
 events.push({sequence:events.length+1,kind:'finalization_local_checks_passed',runId:job.run,artifactId:captured.id,text:finalizationText});
 await page.getByRole('status').filter({hasText:finalizationText}).waitFor();await page.getByRole('button',{name:'Download package',exact:true}).waitFor();
 await page.getByRole('button',{name:'Capture package',exact:true}).click();await page.getByText(/Checks are not independently verified/).waitFor();
 await page.getByRole('button',{name:'Recheck and repair',exact:true}).click();assert.equal(requests.filter(r=>r.action==='recheck').length,1);assert.equal(requests.filter(r=>r.action==='start').length,1,'recheck action does not submit new client intent');
 const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Download package',exact:true}).click();const download=await downloadPromise;assert.match(download.suggestedFilename(),/^engineering-artifact-fixture.zip$/);
 assert(await page.getByRole('button',{name:'Isolated browser tests · unavailable',exact:true}).isDisabled());await page.getByRole('button',{name:'Local Python tests',exact:true}).click();await page.locator('.artifact-checks strong').filter({hasText:'Local Python tests · running'}).waitFor();
 await page.getByRole('tab',{name:'Design',exact:true}).click();await page.reload();await page.getByRole('tab',{name:'Build',exact:true}).click();await page.locator('.artifact-checks strong').filter({hasText:'Local Python tests · running'}).waitFor();assert.equal(requests.filter(r=>r.action==='validation/start').length,1,'reload observes the prior check instead of replaying it');
 validations[0]={...validations[0],state:'finished',result:{status:'incomplete',testsReported:3,skipped:1,output:'One check was deliberately skipped.'}};
 await page.getByText('Local Python tests · incomplete',{exact:true}).waitFor();await page.getByText('3 tests reported · 1 skipped',{exact:true}).waitFor();
 definition='definition-two';await page.getByText('From a previous check definition; retained as historical evidence.',{exact:true}).waitFor();await page.getByRole('button',{name:'Local Python tests',exact:true}).click();assert.equal(requests.filter(r=>r.action==='validation/start').at(-1).payload.retry,false);
 validations[1]={...validations[1],state:'finished',result:{status:'failed',testsReported:0,skipped:0,output:'No tests executed.'}};await page.getByText('Local Python tests · failed',{exact:true}).waitFor();await page.getByRole('button',{name:'Run again: Local Python tests',exact:true}).click();assert.equal(requests.filter(r=>r.action==='validation/start').at(-1).payload.retry,true);
 validations[2]={...validations[2],state:'finished',result:{status:'passed',testsReported:9,skipped:0,output:'Nine local tests executed.'}};await page.getByText('Local Python tests · passed',{exact:true}).waitFor();
 const reportPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Save check report',exact:true}).last().click();assert.match((await reportPromise).suggestedFilename(),/^package-check-check-3.json$/);
 validations[2]={...validations[2],state:'recovery_required',result:null};await page.getByRole('button',{name:'Recover check',exact:true}).click();await page.getByText('Prior cleanup confirmed; no work replayed.',{exact:true}).waitFor({state:'attached'});assert.equal(requests.filter(r=>r.action==='validation/start').length,3,'cleanup does not replay a check');
 await page.screenshot({path:path.join(out,'engineering-desktop.png')});await page.setViewportSize({width:390,height:900});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'engineering-mobile.png')});
 engineeringEnabled=false;await page.reload();await page.locator('.react-flow').waitFor();assert.equal(await page.getByRole('tab',{name:'Build',exact:true}).count(),0);assert.equal(await page.locator('#engineering-intent').count(),0);
 const queuedContext=await browser.newContext(),queuedPage=await queuedContext.newPage();let legacyCalls=0,queuedNativeStarts=0,voicePreparation=0;
 const queuedProject={...project,extensions:{conversation:{version:1,messages:[{role:'user',text:'Preserve this old queued design update.',requestId:'old-design-request',workState:'queued'}]}}};
 await queuedPage.addInitScript(p=>{localStorage.setItem('atforma-workspace-v3',JSON.stringify(p));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'exact-model',effort:'high'}));},queuedProject);
 await queuedPage.route('**/api/**',async route=>{const url=route.request().url();if(url.endsWith('/api/architect'))legacyCalls++;if(/\/engineering\/(create|start|steer)$/.test(url))queuedNativeStarts++;if(url.endsWith('/api/voice/prepare'))voicePreparation++;return route.fulfill({json:url.endsWith('/api/session')?{token:'fixture',engineeringEnabled:true,status:'local-sidecar',providers:{codex:{installed:true,available:true,signedIn:true}}}:url.endsWith('/engineering/list')?{sessions:[]}:{status:'disabled',enabled:false,projects:[],bin:[],saved:true}});});
 queuedPage.on('pageerror',e=>errors.push(e.message));await queuedPage.goto(base);await queuedPage.getByRole('heading',{name:'Build your project',exact:true}).waitFor();await queuedPage.waitForTimeout(1200);assert.equal(legacyCalls,0);assert.equal(queuedNativeStarts,0);assert.equal(voicePreparation,0);const savedQueue=await queuedPage.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')).extensions.conversation.messages);assert(savedQueue.some(m=>m.requestId==='old-design-request'&&m.workState==='queued'&&m.text==='Preserve this old queued design update.'));await queuedContext.close();
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify({passed:true,checks:['native-first default with explicit design navigation','legacy queued intent retained without hidden planner/inference/voice preparation','no inference on opening','single start saves before create/start','save failure retains draft without starting work','complete user/assistant transcript','feature-off design path retained','exact model and effort','project-bound requests without native handles or paths','start once','failed steering preserves draft','successful steering','close/reload/recover without replay','progress replay','capture status boundary','digest-verified download','captured artifact restored on reload','local check survives reload without replay','skipped/zero-test status retained','changed check definition marks prior evidence historical','explicit retry','exact-artifact/run recheck without new client intent','check report download','desktop/mobile'],boundary:'Real browser/UI; fixture session service and model; download body is a fixture, not a generated ZIP package.',errors},null,2)+'\n');
 console.log('Passed engineering browser fixture: scoped job, exact selection, retained updates, recover without replay, immutable download, responsive layout.');
}finally{await browser?.close();server.kill('SIGTERM');}
