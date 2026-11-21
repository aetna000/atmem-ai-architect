// Whole-app UI fixture. No native inference, real pricing or cloud operation.
import {chromium} from '@playwright/test';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {toProjectFile} from '../src/project-file.mjs';
const out=process.env.ATMEM_UI_EVIDENCE_DIR||'.local/external-artifacts/five-stage-journey';fs.mkdirSync(out,{recursive:true});
const socket=createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));
const base=`http://127.0.0.1:${port}`,server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'ignore',env:{...process.env,ATMEM_ARCHITECT_VITE_CACHE_DIR:`${out}/vite-cache`}});
const original={id:'ui-source-project',version:1,revision:1,name:'Existing service',provider:'tools',requirements:'Keep the existing API.',nodes:[{id:'api',position:{x:0,y:0},data:{kind:'resource',provider:'tools',origin:'existing',label:'Existing API',description:'Preserve client ownership.',config:{region:'Local'}}}],edges:[],needs:[],decisions:[]};
let browser;
try{
 for(let i=0;i<60;i++){try{if((await fetch(base)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true});
 for(const width of [1440,390]){
  const page=await browser.newPage({viewport:{width,height:1000}});page.setDefaultTimeout(15000);const errors=[],architect=[],native=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(project=>{localStorage.setItem('atforma-workspace-v3',JSON.stringify(project));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'exact-model',effort:'high'}));},original);
  await page.route('**/api/**',route=>{
   const url=route.request().url(),data=route.request().postDataJSON();
   if(url.endsWith('/api/memory/inspect'))return route.fulfill({json:{enabled:true,status:'ready',engine:'fixture',pending:0,rejected:0,policy:'Fixture',profile:[],project:[],skills:[],activity:[]}});
   if(url.endsWith('/api/architect')){architect.push(data);return route.fulfill({json:{message:'I read the uploaded requirements. Which users should have access?',contextUsed:[]}});}
   if(/\/engineering\/(create|start|steer)$/.test(url))native.push(url);
   return route.fulfill({json:url.endsWith('/api/session')?{token:'fixture',engineeringEnabled:true,status:'local-sidecar',providers:{codex:{installed:true,available:true,signedIn:true}}}:url.endsWith('/engineering/list')?{sessions:[]}:url.endsWith('/engineering/delivery')?{artifact:null,canPackage:false}:{status:'disabled',enabled:false,projects:[],bin:[],saved:true}});
  });
  await page.goto(base);await page.getByRole('tab',{name:'Board',exact:true}).waitFor();
  assert.equal(await page.getByRole('tablist',{name:'Project stages'}).getByRole('tab').count(),5);
  assert.equal(await page.locator('.bar').getByRole('tab').count(),0);
  assert.equal(await page.locator('.bar').getByText('Components',{exact:true}).count(),0);
  await page.getByRole('button',{name:'Toggle components and layers'}).click();await page.getByRole('navigation',{name:'Component tree'}).waitFor();
  await page.screenshot({path:`${out}/board-${width}.png`});
  const treeBox=await page.getByRole('complementary',{name:'Board components'}).boundingBox(),flowBox=await page.locator('.react-flow').boundingBox();assert.ok(flowBox.x>=treeBox.x+treeBox.width-1,'expanded sidebar reserves canvas space');
  await page.locator('.react-flow__node').first().dblclick();await page.getByRole('region',{name:'Block detail'}).waitFor();
  assert.equal(await page.getByRole('complementary',{name:'Board components'}).count(),0,'component navigation cannot cover block detail controls');
  await page.screenshot({path:`${out}/block-detail-${width}.png`});
  await page.getByRole('button',{name:'Back to the board',exact:true}).click();
  await page.getByRole('button',{name:'Toggle components and layers'}).waitFor();
  for(const name of ['Requirements','Choices','Review','Delivery','Board'])await page.getByRole('tab',{name,exact:true}).click();
  assert.equal(architect.length,0);assert.equal(native.length,0);
  await page.getByRole('tab',{name:'Choices',exact:true}).click();await page.getByRole('heading',{name:'Country & region',exact:true}).waitFor();
  await page.getByRole('tab',{name:'Review',exact:true}).click();await page.getByRole('heading',{name:'Generate and verify'}).waitFor();
  await page.getByText('Costs and usage assumptions',{exact:true}).click();await page.getByRole('button',{name:'Medium',exact:true}).waitFor();
  await page.screenshot({path:`${out}/review-${width}.png`});
  assert.equal(architect.length,0);assert.equal(native.length,0);
  await page.getByRole('tab',{name:'Requirements',exact:true}).click();
  await page.locator('#requirements-file-input').setInputFiles({name:'requirements.md',mimeType:'text/markdown',buffer:Buffer.from('Preserve the existing API. Users need a searchable catalogue.')});
  await page.getByText('I read the uploaded requirements. Which users should have access?',{exact:true}).waitFor();
  assert.equal(architect.length,1);assert.equal(architect[0].attachments[0].name,'requirements.md');assert.equal(architect[0].model,'exact-model');assert.equal(architect[0].effort,'high');assert.equal(native.length,0);
  await page.getByRole('button',{name:'Open saved project file',exact:true}).click();
  await page.getByRole('button',{name:'Start a new project from a saved file',exact:true}).click({noWaitAfter:true});
  await page.locator('#project-file-input').setInputFiles({name:'saved-project.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(toProjectFile(original)))});
  await page.waitForFunction(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')).name==='Existing service (copy)');
  const copied=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));assert.notEqual(copied.id,original.id);assert.equal(copied.requirements,original.requirements);
  await page.getByRole('tab',{name:'Delivery',exact:true}).click();
  await page.getByText('Design draft: requirements, Spec Kit and infrastructure',{exact:true}).click();
  await page.getByRole('button',{name:'manifest.json',exact:true}).waitFor();await page.getByRole('button',{name:'manifest.json',exact:true}).click();
  assert.ok(await page.locator('.output-preview .code-string').count()>0);
  assert.equal(await page.getByRole('button',{name:/Download.*ZIP/}).count(),0,'no captured implementation means no final package yet');
  assert.equal(await page.getByRole('button',{name:'Go to Review',exact:true}).count(),1);
  for(const theme of ['light','dark']){
   await page.evaluate(theme=>document.documentElement.dataset.theme=theme,theme);
   async function contrast(selector,pseudo=null){return page.locator(selector).first().evaluate((el,pseudo)=>{
    const style=getComputedStyle(el,pseudo),rgb=text=>{const nums=text.match(/[\d.]+/g).map(Number);return nums.slice(0,3).map(n=>{const s=n/255;return s<=.04045?s/12.92:((s+.055)/1.055)**2.4});},lum=text=>{const c=rgb(text);return .2126*c[0]+.7152*c[1]+.0722*c[2];};
    let bg=el;while(bg&&getComputedStyle(bg).backgroundColor==='rgba(0, 0, 0, 0)')bg=bg.parentElement;
    const foreground=lum(style.color),background=lum(getComputedStyle(bg||document.documentElement).backgroundColor);return (Math.max(foreground,background)+.05)/(Math.min(foreground,background)+.05);
   },pseudo);}
   for(const selector of ['.bar .projects-btn','.code-preview .code-key','.code-preview .code-string','.code-preview .code-number'])assert.ok(await contrast(selector)>=4.5,`${theme}: ${selector} contrast`);
   await page.getByRole('button',{name:'More',exact:true}).click();await page.getByRole('menuitem',{name:'AtMem dashboard'}).click();
   await page.getByLabel('Remember about me',{exact:true}).waitFor();
   for(const [selector,pseudo]of [['.memory-panel select',null],['.memory-panel textarea','::placeholder'],['.memory-profile button:disabled',null]])assert.ok(await contrast(selector,pseudo)>=4.5,`${theme}: ${selector} contrast`);
   await page.screenshot({path:`${out}/memory-${theme}-${width}.png`});await page.getByRole('button',{name:'Close dialog'}).click();
   await page.screenshot({path:`${out}/code-${theme}-${width}.png`});
  }
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.deepEqual(errors,[]);console.log(JSON.stringify({width,stages:5,noInferenceOnNavigation:true,uploadDelivered:true,copyPreservesSource:true,highlightedJSON:true,contrastBothThemes:true,noSidebarDetailOverlap:true,errors}));await page.close();
 }
}finally{await browser?.close();server.kill('SIGTERM');}
