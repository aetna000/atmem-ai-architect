// Real frontend, synthetic transport/project only. Never writes owner projects or calls a model.
import fs from 'node:fs';import assert from 'node:assert/strict';import {chromium}from '@playwright/test';import {toProjectFile}from '../../src/project-file.mjs';
const base=process.argv[2]||'http://127.0.0.1:5297',out=process.argv[3]||'.local/external-artifacts/review-clarity/v1/browser';fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'}),errors=[],calls=[];let emulationCalls=0,enabled=true;
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.1-sol',effort:'high'}));localStorage.setItem('atforma-draw-live','off')});
 const memory=()=>({enabled,status:enabled?'ready':'disabled',pending:0,rejected:0,engine:'AtMem 2.3.10 core SDK',policy:'Synthetic fixture transport',profile:[],project:[],knowledge:[],skills:[],activity:[],events:[]});
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  if(path==='/api/session')return route.fulfill({json:{token:'fixture',status:'local-sidecar',engineeringEnabled:true,providers:{codex:{available:true,installed:true,signedIn:true}}}});
  if(path==='/api/projects/save')return route.fulfill({json:{saved:true,sha256:'a'.repeat(64),memory:memory()}});
  if(path==='/api/memory/settings'){enabled=route.request().postDataJSON().enabled;return route.fulfill({json:memory()})}
  if(path.startsWith('/api/memory/'))return route.fulfill({json:memory()});
  if(path==='/api/emulation/run'){emulationCalls++;return route.fulfill({status:500,json:{detail:'Known missing implementation should not run'}})}
  if(path==='/api/architect'){const body=route.request().postDataJSON();calls.push(body);return route.fulfill({json:{message:'Monitoring needs implementation. I will propose a monitoring design and identify its alert owner.',phase:'Architecture',followUp:null}})}
  if(path==='/api/engineering/list')return route.fulfill({json:{sessions:[]}});
  return route.fulfill({json:{projects:[],bin:[],models:[],saved:true,status:'disabled'}});
 });
 const node=(id,label,x,role)=>({id,type:'resource',position:{x,y:100},data:{label,description:'An existing system with a clear responsibility.',kind:'resource',provider:'tools',origin:'existing',role,config:{region:'External client',classification:'Public'}}});
 const project={id:'review-clarity-fixture',version:1,revision:1,name:'Review clarity fixture',provider:'tools',nodes:[node('model','AI model',0,'llm'),node('client','Existing client',330,'app')],edges:[{id:'request',source:'client',target:'model',label:'Request'}]};
 await page.goto(base+'/');await page.locator('#project-file-input').setInputFiles({name:'review.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(toProjectFile(project)))});
 const memoryButton=page.getByRole('button',{name:'AtMem memory',exact:true});await memoryButton.waitFor();await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.getAttribute('aria-label')==='AtMem memory'&&b.textContent.includes('AtMem on')));
 await memoryButton.click();await page.getByRole('heading',{name:'AtMem dashboard'}).waitFor();await page.getByRole('button',{name:'Turn memory off',exact:true}).click();await page.getByRole('button',{name:'Turn memory on',exact:true}).waitFor();await page.getByRole('button',{name:'Close dialog',exact:true}).click();assert.match(await memoryButton.innerText(),/AtMem off/);
 await page.getByRole('button',{name:/Review AI model: \d+ design issues?$/,exact:false}).click();const panel=page.getByRole('region',{name:'Block design review'});await panel.getByText('No monitoring for model quality or drift.',{exact:true}).waitFor();
 const issue=panel.locator('li').filter({hasText:'No monitoring for model quality or drift.'});assert.equal(await issue.getByText('Design issue',{exact:true}).count(),1);assert.match(await issue.innerText(),/Suggested next step: Add a monitoring block/);assert.equal(await panel.getByRole('button',{name:'Looks good',exact:true}).isDisabled(),true);
 await issue.getByRole('button',{name:'Ask Architect to plan this fix',exact:true}).click();await page.getByText('Monitoring needs implementation.',{exact:false}).waitFor();assert.equal(calls.length,1);assert.equal(calls[0].origin,'workflow');assert.match(calls[0].message,/No monitoring for model quality or drift/);assert.match(calls[0].message,/propose the design changes/);
 await page.getByText('Design draft tools',{exact:true}).click();
 await page.getByRole('button',{name:'Prepare local tests',exact:true}).click();const checks=page.getByRole('complementary',{name:'Local checks',exact:true});await checks.getByRole('heading',{name:'Application code is needed before testing',exact:true}).waitFor();assert.equal(await checks.getByRole('button',{name:'Run local checks',exact:true}).isDisabled(),true);assert.equal(await checks.getByRole('button',{name:'Implement and check',exact:true}).count(),1);assert.equal(emulationCalls,0);
 await page.screenshot({path:out+'/desktop.png'});await page.setViewportSize({width:390,height:844});await page.screenshot({path:out+'/mobile.png'});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);assert.deepEqual(errors,[]);
 const receipt={base,monitoringFindingClassifiedAsIssue:true,focusedFixDispatched:true,knownMissingTestBlocked:true,clearImplementationNextStep:true,visibleAtMemControl:true,optOutStatusUpdated:true,desktopMobileNoPageErrors:true,modelRequests:0,ownerProjectWrites:0,transport:'Synthetic API fixture; actual frontend interactions',emulationCalls};fs.writeFileSync(out+'/receipt.json',JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
}finally{await browser.close()}
