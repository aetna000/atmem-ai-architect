// Qualification of compiler-owned source only. No account credentials or cloud plans.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {azureStructuredProject} from '../tests/fixtures/azure-structured-project.mjs';
import {terraformSketch} from '../src/terraform.mjs';
const root=path.resolve('.'),out=path.resolve(process.argv[2]||'.local/azure-structured-qualification'),tmp=fs.mkdtempSync('/tmp/aaz-');
const files=terraformSketch(azureStructuredProject()),checks=[];
fs.mkdirSync(out,{recursive:true});
for(const [name,body] of Object.entries(files)){const p=path.join(out,name);fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,body);}
const env={PATH:process.env.PATH,HOME:tmp,TMPDIR:tmp,TF_IN_AUTOMATION:'1',CHECKPOINT_DISABLE:'1',TF_PLUGIN_CACHE_DIR:path.join(root,'.local/provider-cache'),PYTHONDONTWRITEBYTECODE:'1'};
const sdk=path.resolve(process.env.ATMEM_AZURE_QUALIFICATION_SDK||'.local/azure-runtime-sdk');
const python=process.env.ATMEM_GENERATED_RUNTIME_PYTHON||'/opt/homebrew/bin/python3.13';
const tf=path.join(root,'.venv/bin/terraform');
function run(name,command,args,cwd=out){
 const r=spawnSync(command,args,{cwd,env,encoding:'utf8',timeout:120000,maxBuffer:3*1024*1024});
 const log=(r.stdout||'')+'\n'+(r.stderr||'');fs.writeFileSync(path.join(out,name+'.log'),log);
 checks.push({name,passed:r.status===0&&!r.error,exitCode:r.status,error:r.error?.message||null,logSha256:crypto.createHash('sha256').update(log).digest('hex')});
 if(r.status!==0||r.error)throw Error(name+' failed: '+log.slice(-2000));
}
try{
 const quality=JSON.parse(files['generation-quality.json']);if(quality.fatalFindings.length)throw Error(JSON.stringify(quality.fatalFindings));
 const apps=[...new Set(Object.keys(files).filter(p=>p.endsWith('/azure_acceptance.py')).map(p=>path.dirname(p)))];
 for(const folder of apps){
  const app=path.join(out,folder);
  // Block all actual sockets even if a test's scripted boundary is accidentally omitted.
  const wrapper=`import sys,runpy,socket\nsys.path[:0]=[${JSON.stringify(sdk)},${JSON.stringify(app)}]\ndef denied(*args,**kwargs):raise RuntimeError('Qualification forbids external network access')\nsocket.socket.connect=denied;socket.socket.connect_ex=denied;socket.getaddrinfo=denied\nsys.argv=['azure_acceptance.py','-v']\nrunpy.run_path(${JSON.stringify(path.join(app,'azure_acceptance.py'))},run_name='__main__')\n`;
  run(path.basename(folder)+'-runtime',python,['-I','-c',wrapper],app);
 }
 run('provider-init',tf,['init','-backend=false','-input=false','-lockfile=readonly','-no-color']);
 run('provider-schema',tf,['validate','-json']);
 run('provider-mocks',tf,['test','-no-color']);
}catch(error){checks.push({name:'qualification',passed:false,error:error.message});process.exitCode=1;}
finally{
 const receipt={kind:'azure-generated-source-local-qualification',checks,passed:checks.length>0&&checks.every(c=>c.passed),cloudOperations:false,artifactHashes:Object.fromEntries(Object.entries(files).map(([name,body])=>[name,crypto.createHash('sha256').update(body).digest('hex')])),boundary:'Emitted Python 3.13 source, real cryptographic/ASGI tests with scripted Entra key/model/policy transport and denied external sockets; native Terraform schemas and mock plans. No container image startup/scan, Azure account plan, Entra sign-in/MFA/revocation, real model-quality test or deployment.'};
 fs.writeFileSync(path.join(out,'qualification.json'),JSON.stringify(receipt,null,2)+'\n');fs.rmSync(tmp,{recursive:true,force:true});console.log(JSON.stringify({passed:receipt.passed,checks:checks.map(c=>({name:c.name,passed:c.passed})),receipt:path.join(out,'qualification.json')}));
}
