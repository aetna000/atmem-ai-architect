// Real frontend, synthetic transport/project only. Never writes owner projects or calls a model.
import {CLOUD_STORAGE_SCENARIOS} from '../../src/cloud-storage-scenarios.mjs';import fs from 'node:fs';import assert from 'node:assert/strict';import {chromium}from '@playwright/test';import {toProjectFile}from '../../src/project-file.mjs';
const base=process.argv[2]||'http://127.0.0.1:5297',out=process.argv[3]||'.local/external-artifacts/navigation-controls/v1/browser';fs.mkdirSync(out,{recursive:true});
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
  if(path==='/api/emulation/run'){emulationCalls++;return route.fulfill({json:{status:'passed',checks:[{name:'Synthetic package check',passed:true}],artifactDigest:'a'.repeat(64),designRevision:1,message:'Fixture local check passed'}})}
  if(path==='/api/architect'){const body=route.request().postDataJSON();calls.push(body);return route.fulfill({json:{message:'Monitoring needs implementation. I will propose a monitoring design and identify its alert owner.',phase:'Architecture',followUp:null}})}
  if(path==='/api/engineering/list')return route.fulfill({json:{sessions:[]}});
  return route.fulfill({json:{projects:[],bin:[],models:[],saved:true,status:'disabled'}});
 });
 const project=CLOUD_STORAGE_SCENARIOS[0].project;
 await page.goto(base+'/');await page.locator('#project-file-input').setInputFiles({name:'checks.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(toProjectFile(project)))});
 await page.getByRole('region',{name:'Architecture journey'}).getByRole('button',{name:'Run local checks',exact:true}).click();
 const panel=page.getByRole('complementary',{name:'Local checks',exact:true});await panel.getByRole('heading',{name:'Local checks passed',exact:true}).waitFor();
 assert.equal(await panel.getByRole('button',{name:'Architect mentoring',exact:true}).count(),0);
 assert.equal(await panel.getByRole('button',{name:'Download check report (JSON)',exact:true}).count(),0);
 await panel.getByRole('button',{name:'Check details and settings',exact:true}).click();
 for(const label of ['Ask Architect to explain new check results automatically','Rerun checks after an accepted correction (up to two attempts)'])assert.equal(await panel.getByRole('checkbox',{name:label,exact:true}).isChecked(),false);
 await panel.getByRole('button',{name:'Ask Architect about these results',exact:true}).click();const composer=page.getByRole('textbox',{name:'Your message',exact:true});await composer.waitFor();assert.match(await composer.inputValue(),/Help me understand these local check results/);
 await composer.fill('Keep this unsent question intact.');await panel.getByRole('button',{name:'Ask Architect about these results',exact:true}).click();assert.equal(await composer.inputValue(),'Keep this unsent question intact.');
 const downloadEvent=page.waitForEvent('download');await panel.getByRole('button',{name:'Download check report (JSON)',exact:true}).click();const download=await downloadEvent;assert.match(download.suggestedFilename(),/^atmem-local-checks-r1.json$/);const report=JSON.parse(fs.readFileSync(await download.path(),'utf8'));assert.equal(report.artifactDigest,'a'.repeat(64));assert.equal(report.checks[0].name,'Synthetic package check');
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:out+'/checks-mobile.png'});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);assert.deepEqual(errors,[]);assert.equal(calls.length,0);assert.equal(emulationCalls,1);
 const receipt={base,clearTextActions:true,assistanceOptIn:true,questionOpensComposer:true,existingDraftPreserved:true,jsonReportNamedAndBehindDetails:true,reportArtifactPreserved:true,modelRequests:0,ownerProjectWrites:0,emulationCalls,transport:'Synthetic check/API service; real frontend and download'};fs.writeFileSync(out+'/receipt.json',JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
}finally{await browser.close()}
