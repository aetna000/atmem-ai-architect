// Independent dependency and archive checks on actual exported Spec Kit packages.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {zipSync,unzipSync,strToU8}from 'fflate';import {deliveryPack}from '../../../../src/delivery.mjs';import {fromProjectFile}from '../../../../src/project-file.mjs';
const base='.local/external-artifacts/deferred-bindings/v1',sha=b=>crypto.createHash('sha256').update(b).digest('hex'),rows=[];
for(const provider of ['aws','azure','gcp','ibm']){
 const project=fromProjectFile(JSON.parse(fs.readFileSync(path.join(base,provider+'.project.json')))).project;
 const files=deliveryPack(project,null,'staging'),archive=path.join(base,provider+'.handoff.zip');assert(!fs.existsSync(archive));
 const zip=zipSync(Object.fromEntries(Object.entries(files).map(([name,value])=>[name,strToU8(value)])));fs.writeFileSync(archive,zip);
 const unpacked=unzipSync(fs.readFileSync(archive));for(const[name,value]of Object.entries(unpacked))assert.equal(sha(value),sha(files[name]));
 const tasks=JSON.parse(new TextDecoder().decode(unpacked['spec-kit/tasks.json'])).tasks;
 const visit=(id,chain=[])=>{assert(!chain.includes(id),'Task cycle: '+[...chain,id].join(' -> '));const task=tasks.find(t=>t.id===id);assert(task,'Missing task '+id);for(const dep of task.dependsOn)visit(dep,[...chain,id]);};for(const task of tasks)visit(task.id);
 const assembly=tasks.find(t=>t.id.startsWith('TASK-APP-ASSEMBLY-')),binding=tasks.find(t=>t.id.startsWith('TASK-APP-BINDING-')),owners=tasks.filter(t=>t.id.startsWith('TASK-RESOURCE-'));
 assert(binding.dependsOn.includes(assembly.id));for(const task of owners)assert(binding.dependsOn.includes(task.id));assert(tasks.find(t=>t.id==='TASK-E2E').dependsOn.includes(binding.id));
 assert(assembly.files.some(n=>n.endsWith('/application-template.json')));assert(!assembly.files.some(n=>n.endsWith('/application-profile.json')));
 rows.push({provider,archive,sha256:sha(zip),files:Object.fromEntries(Object.entries(files).map(([name,value])=>[name,sha(value)])),bindingDependencies:binding.dependsOn,acyclic:true});
}
fs.writeFileSync('specs/029-general-purpose-engine/evidence/20261112-deferred-bindings/handoff-manifest-v1.json',JSON.stringify({passed:true,rows,boundary:'Save/reopen/export/ZIP bytes and complete task DAG; no task execution or deployment acceptance'},null,2)+'\n');
console.log('Four actual handoff archives retain template/resolver, owned dependencies and acyclic task graphs');
