// Component source qualification only; this is not a complete cloud composition.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {publicFaqFiles,PUBLIC_FAQ_SERVICES} from '../src/public-faq.mjs';
const provider=process.argv[2];if(!PUBLIC_FAQ_SERVICES[provider])throw Error('Choose aws, azure, gcp or ibm');
const root=path.resolve('.'),out=path.resolve(process.argv[3]||'.local/public-faq-source-'+provider),files=publicFaqFiles(provider,'block_666171'),checks=[];
const sdk=path.resolve(process.env.ATMEM_FAQ_QUALIFICATION_SDK||({aws:'.local/aws-web-runtime-sdk',azure:'.local/azure-runtime-sdk',gcp:'.local/azure-runtime-sdk',ibm:'.local/ibm-runtime-sdk'}[provider]));
const python=process.env.ATMEM_GENERATED_RUNTIME_PYTHON||'/opt/homebrew/bin/python3.13',scratch=fs.mkdtempSync('/tmp/atmem-faq-');
const env={PATH:process.env.PATH,HOME:scratch,TMPDIR:scratch,AWS_EC2_METADATA_DISABLED:'true',PYTHONDONTWRITEBYTECODE:'1'};
fs.mkdirSync(out,{recursive:true});for(const [name,body]of Object.entries(files)){const target=path.join(out,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,body);}
const app=path.join(out,'applications/block_666171');
function run(name,command,args){const r=spawnSync(command,args,{cwd:app,env,encoding:'utf8',timeout:60000,maxBuffer:3*1024*1024});const log=(r.stdout||'')+'\n'+(r.stderr||'');fs.writeFileSync(path.join(out,name+'.log'),log);checks.push({name,passed:r.status===0&&!r.error,exitCode:r.status,error:r.error?.message||null,logSha256:createHash('sha256').update(log).digest('hex')});if(r.status!==0||r.error)throw Error(name+' failed: '+log.slice(-1800));}
try{
 run('dependency-closure',path.join(root,'.venv/bin/python'),[path.join(root,'scripts/check-python-runtime-lock.py'),app,sdk]);
 const wrapper=`import sys,runpy,socket\nsys.dont_write_bytecode=True\nsys.path[:0]=[${JSON.stringify(sdk)},${JSON.stringify(app)}]\ndef denied(*args,**kwargs):raise RuntimeError('Qualification denies external sockets')\nsocket.socket.connect=denied;socket.socket.connect_ex=denied;socket.getaddrinfo=denied\nsys.argv=['faq_acceptance.py','-v']\nrunpy.run_path(${JSON.stringify(path.join(app,'faq_acceptance.py'))},run_name='__main__')\n`;
 run('public-lifecycle-tests',python,['-I','-c',wrapper]);
}catch(error){checks.push({name:'source-qualification',passed:false,error:error.message});process.exitCode=1;}
finally{const receipt={kind:'public-faq-component-source-qualification',provider,checks,passed:checks.length===2&&checks.every(c=>c.passed),sourceHashes:Object.fromEntries(Object.entries(files).map(([n,b])=>[n,createHash('sha256').update(b).digest('hex')])),cloudOperations:false,nearDeploymentQualified:false,boundary:'Emitted component Python 3.13, actual pinned dependency metadata, local catalog/editor/ASGI and scripted native object-store transport tests with external sockets denied. This is not a complete provider Terraform/role composition, Linux image, cloud IAM, real-model semantic acceptance, account plan or deployment.'};fs.writeFileSync(path.join(out,'qualification.json'),JSON.stringify(receipt,null,2)+'\n');fs.rmSync(scratch,{recursive:true,force:true});console.log(JSON.stringify({provider,passed:receipt.passed,checks:checks.map(c=>({name:c.name,passed:c.passed})),receipt:path.join(out,'qualification.json')}));}
