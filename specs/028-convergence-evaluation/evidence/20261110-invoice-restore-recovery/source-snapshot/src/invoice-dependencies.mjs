import aws from './runtime/aws-web-python-lock.json' with {type:'json'};
import azure from './runtime/azure-python-lock.json' with {type:'json'};
import gcp from './runtime/web-python-lock.json' with {type:'json'};
import ibm from './runtime/ibm-python-lock.json' with {type:'json'};
import durable from './runtime/durable-python-lock.json' with {type:'json'};
import testing from './runtime/azure-test-lock.json' with {type:'json'};

const normalize=name=>name.toLowerCase().replaceAll(/[_.]+/g,'-');
function entries(lock){
 const result=[];let current;
 for(const line of lock.requirements.trim().split('\n')){
  if(!line.trim())continue;
  if(lock===testing&&line==='-r requirements.lock')continue; // Already merged above.
  const start=/^([A-Za-z0-9_.-]+)==([^\s\\]+)((?:\s+--hash=sha256:[0-9a-f]{64})*)(?:\s*\\)?$/.exec(line);
  if(start){current={name:normalize(start[1]),version:start[2],hashes:new Set([...start[3].matchAll(/--hash=sha256:([0-9a-f]{64})/g)].map(match=>match[1]))};result.push(current);continue;}
  const hash=/^\s+--hash=sha256:([0-9a-f]{64})(?:\s*\\)?$/.exec(line);
  if(!hash||!current)throw Error('Invoice dependencies must be exact reviewed version/hash records');current.hashes.add(hash[1]);
 }
 if(!result.length||result.some(entry=>!entry.hashes.size)||new Set(result.map(e=>e.name)).size!==result.length)throw Error('Incomplete or duplicate reviewed dependency records');return result;
}

// One explicit composition decision, not a general dependency-conflict override.
// IBM SDK 3.28.2 requires dateutil >=3,<3.1; Procrastinate/croniter accept it.
// The resulting queue composition still requires independent runtime tests.
export function invoiceDependencies(provider,{tests=false}={}){
 const native={aws,azure,gcp,ibm}[provider];if(!native)throw Error('Unsupported invoice dependency provider');
 const locks=[native,durable,...(tests?[testing]:[])],merged=new Map(),resolutions=[];
 for(const lock of locks)for(const entry of entries(lock)){
  if(provider==='aws'&&entry.name==='mangum')continue; // Fargate, not Lambda.
  const previous=merged.get(entry.name);
  if(previous&&previous.version!==entry.version){
   if(provider==='ibm'&&entry.name==='python-dateutil'&&new Set([previous.version,entry.version]).size===2&&[previous.version,entry.version].every(v=>['2.9.0.post0','3.0.0'].includes(v))){
    merged.set(entry.name,previous.version==='3.0.0'?previous:entry);resolutions.push({name:entry.name,selected:'3.0.0',otherReviewedPin:'2.9.0.post0',reason:'IBM SDK requires >=3,<3.1; queue dependency permits it. Whole composition qualification is mandatory.'});continue;
   }throw Error('Unreviewed invoice dependency conflict for '+entry.name);
  }
  if(previous)for(const hash of entry.hashes)previous.hashes.add(hash);else merged.set(entry.name,entry);
 }
 const records=[...merged.values()].sort((a,b)=>a.name.localeCompare(b.name));
 const requirements=records.map(e=>e.name+'=='+e.version+' \\\n'+[...e.hashes].sort().map((h,i,all)=>'    --hash=sha256:'+h+(i<all.length-1?' \\':'')).join('\n')).join('\n')+'\n';
 const sourceMap=new Map();for(const lock of locks)for(const source of lock.sources){const key=normalize(source.name),selected=merged.get(key);if(selected?.version===source.version)sourceMap.set(key,source);}
 if(records.some(record=>!sourceMap.has(record.name)))throw Error('Missing dependency provenance');
 return{requirements,sources:[...sourceMap.values()],resolutions,scope:'Reviewed dependency union; generation is not a runtime/clean-security claim'};
}
