import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {awsDocumentJobTerraform} from '../src/enterprise-aws-infrastructure.mjs';

const root=process.cwd(),out=path.resolve(process.argv[2]||'.local/enterprise-aws-infrastructure');
if(!out.startsWith(path.join(root,'.local')+path.sep)||fs.existsSync(out))throw Error('Use a fresh owned local qualification directory');
const project={id:'private-knowledge-qualification',revision:7},row={id:'knowledge',address:'block_6b6e6f776c65646765',provider:'aws',region:'ap-southeast-2'};
const literalProbe=process.argv[3]==='--literal-probe';
if(process.argv[3]&&!literalProbe)throw Error('Unknown local fixture mode');
if(literalProbe){row.id='${file("literal-evaluation-probe.txt")} %{if true} marker %{endif}';row.address='block_'+Buffer.from(row.id).toString('hex');}
const files=awsDocumentJobTerraform(project,row,'qualification');
const sources=['tests/enterprise-aws-infrastructure.test.mjs','src/enterprise-aws-infrastructure.mjs','src/enterprise-aws-infrastructure-tests.mjs','src/runtime/enterprise-aws-task-template.json','src/runtime/enterprise-aws-host-bootstrap-source.json','src/runtime/enterprise_aws_host_bootstrap.py','scripts/qualify-enterprise-aws-infrastructure.mjs','src/enterprise-aws-host-infrastructure.mjs','src/enterprise-aws-host-tests.mjs','src/cloud-provider-locks.mjs','src/runtime/enterprise-aws-host-probe-source.json','src/runtime/enterprise_aws_host_probe.py','src/runtime/enterprise_aws_hosts.py','scripts/qualify-enterprise-aws-host-infrastructure.mjs','tests/enterprise-aws-host-infrastructure.test.mjs'];
const sourceHashes=Object.fromEntries(sources.map(name=>[name,createHash('sha256').update(fs.readFileSync(name)).digest('hex')]));
const hashes=()=>Object.fromEntries(Object.keys(files).map(name=>[name,createHash('sha256').update(fs.readFileSync(path.join(out,name))).digest('hex')]));
fs.mkdirSync(out,{recursive:true});
for(const[name,body]of Object.entries(files)){const target=path.join(out,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,body);}
if(literalProbe)fs.writeFileSync(path.join(out,'literal-evaluation-probe.txt'),'OWNED_SYNTHETIC_EXPRESSION_EVALUATION_PROBE');
const emittedHashes=hashes(),scratch=fs.mkdtempSync(path.join(os.tmpdir(),'atmem-aws-pool-'));
const env={PATH:process.env.PATH,HOME:scratch,TMPDIR:scratch,TF_PLUGIN_CACHE_DIR:path.join(root,'.local/provider-cache'),CHECKPOINT_DISABLE:'1',TF_IN_AUTOMATION:'1'};
const checks=[],plans=[],readyPlans=[];let success=false;
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
   try{const value=JSON.parse(raw);if(value.test_plan){plans.push(value.test_plan);if(value['@testrun']==='private_document_substrate')readyPlans.push(value.test_plan);}stream.write(JSON.stringify(compact(value))+'\n');}
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
 const configurations=readyPlans.map(plan=>plan.output_changes?.document_job_configuration?.after).filter(Boolean);
 if(!configurations.length)throw Error('No actual native mock-plan runtime output was observed');
 const provenance=plans.flatMap(plan=>(plan.resource_changes||[]).filter(value=>value.address==='terraform_data.'+row.address+'_review').map(value=>value.change?.after?.input?.source_component)).filter(value=>value!==undefined);
 if(!provenance.length||provenance.some(value=>value!==row.id))throw Error('Untrusted source component was evaluated instead of preserved as literal design evidence');
 fs.writeFileSync(path.join(out,'runtime-configurations.json'),JSON.stringify(configurations,null,2)+'\n');
 if(JSON.stringify(hashes())!==JSON.stringify(emittedHashes)||Object.entries(sourceHashes).some(([name,hash])=>createHash('sha256').update(fs.readFileSync(name)).digest('hex')!==hash))throw Error('Qualification artifact/source drift');
 success=true;
}catch(error){checks.push({check:'qualification',passed:false,error:error.message});process.exitCode=1;}
finally{
 fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({recordedAt:new Date().toISOString(),passed:success,checks,sourceHashes,emittedHashes,literalProbe,sourceComponent:row.id,
  cloudOperations:false,wholeProjectQualified:false,scope:'Exact compiler-emitted new private execution substrate and child fixed host verifier, AWS6.72.0 provider schema and credential-free mock plans. No cloud account/host/IAM behavior, whole application/export, performance or deployment acceptance.'},null,2)+'\n');
 fs.rmSync(scratch,{recursive:true,force:true});console.log(JSON.stringify({passed:success,checks}));
}
