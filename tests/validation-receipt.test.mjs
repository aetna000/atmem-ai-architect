import test from 'node:test';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';import {verifiedReceipt} from '../src/validation-receipt.mjs';
const files={'main.tf.json':'{"resource":{}}','README.md':'Review the generated scope.'};
const result={status:'passed',checks:[{name:'schema',passed:true}],fileDigests:Object.fromEntries(Object.entries(files).map(([n,t])=>[n,createHash('sha256').update(t).digest('hex')]))};
test('validation evidence is included only for exact verified bytes and file inventory',async()=>{
 assert.equal((await verifiedReceipt(files,result)).cloudPlan,'not_run');assert.equal(await verifiedReceipt({...files,'README.md':'changed'},result),null);assert.equal(await verifiedReceipt({...files,'extra.py':'unverified'},result),null);assert.equal(await verifiedReceipt({'main.tf.json':files['main.tf.json']},result),null);assert.equal(await verifiedReceipt(files,null),null);
});
