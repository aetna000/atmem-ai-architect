import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {invoiceProject} from './fixtures/invoice-project.mjs';
import {terraformSketch} from '../src/terraform.mjs';
import {invoiceCaseArtifact} from '../scripts/invoice-case-artifact.mjs';

function fixture(t,provider='ibm'){
 const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'invoice-case-test-')));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const project=invoiceProject(provider),files=terraformSketch(project,'staging'),digests={};
 for(const[name,body]of Object.entries(files)){
  const target=path.join(root,'handoff/terraform',name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,body);digests['terraform/'+name]=createHash('sha256').update(body).digest('hex');
 }
 fs.writeFileSync(path.join(root,'project.json'),JSON.stringify(project));
 fs.writeFileSync(path.join(root,'handoff/manifest.json'),JSON.stringify({environment:'staging',deploymentExecuted:false,files:Object.keys(digests)}));
 fs.writeFileSync(path.join(root,'export-assessment.json'),JSON.stringify({digests}));
 return {root,files,digests};
}
for(const provider of ['aws','azure','gcp','ibm'])test(provider+' admits exact original artifact bytes without modifying them',t=>{
 const{root,files}=fixture(t,provider);assert.deepEqual(invoiceCaseArtifact(root,provider).files,files);
 assert.equal(fs.readFileSync(path.join(root,'handoff/terraform/main.tf.json'),'utf8'),files['main.tf.json']);
});
test('rejects corrupt original bytes and an internally receipted executable mutation',t=>{
 const{root,digests}=fixture(t),name='terraform/tests/invoice.tftest.hcl',body='run "unsafe" { command = apply }\n';
 fs.writeFileSync(path.join(root,'handoff',name),body);
 assert.throws(()=>invoiceCaseArtifact(root,'ibm'),/digest mismatch/);
 digests[name]=createHash('sha256').update(body).digest('hex');fs.writeFileSync(path.join(root,'export-assessment.json'),JSON.stringify({digests}));
 assert.throws(()=>invoiceCaseArtifact(root,'ibm'),/no longer reproduces/);
});
test('rejects provider mismatch, missing inventory and symlinks',t=>{
 const{root}=fixture(t);assert.throws(()=>invoiceCaseArtifact(root,'aws'),/provider differs/);
 const file=path.join(root,'handoff/manifest.json'),manifest=JSON.parse(fs.readFileSync(file));manifest.files=manifest.files.filter(name=>name!=='terraform/main.tf.json');fs.writeFileSync(file,JSON.stringify(manifest));
 assert.throws(()=>invoiceCaseArtifact(root,'ibm'),/Incomplete/);
 fs.unlinkSync(path.join(root,'project.json'));fs.symlinkSync(file,path.join(root,'project.json'));assert.throws(()=>invoiceCaseArtifact(root,'ibm'),/symlink/);
});
