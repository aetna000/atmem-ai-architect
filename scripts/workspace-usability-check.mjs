// Independent UI check using synthetic archive data. No model, account or cloud calls.
import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {emptyDiagramModel,addDiagram} from '../src/architecture-diagrams.mjs';
const base=process.argv[2]||'http://127.0.0.1:5199';
if(!['127.0.0.1','localhost'].includes(new URL(base).hostname))throw Error('Use an isolated loopback preview.');
const out=process.env.WORKSPACE_EVIDENCE||'.local/workspace-usability';fs.mkdirSync(out,{recursive:true});
let model=addDiagram(emptyDiagramModel(),'context','Archive context',true).model;
model=addDiagram(model,'sequence','Archive review sequence',true).model;
const nodes=Array.from({length:22},(_,i)=>({id:'archive-'+i,position:{x:(i%5)*300,y:Math.floor(i/5)*200},data:{label:'Archive component '+i,kind:'resource',provider:'tools',description:'Preserve collection item '+i,...(i>0&&i<10?{parentBlockId:'archive-0'}:{})}}));
const edge={id:'archive-request',source:'archive-4',target:'archive-12',type:'smoothstep',label:'Catalogue request',interfaceSpec:{transport:'HTTPS 1.1',input:'Collection request JSON',output:'Catalogue result JSON',authorization:'Assigned archive role',failure:'Retry with a stable request identifier',verification:'Accept authorized requests and reject missing identity'}};
const project={version:1,revision:1,id:'workspace-usability-check',name:'Archive workspace',provider:'tools',nodes,edges:[edge],extensions:{architectureDiagrams:model}};
const browser=await chromium.launch(process.env.ATMEM_ARCHITECT_BROWSER_BIN?{executablePath:process.env.ATMEM_ARCHITECT_BROWSER_BIN}:{});const errors=[],checks=[];
try{
 const page=await browser.newPage({viewport:{width:1512,height:945}});page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(project=>{localStorage.setItem('atforma-workspace-v3',JSON.stringify(project));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'default',effort:'medium'}));},project);
 await page.route('**/api/**',r=>{const path=new URL(r.request().url()).pathname;return r.fulfill({json:path==='/api/session'?{token:'synthetic-session',providers:{codex:{available:true}},memory:{enabled:false}}:path==='/api/projects/list'?{projects:[]}:path==='/api/projects/save'?{saved:true}:path.includes('/memory/')?{enabled:false,status:'disabled'}:{sessions:[],artifacts:[],checks:[]}})});
 await page.goto(base);const open=page.getByRole('button',{name:'Open drawings',exact:true});if(await open.count())await open.click();
 const tabs=page.getByRole('tablist',{name:'Workspace library'});await tabs.waitFor();
 for(const name of ['Shapes','Blocks','Layers','Pages']){
  const tab=tabs.getByRole('tab',{name,exact:true});const style=await tab.evaluate(e=>{const s=getComputedStyle(e);return {border:s.borderTopWidth,radius:parseFloat(s.borderTopLeftRadius),width:e.getBoundingClientRect().width,scroll:e.scrollWidth}});
  assert.ok(parseFloat(style.border)>=1&&style.radius>=8,name+' has a visible rounded tab boundary');
  assert.ok(style.scroll<=style.width+1,name+' tab fits its label');
 }
 await tabs.getByRole('tab',{name:'Shapes',exact:true}).focus();await page.keyboard.press('ArrowRight');await expect(tabs.getByRole('tab',{name:'Blocks',exact:true})).toHaveAttribute('aria-selected','true');
 await page.keyboard.press('ArrowRight');await expect(tabs.getByRole('tab',{name:'Layers',exact:true})).toHaveAttribute('aria-selected','true');checks.push('rounded tabs and keyboard navigation');
 await page.evaluate(()=>{window.__busySeen=false;new MutationObserver(()=>{if(document.querySelector('.nested-blocks button[aria-busy=true] .layer-spinner'))window.__busySeen=true;}).observe(document.body,{subtree:true,attributes:true,childList:true});});
 const layer=page.locator('.studio-layers').getByRole('button',{name:'Archive component 4',exact:true});const start=Date.now();await layer.click();
 await page.waitForFunction(()=>document.querySelector('.nested-blocks button[aria-current=true]')?.textContent.includes('Archive component 4')&&!document.querySelector('.studio-layers[aria-busy=true]'));
 const layerSelectionMs=Date.now()-start;
 assert.equal(await page.evaluate(()=>window.__busySeen),true,'Layer shows progress before work finishes');
 assert.equal(await layer.getAttribute('aria-current'),'true');
 const canvas=page.locator('.drawio-canvas:visible').last();const target=canvas.locator('[data-cell-kind=vertex][data-record-id=archive-4]');await target.waitFor();
 await target.evaluate(e=>window.__selectedShape=e);await target.click();await page.waitForTimeout(300);
 assert.equal(await page.evaluate(()=>window.__selectedShape.isConnected),true,'Selecting does not rebuild the scene');
 assert.ok(await canvas.locator('[data-transform-handle]').count()>0,'Native selection handles remain');
 if(await page.getByRole('button',{name:'Show properties',exact:true}).isVisible())await page.getByRole('button',{name:'Show properties',exact:true}).click();
 await page.getByRole('group',{name:'Drawing details'}).getByRole('button',{name:'Properties',exact:true}).click();
 const properties=page.getByRole('complementary',{name:'Selected diagram record'});await properties.waitFor();
 const code=properties.getByRole('button',{name:'Mermaid',exact:true});if(await code.count())await code.click();
 assert.ok(await canvas.locator('[data-transform-handle]').count()>0,'Inspecting properties keeps the selection');
 checks.push({layerSelectionMs,loading:true,selectionPreserved:true,geometryReused:true});
 await page.getByRole('button',{name:/^Connections/}).filter({visible:true}).click();
 const beforeEdge=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')).edges.find(e=>e.id==='archive-request'));
 await page.getByRole('button',{name:'Edit connection 1',exact:true}).filter({visible:true}).click();
 const editor=page.getByRole('dialog',{name:'edit-board-connection',exact:true});await editor.waitFor();
 await editor.getByLabel('Interface name',{exact:true}).fill('Catalogue item request');
 await editor.getByLabel('Failure and retry',{exact:true}).fill('Retry only with the original request identifier.');
 await editor.getByRole('button',{name:'Save interface',exact:true}).click();await expect(editor).not.toBeVisible();
 const afterEdge=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')).edges.find(e=>e.id==='archive-request'));
 assert.equal(afterEdge.label,'Catalogue item request');assert.equal(afterEdge.interfaceSpec.failure,'Retry only with the original request identifier.');
 assert.deepEqual({...afterEdge,label:beforeEdge.label,interfaceSpec:beforeEdge.interfaceSpec},beforeEdge,'Connection editing preserves identity, endpoints and wiring metadata');
 assert.equal(afterEdge.interfaceSpec.transport,beforeEdge.interfaceSpec.transport);
 checks.push('connection label and contract editing preserve wiring and other properties');

 await page.getByRole('button',{name:'Hide drawing tools',exact:true}).click();
 const tools=page.getByRole('button',{name:'Show drawing tools',exact:true});await tools.waitFor();
 const toolbar=await tools.boundingBox();const drawing=await canvas.boundingBox();assert.ok(toolbar.y+toolbar.height<=drawing.y,'Tools stay in the single top row');
 await page.locator('.drawing-pagebar:visible').getByLabel('Go to page').selectOption('view/'+model.views[0].id);
 const header=await page.locator('.architecture-header:visible').boundingBox();assert.ok(toolbar.y+toolbar.height<=header.y,'Tools do not overlap a page header');
 for(const view of model.views){
  await page.locator('.drawing-pagebar:visible').getByLabel('Go to page').selectOption('view/'+view.id);
  const canvas=page.locator('.drawio-canvas:visible').last(),focus=page.getByLabel('Focus diagram element').filter({visible:true});
  const id=await focus.locator('option').nth(1).getAttribute('value');await focus.selectOption(id);
  const shape=canvas.locator('[data-cell-kind=vertex][data-record-id="'+id+'"]');await expect(shape).toHaveAttribute('aria-pressed','true');
  const before=await shape.boundingBox();await page.mouse.move(before.x+before.width/2,before.y+before.height/2);await page.mouse.down({button:'middle'});await page.mouse.move(before.x+before.width/2+60,before.y+before.height/2+25,{steps:5});await page.mouse.up({button:'middle'});
  await canvas.focus();await page.keyboard.down('Space');const at=await shape.boundingBox();await page.mouse.move(at.x+at.width/2,at.y+at.height/2);await page.mouse.down();await page.mouse.move(at.x+at.width/2+40,at.y+at.height/2-20,{steps:5});await page.mouse.up();await page.keyboard.up('Space');
  await expect(shape).toBeVisible();await expect(shape).toHaveAttribute('aria-pressed','true');
  assert.ok(await canvas.locator('[data-transform-handle]').count()>0,view.name+' panning keeps the selected element');
 }
 checks.push('context and sequence panning preserve selection without opening details');
 await page.screenshot({path:out+'/desktop-closed.png'});
 await tools.click();await tabs.getByRole('tab',{name:'Layers',exact:true}).click();await page.screenshot({path:out+'/desktop-tabs.png'});
 for(const width of [390,820]){
  await page.setViewportSize({width,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  const active=tabs.getByRole('tab',{name:'Layers',exact:true});await active.waitFor();assert.equal(await active.getAttribute('aria-selected'),'true');
  await page.screenshot({path:out+'/tabs-'+width+'.png'});
  await page.getByRole('button',{name:'Hide drawing tools',exact:true}).click();const closed=await tools.boundingBox(),title=await page.locator('.architecture-header:visible').boundingBox();assert.ok(closed.y+closed.height<=title.y,'Collapsed Tools have space at '+width);
  await tools.click();
 }
 checks.push('Compact Tools control and visible page selector at desktop/tablet/mobile');assert.deepEqual(errors,[]);
 fs.writeFileSync(out+'/results.json',JSON.stringify({checks,errors},null,2));console.log(JSON.stringify({checks,errors,evidence:out}));
}finally{await browser.close()}
