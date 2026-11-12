// Real frontend, synthetic transport/project only. Never writes owner projects or calls a model.
import {validateImport} from '../../src/core.mjs';import {journeyKeys} from '../../src/journey.mjs';import fs from 'node:fs';import assert from 'node:assert/strict';import {chromium}from '@playwright/test';import {toProjectFile}from '../../src/project-file.mjs';
const base=process.argv[2]||'http://127.0.0.1:5297',out=process.argv[3]||'.local/external-artifacts/board-flow/v1/browser';fs.mkdirSync(out,{recursive:true});
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
 const project={id:'board-flow-fixture',version:1,revision:1,name:'Board flow fixture',provider:'tools',requirements:'Keep the existing catalogue unchanged.',nodes:[{id:'catalogue',type:'resource',position:{x:0,y:0},data:{label:'Existing catalogue',description:'Read-only public catalogue',kind:'resource',provider:'tools',origin:'existing',config:{}}}],edges:[]};
 async function load(value){await page.locator('#project-file-input').setInputFiles({name:'flow.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(toProjectFile(value)))});await page.getByRole('tab',{name:'Board',exact:true}).click()}
 await page.goto(base+'/');await load(project);const toolbar=page.getByRole('region',{name:'Architecture journey',exact:true});
 assert.equal(await toolbar.locator('.btn.primary').count(),1);assert.equal(await toolbar.getByRole('button',{name:'Download',exact:true}).count(),0);assert.equal(await toolbar.getByRole('button',{name:'Deploy (under development)',exact:true}).count(),0);
 await toolbar.getByRole('button',{name:'Review requirements',exact:true}).click();await page.getByRole('heading',{name:/Requirements/}).first().waitFor();assert.equal(calls.length,0);
 assert.equal(await page.evaluate(()=>!!JSON.parse(localStorage.getItem('atforma-workspace-v3')).extensions?.journey?.scope),false);
 await toolbar.getByRole('button',{name:'Continue to cloud options',exact:true}).click();await page.getByRole('heading',{name:'Choices',exact:true}).waitFor();await page.waitForFunction(()=>document.querySelectorAll('.msg.assistant').length>=2);assert.equal(calls.length,1);assert.match(calls[0].message,/Compare AWS/);
 await page.getByRole('button',{name:'More',exact:true}).click();await page.getByRole('menuitem',{name:'Save project backup (JSON)',exact:true}).waitFor();assert.equal(await page.getByRole('menuitem',{name:'Download delivery pack',exact:true}).count(),0);await page.getByRole('menuitem',{name:'Delivery',exact:true}).click();await page.getByRole('heading',{name:'Delivery',exact:true}).waitFor();assert.equal(calls.length,1);
 const costs=validateImport({...project,id:'board-cost-fixture',name:'Cost review fixture',nodes:[{id:'store',type:'resource',position:{x:0,y:0},data:{label:'Amazon S3',service:'Amazon S3',description:'Private catalogue storage',kind:'source',provider:'aws',origin:'proposed',config:{region:'ap-southeast-2'}}}],decisions:[{id:'cloud',subject:'platform.cloud',decision:'aws',status:'Accepted'},{id:'country',subject:'data.country',decision:'Australia',status:'Accepted'}]});
 const keys=journeyKeys(costs);costs.extensions={journey:{scope:keys.scope,architecture:keys.architecture,review:keys.architecture}};
 await load(costs);assert.equal(await toolbar.locator('.btn.primary').count(),1);await toolbar.getByRole('button',{name:'Review costs',exact:true}).click();assert.equal(calls.length,1);
 await toolbar.getByRole('button',{name:'Prepare a delivery draft with cost gaps noted',exact:true}).click();await page.getByRole('heading',{name:'Delivery',exact:true}).waitFor();assert.equal(calls.length,1,'opening the prepared handoff does not call an obsolete delivery model prompt');
 await page.getByRole('tab',{name:'Board',exact:true}).click();await toolbar.getByRole('button',{name:'Review delivery',exact:true}).waitFor();assert.equal(await toolbar.locator('.btn.primary').count(),1);assert.equal(await toolbar.getByRole('button',{name:'Delivery',exact:true}).count(),0,'one delivery destination action when it is the primary next step');
 await page.screenshot({path:out+'/board-desktop.png'});await page.setViewportSize({width:390,height:844});await page.screenshot({path:out+'/board-mobile.png'});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);assert.deepEqual(errors,[]);
 const receipt={base,onePrimaryAction:true,scopeReviewBeforeAcknowledgement:true,explicitComparisonRequest:true,noModelOnPassiveNavigation:true,deliveryUsesUnifiedView:true,backupAndExportNamesExplicit:true,mobileNoOverflow:true,ownerProjectWrites:0,modelRequests:0,transport:'Actual UI/state transitions; synthetic API and project data, one stub Architect response'};fs.writeFileSync(out+'/receipt.json',JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
}finally{await browser.close()}
