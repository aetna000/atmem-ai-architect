// Qualify the exact Terraform downloaded by a real UI/model run, without regenerating it.
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const root=path.resolve(import.meta.dirname,'..'),source=path.resolve(process.argv[2]||'');
if(!source.startsWith(path.join(root,'.local/cloud-mentor/') )||!fs.existsSync(path.join(source,'results.json')))throw Error('Supply a completed local real-model browser run');
const out=path.join(root,'.local/cloud-storage',new Date().toISOString().replaceAll(':','-'));fs.mkdirSync(out,{recursive:true});const cache=path.join(root,'.local/provider-cache');fs.mkdirSync(cache,{recursive:true});const results=[];
for(const provider of ['azure','gcp','ibm']){
 const from=path.join(source,provider,'terraform');if(!fs.existsSync(from))continue;
 const folder=path.join(out,provider);fs.cpSync(from,folder,{recursive:true});const digests={};
 for(const file of fs.readdirSync(folder,{recursive:true}).filter(f=>fs.statSync(path.join(folder,f)).isFile()))digests[file]=createHash('sha256').update(fs.readFileSync(path.join(folder,file))).digest('hex');
 const record={provider,kind:'exact-model-output-native-validation',sourceRun:path.basename(source),sourceFileDigests:digests,cloudOperations:false,steps:[]};
 for(const args of [['init','-backend=false','-input=false','-no-color'],['validate','-json'],['test','-no-color']]){
  const r=spawnSync(path.join(root,'.venv/bin/terraform'),[`-chdir=${folder}`,...args],{encoding:'utf8',timeout:180000,env:{PATH:process.env.PATH,HOME:folder,TF_IN_AUTOMATION:'1',CHECKPOINT_DISABLE:'1',TF_PLUGIN_CACHE_DIR:cache}});
  fs.writeFileSync(path.join(folder,args[0]+'.log'),(r.stdout||'')+(r.stderr||'')+(r.error?.message||''));record.steps.push({name:args[0],passed:r.status===0});if(r.status!==0)break;
 }
 record.passed=record.steps.length===3&&record.steps.every(s=>s.passed);results.push(record);console.log(JSON.stringify({provider,passed:record.passed,steps:record.steps}));
}
fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({kind:'exact-model-output-native-validation',results,cloudOperations:false},null,2));console.log(out);if(!results.length||results.some(r=>!r.passed))process.exitCode=1;
