import {existingDeployment} from './deployment-ownership.mjs';
import {sha256} from '@noble/hashes/sha2.js';
const canonical=v=>Array.isArray(v)?v.map(canonical):plain(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const bytes=v=>new TextEncoder().encode(v).length;
const plain=v=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&[Object.prototype,null].includes(Object.getPrototypeOf(v));
const fail=()=>{throw Error('Invalid approval application declaration; no fields were discarded.');};
const exact=(v,keys)=>{if(!plain(v)||Object.keys(v).length!==keys.length||keys.some(k=>!Object.hasOwn(v,k)))fail();};
const integer=(v,min,max)=>Number.isSafeInteger(v)&&v>=min&&v<=max;
function json(value,depth=0){
 if(depth>32)fail();
 if(typeof value==='string'){try{encodeURIComponent(value);}catch{fail();}}
 else if(Array.isArray(value))value.forEach(v=>json(v,depth+1));
 else if(plain(value))Object.values(value).forEach(v=>json(v,depth+1));
 else if(value!==null&&typeof value!=='boolean'&&!Number.isSafeInteger(value))fail();
}
function schema(v,depth,budget){
 if(depth>8||--budget.count<0||!plain(v))fail();
 const shapes={object:['type','properties','required'],array:['type','items','maxItems'],string:['type','minBytes','maxBytes'],integer:['type','minimum','maximum'],boolean:['type'],enum:['type','values']};
 if(!Object.hasOwn(shapes,v.type))fail();exact(v,shapes[v.type]);
 if(v.type==='object'){
  if(!plain(v.properties)||Object.keys(v.properties).length<1||Object.keys(v.properties).length>32||Object.keys(v.properties).some(k=>!/^[A-Za-z][A-Za-z0-9_]{0,79}$/.test(k))||!Array.isArray(v.required)||new Set(v.required).size!==v.required.length||v.required.some(k=>typeof k!=='string'||!Object.hasOwn(v.properties,k)))fail();
  Object.values(v.properties).forEach(s=>schema(s,depth+1,budget));
 }else if(v.type==='array'){if(!integer(v.maxItems,1,64))fail();schema(v.items,depth+1,budget);}
 else if(v.type==='string'){if(!integer(v.minBytes,0,64000)||!integer(v.maxBytes,v.minBytes,64000))fail();}
 else if(v.type==='integer'){if(!Number.isSafeInteger(v.minimum)||!Number.isSafeInteger(v.maximum)||v.minimum>v.maximum)fail();}
 else if(v.type==='enum'){if(!Array.isArray(v.values)||v.values.length<1||v.values.length>64||new Set(v.values).size!==v.values.length||v.values.some(s=>typeof s!=='string'||bytes(s)<1||bytes(s)>256))fail();}
}
const IDENTITY={aws:['REGION','POOL_ID','CLIENT_ID','AUTH_ORIGIN','AUTH_SCOPE'],azure:['TENANT_ID','API_CLIENT_ID','SPA_CLIENT_ID'],gcp:['PROJECT_NUMBER','REGION','SERVICE_NAME'],ibm:['APPID_TENANT_ID','APPID_CLIENT_ID','APPID_ISSUER','AUTH_SCOPE']};
export function validateApprovalProfile(v){
 if(v?.format==='approval-application-template-v1')return validateApprovalTemplate(v);
 json(v);if(bytes(JSON.stringify(v))>64000)fail();
 exact(v,['format','provider','componentId','environment','accountId','publicOrigin','operationKind','identitySettings','payloadContract','destinationContract']);
 if(v.format!=='approval-application-v1'||!Object.hasOwn(IDENTITY,v.provider)||typeof v.componentId!=='string'||bytes(v.componentId)<1||bytes(v.componentId)>512||/[\x00-\x1f]/.test(v.componentId)||!['staging','production','qualification'].includes(v.environment)||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v.accountId)||!['document','draft','account_change'].includes(v.operationKind))fail();
 try{
  const p=new URL(v.publicOrigin),tail=v.publicOrigin.slice(v.publicOrigin.indexOf('://')+3);
  if(typeof v.publicOrigin!=='string'||/[^\x21-\x7e]/.test(v.publicOrigin)||/[/?#]/.test(tail)||p.username||p.password||!p.hostname||p.port&&(!integer(Number(p.port),1,65535))||p.protocol!=='https:'&&!(p.protocol==='http:'&&['localhost','127.0.0.1','[::1]'].includes(p.hostname)))fail();
 }catch{fail();}
 exact(v.identitySettings,IDENTITY[v.provider]);if(Object.values(v.identitySettings).some(s=>typeof s!=='string'||bytes(s)<1||bytes(s)>2000))fail();
 const p=v.payloadContract;exact(p,['version','id','source','result']);if(p.version!==1||typeof p.id!=='string'||!/^[a-z][a-z0-9-]{0,79}$/.test(p.id)||bytes(JSON.stringify(p))>64000)fail();
 const budget={count:256};for(const side of ['source','result']){schema(p[side],0,budget);if(p[side].type!=='object')fail();}
 const d=v.destinationContract;const keys=['id','endpointSha256','scope','mappingVersion'];if(Object.hasOwn(d||{},'payloadContractSha256'))keys.push('payloadContractSha256');exact(d,keys);
 if(typeof d.id!=='string'||!/^[a-z0-9-]{1,80}$/.test(d.id)||typeof d.endpointSha256!=='string'||!/^[0-9a-f]{64}$/.test(d.endpointSha256)||typeof d.scope!=='string'||d.scope.length<1||d.scope.length>200||/[^\x21-\x7e]/.test(d.scope)||!integer(d.mappingVersion,1,10000)||d.payloadContractSha256!==undefined&&!/^[0-9a-f]{64}$/.test(d.payloadContractSha256))fail();
 if(d.payloadContractSha256!==undefined){const hash=Array.from(sha256(new TextEncoder().encode(JSON.stringify(canonical(p)))),b=>b.toString(16).padStart(2,'0')).join('');if(hash!==d.payloadContractSha256)fail();}
 return structuredClone(v);
}
export function outputReference(v){
 exact(v,['nativeOutput']);const r=v.nativeOutput;exact(r,['componentId','provider','environment','name']);
 if(typeof r.componentId!=='string'||bytes(r.componentId)<1||bytes(r.componentId)>512||/[\x00-\x1f]/.test(r.componentId)||!['aws','azure','gcp','ibm','tools'].includes(r.provider)||!['staging','production','qualification'].includes(r.environment)||typeof r.name!=='string'||!/^[A-Za-z][A-Za-z0-9_]{0,79}$/.test(r.name)||/secret|password|credential|private_?key/i.test(r.name))fail();
 return r;
}
export function approvalReferences(v){
 const refs=[];
 if(plain(v.publicOrigin))refs.push({path:'publicOrigin',...outputReference(v.publicOrigin)});
 for(const section of ['identitySettings','destinationContract'])for(const[key,value]of Object.entries(v[section]||{}))if(plain(value))refs.push({path:section+'/'+key,...outputReference(value)});
 return refs;
}
function validateApprovalTemplate(v){
 json(v);if(bytes(JSON.stringify(v))>64000)fail();const trial=structuredClone(v);trial.format='approval-application-v1';
 const refs=approvalReferences(v);if(!refs.length)fail();
 for(const r of refs){
  if(r.environment!==v.environment||r.path.startsWith('identitySettings/')&&r.provider!==v.provider)fail();
  if(r.path==='publicOrigin')trial.publicOrigin='https://unresolved.invalid';
  else if(r.path.startsWith('identitySettings/'))trial.identitySettings[r.path.split('/')[1]]='UNRESOLVED_NATIVE_OUTPUT';
  else if(['destinationContract/endpointSha256','destinationContract/scope'].includes(r.path))trial.destinationContract[r.path.split('/')[1]]=r.path.endsWith('endpointSha256')?'0'.repeat(64):'unresolved';
  else fail();
 }
 validateApprovalProfile(trial);return structuredClone(v);
}
export function approvalProfiles(project){
 const selected=[];
 for(const node of project.nodes||[]){
  if(node.data?.approvalProfile===undefined||node.data.approvalProfile===null)continue;
  const profile=validateApprovalProfile(node.data.approvalProfile);
  if(node.data.kind==='note'||node.data.binding||node.data.implementation!=='approval-workflow'||node.data.provider!==profile.provider||node.id!==profile.componentId||existingDeployment(node)||node.data.origin!==undefined&&node.data.origin!=='proposed')throw Error('Approval application must bind its exact proposed component/provider; preserve existing ownership.');
  for(const ref of approvalReferences(profile)){
   const source=project.nodes.find(n=>n.id===ref.componentId);
   if(!source||source.data.kind==='note'||source.data.provider!==ref.provider)throw Error('Native output reference must retain an existing graph component/provider; no source was substituted.');
  }
  selected.push({node,profile});
 }
 return selected;
}
