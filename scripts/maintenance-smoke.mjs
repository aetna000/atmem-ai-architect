// Real browser → local API → qualified offline Terraform worker. No model/cloud calls.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {template} from '../src/core.mjs';

const root=path.resolve(import.meta.dirname,'..'),output=path.join(root,'.local/maintenance-browser');
await fs.mkdir(output,{recursive:true});
const config=process.env.ATMEM_MAINTENANCE_TEST_CONFIG;
if(!config)throw Error('Set ATMEM_MAINTENANCE_TEST_CONFIG to a qualified local worker registration.');
const home=await fs.mkdtemp(path.join(output,'home-'));
const env={...process.env,ATMEM_ARCHITECT_HOME:home,ATMEM_ARCHITECT_PORT:'5187',ATMEM_ARCHITECT_SIDECAR_PORT:'8787',ATMEM_ARCHITECT_MAINTENANCE_WORKER_CONFIG:path.resolve(config)};
const children=[];let browser;
function start(command,args){const child=spawn(command,args,{cwd:root,env,stdio:'ignore'});children.push(child);child.on('error',e=>{throw e;});return child;}
start(path.join(root,'.venv/bin/python'),['-m','uvicorn','server.app:app','--host','127.0.0.1','--port','8787','--no-access-log']);
start(process.execPath,['node_modules/vite/bin/vite.js']);
const wait=async(url)=>{for(let i=0;i<120;i++){try{if((await fetch(url,{signal:AbortSignal.timeout(1000)})).ok)return;}catch{}await new Promise(r=>setTimeout(r,250));}throw Error('Local smoke server did not start: '+url);};
try{
 await wait('http://127.0.0.1:5187');await wait('http://127.0.0.1:8787/api/maintenance/capabilities');
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true}),errors=[],modelCalls=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/\/api\/architect$|\/engineering\/(start|steer|create)$/.test(r.url()))modelCalls.push(r.url());});
 const project={...template('tools'),id:crypto.randomUUID(),name:'Maintenance acceptance'};
 await page.addInitScript(p=>{localStorage.clear();localStorage.setItem('atforma-workspace-v3',JSON.stringify(p));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'default'}));},project);
 await page.goto('http://127.0.0.1:5187');
 await page.getByRole('button',{name:'Infrastructure upgrades',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'maintenance',exact:true});await dialog.getByText('Prepare an AWS upgrade',{exact:true}).waitFor();
 await dialog.getByLabel('Select Terraform repository folder').setInputFiles(path.join(root,'tests/maintenance/fixtures/holdout'));
 await dialog.getByRole('button',{name:'Inspect 1 file',exact:false}).click();
 try{await dialog.getByText('1 file selected',{exact:true}).waitFor();}
 catch(error){await page.screenshot({path:path.join(output,'failure.png'),fullPage:true});throw Error(error.message+' '+await dialog.locator('[role=alert]').allTextContents());}
 const prepare=dialog.getByRole('button',{name:'Prepare migration',exact:true});await prepare.waitFor();await page.waitForFunction(()=>!document.querySelector('.maintenance-actions button.primary')?.disabled);
 await prepare.click();await dialog.getByRole('progressbar').waitFor();
 await dialog.getByText('Patch ready for review',{exact:true}).waitFor({timeout:180000});
 assert.equal(await dialog.locator('.maintenance-error').count(),0);
 assert.equal(await dialog.getByText('.terraform.lock.hcl',{exact:true}).count(),1);
 await page.screenshot({path:path.join(output,'migration-desktop.png'),fullPage:true});
 const [download]=await Promise.all([page.waitForEvent('download'),dialog.getByRole('button',{name:'Export migration',exact:true}).click()]);
 const section=JSON.parse(await fs.readFile(await download.path(),'utf8'));assert.equal(section.aggregate.jobs.at(-1).status,'ready_for_review');
 assert.deepEqual(section.aggregate.jobs.at(-1).receipts.map(r=>r.status),['passed','failed','passed','passed']);
 await dialog.getByLabel('Import maintenance project').setInputFiles({name:'migration.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(section))});
 await dialog.getByRole('button',{name:'Prepare migration',exact:true}).waitFor();
 await page.waitForFunction(()=>document.querySelector('.maintenance-status')?.textContent.includes('Imported evidence'));
 assert.equal(await dialog.locator('.maintenance-stages .done').count(),0);
 // Imported results stay historical; they never display current ready status.
 assert.equal(await dialog.getByText('Patch ready for review',{exact:true}).count(),0);
 await page.setViewportSize({width:820,height:900});await page.screenshot({path:path.join(output,'migration-compact.png'),fullPage:true});
 assert.ok(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth+1));
 // A slow export completing after a project switch must not attach old source to the new project.
 await page.setViewportSize({width:1440,height:1000});
 let release,seen;const hold=new Promise(resolve=>release=resolve),intercepted=new Promise(resolve=>seen=resolve);
 await page.route('**/api/maintenance/projects/*/export',async route=>{seen();await hold;await route.continue();});
 const delayedDownload=page.waitForEvent('download');
 await dialog.getByRole('button',{name:'Export migration',exact:true}).click();await intercepted;
 await page.getByRole('button',{name:'Close dialog',exact:true}).click();
 await page.getByRole('button',{name:'More',exact:true}).click();await page.getByRole('menuitem',{name:'Start over',exact:true}).click();
 await page.getByRole('button',{name:'Confirm reset board and context',exact:true}).click();
 await page.waitForFunction(old=>JSON.parse(localStorage.getItem('atforma-workspace-v3')||'null')?.id!==old,project.id);
 release();await delayedDownload;
 assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')).extensions?.maintenance),undefined);
 assert.deepEqual(modelCalls,[]);assert.deepEqual(errors,[]);
 await fs.writeFile(path.join(output,'receipt.json'),JSON.stringify({status:'passed',evidenceLevel:'real_local_browser_and_container_schema_checks',modelCalls,errors,screenshots:['migration-desktop.png','migration-compact.png'],cloudOperations:false},null,2)+'\n');
 console.log('Maintenance browser passed: real schema migration, progress, source-bound lock, portable export and historical import.');
}finally{await browser?.close();for(const child of children)child.kill('SIGTERM');}
