// Actual browser/API/native file work with a mid-turn demand and immutable capture.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const base=process.env.ATMEM_ENGINEERING_PREVIEW_URL||'http://127.0.0.1:5274';
const out=path.resolve('specs/029-general-purpose-engine/evidence/20261111-engineering-jobs/live-browser-work');fs.mkdirSync(out,{recursive:true});
const sourcePaths=['server/app.py','server/engineering_jobs.py','server/engineering_sessions.py','server/engineering_routes.py','server/engineering_artifacts.py','server/codex_app_server.py','server/codex_engineering_backend.py','server/codex_worker_policy.py','src/EngineeringPanel.jsx','src/engineering-client.mjs','src/main.jsx'];
const sourceHashes=Object.fromEntries(sourcePaths.map(file=>[file,createHash('sha256').update(fs.readFileSync(file)).digest('hex')]));
fs.writeFileSync(path.join(out,'source-at-start.json'),JSON.stringify(sourceHashes,null,2)+'\n');
const browser=await chromium.launch({headless:true});const errors=[];let receipt={passed:false,model:'gpt-6.1-sol',effort:'high',cloudOperations:false};
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>errors.push(e.message));
 const project={id:'live-browser-normalizer-project',version:1,revision:1,name:'Inventory unit normalization',provider:'tools',requirements:'Independent unit normalization library. Preserve the existing warehouse API. No cloud dependencies.',nodes:[],edges:[]};
 await page.addInitScript(project=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify(project));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.1-sol',effort:'high'}));},project);
 await page.goto(base);await page.getByRole('button',{name:'Engineering',exact:true}).click();await page.getByRole('button',{name:'Open engineering job',exact:true}).click();await page.getByText('Ready · gpt-6.1-sol · high',{exact:true}).waitFor({timeout:60000});
 const intent='Build an independent CommonJS inventory-normalizer.cjs exporting normalize(value, unit), returning grams. Support exact case-sensitive units g and kg. Accept finite nonnegative numbers only; reject booleans, strings, negative/nonfinite numbers and unknown units with TypeError. Preserve the existing warehouse API; do not implement cloud, AI or network dependencies. Write actual module files, meaningful Node built-in tests and a concise README with local run instructions. Execute your tests. Use the supplied composition skill and server tools. Keep the final reply concise.';
 const update='Also export normalizeBatch(items). Each input item is {value, unit}; return the array of gram values using the same validation. Empty batches return []. Reject more than 100 items with RangeError. Preserve the original normalize contract and existing warehouse API.';
 fs.writeFileSync(path.join(out,'intent.txt'),intent+'\n');fs.writeFileSync(path.join(out,'update.txt'),update+'\n');
 await page.getByLabel('What should we build or repair?',{exact:true}).fill(intent);await page.getByRole('button',{name:'Start work',exact:true}).click();await page.getByText('Working · gpt-6.1-sol · high',{exact:true}).waitFor({timeout:60000});
 await page.getByLabel('Add an update',{exact:true}).fill(update);await page.getByRole('button',{name:'Send update',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#engineering-intent')?.value==='',{timeout:60000});
 await page.getByRole('button',{name:'Close dialog',exact:true}).click();await page.reload();await page.getByRole('button',{name:'Engineering',exact:true}).click();
 await page.getByRole('button',{name:'Capture package',exact:true}).waitFor({timeout:300000});
 const capturePromise=page.waitForResponse(response=>response.url().endsWith('/api/engineering/capture')&&response.status()===200);await page.getByRole('button',{name:'Capture package',exact:true}).click();const manifest=await(await capturePromise).json();
 const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Download package',exact:true}).click();const download=await downloadPromise;await download.saveAs(path.join(out,'generated-package.zip'));
 assert.equal(createHash('sha256').update(fs.readFileSync(path.join(out,'generated-package.zip'))).digest('hex'),manifest.sha256);
 const result=await page.evaluate(async projectId=>{const session=await(await fetch('/api/session')).json();const post=async(action,payload)=>(await fetch('/api/engineering/'+action,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({projectId,...payload})})).json();const jobs=await post('list',{});const job=jobs.sessions.at(-1);return {...await post('events',{sessionId:job.id,after:0}),job};},project.id);
 assert.equal(result.job.model,'gpt-6.1-sol');assert.equal(result.job.effort,'high');assert.equal(result.job.last_status,'completed');assert.equal(result.events.filter(e=>e.kind==='accepted').length,1);assert.equal(result.events.filter(e=>e.kind==='steering_accepted').length,1);assert.equal(result.events.find(e=>e.kind==='steering_submitted').text,update);assert.deepEqual(errors,[]);
 for(const [file,hash] of Object.entries(sourceHashes))assert.equal(createHash('sha256').update(fs.readFileSync(file)).digest('hex'),hash,'source changed during live workflow');
 fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');fs.writeFileSync(path.join(out,'events.json'),JSON.stringify(result.events,null,2)+'\n');await page.screenshot({path:path.join(out,'completed.png')});
 receipt={...receipt,passed:true,sessionId:result.job.id,projectId:project.id,artifactId:manifest.id,artifactSha256:manifest.sha256,acceptedRequests:1,steeringAccepted:1,reloadWithoutReplay:true,errors,boundary:'Actual browser, real authenticated loopback API and live native model/tools, mid-turn steering, reload/recovery and digest-verified generated ZIP download on unchanged source. Independent generated-code behavior is a separate check; not original-project/whole-system/cloud acceptance.'};
 console.log('Passed actual browser-to-native generation, live steering, reload without replay and pinned-input/digest-verified download.');
}finally{fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');await browser.close();}
