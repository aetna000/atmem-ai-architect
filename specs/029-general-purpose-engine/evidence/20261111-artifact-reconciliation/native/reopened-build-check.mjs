import {chromium} from '/Users/javadtaghia/gitlab/ai-architect-workbench/node_modules/@playwright/test/index.mjs';
import fs from 'node:fs';import assert from 'node:assert/strict';
import {fromProjectFile} from '/Users/javadtaghia/gitlab/ai-architect-workbench/src/project-file.mjs';
import {artifactWorkProjection} from '/Users/javadtaghia/gitlab/ai-architect-workbench/src/artifact-work.mjs';
const out='/Users/javadtaghia/gitlab/ai-architect-workbench/.local/engine-product/20261111-native-artifact-reconciliation-guarded';
const final=fromProjectFile(JSON.parse(fs.readFileSync(out+'/project-m.json','utf8'))).project;
const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}}),mutations=[],errors=[];
page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/\/api\/engineering\/(create|start|steer|capture|recheck|reconciliation)$/.test(r.url()))mutations.push(r.url());});
try{
 await page.addInitScript(p=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify(p));localStorage.setItem('atmem-workspace-view-v1','build');localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.1-sol',effort:'high'}));},final);
 await page.goto('http://127.0.0.1:5282');await page.getByRole('heading',{name:'Build your project',exact:true}).waitFor();await page.getByText('Work completed · gpt-6.1-sol · high',{exact:true}).waitFor({timeout:60000});
 await page.waitForFunction(()=>document.querySelectorAll('.engineering-conversation .engineering-entry.user').length===2,{timeout:60000});
 await page.locator('.engineering-panel .architecture-work > summary').click();await page.getByText('Earlier artifact retained',{exact:true}).waitFor();await page.getByText('Saved context matches',{exact:true}).waitFor();
 const current=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));assert.deepEqual(artifactWorkProjection(current).mappings.map(m=>m.contextStatus),['superseded','current']);
 await page.getByRole('heading',{name:'Linked artifacts',exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:out+'/reopened-build-desktop.png'});await page.setViewportSize({width:390,height:900});await page.getByRole('heading',{name:'Linked artifacts',exact:true}).scrollIntoViewIfNeeded();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:out+'/reopened-build-mobile.png'});
 await page.reload();await page.getByRole('heading',{name:'Build your project',exact:true}).waitFor();await page.getByText('Work completed · gpt-6.1-sol · high',{exact:true}).waitFor({timeout:60000});await page.waitForFunction(()=>document.querySelectorAll('.engineering-conversation .engineering-entry.user').length===2,{timeout:60000});
 assert.deepEqual(mutations,[]);assert.deepEqual(errors,[]);fs.writeFileSync(out+'/reopened-build.json',JSON.stringify({passed:true,actualBuildAndCompletedSessionRestored:true,nativeClientRequestsVisible:2,preservedMappingVersions:2,inferenceOrMappingMutations:0,errors,boundary:'Actual browser after service discovery, saved model import, native session/history/artifact restoration and subsequent reload. No inference/mapping replay. Metadata source is the already qualified actual-native fixture, not a new project qualification.'},null,2)+'\n');console.log('Actual warm Build restore and reload pass; no inference/mapping replay.');
}finally{await browser.close();}
