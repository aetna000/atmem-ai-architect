// Local artifact audit only. Missing Terraform providers are blocked, never a pass.
import fs from 'node:fs';
import path from 'node:path';
import {assessAwsDeploymentCandidate} from '../src/aws-validation.mjs';
import {AWS_SCENARIOS} from '../src/aws-validation-scenarios.mjs';
import {spawnSync} from 'node:child_process';
const root=path.resolve(process.argv[2]||'');
if(!process.argv[2]||!fs.existsSync(path.join(root,'validation.json')))throw Error('Pass an AWS live-validation run directory');
const report=JSON.parse(fs.readFileSync(path.join(root,'validation.json'),'utf8'));
const binary=process.env.ATMEM_ARCHITECT_TERRAFORM_BIN||path.resolve('.venv/bin/terraform');
const env={PATH:process.env.PATH,HOME:root,TF_IN_AUTOMATION:'1',CHECKPOINT_DISABLE:'1',AWS_EC2_METADATA_DISABLED:'true',...(process.env.ATMEM_ARCHITECT_TERRAFORM_TEST_CACHE?{TF_PLUGIN_CACHE_DIR:path.resolve(process.env.ATMEM_ARCHITECT_TERRAFORM_TEST_CACHE)}:{})};
for(const result of report.results||[]){
 const folder=path.join(root,result.evidenceDirectory||result.id);
 const dir=path.join(folder,'terraform');if(!fs.existsSync(dir))continue;
 const tf=JSON.parse(fs.readFileSync(path.join(dir,'main.tf.json'),'utf8'));
 const check={evidenceKind:'local-generated-artifact-check',cloudOperations:false,resourceTypes:Object.keys(tf.resource),deploymentCoverage:tf.locals.unfinished_work.length?'blocked':'generated_implementation',unfinishedWork:tf.locals.unfinished_work,checks:[]};
 if(fs.existsSync(path.join(dir,'build-runtime.py'))){
  const built=spawnSync(path.resolve('.venv/bin/python'),['build-runtime.py'],{cwd:dir,env,encoding:'utf8',timeout:180000});
  check.checks.push({name:'runtime-build',status:built.status===0?'passed':'failed',exitCode:built.status,stdout:built.stdout,stderr:built.stderr});
 }
 for(const [label,args] of [['provider-init',['init','-backend=false','-input=false','-no-color']],['configuration-load',['providers']],['provider-schema',['validate','-json']]]){
  const r=spawnSync(binary,[`-chdir=${dir}`,...args],{env,encoding:'utf8',timeout:180000});
  let diagnostics;try{diagnostics=JSON.parse(r.stdout);}catch{}
  check.checks.push({name:label,status:r.status===0?'passed':r.error||/Missing required provider|requires provider|not installed/i.test(r.stdout+r.stderr)?'blocked':'failed',exitCode:r.status,stdout:r.stdout||'',stderr:r.stderr||'',...(r.error?{error:r.error.code||r.error.name}:{})});
 }
 if(check.checks.every(c=>c.status==='passed')){
  const commands=[];
  if(fs.existsSync(path.join(dir,'app-tests')))commands.push(['application-tests',path.resolve('.venv/bin/python'),['-I','-m','unittest','discover','-s','app-tests','-p','*_test.py','-v']]);
  if(fs.existsSync(path.join(dir,'tests')))commands.push(['mock-plans',binary,['test','-no-color']]);
  for(const [name,bin,args]of commands){const r=spawnSync(bin,args,{cwd:dir,env,encoding:'utf8',timeout:180000});check.checks.push({name,status:r.status===0?'passed':'failed',exitCode:r.status,stdout:r.stdout,stderr:r.stderr});}
 }
 result.stages.applicationTests=check.checks.find(c=>c.name==='application-tests')?.status||'not_run';
 const receipt=path.join(folder,'artifact-validation.json');fs.writeFileSync(receipt,JSON.stringify(check,null,2));
 result.stages.localValidation=check.checks.every(c=>c.status==='passed')?'passed':check.checks.some(c=>c.status==='failed')?'failed':'blocked';
 const scenario=AWS_SCENARIOS.find(s=>s.id===result.id);
 if(scenario&&fs.existsSync(path.join(folder,'workspace.json')))result.deploymentAssessment=assessAwsDeploymentCandidate(JSON.parse(fs.readFileSync(path.join(folder,'workspace.json'),'utf8')),scenario,tf,{providerSchema:check.checks.find(c=>c.name==='provider-schema')?.status,applicationTests:result.stages.applicationTests});
 result.localValidationEvidence=path.relative(root,receipt);
 fs.writeFileSync(path.join(folder,'validation.json'),JSON.stringify(result,null,2));
 console.log(JSON.stringify({scenario:result.id,localValidation:result.stages.localValidation,checks:check.checks.map(({name,status})=>({name,status})),deploymentCoverage:check.deploymentCoverage}));
}
fs.writeFileSync(path.join(root,'validation.json'),JSON.stringify(report,null,2));
