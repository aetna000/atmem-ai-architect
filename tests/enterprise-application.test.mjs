import test from'node:test';
import assert from'node:assert/strict';
import fs from'node:fs';
import {createHash}from'node:crypto';
import {enterpriseApplicationFiles}from'../src/enterprise-application.mjs';
import inventory from'../src/runtime/enterprise-application-manifest.json'with{type:'json'};
const address='block_6b6e6f776c65646765',root='applications/'+address+'/';
test('private application emissions use the exact common inventory and selected-provider hash lock',()=>{
 for(const provider of ['aws','azure','gcp','ibm']){
  const files=enterpriseApplicationFiles(provider,address),manifest=JSON.parse(files[root+'application-manifest.json']);
  assert.equal(manifest.provider,provider);assert.equal(manifest.wholeProjectQualified,false);
  for(const name of [...inventory.files,...inventory.providerFiles[provider]]){
   const actual=fs.readFileSync(new URL('../src/runtime/'+name,import.meta.url),'utf8');
   assert.equal(files[root+'runtime/'+name],actual);assert.equal(manifest.sourceHashes[name],createHash('sha256').update(actual).digest('hex'));
  }
  const lock=JSON.parse(fs.readFileSync(new URL('../src/runtime/enterprise-runtime-'+provider+'-python-lock.json',import.meta.url)));
  assert.equal(files[root+'requirements.lock'],lock.requirements);
  assert.equal(manifest.documentWorkerImplemented,['aws','gcp'].includes(provider));
 }
});
test('private delivery keeps parser/OCR build recipes separate from the credentialed application',()=>{
 const files=enterpriseApplicationFiles('aws',address);
 assert.equal(files[root+'runtime/enterprise_document.py'],undefined);assert.equal(files[root+'runtime/EnterpriseDocument.java'],undefined);
 assert.equal(files[root+'Dockerfile'],fs.readFileSync(new URL('../src/runtime/enterprise-runtime.Dockerfile',import.meta.url),'utf8'));
 assert.equal(files[root+'parser/EnterpriseDocument.java'],fs.readFileSync(new URL('../src/runtime/EnterpriseDocument.java',import.meta.url),'utf8'));
 assert.equal(files[root+'parser/pdf/Dockerfile'],fs.readFileSync(new URL('../src/runtime/invoice-parser.Dockerfile',import.meta.url),'utf8'));
 assert.equal(files[root+'parser/pdf/parser-requirements.lock'],fs.readFileSync(new URL('../src/runtime/parser-requirements.lock',import.meta.url),'utf8'));
 assert.ok(!files[root+'.dockerignore'].includes('!runtime/**'));
});
test('private process contract separates API metadata, executor configuration and native secret injection',()=>{
 const files=enterpriseApplicationFiles('gcp',address),contract=JSON.parse(files[root+'configuration-contract.json']);
 assert.equal(contract.deployment.direct,'ENTERPRISE_DEPLOYMENT_JSON');assert.equal(contract.documentExecutor.direct,'ENTERPRISE_DOCUMENT_EXECUTOR_JSON');
 assert.equal(contract.documentExecutor.schema,'enterprise-document-executor-v1');assert.equal(contract.documentExecutor.maximumBytes,32768);
 assert.match(files[root+'BUILD.md'],/distinct identities/);assert.match(files[root+'BUILD.md'],/Azure\/IBM loading/);
 assert.equal(files[root+'runtime/enterprise-deployment.json'],undefined);
});
test('private application emission rejects provider fallback and redirected component paths',()=>{
 for(const [provider,key]of [['unknown',address],['aws','../arbitrary'],['aws','block_${file}']])assert.throws(()=>enterpriseApplicationFiles(provider,key));
});
