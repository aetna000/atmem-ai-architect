// Independently checks original exported bytes, then qualifies an isolated copy.
// No regenerated/hand-patched application or Terraform source, account plan or apply.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import {spawnSync} from 'node:child_process';
import {CLOUD_PROVIDER_LOCKS} from '../src/cloud-provider-locks.mjs';
const root=path.resolve('.'),caseDir=path.resolve(process.argv[2]||''),folder=path.join(caseDir,'handoff');
if(!process.argv[2]||!fs.existsSync(path.join(caseDir,'export-assessment.json')))throw Error('Supply a completed evaluation case directory');
const receipt=JSON.parse(fs.readFileSync(path.join(caseDir,'export-assessment.json'))),dir=path.join(caseDir,'qualification');fs.mkdirSync(dir,{recursive:true});
const runtimePython=process.env.ATMEM_ARCHITECT_RUNTIME_PYTHON||'python3.13';
const scratch=fs.mkdtempSync('/tmp/atmem-qa-'),env={PATH:process.env.PATH,HOME:dir,TMPDIR:scratch,TF_IN_AUTOMATION:'1',CHECKPOINT_DISABLE:'1',TF_PLUGIN_CACHE_DIR:path.join(root,'.local/provider-cache'),AWS_EC2_METADATA_DISABLED:'true'},checks=[];
const execute=(name,command,args,timeout=180000)=>{const r=spawnSync(command,args,{cwd:dir,env,encoding:'utf8',timeout});fs.writeFileSync(path.join(dir,name+'.log'),(r.stdout||'')+'\n'+(r.stderr||''));const c={name,passed:r.status===0,status:r.status,error:r.error?.message};checks.push(c);console.log(c);return c.passed;};
try{
 const assessment=spawnSync(path.join(root,'.venv/bin/python'),[path.join(root,'scripts/assess-convergence-package.py'),caseDir],{env,encoding:'utf8',timeout:30000});if(assessment.status!==0)throw Error(assessment.stderr);
 const independent=JSON.parse(assessment.stdout);fs.writeFileSync(path.join(dir,'independent-before.json'),JSON.stringify(independent,null,2));
 if(!independent.staticChecksPassed)throw Error('Original package fails independent static assessment; preserve findings and fix generator first');
 const copied={};
 for(const [name,digest]of Object.entries(receipt.digests)){
  if(!name.startsWith('terraform/'))continue;
  const relative=name.slice('terraform/'.length);if(path.isAbsolute(relative)||relative.split('/').includes('..'))throw Error('Unsafe package path');
  const bytes=fs.readFileSync(path.join(folder,name));if(createHash('sha256').update(bytes).digest('hex')!==digest)throw Error('Original export digest mismatch: '+name);
  const target=path.join(dir,relative);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,bytes);copied[relative]=digest;
 }
 const project=JSON.parse(fs.readFileSync(path.join(caseDir,'project.json')));if(!['aws','azure'].includes(project.provider))throw Error('This runtime qualifier currently supports AWS Python/web and Azure structured application compositions only');
 let auxiliaryProviderLock=false;
 if(project.provider==='aws'){
  if(!fs.existsSync(path.join(dir,'.terraform.lock.hcl'))){fs.writeFileSync(path.join(dir,'.terraform.lock.hcl'),CLOUD_PROVIDER_LOCKS.aws);auxiliaryProviderLock=true;}
  if(!execute('build',path.join(root,'.venv/bin/python'),['build-runtime.py']))throw Error('Emitted build failed');
  execute('application-tests',runtimePython,['-m','unittest','discover','-s','app-tests','-p','*_test.py']);
 }else{
  const sdk=path.resolve(process.env.ATMEM_AZURE_QUALIFICATION_SDK||'.local/azure-runtime-sdk');
  if(!fs.existsSync(sdk))throw Error('Install the emitted hash-locked Azure test requirements into the explicit isolated qualification SDK directory first');
  const applications=Object.keys(copied).filter(name=>name.endsWith('/azure_acceptance.py')).map(name=>path.dirname(name));
  if(!applications.length)throw Error('No generated Azure application acceptance suite; a supplied-image footprint does not qualify');
  for(const application of applications){
   const app=path.join(dir,application),script=`import sys,json,runpy,socket,importlib.metadata\nfrom pathlib import Path\nsys.path[:0]=[${JSON.stringify(sdk)},${JSON.stringify(app)}]\nroot=Path(${JSON.stringify(app)})\nfor name in ['dependency-sources.json','test-dependency-sources.json']:\n for dependency in json.loads((root/name).read_text()):\n  assert importlib.metadata.version(dependency['name'])==dependency['version'],dependency['name']\ndef denied(*args,**kwargs):raise RuntimeError('Qualification denies external network')\nsocket.socket.connect=denied;socket.socket.connect_ex=denied;socket.getaddrinfo=denied\nsys.argv=['azure_acceptance.py','-v']\nrunpy.run_path(str(root/'azure_acceptance.py'),run_name='__main__')\n`;
   if(!execute('application-'+path.basename(application),runtimePython,['-I','-c',script]))throw Error('Emitted Azure source tests failed');
  }
 }
 if(execute('terraform-init',path.join(root,'.venv/bin/terraform'),['init','-backend=false','-input=false','-no-color','-lockfile=readonly'])){
  execute('terraform-validate',path.join(root,'.venv/bin/terraform'),['validate','-json']);
  execute('terraform-mocks',path.join(root,'.venv/bin/terraform'),['test','-no-color']);
 }
 const artifactsFile=path.join(dir,'build/artifact-hashes.json'),artifacts=fs.existsSync(artifactsFile)?JSON.parse(fs.readFileSync(artifactsFile)):[];
 const versions={applicationPython:spawnSync(runtimePython,['--version'],{env,encoding:'utf8'}).stdout.trim(),buildPython:spawnSync(path.join(root,'.venv/bin/python'),['--version'],{env,encoding:'utf8'}).stdout.trim(),terraform:JSON.parse(spawnSync(path.join(root,'.venv/bin/terraform'),['version','-json'],{cwd:dir,env,encoding:'utf8'}).stdout)};
 const expectedChecks=project.provider==='aws'?5:3+Object.keys(copied).filter(name=>name.endsWith('/azure_acceptance.py')).length;
 const report={case:caseDir.split(path.sep).at(-1),originalSourceDigests:copied,auxiliaryProviderLock,checks,versions,artifacts,passed:checks.length===expectedChecks&&checks.every(c=>c.passed),containerImageBuild:project.provider==='azure'?'not_run':'not_applicable',boundary:project.provider==='azure'?'Exact emitted Azure Python source, locked dependency versions, local JWT/ASGI/scripted transport tests with external sockets denied, native provider schema and mock plans. No container image build/startup/scan, real Entra authentication/MFA/revocation, model quality, account plan or deployment.':'Exact emitted package build, tests with mocked provider/model services, provider schema and provider mock plans. No live identity/model, semantic acceptance, account plan or deployment.',cloudOperations:false,nearDeploymentQualified:false};
 fs.writeFileSync(path.join(dir,'qualification.json'),JSON.stringify(report,null,2)+'\n');
 // Runtime dependencies are reproducible from the retained hash lock. Avoid 28 SDK copies.
 for(const artifact of artifacts)if(/^block_[0-9a-f]+$/.test(artifact.component)){fs.rmSync(path.join(dir,'build',artifact.component),{recursive:true,force:true});fs.rmSync(path.join(dir,'build',artifact.component+'.zip'),{force:true});}
 process.exitCode=report.passed?0:1;
}finally{fs.rmSync(scratch,{recursive:true,force:true});}
