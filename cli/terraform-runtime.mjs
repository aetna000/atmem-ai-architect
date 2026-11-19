// Managed local Terraform prerequisite. No cloud account or provider execution.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath}from 'node:url';
import {createHash}from 'node:crypto';
import {execFile}from 'node:child_process';
import {promisify}from 'node:util';
import {unzipSync}from 'fflate';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const lock=JSON.parse(fs.readFileSync(path.join(root,'packaging/terraform-release-lock.json'),'utf8'));
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const execute=promisify(execFile);
export function terraformTarget(platform=process.platform,arch=process.arch){
 const target=lock.targets[`${platform}-${arch}`];if(!target)throw Error(`No managed Terraform runtime for ${platform}/${arch}.`);return{...target,version:lock.version};
}
function locations(home){const target=terraformTarget(),folder=path.join(home,'runtime-tools',`terraform-${target.version}-${process.platform}-${process.arch}`);return{target,folder,binary:path.join(folder,target.binary),receipt:path.join(folder,'ready.json')};}
export function terraformStatus(home){
 const {target,binary,receipt}=locations(home);
 try{const saved=JSON.parse(fs.readFileSync(receipt,'utf8'));if(saved.version===target.version&&saved.archiveSha256===target.sha256&&saved.binarySha256===digest(fs.readFileSync(binary)))return{ready:true,version:target.version,binary};}catch{}
 return{ready:false,version:target.version,binary};
}
export function extractTerraform(archive,target){
 const files=unzipSync(archive,{filter:entry=>{if(![target.binary,'LICENSE.txt'].includes(entry.name))return false;if(entry.originalSize>(entry.name===target.binary?200*1024*1024:1024*1024))throw Error('Terraform archive member exceeds its size limit.');return true;}});
 if(!files[target.binary]?.length)throw Error('Expected the native Terraform executable in its release archive.');
 return{binary:Buffer.from(files[target.binary]),license:files['LICENSE.txt']?Buffer.from(files['LICENSE.txt']):null};
}
async function download(url){
 const response=await fetch(url,{signal:AbortSignal.timeout(120000)});if(!response.ok)throw Error(`Terraform download failed (${response.status}); retry startup when internet access is available.`);
 const chunks=[];let size=0;for await(const chunk of response.body){size+=chunk.length;if(size>80*1024*1024)throw Error('Terraform archive exceeds its download limit.');chunks.push(chunk);}return Buffer.concat(chunks);
}
export async function ensureTerraform(home,{downloadArchive=download}={}){
 const cached=terraformStatus(home);if(cached.ready)return cached.binary;
 const {target,folder,binary,receipt}=locations(home);fs.mkdirSync(folder,{recursive:true,mode:0o700});
 const lease=path.join(folder,'install.lock');let descriptor;
 try{descriptor=fs.openSync(lease,'wx',0o600);}catch{throw Error('Terraform runtime setup is already running. Retry after it finishes.');}
 const temporary=binary+`.tmp-${process.pid}${process.platform==='win32'?'.exe':''}`;
 try{
  process.stdout.write(`Preparing the local Terraform ${target.version} runtime…\n`);
  const archive=await downloadArchive(target.url);
  if(digest(archive)!==target.sha256)throw Error('Terraform checksum mismatch; the download was not installed.');
  const extracted=extractTerraform(archive,target);fs.writeFileSync(temporary,extracted.binary,{mode:0o755,flag:'wx'});
  const result=await execute(temporary,['version','-json'],{cwd:folder,env:{...process.env,CHECKPOINT_DISABLE:'1'},timeout:15000,windowsHide:true});
  if(JSON.parse(result.stdout).terraform_version!==target.version)throw Error('Terraform executable version does not match its release pin.');
  fs.renameSync(temporary,binary);if(extracted.license)fs.writeFileSync(path.join(folder,'LICENSE.txt'),extracted.license,{mode:0o600});
  const pending=receipt+`.tmp-${process.pid}`;fs.writeFileSync(pending,JSON.stringify({version:target.version,archiveSha256:target.sha256,binarySha256:digest(extracted.binary)},null,2)+'\n',{mode:0o600});fs.renameSync(pending,receipt);
  return binary;
 }finally{fs.rmSync(temporary,{force:true});if(descriptor!==undefined)fs.closeSync(descriptor);fs.rmSync(lease,{force:true});}
}
