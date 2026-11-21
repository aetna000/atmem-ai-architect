import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {parseProjectFile,findCredentials} from '../src/project-file.mjs';
import {assessAwsArchitecture} from '../src/aws-validation.mjs';
import {AWS_SCENARIOS} from '../src/aws-validation-scenarios.mjs';

const repository=path.resolve(import.meta.dirname,'..');
export function verifyExamples(root=path.join(repository,'examples/aws')){
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json'),'utf8'));
 if(manifest.format!=='atmem.aws-example-library'||manifest.version!==1)throw Error('Unsupported example manifest');
 if(manifest.scenarios.length!==AWS_SCENARIOS.length||new Set(manifest.scenarios.map(s=>s.id)).size!==AWS_SCENARIOS.length)throw Error('Missing or duplicate scenarios');
 for(const example of manifest.scenarios){
  const scenario=AWS_SCENARIOS.find(s=>s.id===example.id);if(!scenario)throw Error('Unknown scenario');
  if(!example.files.some(f=>f.path===example.project))throw Error('Project lacks integrity evidence');
  for(const file of example.files){
   if(!file.path.startsWith(example.id+'/')||path.isAbsolute(file.path)||file.path.split('/').includes('..'))throw Error('Unsafe archive path');
   const bytes=fs.readFileSync(path.join(root,file.path));
   if(createHash('sha256').update(bytes).digest('hex')!==file.sha256)throw Error('Archive integrity mismatch: '+file.path);
   if(/(?:\.tfstate|\.tfplan)$|reviewed-inputs|\/\.terraform\//.test(file.path))throw Error('Private artifact in archive');
   if(!file.path.endsWith('.png')&&findCredentials(bytes.toString('utf8')).length)throw Error('Credential-like archive content');
  }
  const {project}=parseProjectFile(fs.readFileSync(path.join(root,example.project),'utf8'));
  if(!assessAwsArchitecture(project,scenario).passed)throw Error('Architecture failed: '+example.id);
  const tf=JSON.parse(fs.readFileSync(path.join(root,example.id,'terraform/main.tf.json'),'utf8'));
  if(tf.locals.unfinished_work.length)throw Error('Selected export has incomplete implementation: '+example.id);
  if(example.deployment!=='not_run')throw Error('Live evidence mapping must be explicitly implemented before promoting a selected export');
 }
 for(const reproduction of manifest.reproductions||[])for(const file of reproduction.files){
  if(!file.path.startsWith('evidence/')||file.path.split('/').includes('..'))throw Error('Unsafe reproduction path');
  const bytes=fs.readFileSync(path.join(root,file.path));
  if(createHash('sha256').update(bytes).digest('hex')!==file.sha256)throw Error('Reproduction integrity mismatch: '+file.path);
 }
 return manifest;
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const manifest=verifyExamples();console.log(`Verified ${manifest.scenarios.length} project imports, architecture checks and archived file hashes.`);
 if(process.argv.includes('--artifacts')){
  const run=path.join(repository,'.local/example-validation',new Date().toISOString().replaceAll(':','-'));fs.mkdirSync(run,{recursive:true});
  const results=[];
  for(const example of manifest.scenarios){
   const to=path.join(run,example.id);fs.mkdirSync(to,{recursive:true});
   fs.cpSync(path.join(repository,'examples/aws',example.id,'terraform'),path.join(to,'terraform'),{recursive:true});
   const {project}=parseProjectFile(fs.readFileSync(path.join(repository,'examples/aws',example.project),'utf8'));
   fs.writeFileSync(path.join(to,'workspace.json'),JSON.stringify(project,null,2));
   results.push({id:example.id,evidenceDirectory:example.id,stages:{localValidation:'not_run',applicationTests:'not_run',cloudPlan:'not_run',deployment:'not_run',cleanup:'not_run'}});
  }
  fs.writeFileSync(path.join(run,'validation.json'),JSON.stringify({evidenceKind:'archived-example-reproduction',results},null,2));
  const result=spawnSync(process.execPath,['scripts/aws-artifact-check.mjs',run],{cwd:repository,env:process.env,stdio:'inherit'});
  const report=JSON.parse(fs.readFileSync(path.join(run,'validation.json'),'utf8'));
  console.log('Evidence: '+run);
  process.exitCode=result.status!==0||report.results.some(r=>r.stages.localValidation!=='passed')?1:0;
 }
}
