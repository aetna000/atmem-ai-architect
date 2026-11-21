// Empty-board interaction regression. API calls are mocked; no model work or owner writes.
import {chromium} from '@playwright/test';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const out=process.env.ATMEM_UI_EVIDENCE_DIR||'.local/external-artifacts/board-overlay';fs.mkdirSync(out,{recursive:true});
const socket=createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));
const base=process.env.ATMEM_UI_BASE||`http://127.0.0.1:${port}`,server=process.env.ATMEM_UI_BASE?null:spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'ignore'});let browser;
try{
 for(let i=0;i<60;i++){try{if((await fetch(base)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true});
 for(const width of [1440,390])for(const theme of ['light','dark']){
  const page=await browser.newPage({viewport:{width,height:1000}});page.setDefaultTimeout(12000);const errors=[];let inference=0;page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(({theme,width})=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify({id:`empty-${width}-${theme}`,version:1,revision:1,name:'Empty design',provider:'tools',requirements:'',nodes:[],edges:[]}));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'fixture',effort:'high'}));localStorage.setItem('atmem-architect-theme',theme);},{theme,width});
  await page.route('**/api/**',route=>{if(/\/architect$|\/engineering\/(create|start|steer)$/.test(route.request().url()))inference++;return route.fulfill({json:route.request().url().endsWith('/session')?{token:'fixture',engineeringEnabled:true,providers:{codex:{installed:true,available:true,signedIn:true}}}:{enabled:false,status:'disabled',projects:[],bin:[]}});});
  await page.goto(base);await page.evaluate(theme=>document.documentElement.dataset.theme=theme,theme);
  const welcome=page.getByRole('region',{name:'Start your project'}),picker=page.getByRole('dialog',{name:'Add block'});
  await welcome.waitFor();await page.getByRole('button',{name:'Toggle components and layers'}).click();await page.getByRole('button',{name:'Add component',exact:true}).click();
  await picker.waitFor();assert.equal(await welcome.count(),0,'welcome is hidden during component selection');
  const search=page.getByRole('textbox',{name:'Search blocks',exact:true});await search.fill('');
  assert.ok(await search.evaluate(el=>{const b=el.getBoundingClientRect();return !!document.elementFromPoint(b.x+b.width/2,b.y+b.height/2)?.closest('.palette');}),'picker receives pointer input above the sidebar');
  await picker.getByRole('button',{name:'AWS',exact:true}).click();assert.equal(await page.getByRole('button',{name:'Toggle components and layers'}).getAttribute('aria-expanded'),'true','picker interactions do not collapse the sidebar');
  await page.screenshot({path:`${out}/picker-${theme}-${width}.png`});
  await page.getByRole('button',{name:'Close component picker',exact:true}).click();await welcome.waitFor();
  await page.getByRole('button',{name:'Add component',exact:true}).click();await search.focus();await page.keyboard.press('Escape');await welcome.waitFor();
  await page.getByRole('button',{name:'Dismiss welcome card',exact:true}).click();assert.equal(await welcome.count(),0);
  const before=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));assert.equal(before.nodes.length,0);
  await page.reload();await page.evaluate(theme=>document.documentElement.dataset.theme=theme,theme);await page.getByRole('tab',{name:'Board',exact:true}).waitFor();assert.equal(await welcome.count(),0,'dismissal survives reload');
  await page.getByRole('checkbox',{name:'Draw as we talk'}).uncheck();
  await page.getByRole('button',{name:'Toggle components and layers'}).click();await page.getByRole('button',{name:'Add component',exact:true}).click();await page.getByRole('combobox',{name:'Block scope',exact:true}).selectOption('all');await search.fill('PostgreSQL');await picker.getByRole('button',{name:/^PostgreSQL/}).click();
  assert.equal(await picker.count(),0);await page.locator('.react-flow__node').waitFor();assert.equal(await welcome.count(),0);assert.equal(inference,0);assert.deepEqual(errors,[]);
  console.log(JSON.stringify({base,width,theme,pickerOnTop:true,explicitCloseAndEscape:true,welcomeDismissalSurvivesReload:true,canAddComponent:true,inference,errors}));await page.close();
 }
}finally{await browser?.close();server?.kill('SIGTERM');}
