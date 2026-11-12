// One authorized isolated UI submission. Never rerun after live.json exists.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {randomUUID,createHash}from 'node:crypto';import {execFileSync}from 'node:child_process';import {chromium}from '@playwright/test';
import {toProjectFile}from '../../../../src/project-file.mjs';
const base='http://127.0.0.1:5298',ev='specs/029-general-purpose-engine/evidence/20261112-ui-native-handoff',out='.local/external-artifacts/ui-native-handoff/v1',source=path.resolve('.local/external-artifacts/frozen-provider-eval/board-ui-v1');
assert(!fs.existsSync(out+'/live.json'),'Observe the existing run; do not submit again');
const contract=JSON.parse(fs.readFileSync(ev+'/acceptance-contract.json')),brief=fs.readFileSync(ev+'/client-brief.txt','utf8'),sha=b=>createHash('sha256').update(b).digest('hex');assert.equal(sha(brief),contract.briefSha256);
assert(execFileSync('git',['-C',source,'rev-parse','HEAD'],{encoding:'utf8'}).startsWith(contract.sourceCommit));
const inputs=execFileSync('git',['-C',source,'ls-files','src','server','agent-skills','knowledge','scripts'],{encoding:'utf8'}).trim().split('\n');fs.writeFileSync(out+'/source-at-start.json',JSON.stringify(Object.fromEntries(inputs.map(f=>[f,sha(fs.readFileSync(path.join(source,f)))])),null,2)+'\n');
const project={id:randomUUID(),version:1,revision:1,name:'UI diagnostic — rehearsal room bookings',provider:'tools',requirements:brief,nodes:[{id:'booking-app',type:'resource',position:{x:0,y:0},data:{label:'Rehearsal booking app',kind:'resource',provider:'tools',origin:'proposed',description:'Local browser and loopback HTTP application; durable room/date/slot bookings with conflict and idempotency controls.',config:{region:'Local workstation'}}}],edges:[]};
fs.writeFileSync(out+'/input-project.json',JSON.stringify(toProjectFile(project),null,2)+'\n');
const live={projectId:project.id,sourceCommit:contract.sourceCommit,model:contract.model,effort:contract.effort,briefSha256:sha(brief),status:'preparing_browser',starts:0,cloudOperations:false};
function save(){fs.writeFileSync(out+'/live.json',JSON.stringify(live,null,2)+'\n')};save();
const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],requests=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('request',r=>{const u=new URL(r.url());if(u.pathname==='/api/engineering/start'){live.starts++;requests.push(r.postDataJSON());save()}});
await page.addInitScript(({model,effort})=>{localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model,effort}));localStorage.setItem('atforma-draw-live','off')},contract);
try{
 await page.goto(base+'/');await page.locator('#project-file-input').setInputFiles(out+'/input-project.json');await page.getByText('Project opened.',{exact:true}).waitFor();
 await page.screenshot({path:out+'/design-before.png',fullPage:true});
 const accepted=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/engineering/start',{timeout:120000});
 await page.getByRole('region',{name:'Architecture journey',exact:true}).getByRole('button',{name:'Implement and check',exact:true}).click();
 const response=await accepted;const job=await response.json();assert(response.ok(),JSON.stringify(job));assert.equal(live.starts,1);assert.equal(job.model,contract.model);assert.equal(job.effort,contract.effort);
 live.context={projectId:project.id,sessionId:job.id};live.started=job;live.status='submitted_once';save();fs.writeFileSync(out+'/start-requests.json',JSON.stringify(requests,null,2)+'\n');
 await page.screenshot({path:out+'/implementation-started.png',fullPage:true});assert.deepEqual(errors,[]);console.log(JSON.stringify(live));
}catch(e){live.status='inspect_before_any_retry';live.error=e.message;save();await page.screenshot({path:out+'/start-error.png',fullPage:true}).catch(()=>{});throw e}
finally{fs.writeFileSync(out+'/start-browser-errors.json',JSON.stringify(errors));await browser.close()}
