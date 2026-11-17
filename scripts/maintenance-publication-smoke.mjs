// Actual loopback browser/API with fake GitHub. No GitHub network, cloud or model calls; no remote acceptance claim.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {template} from '../src/core.mjs';

const full=process.argv.includes('--full');if(full&&!process.env.ATMEM_MAINTENANCE_TEST_CONFIG)throw Error('Full fixture requires the qualified offline worker configuration');
const root=path.resolve(import.meta.dirname,'..'),out=path.join(root,'.local/maintenance-publication-browser');await fs.mkdir(out,{recursive:true});
const home=await fs.mkdtemp(path.join(out,'home-'));
const env={...process.env,ATMEM_ARCHITECT_HOME:home,ATMEM_ARCHITECT_PORT:'5187',ATMEM_ARCHITECT_SIDECAR_PORT:'8787',ATMEM_ARCHITECT_ENABLE_MAINTENANCE_PUBLICATION:'1',ATMEM_MAINTENANCE_PUBLICATION_E2E_FULL:full?'1':'0'};
const children=[];let browser;
const start=(command,args)=>{const child=spawn(command,args,{cwd:root,env,stdio:'ignore'});children.push(child);return child;};
start(path.join(root,'.venv/bin/python'),['-m','uvicorn','server.tests.maintenance_publication_e2e:app','--host','127.0.0.1','--port','8787','--no-access-log']);
start(process.execPath,['node_modules/vite/bin/vite.js']);
async function wait(url){for(let i=0;i<160;i++){try{const r=await fetch(url);if(r.ok)return await r.json();}catch{}await new Promise(r=>setTimeout(r,250));}throw Error('Fixture server did not start');}
try{
 const info=await wait('http://127.0.0.1:8787/api/test/publication-fixture');
 browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1366,height:1000},acceptDownloads:true}),errors=[],models=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/\/api\/architect$|\/engineering\/(start|create|steer)$/.test(r.url()))models.push(r.url());});
 const project={...template('tools'),id:info.projectId,name:'Repository migration review'};
 await page.addInitScript(({project,info})=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify(project));localStorage.setItem('atmem-maintenance-campaign-'+project.id,info.campaignId);localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'default'}));},{project,info});
 await page.goto('http://127.0.0.1:5187');
 const open=async()=>{await page.getByRole('button',{name:'Infrastructure upgrades',exact:true}).click();await page.getByRole('button',{name:'Coordinated projects',exact:true}).click();};await open();
 const panel=page.getByRole('region',{name:'GitHub proposals',exact:true});await panel.waitFor({timeout:30000});
 await panel.getByLabel('GitHub repository for '+info.root,{exact:true}).selectOption(info.connectionId+'|'+info.repository);
 if(full)for(const name of ['consumer-a','consumer-b'])await panel.getByLabel('GitHub repository for root-'+name,{exact:true}).selectOption(info.connectionId+'|owner/'+name);
 await panel.getByRole('button',{name:'Review module PR',exact:true}).click();
 await panel.getByRole('checkbox',{name:'I reviewed these patches and accept repository automation.',exact:true}).waitFor({timeout:30000});
 let receipt=await(await fetch('http://127.0.0.1:8787/api/test/publication-receipt')).json();assert.deepEqual(receipt.writes,[]);
 const publish=panel.getByRole('button',{name:'Publish draft PRs',exact:true});assert.equal(await publish.isEnabled(),false);
 await panel.getByRole('checkbox',{name:'I reviewed these patches and accept repository automation.',exact:true}).check();await publish.click();
 await panel.getByText('Draft proposals delivered. Review them on GitHub.',{exact:true}).waitFor({timeout:45000});
 await panel.getByRole('link',{name:'owner/project #1',exact:false}).waitFor({timeout:10000});
 receipt=await(await fetch('http://127.0.0.1:8787/api/test/publication-receipt')).json();assert.equal(receipt.pullRequests,1);assert.equal(receipt.writes.filter(p=>p==='/git/refs').length,2);assert.equal(receipt.defaultHead,'a'.repeat(40));
 const before=receipt.writes.length;await page.reload();await open();await panel.getByText('Draft proposals delivered. Review them on GitHub.',{exact:true}).waitFor({timeout:30000});
 assert.equal((await(await fetch('http://127.0.0.1:8787/api/test/publication-receipt')).json()).writes.length,before);
 if(full){
  const session=await(await fetch('http://127.0.0.1:8787/api/session')).json();
  const operator=async action=>{const r=await fetch('http://127.0.0.1:8787/api/test/publication-operator/'+action,{method:'POST',headers:{Authorization:'Bearer '+session.token}});assert.equal(r.ok,true,await r.text());};
  await operator('release');
  const fetchRelease=async()=>{
   const section=panel.locator('details').filter({has:page.locator('summary',{hasText:'Check actual module release'})});
   if(!(await section.evaluate(el=>el.open)))await section.locator('summary').click();
   await panel.getByLabel('Existing GitHub module release tag',{exact:true}).fill('v2.0.0');
   await panel.getByRole('button',{name:'Fetch release and check consumers',exact:true}).click();
   await panel.getByRole('button',{name:'Review remaining consumer PRs',exact:true}).waitFor({timeout:180000});
  };
  const publishConsumers=async()=>{
   await panel.getByRole('button',{name:'Review remaining consumer PRs',exact:true}).click();
   const checkbox=panel.getByRole('checkbox',{name:'I reviewed these patches and accept repository automation.',exact:true});await checkbox.waitFor({timeout:30000});
   assert.equal(await checkbox.isChecked(),false);assert.equal(await panel.getByRole('button',{name:'Publish draft PRs',exact:true}).isEnabled(),false);
   await checkbox.check();await panel.getByRole('button',{name:'Publish draft PRs',exact:true}).click();
   await panel.getByText('Draft proposals delivered. Review them on GitHub.',{exact:true}).waitFor({timeout:45000});
  };
  await fetchRelease();await publishConsumers();
  await panel.getByRole('link',{name:'owner/consumer-a #1',exact:false}).waitFor();
  await panel.getByRole('link',{name:'owner/consumer-b #1',exact:false}).waitFor();
  await operator('merge-a');await panel.getByRole('button',{name:'Refresh PR status',exact:true}).click();
  await panel.getByText('Inputs changed. Reconcile prior writes and review a fresh wave.',{exact:true}).waitFor();
  assert.equal(await panel.getByRole('button',{name:'Review remaining consumer PRs',exact:true}).count(),0);
  await fetchRelease();await publishConsumers();
  await operator('merge-b');await panel.getByRole('button',{name:'Refresh PR status',exact:true}).click();
  await page.getByText('All consumer proposals merged',{exact:true}).waitFor();
  receipt=await(await fetch('http://127.0.0.1:8787/api/test/publication-receipt')).json();assert.deepEqual(receipt.consumerPullRequests,{'consumer-a':1,'consumer-b':1});assert.equal(receipt.pullRequests,1);
 }
 await page.setViewportSize({width:820,height:1000});await panel.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,'publication-compact.png'),fullPage:true});
 assert.deepEqual(errors,[]);assert.deepEqual(models,[]);
 await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify({...receipt,status:'passed',fullConsumerJourney:full,browserErrors:errors,modelCalls:models,restore:'reload never republished',evidenceLevel:'real_browser_api_fake_github_only'},null,2)+'\n');
 console.log('Publication browser passed; exact review, progress, no reload duplicate writes; full consumer journey: '+full);
}catch(error){if(browser){const page=browser.contexts()[0]?.pages()[0];if(page){console.error((await page.locator('[role=alert]').allTextContents()).join('\n'));await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});}}throw error;
}finally{await browser?.close();for(const child of children)child.kill('SIGTERM');}
