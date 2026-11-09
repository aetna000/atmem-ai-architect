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
 const project=JSON.parse(fs.readFileSync(path.join(caseDir,'project.json')));if(!['aws','azure','gcp','ibm'].includes(project.provider))throw Error('This runtime qualifier currently supports AWS Python/web and Azure/Google structured application compositions only');
 const faq=!!JSON.parse(fs.readFileSync(path.join(dir,'resource-schedule.json'))).publicFaqPlan?.entries?.length;
 let auxiliaryProviderLock=false;
 if(project.provider==='aws'&&!faq){
  if(!fs.existsSync(path.join(dir,'.terraform.lock.hcl'))){fs.writeFileSync(path.join(dir,'.terraform.lock.hcl'),CLOUD_PROVIDER_LOCKS.aws);auxiliaryProviderLock=true;}
  if(!execute('build',path.join(root,'.venv/bin/python'),['build-runtime.py']))throw Error('Emitted build failed');
  execute('application-tests',runtimePython,['-m','unittest','discover','-s','app-tests','-p','*_test.py']);
 }else{
  if(faq&&project.provider==='aws'&&!execute('build',path.join(root,'.venv/bin/python'),['build-runtime.py']))throw Error('Emitted public FAQ Lambda ZIP build failed');
  const sdk=path.resolve(process.env.ATMEM_STRUCTURED_QUALIFICATION_SDK||process.env.ATMEM_AZURE_QUALIFICATION_SDK||({aws:'.local/aws-web-runtime-sdk',azure:'.local/azure-runtime-sdk',gcp:'.local/azure-runtime-sdk',ibm:'.local/ibm-runtime-sdk'}[project.provider]));
  if(!fs.existsSync(sdk))throw Error('Install the emitted hash-locked provider test requirements into the explicit isolated qualification SDK directory first');
  const acceptance=(faq?'faq':project.provider)+'_acceptance.py';
  const applications=Object.keys(copied).filter(name=>name.endsWith('/'+acceptance)).map(name=>path.dirname(name));
  if(!applications.length)throw Error('No generated application acceptance suite; a supplied-image footprint does not qualify');
  for(const application of applications){
   if(!execute('dependency-closure-'+path.basename(application),path.join(root,'.venv/bin/python'),[path.join(root,'scripts/check-python-runtime-lock.py'),path.join(dir,application),sdk]))throw Error('Emitted runtime dependency graph is incomplete or incompatible');
   const app=path.join(dir,application),script=`import sys,json,runpy,socket,importlib.metadata\nsys.dont_write_bytecode=True\nfrom pathlib import Path\nsys.path[:0]=[${JSON.stringify(sdk)},${JSON.stringify(app)}]\nroot=Path(${JSON.stringify(app)})\nfor name in ['dependency-sources.json','test-dependency-sources.json']:\n for dependency in json.loads((root/name).read_text()):\n  assert importlib.metadata.version(dependency['name'])==dependency['version'],dependency['name']\ndef denied(*args,**kwargs):raise RuntimeError('Qualification denies external network')\nsocket.socket.connect=denied;socket.socket.connect_ex=denied;socket.getaddrinfo=denied\nsys.argv=[${JSON.stringify(acceptance)},'-v']\nrunpy.run_path(str(root/${JSON.stringify(acceptance)}),run_name='__main__')\n`;
   if(!execute('application-'+path.basename(application),runtimePython,['-I','-c',script]))throw Error('Emitted source tests failed');
  }
 }
 if(execute('terraform-init',path.join(root,'.venv/bin/terraform'),['init','-backend=false','-input=false','-no-color','-lockfile=readonly'])){
  execute('terraform-validate',path.join(root,'.venv/bin/terraform'),['validate','-json']);
  execute('terraform-mocks',path.join(root,'.venv/bin/terraform'),['test','-no-color']);
 }
 const artifactsFile=path.join(dir,'build/artifact-hashes.json'),artifacts=fs.existsSync(artifactsFile)?JSON.parse(fs.readFileSync(artifactsFile)):[];
 const versions={applicationPython:spawnSync(runtimePython,['--version'],{env,encoding:'utf8'}).stdout.trim(),buildPython:spawnSync(path.join(root,'.venv/bin/python'),['--version'],{env,encoding:'utf8'}).stdout.trim(),terraform:JSON.parse(spawnSync(path.join(root,'.venv/bin/terraform'),['version','-json'],{cwd:dir,env,encoding:'utf8'}).stdout)};
 const expectedChecks=project.provider==='aws'&&!faq?5:(faq&&project.provider==='aws'?4:3)+2*Object.keys(copied).filter(name=>name.endsWith('/'+(faq?'faq':project.provider)+'_acceptance.py')).length;
 const report={case:caseDir.split(path.sep).at(-1),originalSourceDigests:copied,auxiliaryProviderLock,checks,versions,artifacts,passed:checks.length===expectedChecks&&checks.every(c=>c.passed),containerImageBuild:faq||project.provider!=='aws'?'not_run':'not_applicable',boundary:faq?'Exact emitted public FAQ source, dependency metadata closure, catalog/editor/ASGI/scripted native storage tests with network denied, provider schema and mock plans. Real workload identity/effective IAM, model semantics, exact Linux image/scan, account plan and deployment are separate.':project.provider!=='aws'?'Exact emitted provider-specific Python source, locked dependency versions, local JWT/ASGI/scripted transport tests with external sockets denied, native provider schema and mock plans. No container image build/startup/scan, real provider authentication/MFA/revocation, model quality, account plan or deployment.':'Exact emitted package build, tests with mocked provider/model services, provider schema and provider mock plans. No live identity/model, semantic acceptance, account plan or deployment.',cloudOperations:false,nearDeploymentQualified:false};
 fs.writeFileSync(path.join(dir,'qualification.json'),JSON.stringify(report,null,2)+'\n');
 // Runtime dependencies are reproducible from the retained hash lock. Avoid 28 SDK copies.
 for(const artifact of artifacts)if(/^block_[0-9a-f]+$/.test(artifact.component)){fs.rmSync(path.join(dir,'build',artifact.component),{recursive:true,force:true});if(!faq)fs.rmSync(path.join(dir,'build',artifact.component+'.zip'),{force:true});}
 process.exitCode=report.passed?0:1;
}finally{fs.rmSync(scratch,{recursive:true,force:true});}
