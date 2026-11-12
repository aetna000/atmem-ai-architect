// Automated contrast sampling across actual rendered views; no model/cloud calls.
import {chromium} from '@playwright/test';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {pdmTemplate} from '../src/core.mjs';
const out=process.env.ATMEM_CONTRAST_EVIDENCE_DIR||'.local/external-artifacts/contrast-review';fs.mkdirSync(out,{recursive:true});
const socket=createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));const base=process.env.ATMEM_UI_BASE||`http://127.0.0.1:${port}`;
const server=process.env.ATMEM_UI_BASE?null:spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'ignore'});let browser;
try{
 for(let i=0;i<60;i++){try{if((await fetch(base)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:1050}});page.setDefaultTimeout(15000);
 await page.addInitScript(p=>{localStorage.setItem('atforma-workspace-v3',JSON.stringify(p));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'fixture',effort:'high'}));},{...pdmTemplate('aws'),id:'contrast-source'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',route=>{const u=route.request().url();return route.fulfill({json:u.endsWith('/api/session')?{token:'fixture',engineeringEnabled:true,status:'local-sidecar',providers:{codex:{installed:true,available:true,signedIn:true}}}:u.endsWith('/engineering/list')?{sessions:[]}:u.endsWith('/engineering/delivery')?{artifact:null,canPackage:false}:u.endsWith('/memory/inspect')?{enabled:true,status:'ready',engine:'fixture',pending:0,rejected:0,policy:'Fixture',profile:[],project:[],skills:[],activity:[]}:{status:'disabled',enabled:false,projects:[],bin:[],saved:true}})});
 await page.goto(base);await page.getByRole('tab',{name:'Board',exact:true}).waitFor();
 const samples=[];
 async function audit(view,scope='body'){
  const results=await page.locator(scope).evaluate(root=>{
   const rgb=c=>{const n=c.match(/[\d.]+/g)?.map(Number)||[0,0,0];return n;},lum=c=>{const n=rgb(c).slice(0,3).map(x=>{const v=x/255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4});return .2126*n[0]+.7152*n[1]+.0722*n[2];};
   let checked=0;const failures=[];
   for(const el of root.querySelectorAll('*')){
    if(['SCRIPT','STYLE','OPTION'].includes(el.tagName)||el.namespaceURI?.includes('svg'))continue;
    const style=getComputedStyle(el),rect=el.getBoundingClientRect();
    if(!rect.width||!rect.height||rect.bottom<0||rect.top>innerHeight||style.visibility==='hidden'||style.display==='none')continue;
    const text=[...el.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join('').trim();
    const input=el.matches('input:not([type=checkbox]):not([type=radio]),textarea,select,button');
    if(!text&&!input)continue;
    let ancestor=el;while(ancestor&&rgb(getComputedStyle(ancestor).backgroundColor)[3]===0)ancestor=ancestor.parentElement;
    const background=getComputedStyle(ancestor||document.documentElement).backgroundColor;
    const colors=[{color:style.color,text:text||el.value||el.getAttribute('aria-label')||el.tagName}];
    if(input&&el.placeholder)colors.push({color:getComputedStyle(el,'::placeholder').color,text:'placeholder: '+el.placeholder});
    for(const value of colors){
     const l1=lum(value.color),l2=lum(background),ratio=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05),threshold=parseFloat(style.fontSize)>=24||(parseFloat(style.fontSize)>=18.66&&+style.fontWeight>=700)?3:4.5;checked++;
     if(ratio<threshold-.01)failures.push({tag:el.tagName,class:el.className,text:value.text.slice(0,90),ratio:+ratio.toFixed(2),foreground:value.color,background});
    }
   }
   return {checked,failures};
  });samples.push({view,...results});await page.screenshot({path:`${out}/${view}.png`});
 }
 for(const theme of ['light','dark']){
  await page.evaluate(theme=>document.documentElement.dataset.theme=theme,theme);
  for(const stage of ['Board','Requirements','Choices','Review','Delivery']){
   await page.getByRole('tab',{name:stage,exact:true}).click();await page.waitForTimeout(200);
   await audit(`${theme}-${stage}`);
   if(stage==='Board'){
    const toggle=page.getByRole('button',{name:'Toggle components and layers'});if(await toggle.getAttribute('aria-expanded')!=='true')await toggle.click();
    await audit(`${theme}-components`,'.board-components');
    await page.locator('.react-flow__node').first().dblclick();
    if(!await page.getByRole('region',{name:'Block detail'}).isVisible())await page.locator('.react-flow__node').first().dblclick();
    await page.getByRole('region',{name:'Block detail'}).waitFor();assert.equal(await page.getByRole('complementary',{name:'Board components'}).count(),0);
    const confirmation=page.getByRole('button',{name:'Looks good',exact:true});await confirmation.scrollIntoViewIfNeeded();
    await audit(`${theme}-block-review`,'.component-review');
    for(const button of await page.locator('.block-review-actions button:not(:disabled)').all()){await button.hover();await button.focus();await audit(`${theme}-block-review-focus`,'.component-review');}
    await page.getByRole('button',{name:'Back to the board',exact:true}).click();
   }
   if(stage==='Review'){
    await page.getByText('Costs and usage assumptions',{exact:true}).click();await audit(`${theme}-costs`);await page.getByText('Costs and usage assumptions',{exact:true}).click();
    await page.getByText('Generated infrastructure and configuration checks',{exact:true}).click();await audit(`${theme}-infrastructure`);await page.getByText('Generated infrastructure and configuration checks',{exact:true}).click();
   }
  }
  for(const dialog of ['AtMem dashboard','Connections']){
   await page.getByRole('button',{name:'More',exact:true}).click();await page.getByRole('menuitem',{name:dialog,exact:true}).click();await page.waitForTimeout(200);await audit(`${theme}-${dialog.replaceAll(' ','-')}`,'.modal');await page.getByRole('button',{name:'Close dialog'}).click();
  }
  await page.getByRole('button',{name:'Projects',exact:true}).click();await audit(`${theme}-projects`,'.modal');await page.getByRole('button',{name:'Close dialog'}).click();
 }
 fs.writeFileSync(`${out}/results.json`,JSON.stringify({samples,errors},null,2)+'\n');
 console.log(JSON.stringify(samples.map(s=>({view:s.view,checked:s.checked,failures:s.failures})),null,2));assert.deepEqual(errors,[]);assert.equal(samples.reduce((n,s)=>n+s.failures.length,0),0,'all sampled text and controls must meet contrast thresholds');
}finally{await browser?.close();server?.kill('SIGTERM');}
