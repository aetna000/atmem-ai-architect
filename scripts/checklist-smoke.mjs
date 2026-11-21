// Real Chromium rendering; controlled navigation delay, no model or cloud requests.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
const out='.local/checklist-smoke';fs.mkdirSync(out,{recursive:true});
fs.writeFileSync(`${out}/index.html`,'<html><body><div id="root"></div><script type="module" src="/.'+out.slice(1)+'/harness.jsx"></script></body></html>');
fs.writeFileSync(`${out}/harness.jsx`,`import React from 'react';import{createRoot}from'react-dom/client';import{FinalChecklist}from'../../src/FinalChecklist.jsx';import{StarPrompt}from'../../src/StarPrompt.jsx';import '../../src/atmem-tokens.css';import '../../src/brand.css';import '../../src/atflow.css';import '../../src/journey-workspace.css';const project={nodes:[{id:'priced',data:{provider:'gcp',label:'Cloud Storage',service:'Cloud Storage',kind:'source',config:{region:'us-central1'}}},{id:'excluded',data:{provider:'external',label:'External API',kind:'tool',config:{}}}],edges:[],facts:[],decisions:[],needs:[],estimate:{projectSize:'small',prices:{priced:{price:.02,currency:'USD',source:'Synthetic QA quote',region:'us-central1',service:'Standard storage',date:'2026-11-12'}}}};window.calls=[];const root=createRoot(document.getElementById('root'));window.offerStar=offer=>root.render(<StarPrompt offer={offer}/>);root.render(<FinalChecklist project={project} onNavigate={target=>{window.calls.push(target);return new Promise(resolve=>{window.finish=resolve;})}}/>);`);
const probe=createServer();await new Promise(resolve=>probe.listen(0,'127.0.0.1',resolve));const port=probe.address().port;await new Promise(resolve=>probe.close(resolve));
const server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'ignore'});let browser;
try{
 const base=`http://127.0.0.1:${port}`;for(let i=0;i<100;i++){try{if((await fetch(base)).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1280,height:850}});const errors=[];page.on('pageerror',e=>{errors.push(e.message);console.error(e.message)});
 await page.goto(base+'/'+out+'/index.html');const cost=page.getByRole('button',{name:/^Cost estimate:/});await cost.waitFor();assert.match(await cost.innerText(),/Estimated/);assert.doesNotMatch(await cost.innerText(),/Partial|charges missing|unpriced/);assert.equal(await cost.locator('.check-pending').count(),0);
 assert.equal(await cost.locator('strong').evaluate(el=>getComputedStyle(el).cursor),'pointer');
 await cost.click();await page.getByRole('status').getByText('Opening Cost estimate…').waitFor();
 assert.equal(await cost.isDisabled(),true);assert.equal(await cost.evaluate(el=>getComputedStyle(el).cursor),'wait');
 assert.match(await cost.innerText(),/Opening…/);await page.screenshot({path:out+'/opening.png'});
 await page.evaluate(()=>window.finish());await page.waitForFunction(()=>!document.querySelector('.final-checklist[aria-busy="true"]'));
 assert.deepEqual(await page.evaluate(()=>window.calls),['cost']);assert.equal(await cost.isEnabled(),true);
 for(const [name,target]of [['Requirements','requirements'],['Cloud region','location'],['Application checks','checks']]){
  await page.getByRole('button',{name:new RegExp('^'+name+':')}).click();await page.waitForFunction(target=>window.calls.at(-1)===target,target);await page.evaluate(()=>window.finish());await page.waitForFunction(()=>!document.querySelector('.final-checklist[aria-busy="true"]'));assert.equal(await page.evaluate(()=>window.calls.at(-1)),target);
 }
 await page.evaluate(()=>window.offerStar(1));const invitation=page.getByRole('dialog',{name:'Enjoying Architect?'});await invitation.waitFor();
 assert.equal(await invitation.getByRole('link',{name:'Star on GitHub'}).getAttribute('href'),'https://github.com/aetna000/atmem-ai-architect');
 await page.screenshot({path:out+'/star-prompt.png'});await invitation.getByRole('button',{name:'Later',exact:true}).click();assert.equal(await invitation.isVisible(),false);
 await page.evaluate(()=>window.offerStar(2));assert.equal(await invitation.isVisible(),false);
 assert.deepEqual(errors,[]);console.log('Checklist browser: pending feedback, pointer/wait cursors, duplicate prevention and destinations passed.');
}finally{await browser?.close();server.kill('SIGTERM')}
