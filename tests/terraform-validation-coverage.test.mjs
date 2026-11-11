import test from 'node:test';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';import {moduleValidationCoverage} from '../src/terraform-validation-coverage.mjs';import {verifiedReceipt} from '../src/validation-receipt.mjs';
const modules=[{id:'a',path:'units/unit_61'},{id:'b',path:'units/unit_62'}],complete={status:'passed',checks:modules.flatMap(m=>['init','validate','test'].map(stage=>({moduleId:m.id,modulePath:m.path,stage,passed:true,...(stage==='test'?{testsReported:4}:{})})))};
test('complete scoped module results pass while legacy standalone and failed results remain unchanged',()=>{assert.equal(moduleValidationCoverage(complete,modules),complete);const legacy={status:'passed',checks:[]},failure={status:'failed'};assert.equal(moduleValidationCoverage(legacy),legacy);assert.equal(moduleValidationCoverage(failure,modules),failure);});
test('root-only, missing, misbound and zero-test module results remain incomplete without changing the raw response',()=>{
 for(const checks of [[],complete.checks.slice(1),complete.checks.map(c=>({...c,modulePath:'units/foreign'})),complete.checks.map(c=>({...c,testsReported:0}))]){const raw={status:'passed',checks},value=moduleValidationCoverage(raw,modules);assert.equal(value.status,'incomplete');assert(value.missingModuleChecks.length);assert.equal(raw.status,'passed');}
});
test('digest-matching exports cannot turn an old root-only response into passed module evidence',async()=>{
 const files={'main.tf.json':'{}','generation-quality.json':JSON.stringify({modules})},result={status:'passed',checks:[],fileDigests:Object.fromEntries(Object.entries(files).map(([path,body])=>[path,createHash('sha256').update(body).digest('hex')]))};
 assert.equal((await verifiedReceipt(files,result)).status,'incomplete');assert.equal((await verifiedReceipt(files,{...result,checks:complete.checks})).status,'passed');
});
