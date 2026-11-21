import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
const run=args=>spawnSync('.venv/bin/python',['-I','scripts/qualify-invoice-restore.py',...args],{encoding:'utf8',timeout:10000});
test('restore rejects incomplete or non-local artifact admission before importing application code',()=>{
 let result=run(['--application-source','/tmp/unqualified-application']);assert.notEqual(result.status,0);assert.match(result.stderr,/Provide both exact application source/);
 result=run(['--application-source','/tmp/unqualified-application','--artifact-receipt','/tmp/unqualified-receipt']);assert.notEqual(result.status,0);assert.match(result.stderr,/Use local qualification artifacts/);
});
test('restore rejects a failed receipt and modified emitted Python before importing it',t=>{
 fs.mkdirSync(path.resolve('.local'),{recursive:true});
 const root=fs.mkdtempSync(path.resolve('.local/invoice-restore-admission-test-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const app=path.join(root,'application'),receipt=path.join(root,'qualification.json');fs.mkdirSync(app);fs.writeFileSync(path.join(app,'invoice_http.py'),'raise RuntimeError("UNQUALIFIED_CODE_EXECUTED")\n');
 fs.writeFileSync(receipt,JSON.stringify({kind:'invoice-live-artifact-native-qualification',passed:false}));
 let result=run(['--application-source',app,'--artifact-receipt',receipt]);assert.notEqual(result.status,0);assert.match(result.stderr,/Use a passing exact live artifact receipt/);assert.doesNotMatch(result.stderr,/UNQUALIFIED_CODE_EXECUTED/);
 fs.writeFileSync(receipt,JSON.stringify({kind:'invoice-live-artifact-native-qualification',passed:true,sourceHashes:{'applications/application/invoice_http.py':'0'.repeat(64)}}));
 result=run(['--application-source',app,'--artifact-receipt',receipt]);assert.notEqual(result.status,0);assert.match(result.stderr,/Application differs from original live artifact/);assert.doesNotMatch(result.stderr,/UNQUALIFIED_CODE_EXECUTED/);
});
