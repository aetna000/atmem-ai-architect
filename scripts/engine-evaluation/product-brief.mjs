// Generic black-box client for the product's native job/artifact/check API.
// Briefs and optional follow-ups are evaluation inputs, never production recipes.
import fs from 'node:fs';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {toProjectFile} from '../../src/project-file.mjs';
const args=Object.fromEntries(process.argv.slice(2).reduce((items,value,index,all)=>value.startsWith('--')?[...items,[value.slice(2),all[index+1]]]:items,[]));
for(const key of ['brief','output','model','effort'])if(!args[key])throw Error(`Missing --${key}`);
const output=path.resolve(args.output);if(fs.existsSync(output))throw Error('Preserve the previous run; choose a new output directory.');fs.mkdirSync(output,{recursive:true});
const brief=fs.readFileSync(args.brief,'utf8'),updates=args.updates?JSON.parse(fs.readFileSync(args.updates,'utf8')):[];
if(!brief.trim()||brief.length>80000||!Array.isArray(updates)||updates.some(text=>typeof text!=='string'||!text.trim()||text.length>80000))throw Error('Brief/update text must be nonempty and bounded; no text was truncated.');
const seconds=Number(args.seconds||900);if(!Number.isInteger(seconds)||seconds<30||seconds>1800)throw Error('Choose a bounded 30–1800 second observation window.');
const base=args.base||'http://127.0.0.1:5274',sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const project={id:randomUUID(),version:1,revision:1,name:args.name||'Client architecture brief',provider:'tools',requirements:brief,nodes:[],edges:[]};
const source={};for(const folder of ['server','src'])for(const entry of fs.readdirSync(folder,{recursive:true})){const file=path.join(folder,entry);if(fs.statSync(file).isFile()&&/\.(py|jsx|mjs)$/.test(file)&&!file.includes('__pycache__'))source[file]=sha(fs.readFileSync(file));}
source['agent-skills/specialists/composition/SKILL.md']=sha(fs.readFileSync('agent-skills/specialists/composition/SKILL.md'));
fs.writeFileSync(path.join(output,'source-at-start.json'),JSON.stringify(source,null,2)+'\n');fs.writeFileSync(path.join(output,'brief.txt'),brief);fs.writeFileSync(path.join(output,'updates.json'),JSON.stringify(updates,null,2)+'\n');
const live={projectId:project.id,model:args.model,effort:args.effort,status:'starting',startedAt:new Date().toISOString(),observationSeconds:seconds,cloudOperations:false};
const persist=()=>fs.writeFileSync(path.join(output,'live.json'),JSON.stringify(live,null,2)+'\n');persist();
const session=await(await fetch(base+'/api/session')).json();
async function post(endpoint,body){const response=await fetch(base+'/api/'+endpoint,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify(body),signal:AbortSignal.timeout(90000)});const value=await response.json();if(!response.ok)throw Error(typeof value.detail==='string'?value.detail:`HTTP ${response.status}`);return value;}
let state,cursor=0;const events=[];
try{
 await post('projects/save',{id:project.id,file:toProjectFile(project)});
 state=await post('engineering/create',{projectId:project.id,model:args.model,effort:args.effort});
 if(state.model!==args.model||state.effort!==args.effort)throw Error('Exact model/effort was not confirmed.');
 const payload={projectId:project.id,sessionId:state.id};live.sessionId=state.id;persist();
 state=await post('engineering/start',{...payload,text:brief});live.status='running';persist();
 for(const text of updates){
  const current=await post('engineering/state',payload);
  state=await post('engineering/'+(current.state==='running'?'steer':'start'),{...payload,text});
 }
 const deadline=Date.now()+seconds*1000;let lastLog=0;
 while(Date.now()<deadline){
  const result=await post('engineering/events',{...payload,after:cursor});state=result.session;
  for(const event of result.events){events.push(event);fs.appendFileSync(path.join(output,'events.jsonl'),JSON.stringify(event)+'\n');cursor=event.sequence;}
  live.state=state;live.events=events.length;persist();
  if(state.state==='idle')break;
  if(Date.now()-lastLog>30000){console.log('Observed',state.state,'events',events.length);lastLog=Date.now();}
  await new Promise(resolve=>setTimeout(resolve,1000));
 }
 if(state.state==='running'){
  await post('engineering/interrupt',payload);live.status='interruption_requested';persist();
  const settle=Date.now()+30000;
  while(Date.now()<settle){state=await post('engineering/recover',payload);if(state.state==='idle')break;await new Promise(resolve=>setTimeout(resolve,1000));}
 }
 if(state.state!=='idle')throw Error('The existing run remains uncertain; no generation was replayed.');
 // Drain every durable event page, including late terminal/steering receipts.
 while(true){const result=await post('engineering/events',{...payload,after:cursor});for(const event of result.events){events.push(event);fs.appendFileSync(path.join(output,'events.jsonl'),JSON.stringify(event)+'\n');cursor=event.sequence;}if(result.events.length<200)break;}
 const artifact=await post('engineering/capture',payload);fs.writeFileSync(path.join(output,'artifact.json'),JSON.stringify(artifact,null,2)+'\n');
 const download=await fetch(base+'/api/engineering/download',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({...payload,artifactId:artifact.id})});if(!download.ok)throw Error('Artifact download failed.');const bytes=Buffer.from(await download.arrayBuffer());if(sha(bytes)!==artifact.sha256||download.headers.get('x-artifact-sha256')!==artifact.sha256)throw Error('Artifact digest mismatch.');fs.writeFileSync(path.join(output,'artifact.zip'),bytes);
 const catalog=await post('engineering/validators',payload),checks=[];
 if(catalog.available)for(const validator of catalog.validators){let check=await post('engineering/validation/start',{...payload,artifactId:artifact.id,validatorId:validator.id});const budget=Date.now()+360000;while(check.state!=='finished'&&Date.now()<budget){await new Promise(resolve=>setTimeout(resolve,1000));check=await post('engineering/validation/get',{...payload,checkId:check.id});}checks.push(check);}
 fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify(checks,null,2)+'\n');
 const changed=Object.entries(source).filter(([file,digest])=>sha(fs.readFileSync(file))!==digest).map(([file])=>file);
 Object.assign(live,{status:'artifacts_captured',state,artifactId:artifact.id,artifactSha256:artifact.sha256,fileCount:artifact.files.filter(file=>file.kind==='file').length,sourceChangedDuringRun:changed,
  acceptedRequests:events.filter(event=>event.kind==='accepted').length,steeringAccepted:events.filter(event=>event.kind==='steering_accepted').length,
  independentAcceptance:'not_established',boundary:'Client brief through current product API, exact model/effort, natural follow-ups, native work and immutable capture/check receipt. Generated tests, complete turns and files do not establish requirements, Terraform, service connections or system acceptance.'});persist();console.log(JSON.stringify(live,null,2));
}catch(error){live.status='requires_inspection';live.error=error.message;live.state=state;persist();console.error(error.message);process.exitCode=1;}
