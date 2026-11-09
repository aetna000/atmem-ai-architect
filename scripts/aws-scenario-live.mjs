// Opt-in real-model UI validation. Never calls AWS provisioning APIs.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
import {chromium} from '@playwright/test';
import {unzipSync,strFromU8} from 'fflate';
import {assessAwsArchitecture,assessAwsDeploymentCandidate,awsRefinementPrompt} from '../src/aws-validation.mjs';
import {AWS_SCENARIOS} from '../src/aws-validation-scenarios.mjs';
const chosen=process.argv[2]||'01-private-storage';
const selected=new Set(chosen.split(','));
const scenarios=chosen==='all'?AWS_SCENARIOS:AWS_SCENARIOS.filter(s=>selected.has(s.id));
if(!scenarios.length)throw Error('Unknown scenario');
const rounds=Number(process.argv[3]||1);
if(!Number.isInteger(rounds)||rounds<1||rounds>3)throw Error('Choose 1–3 bounded refinement rounds');
const provider=process.env.ATMEM_ARCHITECT_VALIDATION_PROVIDER||'claude-code';
const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'.local','aws-validation',new Date().toISOString().replaceAll(':','-'));
fs.mkdirSync(out,{recursive:true});
// Freeze the application source for the entire prompt/refinement run. Developer edits
// must not hot-reload the page and cancel an in-flight model response.
const source=path.join(out,'source');fs.mkdirSync(source,{recursive:true});
for(const name of ['CONSTITUTION.md','knowledge','src','server','scripts','agent-skills','.specify','public','index.html','vite.config.mjs','vite.config.js','package.json']){
 const from=path.join(root,name);if(fs.existsSync(from))fs.cpSync(from,path.join(source,name),{recursive:true,filter:p=>!p.split(path.sep).includes('__pycache__')});
}
for(const name of ['node_modules','.venv'])fs.symlinkSync(path.join(root,name),path.join(source,name),'dir');

