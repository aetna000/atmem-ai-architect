// Fixture session only; no model or cloud calls.
import fs from 'node:fs';import assert from 'node:assert/strict';import {chromium} from '@playwright/test';import {toProjectFile} from '../src/project-file.mjs';
const browser=await chromium.launch({...(process.env.ATMEM_ARCHITECT_BROWSER_BIN?{executablePath:process.env.ATMEM_ARCHITECT_BROWSER_BIN}:{})});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'claude-code',model:'default'})));
 await page.route('**/api/**',r=>r.fulfill({json:r.request().url().endsWith('/api/session')?{token:'fixture',status:'local-sidecar',providers:{}}:{status:'disabled',projects:[],bin:[],models:[],saved:true}}));
 const node=(id,label,x,group)=>({id,type:'resource',position:{x,y:100},data:{label,description:'A clearly described existing component.',kind:'resource',provider:'tools',origin:'existing',topologyGroup:group,config:{region:'External client',classification:'Public'}}});
 const project={id:'canvas-view-regression',version:1,revision:1,name:'Canvas views',provider:'tools',nodes:[node('client','Visitor',0),node('app','Application',330,'Workspace'),node('worker','Worker',660,'Workspace')],edges:[{id:'request',source:'client',target:'app',label:'Use workspace'},{id:'job',source:'app',target:'worker',label:'Run work'}]};
 const load=async p=>page.locator('#project-file-input').setInputFiles({name:'views.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(toProjectFile(p)))});
 const state=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));
 await page.goto(process.env.ATMEM_ARCHITECT_BROWSER_URL||'http://127.0.0.1:5190');
 await load(project);await page.locator('.react-flow__node-resource').first().waitFor();
 assert.equal(await page.getByRole('button',{name:'Overview',exact:true}).count(),0);
 assert.equal(await page.locator('.react-flow__node-layer').count(),0);
 const before=await state();await page.getByRole('button',{name:'Auto-arrange',exact:true}).click();
 assert.equal(await page.locator('.react-flow__node-resource').count(),3);
 const after=await state();assert.deepEqual(after.edges,before.edges);assert.deepEqual(after.nodes.map(n=>n.data),before.nodes.map(n=>n.data));
 // Escape must not send a novice user into the hidden topology projection.
 await page.locator('.react-flow__pane').first().click({position:{x:20,y:20}});await page.keyboard.press('Escape');
 assert.equal(await page.locator('.react-flow__node-resource').count(),3);assert.equal(await page.locator('.react-flow__node-layer').count(),0);
 // An old saved overview preference must reopen in the component canvas.
 await page.evaluate(()=>localStorage.setItem('atmem-canvas-view-v1:canvas-view-regression',JSON.stringify({level:'system',positions:{}})));
 await page.reload();await page.locator('.react-flow__node-resource').first().waitFor();assert.equal(await page.locator('.react-flow__node-resource').count(),3);
 assert.equal(await page.locator('.react-flow__node-layer').count(),0);
 await page.getByRole('button',{name:'Component tree',exact:true}).click();assert.equal(await page.getByRole('navigation',{name:'Component tree'}).getByRole('button').count(),4);await page.keyboard.press('Escape');
 await load({...project,id:'other-canvas-project',name:'Another project'});await page.locator('.react-flow__node-resource').first().waitFor();assert.equal(await page.locator('.react-flow__node-resource').count(),3);assert.deepEqual(errors,[]);
 if(process.env.ATMEM_ARCHITECT_SCREENSHOT)await page.screenshot({path:process.env.ATMEM_ARCHITECT_SCREENSHOT});console.log('Passed: components only; no topology switch or Escape path; old overview preferences migrate; arrangement preserves component data/connections; component navigation and project switching work.');
}finally{await browser.close()}
