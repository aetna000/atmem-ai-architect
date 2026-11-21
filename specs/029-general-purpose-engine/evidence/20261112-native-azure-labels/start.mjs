// Deliberate one-time fresh product session; observation never submits inference.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {randomUUID,createHash}from 'node:crypto';import {execFileSync}from 'node:child_process';
import {toProjectFile}from '../../../../src/project-file.mjs';
const base='http://127.0.0.1:5288',e='specs/029-general-purpose-engine/evidence/20261112-native-azure-labels',out='.local/external-artifacts/native-azure-labels/v1',source=path.resolve('.local/external-artifacts/frozen-provider-eval/de77256');
assert(!fs.existsSync(out),'Preserve existing run and observe it instead');fs.mkdirSync(out,{recursive:true});
const commit=execFileSync('git',['-C',source,'rev-parse','HEAD'],{encoding:'utf8'}).trim();assert(commit.startsWith('de77256'));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');const files=execFileSync('git',['-C',source,'ls-files','server','src','knowledge','agent-skills','scripts'],{encoding:'utf8'}).trim().split('\n');
fs.writeFileSync(out+'/source-at-start.json',JSON.stringify(Object.fromEntries(files.map(file=>[file,sha(fs.readFileSync(path.join(source,file)))])),null,2)+'\n');
const text=fs.readFileSync(e+'/client-brief.txt','utf8'),contract=JSON.parse(fs.readFileSync(e+'/acceptance-contract.json'));assert.equal(sha(text),contract.briefSha256);
const auth=await(await fetch(base+'/api/session')).json();
async function post(action,payload){const r=await fetch(base+'/api/'+action,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+auth.token},body:JSON.stringify(payload),signal:AbortSignal.timeout(90000)});const v=await r.json();if(!r.ok)throw Error(JSON.stringify(v));return v;}
const project={id:randomUUID(),version:1,revision:1,name:'Exposed Azure transfer — museum exhibit labels',provider:'azure',requirements:text,nodes:[],edges:[]};
await post('projects/save',{id:project.id,file:toProjectFile(project)});const session=await post('engineering/create',{projectId:project.id,model:contract.model,effort:contract.effort});const context={projectId:project.id,sessionId:session.id};
fs.writeFileSync(e+'/context-v1.json',JSON.stringify(context,null,2)+'\n');const catalog=await post('engineering/validators',context);fs.writeFileSync(out+'/catalog.json',JSON.stringify(catalog,null,2)+'\n');
assert(catalog.validators.some(v=>v.id==='python-sql-azure-tests'&&v.available&&v.runtime.platform==='linux/amd64'));
const live={context,sourceCommit:commit,status:'submitting_once',briefSha256:sha(text),model:contract.model,effort:contract.effort,cloudOperations:false};fs.writeFileSync(out+'/live.json',JSON.stringify(live,null,2)+'\n');
live.started=await post('engineering/start',{...context,text});live.status='submitted';fs.writeFileSync(out+'/live.json',JSON.stringify(live,null,2)+'\n');console.log(JSON.stringify(live));