const freePort=async()=>{const s=createServer();await new Promise(r=>s.listen(0,'127.0.0.1',r));const p=s.address().port;await new Promise(r=>s.close(r));return p;};
const uiPort=await freePort(),apiPort=await freePort();
const env={...process.env,ATMEM_ARCHITECT_HOME:path.join(out,'home'),ATMEM_ARCHITECT_PORT:String(uiPort),ATMEM_ARCHITECT_SIDECAR_PORT:String(apiPort)};
for(const key of Object.keys(env))if(key.startsWith('AWS_')||['OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY','GOOGLE_API_KEY','GITHUB_TOKEN','GH_TOKEN'].includes(key))delete env[key];
const log=fs.openSync(path.join(out,'services.log'),'a'),children=[];
const start=(bin,args)=>children.push(spawn(bin,args,{cwd:source,env,stdio:['ignore',log,log]}));
let browser;
const results=[];
async function waitForServer(url){for(let n=0;n<150;n++){try{if((await fetch(url)).ok)return;}catch{}await new Promise(r=>setTimeout(r,100));}throw Error('Local test service did not start');}
try{
 start(path.join(root,'.venv/bin/python'),['-m','uvicorn','server.app:app','--host','127.0.0.1','--port',String(apiPort),'--no-access-log']);
 start(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(uiPort),'--strictPort']);
 await Promise.all([waitForServer(`http://127.0.0.1:${uiPort}`),waitForServer(`http://127.0.0.1:${apiPort}/api/session`)]);
 browser=await chromium.launch({headless:true});
 for(const scenario of scenarios){
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  await context.addInitScript(provider=>localStorage.setItem('atforma-connection-v1',JSON.stringify({provider,model:'default',effort:'low'})),provider);
  const page=await context.newPage();page.setDefaultTimeout(30000);
  let previous;
  for(let round=1;round<=rounds;round++){
  const evidenceDirectory=rounds===1?scenario.id:`${scenario.id}/round-${round}`;
  const folder=path.join(out,evidenceDirectory);fs.mkdirSync(folder,{recursive:true});
  const record={id:scenario.id,round,evidenceDirectory,provider,model:'default',evidenceKind:'real-model-browser-run',stages:{prompt:'not_run',architecture:'not_run',export:'not_run',localValidation:'not_run',cloudPlan:'not_run',deployment:'not_run',applicationTests:'not_run',cleanup:'not_run'},checks:scenario.checks,blockers:[]};
  try{
   if(round===1)await page.goto(`http://127.0.0.1:${uiPort}`);
   await page.getByLabel('Your message').waitFor();
   await page.locator('.model .led.on').waitFor({timeout:30000});
   const prompt=previous?(process.env.ATMEM_ARCHITECT_VALIDATION_FOLLOWUP||awsRefinementPrompt(previous)):scenario.prompt+' Use AWS for this synthetic qualification design. Propose Sydney as a candidate region, but do not record that as an approved deployment region. Draw the architecture and identify the next missing decision. This is a test design, not an instruction to deploy.';
   fs.writeFileSync(path.join(folder,'prompt.txt'),prompt);
   console.log(JSON.stringify({scenario:scenario.id,round,event:'prompt_submitted',provider}));
   const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/architect')&&r.request().method()==='POST',{timeout:480000});
   await page.getByLabel('Your message').fill(prompt);await page.keyboard.press('Enter');
   const response=await responsePromise,body=await response.json();
   fs.writeFileSync(path.join(folder,'model-response.json'),JSON.stringify(body,null,2));
   if(!response.ok())throw Error(`Architect HTTP ${response.status()}`);
   record.stages.prompt='passed';
   await page.waitForFunction(()=>!document.querySelector('.msg.working'),{},{timeout:30000});
   const project=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));
   fs.writeFileSync(path.join(folder,'workspace.json'),JSON.stringify(project,null,2));
   const names=project.nodes.filter(n=>n.data.kind!=='note').map(n=>`${n.data.service||''} ${n.data.label}`.toLowerCase());
   const missing=scenario.expected.filter(name=>!names.some(n=>n.includes(name)));
   record.components=project.nodes.filter(n=>n.data.kind!=='note').map(n=>({id:n.id,label:n.data.label,service:n.data.service,origin:n.data.origin}));
   record.architectureAssessment=assessAwsArchitecture(project,scenario);
   record.stages.architecture=record.architectureAssessment.passed?'passed':'failed';
   for(const check of record.architectureAssessment.checks.filter(c=>!c.passed))record.blockers.push(`Architecture structural check failed: ${check.id}`);
   if(missing.length)record.blockers.push(`Expected service families absent: ${missing.join(', ')}`);
   if(!names.length)record.blockers.push('No architecture was applied through the UI');
   await page.getByRole('tab',{name:'Board',exact:true}).click();
   await page.screenshot({path:path.join(folder,'architecture.png'),fullPage:true});
   if(names.length){
    await page.getByRole('region',{name:'Architecture journey',exact:true}).getByRole('button',{name:'Outputs',exact:true}).click();
    const outputs=page.getByRole('region',{name:'Outputs',exact:true});
    const button=outputs.getByRole('button',{name:'Download reviewed ZIP',exact:true});
    await button.waitFor();await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='Download reviewed ZIP'&&!b.disabled),{},{timeout:120000});
    const downloadPromise=page.waitForEvent('download',{timeout:120000});downloadPromise.catch(()=>{});
    await button.click();
    const download=await downloadPromise;await download.saveAs(path.join(folder,'delivery.zip'));
    const files=unzipSync(fs.readFileSync(path.join(folder,'delivery.zip')));
    for(const name of ['diagram.svg','spec-kit/readiness.json','spec-kit/tasks.json','project.atmem-ai-architect.json',...Object.keys(files).filter(n=>n.startsWith('terraform/')&&!n.split('/').includes('..'))]){
     const dest=path.join(folder,name);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,strFromU8(files[name]));
    }
    const tf=JSON.parse(strFromU8(files['terraform/main.tf.json']));
    record.artifactSha256=createHash('sha256').update(fs.readFileSync(path.join(folder,'delivery.zip'))).digest('hex');
    record.resourceTypes=Object.keys(tf.resource).filter(k=>k!=='terraform_data');
    record.unfinishedWork=tf.locals.unfinished_work;
    record.deploymentAssessment=assessAwsDeploymentCandidate(project,scenario,tf);
    previous=record.deploymentAssessment;
    record.stages.export='passed';
    if(record.unfinishedWork.length)record.blockers.push(`${record.unfinishedWork.length} generated infrastructure/integration gaps block a deployment plan`);
    record.blockers.push('Product qualification loop: close implementation gaps and validate this artifact before any account plan or deployment');
   }
  }catch(error){record.error=error.message;record.blockers.push(error.message);}
  finally{
   results.push(record);fs.writeFileSync(path.join(folder,'validation.json'),JSON.stringify(record,null,2));
   fs.writeFileSync(path.join(out,'validation.json'),JSON.stringify({scope:'AWS scenario qualification',cloudOperations:false,results},null,2));
   console.log(JSON.stringify({scenario:scenario.id,stages:record.stages,blockers:record.blockers,evidence:folder}));
  }
  if(!previous)break;
  }
  await context.close();
 }
}finally{await browser?.close();for(const child of children)child.kill('SIGTERM');fs.closeSync(log);}
console.log(`Validation evidence: ${out}`);
if(results.some(r=>r.stages.architecture!=='passed'||r.stages.export!=='passed'))process.exitCode=1;
