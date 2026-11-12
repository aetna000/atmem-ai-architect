// Qualification driver. Provider selection belongs to the real application builder.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {zipSync,unzipSync,strToU8} from 'fflate';
import {invoiceApplicationFiles} from '../../../../src/invoice-application.mjs';
const version=process.argv[2]||'v1';
if(!/^v[1-9][0-9]*$/.test(version))throw Error('Use a fresh numbered artifact revision');
const bulk='.local/external-artifacts/workflow-bootstrap/emitted-'+version;
if(fs.existsSync(bulk))throw Error('Preserve old bytes; select a fresh revision');
fs.mkdirSync(bulk,{recursive:true});
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex'),manifest=[];
for(const provider of ['aws','azure','gcp','ibm']){
 const files=invoiceApplicationFiles(provider,'block_626f6f747374726170');
 const bytes=zipSync(Object.fromEntries(Object.entries(files).map(([name,source])=>[name,strToU8(source)])));
 const archive=path.join(bulk,provider+'.zip');fs.writeFileSync(archive,bytes);
 for(const[name,raw]of Object.entries(unzipSync(fs.readFileSync(archive)))){
  if(sha(raw)!==sha(files[name]))throw Error('Exported file identity mismatch');
  const destination=path.join(bulk,provider,name);fs.mkdirSync(path.dirname(destination),{recursive:true});fs.writeFileSync(destination,raw);
 }
 manifest.push({provider,archive,sha256:sha(bytes),files:Object.fromEntries(Object.entries(files).map(([name,source])=>[name,sha(source)])),boundary:'Four application emissions; no four-cloud runtime, IAM, network or Terraform qualification claim'});
}
for(const name of ['workflow_application.py','workflow_configuration.py','workflow_identity.py','workflow_http.py','workflow_payload.py','workflow_worker.py']){
 if(new Set(manifest.map(row=>row.files['applications/block_626f6f747374726170/'+name])).size!==1)throw Error('Unexpected provider divergence in shared runtime');
}
fs.writeFileSync('specs/029-general-purpose-engine/evidence/20261112-workflow-bootstrap/emitted-manifest-'+version+'.json',JSON.stringify(manifest,null,2)+'\n');
console.log('Four actual application ZIPs unpacked and byte-verified');
