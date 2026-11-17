export const ACTIVE = new Set(['queued','inventory','baseline','drafting','checking']);
export const PHASES = ['inventory','baseline','control','drafting','candidate','ready_for_review'];
export function progress(job) {
  const done = job?.status === 'ready_for_review';
  const active=ACTIVE.has(job?.status);
  const completed = new Set(active||done?(job?.receipts || []).filter(r=>r.status==='passed'&&r.kind==='baseline'||r.kind==='control'&&r.status==='failed').map(r=>r.kind):[]);
  if(job?.candidate&&(active||done))completed.add('patch');
  const labels={queued:'Queued',inventory:'Reading Terraform',baseline:'Checking baseline',control:'Confirming upgrade break',drafting:'Preparing patch',candidate:'Checking candidate',ready_for_review:'Patch ready for review',blocked:'Needs attention',failed:'Preparation failed',canceled:'Canceled',stale:'Source or tools changed',historical:'Imported evidence · recheck required'};
  return {active,completed,done,label:labels[active?job?.phase:job?.status] || 'Select source'};
}
export function selectionPath(file) {
  const raw=file.webkitRelativePath || file.name;
  const path=file.webkitRelativePath ? raw.split('/').slice(1).join('/') : raw;
  if (!path || path.startsWith('/') || path.includes('\\') || path.split('/').some(p=>!p||p==='..'||p==='.')) throw Error('Invalid source path.');
  return path;
}
export function selectable(path) {
  return !path.split('/').some(p=>['.git','.terraform','node_modules','.venv'].includes(p)) &&
    !/(^|\/)(\.env[^/]*|.*\.tfvars(?:\.json)?|.*\.pem|.*\.key|credentials|secrets?[^/]*)$/i.test(path) &&
    (path.endsWith('.tf')||path.endsWith('.tf.json')||path.endsWith('.tftest.hcl')||path.endsWith('.terraform.lock.hcl')||/(^|\/)(\.github\/|\.gitlab-ci|atlantis\.|Jenkinsfile|azure-pipelines|\.circleci\/|\.buildkite\/)/i.test(path));
}
export async function readSelection(fileList) {
  const selected={};let total=0;
  for(const file of fileList) {
    const path=selectionPath(file);
    if(!selectable(path))continue;
    if(selected[path]!==undefined)throw Error('Duplicate source paths.');
    total+=file.size;
    if(file.size>2_000_000||total>8_000_000||Object.keys(selected).length>=1000)throw Error('Source exceeds limits. No files were truncated.');
    try{selected[path]=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(await file.arrayBuffer());}
    catch{throw Error('Select valid UTF-8 source. Invalid bytes were rejected without altering files.');}
  }
  if(!Object.keys(selected).length)throw Error('Select a folder containing Terraform files.');
  return selected;
}
export function historicalSection(section) {
  validateSection(section);
  const value=structuredClone(section);
  value.aggregate.imported=true;
  for(const job of value.aggregate.jobs){job.status='historical';job.phase='reproduce_checks';for(const receipt of job.receipts||[])receipt.status='historical';}
  value.sha256=sectionDigest(value.aggregate);return value;
}
import {sha256} from '@noble/hashes/sha2.js';
import {bytesToHex} from '@noble/hashes/utils.js';
const codepointOrder=(a,b)=>{const x=Array.from(a,c=>c.codePointAt(0)),y=Array.from(b,c=>c.codePointAt(0));for(let i=0;i<Math.min(x.length,y.length);i++)if(x[i]!==y[i])return x[i]-y[i];return x.length-y.length;};
export function canonical(value){
 if(value===null||typeof value!=='object')return JSON.stringify(value);
 if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
 return '{'+Object.keys(value).sort(codepointOrder).map(key=>JSON.stringify(key)+':'+canonical(value[key])).join(',')+'}';
}
export function sectionDigest(value){return bytesToHex(sha256(new TextEncoder().encode(canonical(value))));}
export function validateSection(section){
 if(!section||Object.keys(section).some(k=>!['schemaVersion','aggregate','sha256'].includes(k))||section.schemaVersion!==1||!section.aggregate||!Array.isArray(section.aggregate.snapshots)||!Array.isArray(section.aggregate.jobs)||sectionDigest(section.aggregate)!==section.sha256)throw Error('Invalid maintenance section or content digest.');
 return section;
}
