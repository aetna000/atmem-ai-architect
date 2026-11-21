// Deliberately corrupt an isolated test copy. Never repair or mutate a client export.
import fs from 'node:fs';import path from 'node:path';import {spawnSync} from 'node:child_process';import {createHash} from 'node:crypto';
const root=path.resolve('.'),original=path.resolve(process.argv[2]||'');if(!process.argv[2])throw Error('Supply an emitted Azure Terraform directory');
const out=path.resolve(process.argv[3]||'.local/azure-health-mock-challenge'),scratch=fs.mkdtempSync('/tmp/azure-challenge-');fs.mkdirSync(out,{recursive:true});
const bytes=fs.readFileSync(path.join(original,'main.tf.json')),config=JSON.parse(bytes);let mutations=0;
for(const body of Object.values(config.resource?.azurerm_linux_web_app||{}))if(body.site_config?.health_check_path){if(body.site_config.health_check_eviction_time_in_min===undefined)throw Error('Original must contain the corrected paired setting');delete body.site_config.health_check_eviction_time_in_min;mutations++;}
if(!mutations)throw Error('No corrected health-check contract to challenge');
fs.writeFileSync(path.join(out,'main.tf.json'),JSON.stringify(config,null,2));fs.copyFileSync(path.join(original,'.terraform.lock.hcl'),path.join(out,'.terraform.lock.hcl'));fs.cpSync(path.join(original,'tests'),path.join(out,'tests'),{recursive:true});
const env={PATH:process.env.PATH,HOME:scratch,TMPDIR:scratch,TF_PLUGIN_CACHE_DIR:path.join(root,'.local/provider-cache'),CHECKPOINT_DISABLE:'1',TF_IN_AUTOMATION:'1'},tf=path.join(root,'.venv/bin/terraform');
try{
 const init=spawnSync(tf,['init','-backend=false','-input=false','-lockfile=readonly','-no-color'],{cwd:out,env,encoding:'utf8',timeout:120000});fs.writeFileSync(path.join(out,'init.log'),(init.stdout||'')+'\n'+(init.stderr||''));if(init.status!==0)throw Error('Challenge initialization failed');
 const result=spawnSync(tf,['test','-no-color'],{cwd:out,env,encoding:'utf8',timeout:120000});const log=(result.stdout||'')+'\n'+(result.stderr||'');fs.writeFileSync(path.join(out,'fault.log'),log);
 const passed=result.status!==0&&!result.error&&log.includes('health_check_eviction_time_in_min')&&log.includes('must be specified');
 const sha=b=>createHash('sha256').update(b).digest('hex');const receipt={kind:'azure-plan-mock-fault-challenge',passed,mutations,original:path.relative(root,original),originalSha256:sha(bytes),mutantSha256:sha(fs.readFileSync(path.join(out,'main.tf.json'))),failureExitCode:result.status,cloudOperations:false,boundary:'Deliberately removed the required paired health-check interval only in this isolated copy. Native plan-time validation must reject it; original emitted source is preserved. No cloud plan/deployment.'};fs.writeFileSync(path.join(out,'challenge.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));process.exitCode=passed?0:1;
}finally{fs.rmSync(scratch,{recursive:true,force:true});}
