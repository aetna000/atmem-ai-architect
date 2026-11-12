import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {googleDocumentJobTerraform} from '../src/enterprise-google-infrastructure.mjs';

const root=process.cwd(),out=path.resolve(process.argv[2]||'.local/enterprise-google-infrastructure');
if(!out.startsWith(path.join(root,'.local')+path.sep)||fs.existsSync(out))throw Error('Use a fresh owned local qualification directory');
const project={id:'private-knowledge-qualification',revision:7},row={id:'knowledge',address:'block_6b6e6f776c65646765',provider:'gcp',region:'australia-southeast1'};
const files=googleDocumentJobTerraform(project,row,'qualification');
const sources=['src/enterprise-google-infrastructure.mjs','src/enterprise-google-tests.mjs','src/cloud-provider-locks.mjs','scripts/qualify-enterprise-google-infrastructure.mjs','tests/enterprise-google-infrastructure.test.mjs','src/runtime/enterprise_google_jobs.py'];
const sourceHashes=Object.fromEntries(sources.map(name=>[name,createHash('sha256').update(fs.readFileSync(name)).digest('hex')]));
const hashes=()=>Object.fromEntries(Object.keys(files).map(name=>[name,createHash('sha256').update(fs.readFileSync(path.join(out,name))).digest('hex')]));
fs.mkdirSync(out,{recursive:true});
for(const[name,body]of Object.entries(files)){const target=path.join(out,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,body);}
const emittedHashes=hashes(),scratch=fs.mkdtempSync(path.join(os.tmpdir(),'atmem-google-documents-'));
const env={PATH:process.env.PATH,HOME:scratch,TMPDIR:scratch,TF_PLUGIN_CACHE_DIR:path.join(root,'.local/provider-cache'),CHECKPOINT_DISABLE:'1',TF_IN_AUTOMATION:'1'};
const checks=[],plans=[];let success=false;
function compact(value){
 if(Array.isArray(value))return value.map(compact);
 if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([key,item])=>[key,key==='provider_schemas'?{omitted:true,sha256:createHash('sha256').update(JSON.stringify(item)).digest('hex')}:compact(item)]));
 return value;
}
async function run(label,args){
 const child=spawn(path.join(root,'.venv/bin/terraform'),args,{cwd:out,env});let pending='',error=null;
 const stream=fs.createWriteStream(path.join(out,label+'.log'));
 function line(raw){
  if(label==='mock-plans'){
   try{const value=JSON.parse(raw);if(value.test_plan)plans.push(value.test_plan);stream.write(JSON.stringify(compact(value))+'\n');}
   catch{stream.write(raw+'\n');}
  }else stream.write(raw+'\n');
 }
 const stdout=(async()=>{for await(const chunk of child.stdout){pending+=chunk.toString();let index;while((index=pending.indexOf('\n'))>=0){line(pending.slice(0,index));pending=pending.slice(index+1);}}if(pending)line(pending);})();
 const stderr=(async()=>{for await(const chunk of child.stderr)stream.write(chunk);})();
 child.on('error',value=>{error=value.message;});
 const timer=setTimeout(()=>child.kill('SIGTERM'),180000),code=await new Promise(resolve=>child.on('close',resolve));clearTimeout(timer);
 await Promise.all([stdout,stderr]);await new Promise(resolve=>stream.end(resolve));
 checks.push({check:label,passed:code===0&&!error,exitCode:code,error});if(code!==0||error)throw Error('Native document infrastructure qualification failed: '+label);
}
try{
 await run('provider-init',['init','-backend=false','-input=false','-lockfile=readonly','-no-color']);
 await run('provider-schema',['validate','-json']);await run('mock-plans',['test','-json','-verbose']);
 const configurations=plans.map(plan=>plan.output_changes?.document_job_configuration?.after).filter(Boolean);
 if(!configurations.length)throw Error('No actual native mock-plan runtime output was observed');
 fs.writeFileSync(path.join(out,'runtime-configurations.json'),JSON.stringify(configurations,null,2)+'\n');
 if(JSON.stringify(hashes())!==JSON.stringify(emittedHashes)||Object.entries(sourceHashes).some(([name,hash])=>createHash('sha256').update(fs.readFileSync(name)).digest('hex')!==hash))throw Error('Qualification artifact/source drift');
 success=true;
}catch(error){checks.push({check:'qualification',passed:false,error:error.message});process.exitCode=1;}
finally{
 fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({recordedAt:new Date().toISOString(),passed:success,checks,sourceHashes,emittedHashes,
  cloudOperations:false,wholeProjectQualified:false,scope:'Exact compiler-emitted parser substrate, real Google7.46.2/google-beta7.46.2 provider schemas and credential-free mock plans. No native IAM/network/account or application/recovery acceptance.'},null,2)+'\n');
 fs.rmSync(scratch,{recursive:true,force:true});console.log(JSON.stringify({passed:success,checks}));
}
