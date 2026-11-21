// Publish only synthetic, allowlisted evidence. Never copy a Terraform working directory.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {unzipSync} from 'fflate';
import {AWS_SCENARIOS} from '../src/aws-validation-scenarios.mjs';
import {parseProjectFile,findCredentials} from '../src/project-file.mjs';

const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'examples/aws');
const batch='2026-11-07T05-49-19.638Z',corrected='2026-11-07T05-56-30.120Z';
const hash=value=>createHash('sha256').update(value).digest('hex');
const account=JSON.parse(fs.readFileSync(path.join(root,'.local/aws-validation/2026-11-07T04-36-15.803Z/01-private-storage/terraform/reviewed-inputs.tfvars.json'),'utf8')).aws_account_id;
const manifest={format:'atmem.aws-example-library',version:1,milestone:'milestone/aws-qualification-foundation-2026-11-07',region:'ap-southeast-2',scenarios:[]};
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
function write(relative,bytes){const p=path.join(out,relative);fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,bytes);}
function publish(source,relative,files){
 const original=fs.readFileSync(source);let bytes=original;
 if(!relative.endsWith('.png')){
  let text=original.toString('utf8').replaceAll(root,'<repository>').replaceAll('/Users/javadtaghia','<local-user>').replaceAll(account,'000000000000');
  // Credential literals in source-code security tests are not included in these exports.
  let value;try{value=JSON.parse(text);}catch{value=text;}
  if(findCredentials(value).length)throw Error('Credential-like content in '+relative);
  bytes=Buffer.from(text);
 }
 write(relative,bytes);files.push({path:relative,sha256:hash(bytes),sourceSha256:hash(original),sanitized:!bytes.equals(original)});
}
for(const scenario of AWS_SCENARIOS){
 const id=scenario.id,run=id.startsWith('07-')?corrected:batch;
 const source=path.join(root,'.local/aws-validation',run,id),files=[];
 const latest=path.join(source,'round-2');
 const validation=read(path.join(latest,'validation.json'));
 const receiptPath=path.join(latest,'terraform/account-plan-receipt.json');
 const receipt=fs.existsSync(receiptPath)?read(receiptPath):null;
 const entry={id,name:scenario.name,sourceRun:run,project:`${id}/project.atmem-ai-architect.json`,localValidation:validation.stages.localValidation,cloudPlan:receipt?(receipt.exitCode===0?'passed':'failed'):'not_run',preflight:receipt?.preflight||'not_run',deployment:'not_run',cleanup:'not_run',liveAcceptance:scenario.checks.map(name=>({name,status:'not_run'})),files};
 for(const round of ['round-1','round-2']){
  for(const name of ['prompt.txt','project.atmem-ai-architect.json','workspace.json','model-response.json','validation.json','artifact-validation.json','diagram.svg','architecture.png']){
   const from=path.join(source,round,name);if(fs.existsSync(from))publish(from,`${id}/history/${run}/${round}/${name}`,files);
  }
 }
 publish(path.join(latest,'project.atmem-ai-architect.json'),entry.project,files);
 parseProjectFile(fs.readFileSync(path.join(out,entry.project),'utf8'));
 publish(path.join(latest,'diagram.svg'),`${id}/diagram.svg`,files);
 // Read the original delivery archive: no build output, credentials, state or account plans.
 const delivery=unzipSync(fs.readFileSync(path.join(latest,'delivery.zip')));
 for(const [name,bytes] of Object.entries(delivery)){
  if(!name.startsWith('terraform/')||name.endsWith('/'))continue;
  if(path.isAbsolute(name)||name.split('/').includes('..')||/tfstate|\.tfplan|reviewed-inputs|\.terraform\//.test(name))throw Error('Unsafe export member');
  const relative=`${id}/${name}`,text=Buffer.from(bytes).toString('utf8');
  if(text.includes(account)||findCredentials(text).length)throw Error('Private content in export '+name);
  write(relative,bytes);files.push({path:relative,sha256:hash(bytes),sourceSha256:hash(bytes),sanitized:false});
 }
 for(const name of ['account-plan-receipt.json','account-preflight.json','qualification-inputs.json']){
  const from=path.join(latest,'terraform',name);if(fs.existsSync(from))publish(from,`${id}/evidence/${name}`,files);
 }
 if(id.startsWith('07-')){
  for(const round of ['round-1','round-2'])for(const name of ['prompt.txt','project.atmem-ai-architect.json','validation.json','artifact-validation.json'])publish(path.join(root,'.local/aws-validation',batch,id,round,name),`${id}/history/${batch}/${round}/${name}`,files);
 }
 if(id.startsWith('01-')){
  const live=path.join(root,'.local/live-storage/6f875fc797e9'),r=read(path.join(live,'receipt.json'));
  entry.priorLiveQualification={deployment:r.status,cleanup:r.cleanup,sourceWorkspace:r.sourceWorkspace,scope:'Earlier prompt-derived storage project; not the latest example export. See evidence/live/project.atmem-ai-architect.json.'};
  for(const name of ['receipt.json','application-tests.json','main.tf.json'])publish(path.join(live,name),`${id}/evidence/live/${name}`,files);
  publish(path.join(root,path.dirname(r.sourceWorkspace),'project.atmem-ai-architect.json'),`${id}/evidence/live/project.atmem-ai-architect.json`,files);
 }
 write(`${id}/results.json`,JSON.stringify({...entry,files:undefined},null,2)+'\n');
 const requirements=scenario.checks.map(c=>`- [ ] ${c}`).join('\n');
 write(`${id}/README.md`,`# ${scenario.name}\n\nOpen [project.atmem-ai-architect.json](project.atmem-ai-architect.json) using **⋯ → Open project file** in AtMem Architect. [Diagram](diagram.svg).\n\n## Prompt and refinement history\n\nExact submitted prompts and responses are in [history/${run}](history/${run}), in round order. The selected project and Terraform come from round 2. Changing a prompt may produce a different architecture; these are captured outputs, not deterministic model guarantees.\n\n## Recorded results\n\n- Local exported-artifact checks: **${entry.localValidation}**.\n- Actual AWS account plan: **${entry.cloudPlan}**.\n- Account preflight: **${entry.preflight}**.\n- This exact export deployed: **${entry.deployment}**.\n- This exact export cleanup: **${entry.cleanup}**.\n${entry.priorLiveQualification?'\nAn earlier storage project passed live AWS tests and cleanup. Its exact project, generated configuration and receipt are retained under evidence/live; that result is not transferred to this newer export.\n':''}\n## Live acceptance still required for this export\n\n${requirements}\n\nSee [the shared runbook](../RUNBOOK.md) for local reproduction, account checks, deployment gates and cleanup. Model outputs in history are design evidence, not authoritative test results. Local application tests use mocks; AWS model availability checks do not invoke the model.\n`);
 manifest.scenarios.push(entry);
}
publish(path.join(root,'.local/account-preflight/lambda-quota-status.json'),'evidence/lambda-quota-status.json',[]);
const replacedKinds=[...(process.argv.includes('--local-recheck')?['local-artifacts']:[]),...(process.argv.includes('--browser-recheck')?['browser-import']:[])];
manifest.reproductions=fs.existsSync(path.join(out,'manifest.json'))?(read(path.join(out,'manifest.json')).reproductions||[]).filter(r=>!replacedKinds.includes(r.kind)):[];
for(const [flag,kind] of [['--local-recheck','local-artifacts'],['--browser-recheck','browser-import']]){
 const index=process.argv.indexOf(flag);if(index<0)continue;
 if(!process.argv[index+1])throw Error('Missing directory for '+flag);
 const source=path.resolve(process.argv[index+1]);
 if(!source.startsWith(path.join(root,'.local')+path.sep))throw Error('Recheck source must be a local evidence directory');
 const files=[],report=read(path.join(source,kind==='local-artifacts'?'validation.json':'results.json'));
 if(report.results.length!==7||report.results.some(r=>(kind==='local-artifacts'?r.stages.localValidation:r.status)!=='passed'))throw Error('Recheck is incomplete or failed; retain its private evidence, do not publish a pass');
 publish(path.join(source,kind==='local-artifacts'?'validation.json':'results.json'),`evidence/${kind}/results.json`,files);
 for(const result of report.results){
  const name=kind==='local-artifacts'?'artifact-validation.json':result.id+'.png';
  publish(path.join(source,...(kind==='local-artifacts'?[result.id,name]:[name])),`evidence/${kind}/${result.id}/${name}`,files);
 }
 manifest.reproductions.push({kind,sourceRun:path.basename(source),files});
}
write('manifest.json',JSON.stringify(manifest,null,2)+'\n');
console.log(`Archived ${manifest.scenarios.length} loadable examples under examples/aws; raw state, binary plans and credentials excluded.`);
