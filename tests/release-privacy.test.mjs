import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {zipSync,strToU8} from 'fflate';
import {createHash} from 'node:crypto';

test('release privacy checks inspect nested documents and keep confidential findings out of logs',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'architect-privacy-'));
 try{
  const policy=path.join(dir,'policy.json');fs.writeFileSync(policy,JSON.stringify({patterns:['ReservedClient-Example']}));
  const target=path.join(dir,'release.zip'),report=path.join(dir,'report.json');
  const run=()=>spawnSync(process.platform==='win32'?'python':'python3',['scripts/release-privacy-check.py','--require-policy','--policy',policy,'--report',report,target],{encoding:'utf8'});
  fs.writeFileSync(target,zipSync({'examples/neutral.json':strToU8('{"name":"Support assistant"}')}));
  assert.equal(run().status,0);
  fs.writeFileSync(target,zipSync({'examples/neutral.docx':zipSync({'word/document.xml':strToU8('<w:t>ReservedClient-Example</w:t>')})}));
  const rejected=run();assert.equal(rejected.status,1);assert.doesNotMatch(rejected.stdout,/ReservedClient/);assert.equal(JSON.parse(fs.readFileSync(report)).findings[0].reason,'confidential_content');
  fs.writeFileSync(target,zipSync({'client-projects/snapshot.json':strToU8('{}')}));assert.equal(run().status,1);
  const binary=Buffer.from([255,0,...Buffer.from('ReservedClient-Example'),254]);
  fs.writeFileSync(target,zipSync({'public-image.png':binary}));assert.equal(run().status,0,'compressed binary substrings are not text evidence');
  fs.writeFileSync(policy,JSON.stringify({file_sha256:[createHash('sha256').update(binary).digest('hex')]}));assert.equal(run().status,1,'private binary digests are rejected inside archives');
  fs.writeFileSync(target,Buffer.from('corrupt zip'));assert.equal(run().status,2);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

test('release package inspection allows contained archive aliases and rejects escaping targets',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'architect-privacy-links-'));
 try{
  const file=path.join(dir,'release.tgz'),python=process.platform==='win32'?'python':'python3';
  const make=target=>spawnSync(python,['-c','import tarfile,sys; a=tarfile.open(sys.argv[1],"w:gz"); m=tarfile.TarInfo("package/data/alias"); m.type=tarfile.SYMTYPE; m.linkname=sys.argv[2]; a.addfile(m); a.close()',file,target],{encoding:'utf8'});
  const check=()=>spawnSync(python,['scripts/release-privacy-check.py','--package',file],{encoding:'utf8'});
  assert.equal(make('target').status,0);assert.equal(check().status,0);
  assert.equal(make('../../../external').status,0);assert.equal(check().status,1);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
