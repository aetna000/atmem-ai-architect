import test from 'node:test';import assert from 'node:assert/strict';
import {deliveryPack} from '../src/delivery.mjs';import {CONTAINER_SERVICES} from '../src/container-contracts.mjs';
for(const [provider,c] of Object.entries(CONTAINER_SERVICES))test(`${provider}: Spec Kit tasks link to emitted files and supplied-image inputs`,()=>{
 const p={version:1,revision:1,name:'Deployment',provider,nodes:[{id:'app',position:{x:0,y:0},data:{label:'Application',kind:'resource',provider,origin:'proposed',service:c.service,implementation:'container-service'}}],edges:[]};
 const files=deliveryPack(p,null),map=JSON.parse(files['spec-kit/implementation-map.json']);const row=map.components[0];assert.ok(row.terraformAddresses.includes(c.type+'.block_617070'));assert.ok(row.requiredInputs.includes('block_617070_image'));assert.equal(row.applicationImplementation,'supplied_image_required');
 for(const name of row.generatedFiles)assert.ok(files[name],name);const tasks=JSON.parse(files['spec-kit/tasks.json']).tasks;assert.ok(tasks.some(t=>t.componentIds?.includes('app')&&t.files.includes('terraform/main.tf.json')));assert.ok(JSON.parse(files['manifest.json']).files.includes('spec-kit/implementation-map.json'));
});
