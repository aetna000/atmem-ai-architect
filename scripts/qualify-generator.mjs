// Generates a repeatable local qualification suite. This script never applies resources.
import fs from 'node:fs';import path from 'node:path';import {spawnSync} from 'node:child_process';
import {CONTAINER_SERVICES} from '../src/container-contracts.mjs';import {terraformSketch} from '../src/terraform.mjs';import {generationQuality} from '../src/generation-quality.mjs';import {resourcePlan} from '../src/resources.mjs';
const root=path.resolve(process.argv[2]||'.local/generator-qualification'),terraform=process.env.ATMEM_ARCHITECT_TERRAFORM_BIN||path.resolve('.venv/bin/terraform');
fs.mkdirSync(root,{recursive:true});const results=[];
for(const [provider,c] of Object.entries(CONTAINER_SERVICES)){
 const project={version:1,revision:2,name:'Fresh deployment qualification',provider,nodes:[{id:'service/new-v2',position:{x:0,y:0},data:{label:'Supplied application',kind:'resource',provider,origin:'existing',deploymentMode:'create',service:c.service,implementation:'container-service',description:'Preserve existing source; create a new private cloud deployment.'}}],edges:[]};
 const files=terraformSketch(project),dir=path.join(root,provider);fs.mkdirSync(dir,{recursive:true});
 for(const [name,body] of Object.entries(files)){const file=path.join(dir,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,body);}
 const quality=generationQuality(project,resourcePlan(project),files);const checks=[{name:'Independent resource coverage',passed:quality.findings.length===0,findings:quality.findings}];
 const env={TF_PLUGIN_CACHE_DIR:path.resolve('.local/provider-cache'),PATH:process.env.PATH,HOME:dir,TMPDIR:dir,TF_IN_AUTOMATION:'1',CHECKPOINT_DISABLE:'1',AWS_EC2_METADATA_DISABLED:'true'};
 for(const args of [['init','-backend=false','-input=false','-no-color'],['validate','-json'],['test','-no-color']]){
  const run=spawnSync(terraform,args,{cwd:dir,env,encoding:'utf8',timeout:180000});const output=(run.stdout||'')+'\n'+(run.stderr||'');fs.writeFileSync(path.join(dir,'qualification-'+args[0]+'.log'),output);checks.push({name:args[0],passed:run.status===0,error:run.error?.message});if(run.status!==0)break;
 }
 results.push({provider,checks,passed:checks.every(c=>c.passed)});
}
const report={generatedAt:new Date().toISOString(),scope:'local compiler, provider schema and provider-mock qualification only',deploymentExecuted:false,results};fs.writeFileSync(path.join(root,'qualification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));process.exitCode=results.every(r=>r.passed)?0:1;
