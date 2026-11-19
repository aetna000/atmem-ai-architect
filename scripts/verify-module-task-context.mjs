// Independent receiving-package inspection: no generator imports or inferred execution.
import fs from'node:fs';import path from'node:path';import assert from'node:assert/strict';
const root=fs.realpathSync(path.resolve(process.argv[2]||'.')),baseline=process.argv[3]?fs.realpathSync(path.resolve(process.argv[3])):null;
function bytes(base,name){
 assert.equal(typeof name,'string');assert.ok(!name.includes('\\')&&name.split('/').every(part=>part&&part!=='.'&&part!=='..'),'Invalid package path');
 const target=path.resolve(base,name);assert.ok(target.startsWith(base+path.sep));assert.ok(fs.realpathSync(target).startsWith(base+path.sep));assert.ok(fs.statSync(target).isFile()&&fs.statSync(target).size<=20_000_000);return fs.readFileSync(target);
}
const read=(base,name)=>JSON.parse(bytes(base,name).toString('utf8'));
const project=read(root,'project.atmem-ai-architect.json'),tasks=read(root,'spec-kit/tasks.json').tasks;
const byId=new Map(tasks.map(task=>[task.id,task]));assert.equal(byId.size,tasks.length);
function dependencies(task){const seen=new Set(),active=new Set();function visit(id){assert.ok(!active.has(id),'Cycle at '+id);if(seen.has(id))return;assert.ok(byId.has(id),'Missing '+id);active.add(id);byId.get(id).dependsOn.forEach(visit);active.delete(id);seen.add(id);}task.dependsOn.forEach(visit);return seen;}
const components=tasks.filter(task=>task.phase==='Components'),contracts=tasks.filter(task=>task.phase==='Contracts');
for(const task of components){const prior=dependencies(task);assert.ok(!prior.has('TASK-COST-BASELINE'),'Cost blocks local '+task.id);assert.ok(!prior.has('TASK-STAGING'),'Staging blocks local '+task.id);}
let savedContracts=0,scopedComponents=0;
for(const edge of project.design.edges.filter(edge=>edge.interfaceSpec)){
 const task=contracts.find(task=>task.edgeIds.includes(edge.id));assert.ok(task,'Missing contract task '+edge.id);
 for(const value of Object.values(edge.interfaceSpec))assert.ok(task.steps.some(step=>step.includes(value)),'Lost saved contract detail '+edge.id);
 savedContracts++;
}
for(const node of project.design.nodes.filter(node=>node.data.buildSpec)){
 const task=components.find(task=>task.componentIds.includes(node.id));assert.ok(task,'Missing component '+node.id);
 for(const [field,text]of Object.entries(node.data.buildSpec))if(field!=='scenarios')assert.ok(task.steps.some(step=>step.includes(text)),'Lost block detail '+node.id+'/'+field);
 if(node.data.provider==='tools'&&!node.data.implementation)assert.ok(!task.files.some(name=>name.startsWith('terraform/')),'Assumed IaC target '+node.id);
 scopedComponents++;
}
assert.ok(dependencies(byId.get('TASK-CLOUD-PLAN')).has('TASK-COST-BASELINE'));
assert.ok(dependencies(byId.get('TASK-STAGING')).has('TASK-COST'));
assert.match(byId.get('TASK-STAGING').steps.join(' '),/explicit staging deployment authorization/);
let preservedDocuments=0;
if(baseline){
 const old=read(baseline,'project.atmem-ai-architect.json');
 for(const key of ['design','requirements','decisions','assumptions','openQuestions','extensions'])assert.deepEqual(project[key],old[key],'Source '+key+' changed');
 assert.deepEqual(tasks.map(task=>task.id),read(baseline,'spec-kit/tasks.json').tasks.map(task=>task.id),'Task identities changed');
 for(const file of read(baseline,'design-documents-receipt.json').files){assert.ok(bytes(root,file.exportPath).equals(bytes(baseline,file.exportPath)),'Authored file changed '+file.exportPath);preservedDocuments++;}
}
console.log(JSON.stringify({status:'task_context_checks_passed',tasks:tasks.length,localBuildsWithoutCostOrStagingDependency:components.length,savedContracts,scopedComponents,preservedDocuments,boundary:'Task/source correspondence, dependency and custody inspection only. No code, live integration or deployment acceptance.'},null,2));
