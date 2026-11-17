// Real browser/API/offline provider qualification. Release/merge observations are local simulations.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {template} from '../src/core.mjs';

const root=path.resolve(import.meta.dirname,'..'),out=path.join(root,'.local/maintenance-campaign-browser');
await fs.mkdir(out,{recursive:true});
const config=process.env.ATMEM_MAINTENANCE_TEST_CONFIG;if(!config)throw Error('Explicit qualified local worker required');
const home=await fs.mkdtemp(path.join(out,'home-'));
const env={...process.env,ATMEM_ARCHITECT_HOME:home,ATMEM_ARCHITECT_PORT:'5187',ATMEM_ARCHITECT_SIDECAR_PORT:'8787',ATMEM_ARCHITECT_MAINTENANCE_WORKER_CONFIG:path.resolve(config)};
let browser;const children=[];
const start=(cmd,args)=>{const child=spawn(cmd,args,{cwd:root,env,stdio:'ignore'});children.push(child);return child;};
start(path.join(root,'.venv/bin/python'),['-m','uvicorn','server.app:app','--host','127.0.0.1','--port','8787','--no-access-log']);
start(process.execPath,['node_modules/vite/bin/vite.js']);
async function wait(url){for(let i=0;i<120;i++){try{if((await fetch(url)).ok)return;}catch{}await new Promise(r=>setTimeout(r,250));}throw Error('Local server did not start');}
try{
 await wait('http://127.0.0.1:5187');await wait('http://127.0.0.1:8787/api/maintenance/capabilities');
 browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:1100},acceptDownloads:true}),errors=[],modelCalls=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/\/api\/architect$|\/engineering\/(create|start|steer)$/.test(r.url()))modelCalls.push(r.url());});
 const project={...template('tools'),id:crypto.randomUUID(),name:'Shared module migration'};
 await page.addInitScript(p=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify(p));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'default'}));},project);
 await page.goto('http://127.0.0.1:5187');
 const open=async()=>{await page.getByRole('button',{name:'Infrastructure upgrades',exact:true}).click();await page.getByRole('button',{name:'Coordinated projects',exact:true}).click();};await open();
 const panel=page.getByRole('region',{name:'Coordinated projects',exact:true});
 for(const name of ['shared','consumer-a','consumer-b','unrelated']){
  await panel.getByLabel('Root name',{exact:true}).fill(name);
  await panel.getByLabel('Materialized revision',{exact:true}).fill('a'.repeat(40));
  await panel.getByLabel('Select campaign repository folder',{exact:true}).setInputFiles(path.join(root,'tests/maintenance/fixtures/campaign',name));
  const add=panel.getByRole('button',{name:'Add selected repository',exact:true});await page.waitForFunction(()=>!Array.from(document.querySelectorAll('button')).find(b=>b.textContent==='Add selected repository')?.disabled);await add.click();
 }
 await panel.getByRole('button',{name:'Inspect dependencies',exact:true}).click();
 await panel.getByText('Resolve module sources',{exact:true}).waitFor({timeout:30000});
 await panel.getByLabel('Materialization for root-consumer-a queue',{exact:true}).selectOption('root-shared');
 await panel.getByLabel('Materialization for root-consumer-b archive',{exact:true}).selectOption('root-shared');
 await panel.getByRole('button',{name:'Confirm selected bindings',exact:true}).click();
 await panel.getByText('Resolve module sources',{exact:true}).waitFor({state:'hidden',timeout:30000});
 await panel.getByLabel('Shared module to upgrade',{exact:true}).selectOption('root-shared');
 await panel.getByRole('button',{name:'Prepare campaign',exact:true}).click();
 await panel.getByRole('progressbar',{name:'Campaign checks'}).waitFor();
 await panel.getByText('Module release pending',{exact:true}).waitFor({timeout:240000});
 assert.deepEqual(await panel.locator('[role=alert]').allTextContents(),[]);
 const exported=async()=>{const [download]=await Promise.all([page.waitForEvent('download'),panel.getByRole('button',{name:'Export campaign',exact:true}).click()]);return JSON.parse(await fs.readFile(await download.path(),'utf8'));};
 const prepared=await exported(),campaign=prepared.aggregate.result;
 assert.equal(campaign.status,'module_release_pending');assert.deepEqual(Object.keys(campaign.consumers),['root-consumer-a','root-consumer-b']);assert.equal(campaign.checks.length,8);
 const released=path.join(out,'released-module');await fs.mkdir(released,{recursive:true});
 const files={...campaign.moduleBefore};for(const change of campaign.moduleCandidate.changes)files[change.path]=change.after;
 for(const [name,text] of Object.entries(files))await fs.writeFile(path.join(released,name),text);
 await panel.getByText('Check a local module release',{exact:true}).click();
 await panel.getByLabel('Select released module folder',{exact:true}).setInputFiles(released);
 await panel.getByLabel('Released source',{exact:true}).fill('git::https://example.invalid/shared-batch.git?ref=v2.0.0');
 await panel.getByLabel('Released immutable revision',{exact:true}).fill('b'.repeat(40));
 if(!await panel.getByRole('button',{name:'Check supplied release',exact:true}).isVisible())await panel.getByText('Check a local module release',{exact:true}).click();
 await panel.getByRole('button',{name:'Check supplied release',exact:true}).click();
 await panel.getByText('Local release checked',{exact:true}).waitFor({timeout:120000});
 const observed=await exported();assert.equal(observed.aggregate.result.releaseChecks.length,2);assert.equal(observed.aggregate.result.release.observation,'operator_supplied_local_simulation');
 await panel.getByText('Simulate a partial merge',{exact:true}).click();
 await panel.getByLabel('Simulated merged consumer',{exact:true}).selectOption('root-consumer-a');
 await panel.getByLabel('Fresh source for root-consumer-b',{exact:true}).setInputFiles(path.join(root,'tests/maintenance/fixtures/campaign/consumer-b'));
 await panel.getByRole('button',{name:'Record local merge simulation',exact:true}).click();
 await panel.getByText('Module release pending',{exact:true}).waitFor({timeout:30000});
 const partial=await exported();assert.equal(partial.aggregate.result.releaseChecks.length,0);assert.equal(partial.aggregate.result.checks.filter(r=>r.consumer==='root-consumer-b').every(r=>r.status==='stale'),true);
 if(!await panel.getByRole('button',{name:'Check supplied release',exact:true}).isVisible())await panel.getByText('Check a local module release',{exact:true}).click();
 await panel.getByRole('button',{name:'Check supplied release',exact:true}).click();
 await panel.getByText('Local release checked',{exact:true}).waitFor({timeout:120000});
 const final=await exported();assert.equal(final.aggregate.result.releaseChecks.length,1);assert.equal(final.aggregate.result.releaseChecks[0].consumer,'root-consumer-b');
 await fs.writeFile(path.join(out,'campaign.json'),JSON.stringify(final,null,2));
 await page.reload();await open();await panel.getByText('Local release checked',{exact:true}).waitFor({timeout:30000});
 await page.screenshot({path:path.join(out,'campaign-desktop.png'),fullPage:true});await page.setViewportSize({width:820,height:1000});await page.screenshot({path:path.join(out,'campaign-compact.png'),fullPage:true});
 assert.deepEqual(errors,[]);assert.deepEqual(modelCalls,[]);
 await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify({status:'passed',evidenceLevel:'real_browser_local_offline_provider_checks',modelCalls,errors,cloudOperations:false,remoteWrites:false,releaseObservation:'local_operator_simulation',partialMerge:'remaining wave invalidated and freshly checked',persistence:'reloaded from private SQLite'},null,2)+'\n');
 console.log('Campaign browser passed: module/two consumers, exact overlay, release equality, partial-merge invalidation, fresh remaining wave and persistence.');
}catch(error){console.error(error);if(browser){const pages=browser.contexts().flatMap(c=>c.pages());if(pages[0]){console.error((await pages[0].locator('[role=alert]').allTextContents()).join('\n'));await pages[0].screenshot({path:path.join(out,'failure.png'),fullPage:true});}}throw error;
}finally{await browser?.close();for(const child of children)child.kill('SIGTERM');}
