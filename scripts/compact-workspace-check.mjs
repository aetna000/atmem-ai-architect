// Synthetic browser evidence only. No model work, private projects or cloud calls.
import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const base=process.argv[2]||'http://127.0.0.1:5199',out=process.env.COMPACT_EVIDENCE||'.local/compact-workspace';
if(!['127.0.0.1','localhost'].includes(new URL(base).hostname))throw Error('Loopback only.');
fs.mkdirSync(out,{recursive:true});
const node=(id,label,parent)=>({id,type:'resource',position:{x:id==='system'?0:280,y:100},data:{kind:'resource',provider:'tools',label,description:'Synthetic planning component',config:{region:'To be selected',classification:'Internal',timeout:5000},origin:'proposed',inputPosition:'left',outputPosition:'right',...(parent?{parentBlockId:parent}:{})}});
const project={version:1,revision:1,id:'compact-workspace-test',name:'Archive planning',provider:'tools',nodes:[node('system','Archive system'),node('a','Catalogue','system'),node('outside','Partner')],edges:[{id:'exchange',source:'a',target:'outside',type:'smoothstep',label:'Publish record'}]};
const browser=await chromium.launch(process.env.ATMEM_ARCHITECT_BROWSER_BIN?{executablePath:process.env.ATMEM_ARCHITECT_BROWSER_BIN}:{}),results=[];let activePage;
try{
 for(const width of [1440,900,390])for(const theme of ['light','dark']){
  const page=await browser.newPage({viewport:{width,height:1000}}),errors=[];
  activePage=page;page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(({project,theme})=>{localStorage.setItem('atforma-workspace-v3',JSON.stringify(project));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'default',effort:'medium'}));localStorage.setItem('atmem-architect-theme',theme);},{project,theme});
  await page.route('**/api/**',r=>r.fulfill({json:new URL(r.request().url()).pathname==='/api/session'?{token:'synthetic',status:'local-sidecar',providers:{codex:{available:true}},memory:{enabled:false}}:{projects:[],sessions:[],artifacts:[],checks:[],saved:true,enabled:false}}));
  await page.goto(base);
  const canvas=page.locator('.drawio-canvas:visible').last(),shape=id=>canvas.locator(`[data-cell-kind=vertex][data-record-id="${id}"]`);
  await shape('system').waitFor();
  const chatClose=page.getByRole('button',{name:'Hide chat',exact:true});if(await chatClose.isVisible())await chatClose.click();
  const tools=page.getByRole('button',{name:'Hide drawing tools',exact:true});if(await tools.isVisible())await tools.click();
  await page.getByRole('button',{name:'Fit drawing',exact:true}).click();
  await page.getByRole('button',{name:'Show properties',exact:true}).click();
  await shape('outside').click();
  const panel=page.getByRole('complementary',{name:'Selected diagram record'});
  await expect(panel.getByLabel('Block name',{exact:true})).toHaveValue('Partner');
  const bounds=await canvas.boundingBox(),props=await panel.boundingBox(),header=await page.locator('.bar').boundingBox();
  assert.equal(header.height,44,'Entire top fits one narrow row');
  assert.ok(bounds.y<=70,'No stacked toolbar rows above the canvas');
  assert.ok(bounds.height>=800,'Canvas retains most of the window height');
  assert.ok(props.x+props.width<=bounds.x+1,'Properties are left of the drawing');
  assert.ok(props.y<bounds.y+100,'Properties start near the top');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No page horizontal overflow');
  await page.screenshot({path:`${out}/properties-${theme}-${width}.png`});
  // Connections remain editable in the left rail.
  await page.getByRole('button',{name:'Connections 1',exact:true}).click();
  await page.getByRole('button',{name:'Edit connection 1',exact:true}).click();
  const dialog=page.getByRole('dialog');await expect(dialog).toBeVisible();await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Hide properties',exact:true}).click();
  const collapsedProps=await canvas.boundingBox();assert.ok(collapsedProps.width>bounds.width+100);
  await page.getByRole('button',{name:'Show drawing tools',exact:true}).click();
  await expect(page.getByRole('complementary',{name:'Board library'})).toBeVisible();
  assert.equal((await canvas.boundingBox()).y,bounds.y,'Tools opening adds no header row');
  await page.getByRole('button',{name:'Hide drawing tools',exact:true}).click();
  await page.locator('.board-actions-menu>summary').click();await expect(page.getByRole('button',{name:'Export diagram',exact:true})).toBeVisible();await page.locator('.board-actions-menu>summary').click();
  await page.screenshot({path:`${out}/${theme}-${width}.png`});
  const before=await canvas.boundingBox();
  await page.getByRole('button',{name:'Hide top toolbar',exact:true}).click();
  await expect(page.locator('.bar')).toBeHidden();
  await expect.poll(async()=>(await canvas.boundingBox()).height).toBeGreaterThan(before.height+40);
  await page.reload();await shape('system').waitFor();await expect(page.locator('.bar')).toBeHidden();
  await page.getByRole('button',{name:'Show top toolbar',exact:true}).click();await expect(page.locator('.bar')).toBeVisible();
  await page.locator('.drawing-journey-menu>summary').click();await page.getByRole('tab',{name:'Requirements',exact:true}).click();
  await expect(page.locator('.app')).not.toHaveClass(/compact-drawing-workspace/);
  await page.getByRole('tab',{name:'Board',exact:true}).click();await shape('system').waitFor();
  const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));assert.deepEqual(saved.nodes,project.nodes);assert.deepEqual(saved.edges,project.edges);
  assert.deepEqual(errors,[]);results.push({width,theme,headerHeight:header.height,canvasHeight:bounds.height,propertiesLeft:true,collapsePersists:true,errors});await page.close();
 }
 fs.writeFileSync(`${out}/results.json`,JSON.stringify(results,null,2));console.log(JSON.stringify(results));
}catch(error){await activePage?.screenshot({path:`${out}/failure.png`}).catch(()=>{});throw error;}finally{await browser.close();}
