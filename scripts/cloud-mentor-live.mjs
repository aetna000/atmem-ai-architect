// Explicit opt-in real-model browser qualification; never deploys to cloud accounts.
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
import {chromium} from '@playwright/test';
import {unzipSync} from 'fflate';
import {CLOUD_STORAGE_SCENARIOS} from '../src/cloud-storage-scenarios.mjs';
import {AI_QUALIFICATION_SCENARIOS,assessAiArchitecture} from '../src/ai-qualification-scenarios.mjs';
import {AWS_SCENARIOS} from '../src/aws-validation-scenarios.mjs';
const root=path.resolve(import.meta.dirname,'..'),out=path.join(root,'.local/cloud-mentor',new Date().toISOString().replaceAll(':','-'));fs.mkdirSync(out,{recursive:true});
const architectProvider=process.env.ATMEM_ARCHITECT_VALIDATION_PROVIDER||'claude-code';
const selected=(process.argv[2]||'aws,azure,gcp,ibm').split(',');
const storageScenarios=[{id:'aws',prompt:AWS_SCENARIOS[0].prompt+' An existing IAM operator needs upload, read and delete access. Draw the caller and its explicit scoped access contract. Do not deploy.'},...CLOUD_STORAGE_SCENARIOS].filter(s=>selected.includes(s.id));
const scenarios=process.argv.includes('--ai')?AI_QUALIFICATION_SCENARIOS.filter(s=>selected.includes(s.provider)||selected.includes(s.id)):storageScenarios;
const source=path.join(out,'source');fs.mkdirSync(source,{recursive:true});
for(const name of ['CONSTITUTION.md','knowledge','src','server','scripts','agent-skills','.specify','public','index.html','vite.config.mjs','package.json'])if(fs.existsSync(path.join(root,name)))fs.cpSync(path.join(root,name),path.join(source,name),{recursive:true,filter:p=>!p.split(path.sep).includes('__pycache__')});
for(const name of ['node_modules','.venv','.memory-venv'])if(fs.existsSync(path.join(root,name)))fs.symlinkSync(path.join(root,name),path.join(source,name),'dir');
fs.mkdirSync(path.join(source,'.local'),{recursive:true});fs.symlinkSync(path.join(root,'.local/cloud-emulators'),path.join(source,'.local/cloud-emulators'),'dir');
async function port(){const s=createServer();await new Promise(r=>s.listen(0,'127.0.0.1',r));const p=s.address().port;await new Promise(r=>s.close(r));return p;}
const ui=await port(),api=await port(),base=`http://127.0.0.1:${ui}`;
const env={...process.env,ATMEM_ARCHITECT_HOME:path.join(out,'home'),ATMEM_ARCHITECT_PORT:String(ui),ATMEM_ARCHITECT_SIDECAR_PORT:String(api)};
for(const key of Object.keys(env))if(key.startsWith('AWS_')||['OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY','GOOGLE_API_KEY','GITHUB_TOKEN','GH_TOKEN'].includes(key))delete env[key];
const log=fs.openSync(path.join(out,'services.log'),'a'),children=[];let browser;const results=[];let providerBlocked=null;
try{
 for(const [bin,args]of [[path.join(root,'.venv/bin/python'),['-m','uvicorn','server.app:app','--host','127.0.0.1','--port',String(api),'--no-access-log']],[process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(ui),'--strictPort']]])children.push(spawn(bin,args,{cwd:source,env,stdio:['ignore',log,log]}));
 for(const url of [base,`http://127.0.0.1:${api}/api/session`])for(let i=0;i<200;i++){try{if((await fetch(url)).ok)break;}catch{}if(i===199)throw Error('Service startup failed');await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true});
 for(const scenario of scenarios){
  if(providerBlocked){results.push({provider:scenario.id,architectProvider,evidenceKind:"not-run-provider-unavailable",passed:false,error:providerBlocked,cloudOperations:false});continue;}
  const folder=path.join(out,scenario.id);fs.mkdirSync(folder,{recursive:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000}});await context.addInitScript(provider=>localStorage.setItem('atforma-connection-v1',JSON.stringify({provider,model:'default',effort:'low'})),architectProvider);
  const page=await context.newPage();page.setDefaultTimeout(30000);const errors=[],turns=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('response',async response=>{if(response.url().endsWith('/api/architect')){try{turns.push({request:response.request().postDataJSON(),response:await response.json()});}catch{}}});
  const record={provider:scenario.id,architectProvider,evidenceKind:'real-model-browser-run',cloudOperations:false};
  try{
   await page.goto(base);await page.locator('.model .led.on').waitFor({timeout:90000});
   const reply=page.waitForResponse(r=>r.url().endsWith('/api/architect'),{timeout:480000});await page.getByLabel('Your message').fill(scenario.prompt);await page.keyboard.press('Enter');const r=await reply;if(!r.ok())throw Error((await r.json()).detail||'Model request failed');await page.waitForFunction(()=>!document.querySelector('.msg.working'),{},{timeout:30000});
   await page.screenshot({path:path.join(folder,'architecture.png'),fullPage:true});
   await page.getByRole('region',{name:'Architecture journey'}).getByRole('button',{name:'Emulate & improve',exact:true}).click();
   const panel=page.getByRole('complementary',{name:'Cloud emulation'});
   const reportPromise=page.waitForResponse(r=>r.url().endsWith('/api/emulation/run'),{timeout:120000});
   const coachPromise=page.waitForResponse(r=>r.url().endsWith('/api/architect')&&r.request().postDataJSON()?.origin==='emulation',{timeout:480000});coachPromise.catch(()=>{});
   await panel.getByRole('button',{name:'Emulate locally',exact:true}).click();
   const report=await (await reportPromise).json();fs.writeFileSync(path.join(folder,'emulation.json'),JSON.stringify(report,null,2));record.emulation=report.status;
   const coaching=await (await coachPromise).json();fs.writeFileSync(path.join(folder,'coaching.json'),JSON.stringify(coaching,null,2));record.mentorResponded=Boolean(coaching.message);if(coaching.detail){record.providerIssue=coaching.detail;if(/usage or rate limit|sign in again/.test(String(coaching.detail)))providerBlocked=String(coaching.detail);}
   await page.waitForFunction(()=>!document.querySelector('.msg.working'),{},{timeout:30000});
   fs.writeFileSync(path.join(folder,'rendered-conversation.txt'),await page.locator('.msg').allTextContents().then(parts=>parts.join('\n\n')));
   await page.screenshot({path:path.join(folder,'mentor.png'),fullPage:true});
   const workspace=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));fs.writeFileSync(path.join(folder,'workspace.json'),JSON.stringify(workspace,null,2));
   await page.getByRole('region',{name:'Architecture journey'}).getByRole('button',{name:'Outputs',exact:true}).click();
   const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download reviewed ZIP',exact:true}).click();await(await download).saveAs(path.join(folder,'delivery.zip'));
   const files=unzipSync(fs.readFileSync(path.join(folder,'delivery.zip')));for(const [name,bytes]of Object.entries(files))if(name==='project.atmem-ai-architect.json'||name==='diagram.svg'||name.startsWith('terraform/')){const dest=path.join(folder,name);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,bytes);}
   record.architecturePresent=workspace.nodes.filter(n=>n.data.kind!=='note').length>=3&&workspace.edges.length>=2;
   record.acceptanceRequirements=scenario.checks||[];if(scenario.family)record.staticAssessment=assessAiArchitecture(workspace,scenario);
   record.components=workspace.nodes.map(n=>({id:n.id,service:n.data.service,implementation:n.data.implementation,binding:n.data.binding}));record.passed=record.emulation==='passed'&&record.mentorResponded&&errors.length===0;record.mentorJourneyPassed=record.mentorResponded&&errors.length===0&&(scenario.family?record.architecturePresent:true);
  }catch(error){record.passed=false;record.error=error.message;if(/usage or rate limit|sign in again/.test(error.message))providerBlocked=error.message;await page.screenshot({path:path.join(folder,'failure.png'),fullPage:true}).catch(()=>{});}
  finally{fs.writeFileSync(path.join(folder,'prompt-history.json'),JSON.stringify(turns,null,2));fs.writeFileSync(path.join(folder,'results.json'),JSON.stringify({...record,errors},null,2));results.push(record);console.log(JSON.stringify(record));await context.close();}
 }
}finally{await browser?.close();for(const child of children)child.kill('SIGTERM');fs.closeSync(log);fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));console.log(out);}
if(results.some(r=>!r.passed))process.exitCode=1;
