import {reservationSystemModel} from '../tests/fixtures/system-model.mjs';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {zipSync,strToU8,unzipSync,strFromU8} from 'fflate';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
import {toProjectFile} from '../src/project-file.mjs';
// Real browser, fixture service. No inference, credentials or cloud operations.
const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'atmem-workflow-'));
const file=process.argv[2]||path.join(temporary,'requirements.txt');
if(!process.argv[2])fs.writeFileSync(file,'Versioned dispatch requirements.\n'.repeat(140000));
const extra=path.join(temporary,'exceptions.md');
fs.writeFileSync(extra,'Reconcile ambiguous reservation timeouts.');
const imageFile=path.join(temporary,'diagram.png');
fs.writeFileSync(imageFile,Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=','base64'));
const base=process.env.ATMEM_WORKFLOW_URL||'http://127.0.0.1:5194';
const browser=await chromium.launch();
const hash=value=>createHash('sha256').update(value).digest('hex');
function capturedDesign(saved){
 const steps=[{sender:'Client',receiver:'Ledger',action:'Reserve numbered item'}];
 const journeys=[{name:'Reserve',steps},{name:'Recover',steps}];
 const buildSpec={inputs:'Stable request',outputs:'Reservation receipt',behavior:'Single active reservation',failures:'Read durable prior outcome',implementation:'Atomic ledger update',infrastructure:'Transactional storage',operations:'Backup and replay audit',tests:'Race the final item',scenarios:journeys};
 const node=(id,parentBlockId)=>({id,type:'resource',position:{x:0,y:0},data:{label:id,provider:'tools',kind:'resource',origin:'proposed',buildSpec:parentBlockId?{...buildSpec,verificationCases:[{
   id:'checkout-race',name:'Concurrent reservation',category:'contract',requirementIds:['unique-reservation'],
   environment:'Local harness',setup:'One available item',input:'Two reservation IDs',action:'Send simultaneously',
   expected:'Exactly one winner',evidence:'Compare both responses',interfaceId:'reserve',
 }]}:buildSpec,...(parentBlockId?{parentBlockId}:{})}});
 const draft={version:1,baseRevision:saved.meta.revision,sourceSlots:saved.extensions.designSources.map((_,i)=>i+1),title:'Fixture architecture',
   addNodes:[node('Ledger'),node('Reservations','Ledger')],
   addEdges:[{id:'reserve',source:'Ledger',target:'Reservations',label:'Reserve',interfaceSpec:{transport:'Local call',input:'Item ID',output:'Receipt',authorization:'Staff',failure:'Replay prior receipt',verification:'Race final item'}}],
   requirements:[{id:'unique-reservation',statement:'Reserve each item at most once.',kind:'nonfunctional',priority:'must',acceptance:'Two concurrent requests produce one winner.',sourceSlot:1,reference:'Fixture section 1',links:['Reservations']},
     ...saved.extensions.designSources.slice(1).map((source,i)=>({id:'restore-'+i,statement:source.text,kind:'functional',priority:'should',acceptance:'Retry returns the previous receipt.',sourceSlot:i+2,reference:'Recovery section',links:['Ledger']}))],
   systemModel:reservationSystemModel(),
   systemSpec:{title:'Reservations',decomposition:'Ledger and reservation responsibilities',infrastructure:'Portable site or cloud',operations:'Backup and restore',testing:'Race and reconcile timeouts',journeys,
     stateMachines:[{name:'Reservation',states:['Open','Held'],initial:'Open',transitions:[{from:'Open',to:'Held',event:'Reserved'}]}],
     deploymentUnits:[{name:'Local runtime',placement:'site',blocks:['Ledger','Reservations']}]}};
 const bytes=strToU8(JSON.stringify(draft));
 const archive=zipSync({'architecture.canvas.json':bytes,'architecture.review.md':strToU8('Draft SHA-256: '+hash(bytes)),
   'specs/reservations/plan.md':strToU8('# Plan\n\n```mermaid\nflowchart LR\nA[Request] --> B[Receipt]\n```\n')});
 const artifact={id:'captured',runId:1,sha256:hash(archive),files:['architecture.canvas.json','architecture.review.md','specs/reservations/plan.md'].map(path=>({path,kind:'file'}))};
 return {archive,artifact};
}
try{
 for(const [inputId,selectedFile] of [['requirements-file-input',file],['chat-attachment-input',file],['requirements-file-input',imageFile],['chat-attachment-input',imageFile]]){
  const bytes=fs.readFileSync(selectedFile),illustrated=selectedFile===imageFile;
  const delayedSession=selectedFile===file;
  const previewOnly=inputId==='chat-attachment-input'&&!illustrated;
  const selectedFiles=previewOnly?[selectedFile,extra]:[selectedFile];
  let sessionRequests=0;
  const page=await browser.newPage({viewport:{width:1570,height:1020}});
  let saved,started,capture,oldCalls=0,creationTime,startCount=0;
  const paths=[];
  const job={id:'session',state:'idle',run:1,last_status:'completed',model:'gpt-6.2-sol',effort:'medium'};
  await page.addInitScript(preview=>{
   localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.2-sol',effort:'medium'}));
   localStorage.setItem('atforma-draw-live',preview?'off':'on');
  },previewOnly);
  await page.route('**/api/**',async route=>{
   const pathname=new URL(route.request().url()).pathname;
   if(!paths.includes(pathname))paths.push(pathname);
   let result={status:'disabled',projects:[],bin:[],sessions:[],events:[],artifacts:[]};
   if(pathname==='/api/session'){sessionRequests++;if(delayedSession)await new Promise(resolve=>setTimeout(resolve,1800));result={status:'local-sidecar',token:'fixture',engineeringEnabled:true,providers:{codex:{installed:true,available:true,signedIn:true}}};}
   if(pathname==='/api/design-sources'){
    const payload=route.request().postDataJSON();assert.equal(payload.projectId,saved.meta.id);
    assert.equal(payload.attachments.length,selectedFiles.length);
    assert.ok(Buffer.from(payload.attachments[0].data,'base64').equals(bytes));
    result={sources:payload.attachments.map((source,i)=>({name:source.name,mime:source.mime,text:'Require correlated tasks and reconciliation.',sha256:(i===0?'a':'c').repeat(64),
      ...(illustrated?{graphics:['diagram.png'],figureEvidence:{manifestSha256:'f'.repeat(64),figures:[{id:'figure-1',sha256:'e'.repeat(64),status:'available'}]}}:{})}))};
   }
   if(pathname==='/api/projects/save'){saved=route.request().postDataJSON().file;creationTime??=saved.meta.createdAt;assert.equal(saved.meta.createdAt,creationTime,'Autosave and engineering must preserve initial document creation time');result={saved:true,sha256:'b'.repeat(64)};}
   if(pathname==='/api/engineering/list'&&started)result={sessions:[job]};
   if(pathname==='/api/engineering/recover')result=job;
   if(pathname==='/api/engineering/create')result={id:'session',state:'idle',run:0,model:'gpt-6.2-sol',effort:'medium'};
   if(pathname==='/api/engineering/start'){startCount++;started=route.request().postDataJSON();capture=capturedDesign(saved);result=job;}
   if(pathname==='/api/engineering/events')result={events:started?[{sequence:1,runId:1,kind:'accepted',text:started.text}]:[],session:started?job:{...job,run:0,last_status:null}};
   if(pathname==='/api/engineering/artifacts')result={artifacts:capture?[capture.artifact]:[]};
   if(pathname==='/api/engineering/delivery'&&capture)result={relation:'matches_saved_design',savedFileSha256:'b'.repeat(64),artifact:capture.artifact,session:job,context:{sha256:'b'.repeat(64)},
     sourceFigureEvidence:{artifactId:capture.artifact.id,contextSha256:'b'.repeat(64),deliveries:illustrated?[{sourceSha256:'a'.repeat(64),manifestSha256:'f'.repeat(64),figureId:'figure-1',sha256:'e'.repeat(64)}]:[]}};
   if(pathname==='/api/engineering/reconciliation')result={status:'proposal_missing'};
   if(pathname==='/api/engineering/download')return route.fulfill({body:Buffer.from(capture.archive),contentType:'application/zip',headers:{'X-Artifact-Sha256':capture.artifact.sha256}});
   if(pathname==='/api/architect')oldCalls++;
   await route.fulfill({json:result});
  });
  await page.goto(base);
  await page.getByRole('button',{name:'Upload specification',exact:true}).waitFor();
  assert.equal(await page.getByText('Design with Codex',{exact:true}).count(),0);
  await page.locator('#'+inputId).setInputFiles(selectedFiles);
  const uploaded=page.getByRole('complementary',{name:'Uploaded specifications'});
  await uploaded.getByRole('list',{name:'Loaded files'}).getByText(path.basename(selectedFile),{exact:true}).waitFor();
  if(previewOnly)await uploaded.getByText('exceptions.md',{exact:true}).waitFor();
  assert.equal(await page.getByRole('tab',{name:'Board',exact:true}).getAttribute('aria-selected'),'true');
  await uploaded.getByRole('button',{name:'Architecture progress',exact:true}).click();
  await page.getByRole('heading',{name:'Architecture workspace',exact:true}).waitFor();
  await page.getByRole('button',{name:'Close architecture progress',exact:true}).click();
  for(let i=0;i<60&&!started;i++)await page.waitForTimeout(100);
  assert.ok(started,inputId+' must automatically submit the same engineering workflow');
  assert.equal(started.contextSha256,'b'.repeat(64));
  assert.equal(saved.extensions.designSources[0].name,path.basename(selectedFile));
  assert.equal(oldCalls,0);
  if(delayedSession)assert.equal(sessionRequests,1,'An immediate upload must await the in-flight session lookup');
  if(previewOnly){
   const preview=page.locator('.preview-bar').filter({hasText:'Fixture architecture'});
   await preview.getByRole('button',{name:'Apply',exact:true}).waitFor();
   await page.getByRole('button',{name:'System diagrams',exact:true}).click();
   const dialog=page.getByRole('region',{name:'System diagrams'});
   await dialog.getByRole('button',{name:'Inventory ledger',exact:true}).click();
   assert.match(await dialog.getByRole('complementary').innerText(),/Module · Ledger/);
   assert.equal(await dialog.getByRole('button',{name:'Open module',exact:true}).count(),0);
   await dialog.getByRole('button',{name:'Back to Board',exact:true}).click();
   await preview.getByRole('button',{name:'Apply',exact:true}).click();
  }
  try {
   await page.waitForFunction(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')||'{}').nodes?.some(node=>node.id==='Reservations'));
  } catch(error) {
   console.error(paths,await page.locator('.engineering-panel').innerText());
   throw error;
  }
  assert.equal(await page.getByText('Design with Codex',{exact:true}).count(),0);
  assert.equal(await page.getByRole('button',{name:'Apply to canvas',exact:true}).count(),0);
  console.log(inputId,path.basename(selectedFile),'saved source and automatically started the single workflow');
  if(inputId==='requirements-file-input'&&!illustrated){
   assert.match(started.text,/systemModel.*functional flow and sequence/);
   await page.getByRole('button',{name:'System diagrams',exact:true}).click();
   const model=page.getByRole('region',{name:'System diagrams'});
   const views=model.getByRole('navigation',{name:'System diagram views'});
   const drawing=model.getByLabel('Scrollable diagram');
   const properties=model.getByRole('complementary',{name:'System model properties'});
   await drawing.getByRole('button',{name:'Reserve item',exact:true}).click();
   assert.match(await properties.innerText(),/Interface contract[\s\S]*Local call[\s\S]*Concurrent reservation[\s\S]*Reserve each item at most once/);
   await views.getByRole('button',{name:'Exclusive hold flow',exact:true}).click();
   await drawing.getByRole('button',{name:'Acquire exclusive hold',exact:true}).click();
   assert.match(await properties.innerText(),/Allocated to · Reservation allocator/);
   await drawing.getByRole('button',{name:'Validated reservation',exact:true}).click();
   await properties.getByRole('button',{name:'Reserve item',exact:true}).click();
   await properties.getByRole('button',{name:'Retry after timeout',exact:true}).click();
   assert.equal(await drawing.getByRole('button',{name:/^[12]\. Reserve item$/}).count(),2);
   assert.equal(await drawing.locator('[aria-pressed=true]').count(),2);
   if(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR){
    const directory=process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR;
    fs.mkdirSync(directory,{recursive:true});
    for(const [name,file] of [['Reservation architecture','logical-components'],['Exclusive hold flow','functional-flow'],['Reserve a numbered item','sequence']]){
      await views.getByRole('button',{name,exact:true}).click();
      await model.screenshot({path:path.join(directory,file+'.png')});
    }
   }
   await page.keyboard.press('Escape');
   await model.waitFor({state:'hidden'});
   await page.reload();
   await page.getByRole('button',{name:'System diagrams',exact:true}).click();
   await model.getByRole('button',{name:'Inventory ledger',exact:true}).click();
   await model.getByRole('button',{name:'Open module',exact:true}).click();
   await page.getByRole('region',{name:'Block detail',exact:true}).getByRole('heading',{name:'Ledger',exact:true}).waitFor();
   await page.getByRole('button',{name:'Prepare agent handoff',exact:true}).click();
   const ready=page.waitForEvent('download');
   await page.getByRole('button',{name:'Download agent handoff',exact:true}).click();
   const modelFiles=unzipSync(fs.readFileSync(await (await ready).path()));
   assert.equal(JSON.parse(strFromU8(modelFiles['spec-kit/system/system-model.json'])).id,'reservation-system');
   const assignment=Object.keys(modelFiles).find(name=>name.endsWith('/system-model-assignment.json'));
   assert.ok(JSON.parse(strFromU8(modelFiles[assignment])).diagramIds.includes('flow'));
   const moduleTabs=page.getByRole('navigation',{name:'Module details'});
   await moduleTabs.getByRole('button',{name:'Interfaces',exact:true}).click();
   await page.getByText('Ledger → Reservations · Reserve',{exact:true}).click();
   await page.getByRole('button',{name:'Edit interface',exact:true}).click();
   await page.getByRole('textbox',{name:'Transport and version',exact:true}).fill('Local call v2');
   await page.getByRole('button',{name:'Save interface',exact:true}).click();
   await page.getByRole('button',{name:'System diagrams',exact:true}).click();
   await views.getByRole('button',{name:'Reserve a numbered item',exact:true}).click();
   await drawing.getByRole('button',{name:'2. Reserve item',exact:true}).click();
   assert.match(await properties.innerText(),/Local call v2[\s\S]*Concurrent reservation/);
   await page.setViewportSize({width:600,height:900});
   assert.ok((await model.boundingBox()).width<=600);
   await model.getByRole('button',{name:'Actual size',exact:true}).click();
   assert.ok(await drawing.evaluate(el=>el.scrollWidth>el.clientWidth));
   await model.getByRole('button',{name:'Fit width',exact:true}).click();
   assert.ok(await drawing.evaluate(el=>el.scrollWidth<=el.clientWidth+1));
   await model.getByRole('button',{name:'Back to Board',exact:true}).click();
   await page.setViewportSize({width:1570,height:1020});

   await page.getByRole('tab',{name:'Review',exact:true}).click();
   console.log('Uploaded fixture generated navigable logical views, with shared exchange selection and a module link after reload.');
   const refine=page.getByRole('button',{name:'Refine architecture',exact:true});
   await refine.waitFor();
   await page.locator('.review-generation summary').filter({hasText:'Additional instructions (optional)'}).click();
   await page.getByRole('textbox',{name:'Additional instructions (optional)',exact:true}).fill('Add explicit restore failure reasoning.');
   await refine.click();
   await page.waitForFunction(()=>document.querySelector('#engineering-intent')?.value==='');
   assert.equal(startCount,2);
   assert.ok(started.text.startsWith('Design the full system described by the saved source documents.'));
   assert.match(started.text,/Add explicit restore failure reasoning/);
   console.log('Review refines architecture with user instructions through the same source-bound workflow.');
  }

  await page.close();
 }
 const page=await browser.newPage({viewport:{width:1500,height:1000}});
 const errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 let executionRequests=0;
 await page.route('**/api/**',route=>{if(/\/engineering\/(start|work-orders\/block)$/.test(new URL(route.request().url()).pathname))executionRequests++;return route.fulfill({json:{status:'disabled',projects:[],bin:[],sessions:[],events:[],artifacts:[]}});});
 const block=(id,parentBlockId)=>({id,type:'resource',position:{x:0,y:0},data:{label:id,kind:'resource',provider:'tools',origin:'proposed',parentBlockId}});
 const project={id:'nested-theatre',version:1,revision:1,name:'Theatre reservations',provider:'tools',
   nodes:[block('Theatre'),block('Reservations','Theatre'),block('Seat holds','Reservations'),block('Admission','Theatre'),block('Payments','Theatre'),block('Reporting','Theatre')],
   edges:[['Admission','Reservations'],['Reservations','Payments'],['Payments','Reporting']].map(([source,target],index)=>({id:'edge-'+index,source,target,label:'Contract'})),needs:[]};
 project.nodes[2].data.buildSpec={behavior:'Acquire the last seat atomically.',inputs:'Seat and session.',outputs:'Accepted or unavailable.',
   implementation:'Implement compare and set.',failures:'Reconcile ambiguous timeouts.',infrastructure:'Reservation database.',
   operations:'Restore and verify holds.',tests:'Two requests produce one winner.',scenarios:[{name:'Last seat race',steps:[
     {sender:'Box office',receiver:'Reservations',action:'Hold seat',messageKind:'command',senderBlockId:'Admission',receiverBlockId:'Reservations',interfaceId:'edge-0',requirementIds:['seat-once']},
     {sender:'Reservations',receiver:'Box office',action:'Accepted or unavailable',messageKind:'result',senderBlockId:'Reservations',receiverBlockId:'Admission',interfaceId:'edge-0',requirementIds:['seat-once']},
     {sender:'Reservations',receiver:'Payments',action:'SeatHeld',messageKind:'event',senderBlockId:'Reservations',receiverBlockId:'Payments',interfaceId:'edge-1',requirementIds:['seat-once']},
   ]}]};
 project.needs=[{id:'seat-once',statement:'Allocate a seat at most once.',links:['Seat holds'],acceptance:'A concurrent race has one winner.'}];
 await page.goto(base);
 const invalid=await page.evaluate(async()=>{
   const {validateCapturedDiagrams}=await import('/src/captured-diagrams.mjs');
   try{await validateCapturedDiagrams({files:[{path:'specs/broken.md',content:'```mermaid\nsequenceDiagram\nUnexpected invalid syntax\n```\n'}]});return null;}
   catch(error){return {message:error.message,diagnostic:error.canvasDiagnostic};}
 });
 assert.match(invalid.message,/captured diagram is invalid/);
 assert.match(invalid.diagnostic,/specs\/broken.md#mermaid-1/);
 await page.locator('#project-file-input').setInputFiles({name:'theatre.atmem-ai-architect.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(toProjectFile(project)))});
 const read=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));
 await page.getByRole('combobox',{name:'Architecture level'}).waitFor();
 await page.getByRole('combobox',{name:'Architecture level'}).selectOption('');
 const before=await read();
 assert.equal(await page.locator('.react-flow__node').count(),1);
 await page.getByRole('button',{name:'Explore 4 subsystems →',exact:true}).click();
 assert.equal(await page.getByRole('combobox',{name:'Architecture level'}).inputValue(),'Theatre');
 try{await page.waitForFunction(()=>{
   const flow=document.querySelector('.react-flow')?.getBoundingClientRect(),surface=document.querySelector('.board-surface')?.getBoundingClientRect();
   const frame=flow&&surface?{left:Math.max(flow.left,surface.left),right:Math.min(flow.right,surface.right),top:Math.max(flow.top,surface.top),bottom:Math.min(flow.bottom,surface.bottom)}:null;
   const nodes=[...document.querySelectorAll('.react-flow__node')];
   return frame&&nodes.length===4&&nodes.every(node=>{const box=node.getBoundingClientRect();return box.width>=180&&box.left>=frame.left-1&&box.right<=frame.right+1&&box.top>=frame.top-1&&box.bottom<=frame.bottom+1;});
 });}catch(error){console.log('Visible canvas bounds',await page.evaluate(()=>({flow:document.querySelector('.react-flow')?.getBoundingClientRect().toJSON(),surface:document.querySelector('.board-surface')?.getBoundingClientRect().toJSON(),nodes:[...document.querySelectorAll('.react-flow__node')].map(node=>({id:node.dataset.id,rect:node.getBoundingClientRect().toJSON()}))})));await page.screenshot({path:'/tmp/atmem-context-fit-failure.png'});throw error;}
 await page.getByRole('button',{name:'Toggle components and layers'}).click();
 await page.waitForFunction(()=>{
   const flow=document.querySelector('.react-flow')?.getBoundingClientRect(),surface=document.querySelector('.board-surface')?.getBoundingClientRect();
   return flow&&surface&&flow.right<=surface.right+1&&flow.left>=surface.left;
 });
 await page.getByRole('button',{name:'Toggle components and layers'}).click();
 await page.getByRole('combobox',{name:'Architecture level'}).selectOption('Reservations');
 await page.evaluate(()=>document.activeElement.blur());
 await page.keyboard.press('Escape');
 assert.equal(await page.getByRole('combobox',{name:'Architecture level'}).inputValue(),'Theatre');
 await page.keyboard.press('ControlOrMeta+a');
 await page.keyboard.press('Delete');
 assert.equal((await read()).nodes.length,project.nodes.length,'Collapsed projections must preserve hidden descendants');
 await page.getByRole('combobox',{name:'Architecture level'}).selectOption('*');
 assert.equal(await page.locator('.react-flow__node').count(),project.nodes.length);
 await page.getByRole('button',{name:'Toggle components and layers'}).click();
 await page.getByRole('navigation',{name:'Component tree'}).getByRole('button',{name:'Seat holds',exact:true}).click();
 await page.getByText('Block Spec Kit',{exact:true}).click();
 const hierarchy=page.getByRole('navigation',{name:'Block hierarchy'});
 assert.match(await hierarchy.innerText(),/Theatre[\s\S]*Reservations[\s\S]*Seat holds/);
 assert.equal(await page.locator('.module-spec-card').count(),8);
 assert.equal(await page.getByLabel('Block contents').getByText('8/8 spec sections documented',{exact:true}).count(),1);
 await page.getByRole('button',{name:'Prepare agent handoff',exact:true}).click();
 assert.ok(await page.getByRole('region',{name:'Module agent handoff'}).isVisible());
 const downloadPending=page.waitForEvent('download');
 await page.getByRole('button',{name:'Download agent handoff',exact:true}).click();
 const download=await downloadPending;
 const archive=unzipSync(fs.readFileSync(await download.path()));
 const manifest=JSON.parse(strFromU8(archive['handoff-manifest.json']));
 assert.equal(manifest.blockId,'Seat holds');
 assert.deepEqual(manifest.blockIds,['Seat holds']);
 assert.equal(manifest.implementationExecuted,false);
 assert.equal(manifest.deploymentExecuted,false);
 const behaviorReport=JSON.parse(strFromU8(archive['spec-kit/architecture-consistency.json']));assert.equal(behaviorReport.counts.errors,0);assert.equal(behaviorReport.counts.classified,3);assert.equal(behaviorReport.counts.interfaceBound,3);
 for(const [name,receipt] of Object.entries(manifest.files)){
  assert.ok(archive[name],name+' must be included');
  assert.equal(hash(archive[name]),receipt.sha256,name+' digest');
  assert.equal(archive[name].length,receipt.bytes,name+' length');
 }
 assert.equal(hash(archive['source-context.json']),manifest.sourceSha256);
 assert.match(strFromU8(archive['AGENT_PROMPT.md']),/destination repository/);
 assert.match(strFromU8(archive['READ_ME_FIRST.md']),/Seat holds/);
 console.log('Offline external handoff ZIP: scoped kit, exact source and every file digest verified.');
 await page.context().grantPermissions(['clipboard-read','clipboard-write']);
 await page.getByRole('button',{name:'Copy agent prompt',exact:true}).click();
 await page.getByText('Agent prompt copied. Give it the handoff ZIP.',{exact:true}).waitFor();
 assert.match(await page.evaluate(()=>navigator.clipboard.readText()),/block \"Seat holds\"/);

 if(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR){fs.mkdirSync(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR,{recursive:true});await page.getByRole('region',{name:'Module agent handoff'}).scrollIntoViewIfNeeded();await page.screenshot({path:path.join(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR,'agent-handoff-desktop.png')});}

 await page.getByRole('navigation',{name:'Module details'}).getByRole('button',{name:'Specification',exact:true}).click();
 if(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR){fs.mkdirSync(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR,{recursive:true});await page.locator('.block-build-spec').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR,'spec-desktop.png')});}
 await page.getByRole('navigation',{name:'Module details'}).getByRole('button',{name:'Diagrams',exact:true}).click();
 await page.getByText('Last seat race',{exact:true}).click();
 const diagram=page.locator('.scenario-diagram');
 for(const view of ['sequence','functional','events']){
   await diagram.getByLabel('Diagram view').selectOption(view);
   await diagram.locator('img').waitFor();
   assert.ok(await diagram.locator('img').evaluate(async image=>{await image.decode();return image.naturalWidth>0&&image.naturalHeight>0;}));
 }
 assert.ok((await diagram.boundingBox()).width>800,'Module diagrams must use the workspace width');
 if(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR){fs.mkdirSync(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR,{recursive:true});await diagram.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR,'module-desktop.png')});}
 await page.setViewportSize({width:650,height:900});
 await diagram.scrollIntoViewIfNeeded();
 assert.ok((await diagram.boundingBox()).width>200);
 if(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR,'module-mobile.png')});
 await page.getByRole('navigation',{name:'Module details'}).getByRole('button',{name:'Specification',exact:true}).click();
 assert.ok(await page.locator('.module-spec-card').evaluateAll(cards=>cards.every(card=>{const box=card.getBoundingClientRect();return box.left>=0&&box.right<=innerWidth;})),'Specification cards must fit the mobile viewport');
 await page.getByRole('button',{name:'Hide chat',exact:true}).click();
 await page.locator('.module-overview').evaluate(element=>element.scrollIntoView({block:'start'}));
 assert.ok(await hierarchy.evaluate(element=>element.getBoundingClientRect().top>=document.querySelector('.detail-navigation').getBoundingClientRect().bottom),'Hierarchy must stay below the sticky back control');
 if(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.ATMEM_WORKFLOW_SCREENSHOT_DIR,'spec-mobile.png')});
 await hierarchy.getByRole('button',{name:'Reservations',exact:true}).click();
 await page.getByRole('region',{name:'Block detail',exact:true}).getByRole('heading',{name:'Reservations',exact:true}).waitFor();
 await hierarchy.getByRole('button',{name:'Theatre',exact:true}).click();
 await page.getByRole('region',{name:'Block detail',exact:true}).getByRole('heading',{name:'Theatre',exact:true}).waitFor();
 const after=await read();
 assert.equal(after.revision,before.revision);
 assert.deepEqual(after.nodes,before.nodes);
 assert.deepEqual(after.edges,before.edges);
 assert.equal(executionRequests,0,'Offline handoff must never start a coding/model session');
 assert.deepEqual(errors,[]);
 console.log('Nested theatre canvas, three rendered diagram views, responsive module workspace and unchanged source graph passed.');
}finally{await browser.close();fs.rmSync(temporary,{recursive:true,force:true});}
