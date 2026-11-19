import test from'node:test';import assert from'node:assert/strict';import{readSystemSpec}from'../src/canvas-quality.mjs';
const spec=()=>({title:'Portable records',decomposition:'Records and admission',infrastructure:'Preserve complete placement reasoning.',operations:'Recover using a fenced writer',testing:'Exercise approved recovery',journeys:[{name:'Admit',steps:[{sender:'User',receiver:'Records',action:'Store'}]}],deploymentUnits:[{name:'Record writer',placement:'Qualified on-premises runtime',blocks:['records']}]});
test('deployment diagnostics name exact field and unchanged bound without discarding content',()=>{
 const value=spec();value.deploymentUnits[0].placement='placement rationale '.repeat(20);const copy=structuredClone(value);
 assert.throws(()=>readSystemSpec(value,[{id:'records'}]),/deploymentUnits\[0\]\.placement needs 1–150 UTF-16/);assert.deepEqual(value,copy);
 value.deploymentUnits[0].placement='on-prem';assert.equal(readSystemSpec(value,[{id:'records'}]).infrastructure,value.infrastructure);
});
test('unknown deployment IDs are distinguished from text limits and valid domain IDs transfer',()=>{
 const value=spec();value.deploymentUnits[0].blocks=['award-ledger'];assert.throws(()=>readSystemSpec(value,[{id:'records'}]),/unknown IDs: \["award-ledger"\]/);
 assert.deepEqual(readSystemSpec(value,[{id:'award-ledger'}]).deploymentUnits,value.deploymentUnits);
});
