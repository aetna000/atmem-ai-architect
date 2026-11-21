// Local emitted-package qualification; never runs an account plan or deployment.
import fs from 'node:fs';import path from 'node:path';import {spawnSync} from 'node:child_process';import {createHash} from 'node:crypto';
import {structuredWebProject} from '../tests/fixtures/structured-web-project.mjs';import {terraformSketch} from '../src/terraform.mjs';
const root=path.resolve('.'),dir=path.resolve(process.argv[2]||'.local/structured-web-qualification');fs.mkdirSync(dir,{recursive:true});
const files=terraformSketch(structuredWebProject());for(const [name,body]of Object.entries(files)){const target=path.join(dir,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,body);}
// Reuse the reviewed installed provider lock; no new provider version is selected by a floating init.
const lock=path.resolve('.local/generator-qualification/aws/.terraform.lock.hcl');
const alternate=path.resolve('specs/027-deployment-grade-generator/evidence/20261110-harness-qualification-r2/terraform-fixtures/aws/.terraform.lock.hcl');
const found=[lock,alternate].find(fs.existsSync);if(!found)throw Error('Reviewed provider lock missing');fs.copyFileSync(found,path.join(dir,'.terraform.lock.hcl'));
const scratch=fs.mkdtempSync('/tmp/atmem-tf-');
const runtimePython=process.env.ATMEM_ARCHITECT_RUNTIME_PYTHON||'python3.13';
const checks=[],env={PATH:process.env.PATH,HOME:dir,TMPDIR:scratch,TF_IN_AUTOMATION:'1',CHECKPOINT_DISABLE:'1',TF_PLUGIN_CACHE_DIR:path.resolve('.local/provider-cache'),AWS_EC2_METADATA_DISABLED:'true'};
const execute=(name,command,args,timeout=180000)=>{const r=spawnSync(command,args,{cwd:dir,env,encoding:'utf8',timeout});fs.writeFileSync(path.join(dir,name+'.log'),(r.stdout||'')+'\n'+(r.stderr||''));const c={name,passed:r.status===0,status:r.status,error:r.error?.message};checks.push(c);console.log(c);return c.passed;};
if(execute('build',path.resolve('.venv/bin/python'),['build-runtime.py'])){
 execute('application-tests',runtimePython,['-m','unittest','discover','-s','app-tests','-p','*_test.py']);
 if(execute('terraform-init',path.resolve('.venv/bin/terraform'),['init','-backend=false','-input=false','-no-color','-lockfile=readonly'])){
  execute('terraform-validate',path.resolve('.venv/bin/terraform'),['validate','-json']);
  execute('terraform-mocks',path.resolve('.venv/bin/terraform'),['test','-no-color']);
 }
}
const report={scope:'Emitted package build, mocked application services, native provider schema and provider mocks only',deploymentExecuted:false,realModelTests:false,liveCognitoTests:false,files:Object.fromEntries(Object.entries(files).map(([name,body])=>[name,createHash('sha256').update(body).digest('hex')])),checks,passed:checks.length===5&&checks.every(c=>c.passed)};fs.writeFileSync(path.join(dir,'qualification.json'),JSON.stringify(report,null,2)+'\n');process.exitCode=report.passed?0:1;

fs.rmSync(scratch,{recursive:true,force:true});
