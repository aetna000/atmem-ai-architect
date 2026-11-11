// Real local UI/API/native session registration; deliberately submits no inference.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
const base=process.env.ATMEM_ENGINEERING_PREVIEW_URL||'http://127.0.0.1:5274';
const out=path.resolve('specs/029-general-purpose-engine/evidence/20261111-engineering-jobs');
const browser=await chromium.launch({headless:true});const errors=[];
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>errors.push(e.message));
 const project={id:'live-ui-inventory-project',version:1,revision:1,name:'Inventory conversion',provider:'tools',requirements:'Normalize measurement units without changing the warehouse service.',nodes:[],edges:[]};
 await page.addInitScript(project=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify(project));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.1-sol',effort:'high'}));},project);
 await page.goto(base);await page.getByRole('button',{name:'Engineering',exact:true}).click();
 const open=page.getByRole('button',{name:'Open engineering job',exact:true}),ready=page.getByText('Ready · gpt-6.1-sol · high',{exact:true});
 await open.or(ready).waitFor({timeout:60000});if(await open.isVisible())await open.click();
 await page.getByText('Ready · gpt-6.1-sol · high',{exact:true}).waitFor({timeout:60000});
 await page.getByLabel('What should we build or repair?',{exact:true}).fill('Normalize inventory units without changing the warehouse service.');
 await page.screenshot({path:path.join(out,'live-ui-ready.png')});
 await page.getByRole('button',{name:'Close dialog',exact:true}).click();await page.reload();await page.getByRole('button',{name:'Engineering',exact:true}).click();
 await page.getByText('Ready · gpt-6.1-sol · high',{exact:true}).waitFor({timeout:60000});
 assert.equal(await page.getByLabel('What should we build or repair?',{exact:true}).inputValue(),'Normalize inventory units without changing the warehouse service.');
 const state=await page.evaluate(async project=>{const session=await(await fetch('/api/session')).json();const response=await fetch('/api/engineering/list',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({projectId:project.id})});return response.json();},project);
 assert.equal(state.sessions.length,1);assert.equal(state.sessions[0].run,null);assert.equal(state.sessions[0].model,'gpt-6.1-sol');assert.equal(state.sessions[0].effort,'high');assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(out,'live-ui-receipt.json'),JSON.stringify({passed:true,url:base,exactSelection:true,jobCount:1,run:null,reloadResumedSameJob:true,inferenceTurns:0,errors,boundary:'Actual browser, authenticated loopback API, project save and native session/policy/tool registration. No engineering turn or generated output was requested; live output work is proved separately by the API probe.'},null,2)+'\n');
 console.log('Passed actual local UI/API/native registration and reload; no model inference submitted.');
}finally{await browser.close();}
