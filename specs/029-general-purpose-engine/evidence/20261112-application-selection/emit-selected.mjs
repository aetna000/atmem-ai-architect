import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
import {zipSync,unzipSync,strToU8} from 'fflate';import {approvalProject} from '../../../../tests/fixtures/approval-project.mjs';import {terraformSketch} from '../../../../src/terraform.mjs';import {toProjectFile,fromProjectFile} from '../../../../src/project-file.mjs';
const revision=process.argv[2]||'v1';if(!/^v[1-9][0-9]*$/.test(revision))throw Error('Use a new artifact revision');
const bulk='.local/external-artifacts/application-selection/'+revision;if(fs.existsSync(bulk))throw Error('Preserve previous qualification bytes');fs.mkdirSync(bulk,{recursive:true});
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex'),rows=[];
for(const provider of ['aws','azure','gcp','ibm']){
 const project=approvalProject(provider);project.nodes[0].data.approvalProfile.accountId=crypto.randomUUID();
 const saved=toProjectFile(project),reopened=fromProjectFile(saved).project,files=terraformSketch(reopened);
 const zip=zipSync(Object.fromEntries(Object.entries(files).map(([name,text])=>[name,strToU8(text)]))),archive=path.join(bulk,provider+'.zip');fs.writeFileSync(archive,zip);
 for(const[name,bytes]of Object.entries(unzipSync(fs.readFileSync(archive)))){if(sha(bytes)!==sha(files[name]))throw Error('Unpacked selected source differs');const destination=path.join(bulk,provider,name);fs.mkdirSync(path.dirname(destination),{recursive:true});fs.writeFileSync(destination,bytes);}
 fs.writeFileSync(path.join(bulk,provider+'.project.json'),JSON.stringify(saved,null,2)+'\n');
 rows.push({provider,archive,sha256:sha(zip),sourceProject:path.join(bulk,provider+'.project.json'),files:Object.fromEntries(Object.entries(files).map(([name,text])=>[name,sha(text)])),infrastructureComplete:JSON.parse(files['generation-quality.json']).infrastructureComplete});
}
fs.writeFileSync('specs/029-general-purpose-engine/evidence/20261112-application-selection/selected-manifest-'+revision+'.json',JSON.stringify(rows,null,2)+'\n');
console.log('Four actual selected-profile exports saved, reopened, unpacked and byte-checked');
