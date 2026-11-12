// Use only after observe.mjs confirms settlement; this never starts/rechecks work.
import fs from 'node:fs';import assert from 'node:assert/strict';import path from 'node:path';import {createHash}from 'node:crypto';import {unzipSync,strFromU8}from 'fflate';import {chromium}from '@playwright/test';
const base='http://127.0.0.1:5298',out='.local/external-artifacts/ui-native-handoff/v1',live=JSON.parse(fs.readFileSync(out+'/live.json')),settled=JSON.parse(fs.readFileSync(out+'/settled.json')),artifact=JSON.parse(fs.readFileSync(out+'/artifact.json')),sha=b=>createHash('sha256').update(b).digest('hex');
const auth=await(await fetch(base+'/api/session')).json();
async function post(action,extra={}){const r=await fetch(base+'/api/'+action,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+auth.token},body:JSON.stringify({projectId:live.projectId,...extra})});assert(r.ok,action+' HTTP'+r.status);return r.json()}
const file=await post('projects/get',{id:live.projectId}),before=await post('engineering/delivery');assert.equal(before.artifact.id,settled.artifactId);assert.equal(before.artifact.sha256,artifact.sha256);
fs.writeFileSync(out+'/project-before-delivery.json',JSON.stringify(file,null,2)+'\n');fs.writeFileSync(out+'/delivery-before.json',JSON.stringify(before,null,2)+'\n');
const browser=await chromium.launch({headless:true}),page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];let starts=0,handoffs=0;page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{const p=new URL(r.url()).pathname;if(p==='/api/engineering/start')starts++;if(p==='/api/engineering/handoff')handoffs++});
await page.addInitScript(()=>{localStorage.setItem('atforma-draw-live','off');localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.1-sol',effort:'high'}))});
try{
 await page.goto(base+'/');await page.locator('#project-file-input').setInputFiles({name:'saved-project.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(file))});await page.getByText('Project opened.',{exact:true}).waitFor();
 await page.getByRole('tab',{name:'Implementation',exact:true}).click();
 await page.getByRole('log',{name:'Project conversation',exact:true}).getByText(/I’m using the composition skill/).waitFor();
 await page.getByRole('button',{name:'Review and download handoff',exact:true}).click();
 const panel=page.getByRole('region',{name:'Implementation delivery',exact:true}),button=panel.getByRole('button',{name:'Download handoff package (ZIP)',exact:true});await button.waitFor();
 await panel.getByRole('heading',{name:'Package checks',exact:true}).waitFor();await page.screenshot({path:out+'/delivery-before-download.png',fullPage:true});
 const downloaded=page.waitForEvent('download',{timeout:45000});await button.click();const download=await downloaded;await download.saveAs(out+'/handoff.zip');
 const archive=unzipSync(fs.readFileSync(out+'/handoff.zip')),original=archive['evidence/original-implementation.zip'];assert(original);assert.equal(sha(original),artifact.sha256);
 const included=unzipSync(original);let verified=0;
 for(const f of artifact.files.filter(f=>f.kind==='file')){assert(included[f.path],f.path);assert.equal(sha(included[f.path]),f.sha256,f.path);assert.equal(sha(archive['implementation/'+f.path]),f.sha256,f.path);verified++}
 const submitted=JSON.parse(strFromU8(archive['design/submitted-project.json']));assert.equal(sha(submitted.discovery.problem),live.briefSha256,'Full frozen requirements must survive the submitted snapshot');
 const checks=JSON.parse(strFromU8(archive['evidence/local-checks.json']));assert(checks.length>0,'Actual captured checks must be included');
 const receiving=path.resolve(out+'/receiving');assert(!fs.existsSync(receiving),'Preserve previous receiving directory');fs.mkdirSync(receiving);
 for(const [name,bytes]of Object.entries(archive)){if(name.endsWith('/'))continue;assert(!name.startsWith('/')&&!name.split('/').includes('..'));const dest=path.resolve(receiving,name);assert(dest.startsWith(receiving+'/'));fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,bytes)}
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await page.screenshot({path:out+'/delivery-mobile.png',fullPage:true});
 assert.equal(starts,0);assert.equal(handoffs,1);assert.deepEqual(errors,[]);
 const after=await post('engineering/delivery');fs.writeFileSync(out+'/delivery-after.json',JSON.stringify(after,null,2)+'\n');
 fs.writeFileSync(out+'/browser-delivery-receipt.json',JSON.stringify({sourceCommit:live.sourceCommit,artifactSha256:artifact.sha256,handoffSha256:sha(fs.readFileSync(out+'/handoff.zip')),verifiedImplementationFiles:verified,relationBefore:before.relation,relationAfter:after.relation,checkStates:checks.map(c=>({id:c.id,state:c.state,status:c.result?.status})),starts,handoffs,pageErrors:errors,mobileNoOverflow:true,cloudOperations:false,receivingAcceptance:false},null,2)+'\n');
 console.log('Actual UI Delivery download verified',verified,'files');
}finally{await browser.close()}
