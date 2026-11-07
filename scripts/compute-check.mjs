// Generate and validate the exact exported compute files; no cloud credentials or AWS calls.
import fs from 'node:fs';
import {webProject} from '../tests/fixtures/web-project.mjs';
import {ragProject} from '../tests/fixtures/rag-project.mjs';
import {summaryProject} from '../tests/fixtures/summary-project.mjs';
import {asyncProject} from '../tests/fixtures/async-project.mjs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {terraformSketch} from '../src/terraform.mjs';
const root=path.resolve('.local/compute-validation',new Date().toISOString().replaceAll(':','-'));fs.mkdirSync(root,{recursive:true});
const p={version:1,revision:1,name:'Text statistics qualification',provider:'aws',nodes:[{id:'caller',data:{kind:'resource',label:'Caller',provider:'tools',origin:'existing',binding:'aws-iam-principal'}},{id:'counter',data:{kind:'resource',label:'Counter',provider:'aws',service:'AWS Lambda',implementation:'text-statistics'}}],edges:[{id:'invoke',source:'caller',target:'counter',access:'lambda-invoke'}]};
for(const [name,content]of Object.entries(terraformSketch(process.argv.includes('--web')?webProject():process.argv.includes('--rag')?ragProject():process.argv.includes('--summary')?summaryProject():process.argv.includes('--async')?asyncProject():p,process.argv.includes('--production')?'production':'staging'))){const dest=path.join(root,name);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,content);}
const env={PATH:process.env.PATH,HOME:root,TF_IN_AUTOMATION:'1',CHECKPOINT_DISABLE:'1',AWS_EC2_METADATA_DISABLED:'true',...(process.env.ATMEM_ARCHITECT_TERRAFORM_TEST_CACHE?{TF_PLUGIN_CACHE_DIR:path.resolve(process.env.ATMEM_ARCHITECT_TERRAFORM_TEST_CACHE)}:{})};
const evidence=[];
for(const [binary,args]of [[path.resolve('.venv/bin/python'),['build-runtime.py']],[path.resolve('.venv/bin/python'),['-m','unittest','discover','-s','app-tests','-p','*_test.py','-v']],...['init','validate','test'].map(command=>[path.resolve('.venv/bin/terraform'),[command,...(command==='init'?['-backend=false','-input=false']:[]),'-no-color']])]){
 const r=spawnSync(binary,args,{cwd:root,env,encoding:'utf8',timeout:180000});evidence.push({command:args,exitCode:r.status,stdout:r.stdout,stderr:r.stderr});fs.writeFileSync(path.join(root,'validation.json'),JSON.stringify({scope:'local application and mock-provider validation; no cloud operations',evidence},null,2));
 console.log(r.stdout+r.stderr);if(r.status!==0)throw Error(`Validation failed; see ${root}`);
}
console.log(`Compute qualification evidence: ${root}`);
