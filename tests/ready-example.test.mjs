import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {createHash} from 'node:crypto';import {unzipSync,strFromU8} from 'fflate';
import {readyExample,isReadyExample} from '../src/ready-example.mjs';import {estimate} from '../src/estimate.mjs';
test('portable reference includes complete priced source, built runtime and exact local qualification',()=>{
 const p=readyExample(),second=readyExample();assert.ok(isReadyExample(p));p.nodes.pop();assert.notEqual(p.nodes.length,second.nodes.length);assert.equal(isReadyExample({nodes:[]}),false);
 const cost=estimate(second);assert.equal(cost.complete,true);assert.equal(cost.expected,7.56);
 const receipt=JSON.parse(fs.readFileSync('src/reference-example/receipt.json'));assert.equal(receipt.sessionId,undefined);assert.equal(receipt.artifactId,undefined);
 const bytes=fs.readFileSync('public/reference-example.zip');assert.equal(createHash('sha256').update(bytes).digest('hex'),receipt.sha256);const files=unzipSync(bytes);
 assert.ok(files['terraform/build/block_7261672d666e.zip']);assert.ok(files['terraform/main.tf.json']);assert.ok(files['START_HERE.md']);assert.equal(files['project-context.json'],undefined);
 const q=JSON.parse(strFromU8(files['evidence/qualification.json']));assert.equal(q.applicationTests.count,13);assert.equal(q.terraformMockPlans.count,2);assert.equal(q.cloudDeployment,'not_run');
 for(const f of q.files)assert.equal(createHash('sha256').update(files[f.path]).digest('hex'),f.sha256,f.path);
 assert.equal(Object.keys(files).some(n=>n.startsWith('.agents/')||n.startsWith('atmem-tools/')),false);
});
