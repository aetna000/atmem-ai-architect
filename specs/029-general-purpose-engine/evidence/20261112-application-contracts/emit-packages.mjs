// Qualification only: exact generated application packages, no cloud resources.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {zipSync,unzipSync,strToU8} from 'fflate';
import {invoiceApplicationFiles} from '../../../../src/invoice-application.mjs';
const revision=process.argv[2]||'v3';
if(!/^v[1-9][0-9]*$/.test(revision))throw Error('Use a new numbered evidence revision');
const bulk='.local/external-artifacts/application-contracts/emitted-'+revision;
if(fs.existsSync(bulk))throw Error('Preserve previous artifact bytes; choose a fresh revision');
fs.mkdirSync(bulk,{recursive:true});
const sha=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const manifest=[];
for(const provider of ['aws','azure','gcp','ibm']){
 const files=invoiceApplicationFiles(provider,'block_636f6e7472616374');
 const raw=zipSync(Object.fromEntries(Object.entries(files).map(([name,source])=>[name,strToU8(source)])));
 const archive=path.join(bulk,provider+'.zip');fs.writeFileSync(archive,raw);
 const unpacked=unzipSync(fs.readFileSync(archive));
 for(const [name,bytes]of Object.entries(unpacked)){
  if(sha(bytes)!==sha(files[name]))throw Error('Unpacked source differs');
  const dest=path.join(bulk,provider,name);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,bytes);
 }
 manifest.push({provider,archive,sha256:sha(raw),files:Object.fromEntries(Object.entries(files).map(([name,source])=>[name,sha(source)])),boundary:'Application emission only; not four cloud resource, identity or runtime acceptance'});
}
for(const name of ['durable_workflow.py','workflow_payload.py','workflow_contract.py','workflow_worker.py']){
 if(new Set(manifest.map(row=>row.files['applications/block_636f6e7472616374/'+name])).size!==1)throw Error('Unexpected provider divergence of shared runtime');
}
fs.writeFileSync('specs/029-general-purpose-engine/evidence/20261112-application-contracts/emitted-manifest-'+revision+'.json',JSON.stringify(manifest,null,2)+'\n');
console.log('Four application archives unpacked and byte-verified; shared runtime bytes identical');
