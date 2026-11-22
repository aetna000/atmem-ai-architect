// Deliberately colliding synthetic records. APIs and model calls stay intercepted.
import {validateImport} from '../src/core.mjs';
import fs from 'node:fs';import assert from 'node:assert/strict';import {chromium,expect} from '@playwright/test';
const base=process.argv[2]||'http://127.0.0.1:5199',out=process.env.LAYOUT_EVIDENCE||'.local/layout-recovery-synthetic';
if(!['localhost','127.0.0.1'].includes(new URL(base).hostname))throw Error('Loopback only.');fs.mkdirSync(out,{recursive:true});
const nodes=Array.from({length:6},(_,i)=>({id:'archive-'+i,type:'resource',position:{x:40,y:40},data:{label:'Archive stage '+i,kind:'resource',provider:'tools',description:'Preserve archive records.',origin:'proposed',inputPosition:'left',outputPosition:'right',config:{region:'To be selected',classification:'Internal',timeout:5000}}}));
const edges=[[0,1],[1,2],[2,3],[3,4],[4,5],[0,3],[1,4],[2,5]].map(([a,b],i)=>({id:'exchange-'+i,source:nodes[a].id,target:nodes[b].id,label:'Preserve records '+i,type:'smoothstep',interfaceSpec:{transport:'HTTPS',input:'Archive record',output:'Accepted record',authorization:'Assigned archive role',failure:'Retry the same record identifier',verification:'Reject unauthorized requests'}}));
const project={version:1,revision:1,id:'layout-recovery-test',name:'Archive layout recovery',provider:'tools',nodes,edges};
validateImport(project);
const browser=await chromium.launch(process.env.ATMEM_ARCHITECT_BROWSER_BIN?{executablePath:process.env.ATMEM_ARCHITECT_BROWSER_BIN}:{});let page;
try{
 page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(30000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(p=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify(p));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.2-sol',effort:'low'}));},project);
 await page.route('**/api/**',r=>r.fulfill({json:r.request().url().endsWith('/api/session')?{status:'local-sidecar',token:'fixture',engineeringEnabled:true,providers:{codex:{available:true}}}:{saved:true,sessions:[],projects:[],events:[],artifacts:[],checks:[],enabled:false,status:'disabled'}}));
 await page.goto(base);const canvas=page.locator('.drawio-canvas:visible').last(),issues=page.locator('.diagram-layout-issues');await expect(canvas.locator('[data-cell-kind=vertex][role=button]')).toHaveCount(6);
 const count=()=>page.locator('[data-layout-issue]').count(),read=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));
 const before=await count();assert.ok(before>10,'Fixture has real rendered conflicts');assert.equal(await issues.getByRole('button',{name:'Reset page layout',exact:true}).count(),0);
 await issues.locator('summary').click();const first=issues.locator('li').first(),id=await first.getAttribute('data-issue-id');await first.getByRole('button').click();await expect.poll(async()=>JSON.parse(await canvas.getAttribute('data-selected-records'))).toContain(id);
 if(await page.getByRole('button',{name:'Hide properties',exact:true}).isVisible())await page.getByRole('button',{name:'Hide properties',exact:true}).click();
 await page.screenshot({path:out+'/before.png'});const start=Date.now();await issues.getByRole('button',{name:'Arrange page',exact:true}).click();
 await expect.poll(async()=>Object.keys((await read()).extensions?.drawingLayouts?.pages?.['board/full']||{}).length).toBe(6);
 await expect(page.locator('.diagram-layout-issues[aria-busy=true]')).toHaveCount(0);const after=await count();assert.ok(after<before,'Arrange improves the measured page');
 const arranged=await read(),cells=arranged.extensions.drawingLayouts.pages['board/full'];assert.deepEqual(arranged.nodes,project.nodes);assert.deepEqual(arranged.edges,project.edges);
 await page.getByRole('button',{name:'Undo',exact:true}).click();await expect.poll(async()=>Object.keys((await read()).extensions?.drawingLayouts?.pages?.['board/full']||{}).length).toBe(0);
 await page.getByRole('button',{name:'Redo',exact:true}).click();await expect.poll(async()=>(await read()).extensions?.drawingLayouts?.pages?.['board/full']).toEqual(cells);
 await page.reload();await expect(canvas.locator('[data-cell-kind=edge][role=button]')).toHaveCount(8);assert.deepEqual((await read()).extensions.drawingLayouts.pages['board/full'],cells);assert.ok(await count()<before);
 assert.deepEqual(errors,[]);await page.screenshot({path:out+'/after.png'});const result={before,after,arrangeMs:Date.now()-start,undoRedo:true,survivesReload:true,recordsAndContractsPreserved:true,issueFocusWorks:true,errors};fs.writeFileSync(out+'/results.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}catch(error){await page?.screenshot({path:out+'/failure.png',timeout:3000}).catch(()=>{});throw error;}finally{await browser.close();}
