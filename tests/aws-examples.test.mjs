import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {verifyExamples} from '../scripts/aws-example-check.mjs';

test('all published AWS examples import, satisfy scope and match their evidence hashes',()=>{
 const manifest=verifyExamples();
 assert.equal(manifest.scenarios.length,7);
 assert.equal(manifest.scenarios.filter(s=>s.cloudPlan==='passed').length,6);
 assert.ok(manifest.scenarios.every(s=>s.deployment==='not_run'));
 assert.equal(manifest.scenarios[0].priorLiveQualification.cleanup,'passed');
 const connector=manifest.scenarios.at(-1);
 assert.ok(connector.files.some(f=>f.path.includes('2026-11-07T05-49-19.638Z/round-1/validation.json')));
});

test('archive verification rejects changed evidence instead of reporting an inherited pass',()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'atmem-example-integrity-'));
 try{
  const manifest=JSON.parse(fs.readFileSync(new URL('../examples/aws/manifest.json',import.meta.url),'utf8'));
  const file=manifest.scenarios[0].files[0];
  fs.mkdirSync(path.dirname(path.join(tmp,file.path)),{recursive:true});
  fs.writeFileSync(path.join(tmp,file.path),'changed');
  fs.writeFileSync(path.join(tmp,'manifest.json'),JSON.stringify(manifest));
  assert.throws(()=>verifyExamples(tmp),/integrity mismatch/);
 }finally{fs.rmSync(tmp,{recursive:true,force:true});}
});
