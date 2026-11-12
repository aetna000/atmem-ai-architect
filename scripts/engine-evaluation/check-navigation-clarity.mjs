// Real frontend, synthetic transport/project only. Never writes owner projects or calls a model.
import fs from 'node:fs';import assert from 'node:assert/strict';import {chromium}from '@playwright/test';import {toProjectFile}from '../../src/project-file.mjs';
const base=process.argv[2]||'http://127.0.0.1:5297',out=process.argv[3]||'.local/external-artifacts/navigation-clarity/v1/browser';fs.mkdirSync(out,{recursive:true});
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
 const project={id:'navigation-fixture',version:1,revision:1,name:'Navigation fixture',provider:'tools',requirements:'Keep the existing catalogue unchanged.',nodes:[{id:'catalogue',type:'resource',position:{x:0,y:0},data:{label:'Existing catalogue',description:'Read-only public catalogue',kind:'resource',provider:'tools',origin:'existing',config:{region:'External'}}}],edges:[]};
 await page.goto(base+'/');await page.locator('#project-file-input').setInputFiles({name:'navigation.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(toProjectFile(project)))});
 const map=page.locator('.journey-map');
 async function visit(label,index){
  if(await map.getAttribute('open')===null)await map.locator('summary').click();
  const button=map.getByRole('button',{name:'Go to '+label,exact:true});assert.equal(await button.locator('span').innerText(),String(index));await button.click();
  assert.equal(await map.locator('summary').innerText(),label);assert.equal((await map.locator('li[aria-current="page"]').textContent()).replace(/\s+/g,''),(String(index)+label).replace(/\s+/g,''));
 }
 const sections=['Board','Requirements','Choices','Country & region','Infrastructure','Review','Costs','Delivery'];
 for(const [i,label] of sections.entries()){
  await visit(label,i+1);
  if(label==='Board')await page.locator('.react-flow').waitFor();
  if(label==='Requirements')await page.getByRole('heading',{name:/Requirements/}).first().waitFor();
  if(label==='Choices'){await page.getByRole('heading',{name:'Choices',exact:true}).waitFor();await page.getByRole('heading',{name:'Choices we’ve made',exact:true}).waitFor();assert.equal(await page.getByRole('tab',{name:'Design choices',exact:true}).count(),0);}
  if(label==='Country & region'){const region=page.getByRole('region',{name:'Country and region'});await region.waitFor();assert.match(await region.innerText(),/Not yet agreed/);}
  if(label==='Infrastructure')await page.getByRole('heading',{name:'Terraform deployment draft',exact:true}).waitFor();
  if(label==='Delivery')await page.getByRole('heading',{name:'Outputs',exact:true}).waitFor();
 }
 await visit('Choices',3);await page.screenshot({path:out+'/choices-desktop.png'});await page.setViewportSize({width:390,height:844});await visit('Country & region',4);await page.screenshot({path:out+'/region-mobile.png'});const overflow=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,elements:[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1&&getComputedStyle(e).position!=='absolute').slice(0,12).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right,text:e.textContent.slice(0,90)}))}));if(overflow.scroll>overflow.width+1)console.log(JSON.stringify(overflow));assert.equal(overflow.scroll>overflow.width+1,false);
 await visit('Board',1);assert.deepEqual(errors,[]);assert.equal(calls.length,0);assert.equal(emulationCalls,0);
 const receipt={base,sections,navigationRequestsToModel:0,emulationCalls,ownerProjectWrites:0,matchingNumbersAndDestinations:true,combinedChoices:true,unknownLocationsPreserved:true,noPageErrors:true,mobileNoOverflow:true,transport:'Synthetic API fixture; actual frontend interactions; completion gates unchanged'};fs.writeFileSync(out+'/receipt.json',JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
}finally{await browser.close()}
