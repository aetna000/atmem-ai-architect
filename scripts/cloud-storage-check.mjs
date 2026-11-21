// Native schema + mock plans only. No account credentials, cloud plans or apply.
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {terraformSketch} from '../src/terraform.mjs';
import {toProjectFile} from '../src/project-file.mjs';
import {CLOUD_STORAGE_SCENARIOS} from '../src/cloud-storage-scenarios.mjs';
const root=path.resolve(import.meta.dirname,'..'),out=path.join(root,'.local/cloud-storage',new Date().toISOString().replaceAll(':','-'));
fs.mkdirSync(out,{recursive:true});const cache=path.join(root,'.local/provider-cache');fs.mkdirSync(cache,{recursive:true});
const results=[];
for(const scenario of CLOUD_STORAGE_SCENARIOS){
 const folder=path.join(out,scenario.id);fs.mkdirSync(folder,{recursive:true});
 fs.writeFileSync(path.join(folder,'project.atmem-ai-architect.json'),JSON.stringify(toProjectFile(scenario.project),null,2));
 fs.writeFileSync(path.join(folder,'workspace.json'),JSON.stringify(scenario.project,null,2));
 fs.writeFileSync(path.join(folder,'prompt.txt'),scenario.prompt);
 for(const [name,content]of Object.entries(terraformSketch(scenario.project))){const dest=path.join(folder,name);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,content);}
 const record={provider:scenario.id,evidenceKind:'synthetic-contract-fixture',cloudOperations:false,steps:[]};
 for(const args of [['init','-backend=false','-input=false','-no-color'],['validate','-json'],['test','-no-color']]){
  const r=spawnSync(path.join(root,'.venv/bin/terraform'),[`-chdir=${folder}`,...args],{encoding:'utf8',timeout:180000,env:{PATH:process.env.PATH,HOME:folder,TF_IN_AUTOMATION:'1',CHECKPOINT_DISABLE:'1',TF_PLUGIN_CACHE_DIR:cache}});
  fs.writeFileSync(path.join(folder,args[0]+'.log'),(r.stdout||'')+(r.stderr||'')+(r.error?.message||''));record.steps.push({name:args[0],passed:r.status===0});if(r.status!==0)break;
 }
 const emulation=spawnSync(path.join(root,'.venv/bin/python'),['-c','import json,sys;from server.emulation_routes import emulate,EmulationRequest;print(json.dumps(emulate(EmulationRequest(project=json.load(open(sys.argv[1]))))))',path.join(folder,'workspace.json')],{cwd:root,encoding:'utf8',timeout:120000,env:{PATH:process.env.PATH,HOME:folder}});
 try{const report=JSON.parse(emulation.stdout);fs.writeFileSync(path.join(folder,'emulation.json'),JSON.stringify(report,null,2));record.emulation=report.status;}catch{record.emulation='failed';fs.writeFileSync(path.join(folder,'emulation-error.log'),emulation.stderr||'Invalid report');}
 record.passed=record.emulation==='passed'&&record.steps.length===3&&record.steps.every(x=>x.passed);results.push(record);console.log(JSON.stringify(record));
}
fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({results,cloudOperations:false},null,2));console.log(out);if(results.some(r=>!r.passed))process.exitCode=1;
