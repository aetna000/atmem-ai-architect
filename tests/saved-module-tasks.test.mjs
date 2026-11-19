import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import test from 'node:test';
import assert from 'node:assert/strict';
import {deliveryPack} from '../src/delivery.mjs';
import {blockSpecPath} from '../src/block-spec-kit.mjs';
const spec=domain=>({behavior:`Own ${domain} ownership and its durable lifecycle.`,inputs:`Stable ${domain} command and authorized actor.`,outputs:`Immutable ${domain} receipt.`,failures:`Reconcile uncertain ${domain} effects before retry.`,implementation:`Use an atomic ${domain} transition with a fenced writer.`,infrastructure:'Choose a qualified local or cloud transaction service.',operations:'Restore a coherent checkpoint and reject stale writers.',tests:`Race duplicate ${domain} commands and demonstrate approved recovery.`,scenarios:[{name:'Commit',steps:[{sender:'Caller',receiver:'Ledger',action:'Reserve'}]}]});
function fixture(domain,provider='tools'){
 const node=(id,existing=false)=>({id,type:'resource',position:{x:0,y:0},data:{kind:'resource',provider,origin:existing?'existing':'proposed',label:domain+' '+id,description:'Own '+id,buildSpec:spec(domain),config:{region:'To be selected'}}});
 return {id:'00000000-0000-0000-0000-000000000023',version:1,revision:1,name:domain,provider,nodes:[node('ledger'),node('adapter',true)],edges:[{id:'receipt',source:'ledger',target:'adapter',label:'Accepted receipt',interfaceSpec:{transport:'versioned local event',input:domain+' accepted version and operation ID',output:'durable consumer checkpoint',authorization:'scoped service identity',failure:'same-ID replay with contradictory-payload quarantine',verification:'duplicate, conflicting payload, denied caller and restart tests'}}],needs:[{id:'receipt-rule',source:'user',kind:'functional',priority:'must',status:'open',statement:'Preserve accepted evidence.',acceptance:'Duplicate operations have one durable result.',links:['ledger','adapter']}],decisions:[],openQuestions:[],assumptions:[]};
}
const tasks=files=>JSON.parse(files['spec-kit/tasks.json']).tasks;
function ancestors(list,task){const result=new Set();function visit(id){if(result.has(id))return;result.add(id);const row=list.find(t=>t.id===id);assert.ok(row,'Missing dependency '+id);row.dependsOn.forEach(visit);}task.dependsOn.forEach(visit);return result;}
for(const domain of ['library-loans','procurement-review','clinical-referrals'])test(domain+': saved contracts and exact block behavior enter executable handoff without invented IaC targets',()=>{
 const project=fixture(domain),before=structuredClone(project),files=deliveryPack(project,null),list=tasks(files);
 const contract=list.find(t=>t.phase==='Contracts');
 for(const value of Object.values(project.edges[0].interfaceSpec))assert.ok(contract.steps.some(step=>step.includes(value)),value);
 assert.doesNotMatch(contract.steps.join('\n'),/Determine whether/);assert.deepEqual(contract.files,['spec-kit/interfaces.json']);
 for(const node of project.nodes){const component=list.find(t=>t.phase==='Components'&&t.componentIds.includes(node.id));
  for(const [field,value]of Object.entries(node.data.buildSpec))if(field!=='scenarios')assert.ok(component.steps.some(step=>step.includes(value)),field);
  assert.equal(ancestors(list,component).has('TASK-COST-BASELINE'),false);assert.equal(ancestors(list,component).has('TASK-STAGING'),false);
  assert.deepEqual(component.files,[]);const path=blockSpecPath(node.id),plan=files[path+'/plan.md'];
  const local=plan.split('## Local build prerequisites')[1].split('## Integration prerequisites')[0];assert.doesNotMatch(local,/TASK-STAGING|TASK-COST/);
  assert.match(plan,/## Qualification prerequisites[\s\S]*TASK-STAGING/);assert.ok(files[path+'/testing.md'].includes(node.data.buildSpec.tests));
 }
 const existing=list.find(t=>t.phase==='Components'&&t.componentIds.includes('adapter'));assert.match(existing.steps.join(' '),/do not recreate/);
 assert.doesNotMatch(files['spec-kit/tasks.md'],/Clarify with the user\./);
 assert.equal(list.find(t=>t.id==='TASK-CLOUD-PLAN').dependsOn.includes('TASK-COST-BASELINE'),true);
 assert.match(list.find(t=>t.id==='TASK-STAGING').steps.join(' '),/explicit staging deployment authorization/);
 assert.deepEqual(project,before);
});
test('missing contracts stay explicit work and do not receive fabricated saved details',()=>{
 const project=fixture('missing-contract');delete project.edges[0].interfaceSpec;const list=tasks(deliveryPack(project,null));
 const task=list.find(t=>t.phase==='Contracts');assert.match(task.steps.join(' '),/Determine whether/);assert.doesNotMatch(task.steps.join(' '),/same-ID replay/);
});
test('provider-specific unimplemented resources preserve infrastructure and ownership requirements',()=>{
 for(const provider of ['aws','azure','gcp','ibm']){
  const project=fixture('provider-'+provider,provider);const list=tasks(deliveryPack(project,null));
  const component=list.find(t=>t.phase==='Components'&&t.componentIds.includes('ledger'));
  assert.match(component.steps.join(' '),/has not generated this implementation/);assert.match(component.steps.join(' '),/fenced writer/);
  assert.equal(ancestors(list,component).has('TASK-COST-BASELINE'),false);
  assert.ok(list.find(t=>t.id==='TASK-CLOUD-PLAN').dependsOn.includes('TASK-COST-BASELINE'));
  const existing=list.find(t=>t.phase==='Components'&&t.componentIds.includes('adapter'));assert.match(existing.steps.join(' '),/do not recreate/);
 }
});
test('all task dependencies stay resolvable without making cyclic domain flows cyclic builds',()=>{
 const project=fixture('round-trip');project.edges.push({...structuredClone(project.edges[0]),id:'ack',source:'adapter',target:'ledger'});
 const list=tasks(deliveryPack(project,null)),done=new Set();while(done.size<list.length){const ready=list.filter(t=>!done.has(t.id)&&t.dependsOn.every(id=>done.has(id)));assert.ok(ready.length);ready.forEach(t=>done.add(t.id));}
});

test('a saved proposal never overwrites a generated compiler contract or its scoped file facts',async()=>{
 const {applySavedModuleTasks}=await import('../src/saved-module-tasks.mjs');const project=fixture('emitted-contract','aws');
 const baseline={id:'contract',phase:'Contracts',componentIds:['ledger','adapter'],edgeIds:['receipt'],steps:['POST /api/receipt requires exact audience and a current actor check.'],files:['terraform/app/receipt.py'],acceptance:['Reject revoked subjects.']};const rows=[structuredClone(baseline)];
 applySavedModuleTasks(project,{rows:[],connections:[{id:'receipt',generated:true}]},rows);
 assert.equal(rows[0].steps[0],baseline.steps[0]);assert.deepEqual(rows[0].files,baseline.files);assert.equal(rows[0].acceptance[0],baseline.acceptance[0]);
 assert.ok(rows[0].steps.some(step=>step.includes(project.edges[0].interfaceSpec.failure)));assert.match(rows[0].steps.join(' '),/record any conflict/);
});

test('the actual receiving CLI runs and rejects cost coupling, missing contract detail and escaped evidence paths',()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atmem-receiving-cli-'));
 const cli=path.resolve('scripts/verify-module-task-context.mjs');
 function write(root,files){for(const [name,text]of Object.entries(files)){const target=path.join(root,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,text);}}
 function inspect(root,baseline){return spawnSync(process.execPath,[cli,root,...(baseline?[baseline]:[])],{encoding:'utf8'});}
 try{
  for(const domain of ['library-loans','procurement-review']){
   const root=path.join(directory,domain),files=deliveryPack(fixture(domain),null);write(root,files);
   let check=inspect(root);assert.equal(check.status,0,check.stderr);assert.equal(JSON.parse(check.stdout).savedContracts,1);
   const original=JSON.parse(files['spec-kit/tasks.json']);let broken=structuredClone(original);
   broken.tasks.find(task=>task.phase==='Components').dependsOn.push('TASK-COST-BASELINE');fs.writeFileSync(path.join(root,'spec-kit/tasks.json'),JSON.stringify(broken));
   check=inspect(root);assert.notEqual(check.status,0);assert.match(check.stderr,/Cost blocks local/);
   broken=structuredClone(original);const contract=broken.tasks.find(task=>task.phase==='Contracts');contract.steps=contract.steps.filter(step=>!step.includes('same-ID replay'));fs.writeFileSync(path.join(root,'spec-kit/tasks.json'),JSON.stringify(broken));
   check=inspect(root);assert.notEqual(check.status,0);assert.match(check.stderr,/Lost saved contract detail/);
   write(root,files);const baseline=path.join(directory,domain+'-baseline');write(baseline,files);fs.writeFileSync(path.join(baseline,'design-documents-receipt.json'),JSON.stringify({files:[{exportPath:'../outside.md'}]}));
   check=inspect(root,baseline);assert.notEqual(check.status,0);assert.match(check.stderr,/Invalid package path/);
  }
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});
