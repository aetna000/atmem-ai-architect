import {sha256} from '@noble/hashes/sha2.js';

const encode=value=>new TextEncoder().encode(value);
const hash=bytes=>Array.from(sha256(bytes),byte=>byte.toString(16).padStart(2,'0')).join('');
const permitted=path=>typeof path==='string'&&path.length<=500&&!/[\\\u0000-\u001f:]/.test(path)
  &&path.split('/').every(part=>part&&part!=='.'&&part!=='..'&&part.trim()===part&&!part.endsWith('.')
    &&!['.git','.agents','node_modules','agents.md','skill.md'].includes(part.toLowerCase())
    &&!/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)/i.test(part))
  &&(/^(specs|docs)\/.+\.(md|txt|json|ya?ml|mmd)$/i.test(path)||['README.md','architecture.coverage.md','architecture.review.md'].includes(path));

export function designDocumentPath(path){return path==='README.md'?'NATIVE_DESIGN.md':path;}
export function isDesignDocument(path){return permitted(path);}

export function captureDesignDocuments(files,artifactId,draftSha256,contextSha256){
  let bytes=0;
  const captured=Object.entries(files).filter(([path])=>permitted(path)).map(([path,content])=>{
    bytes+=content.byteLength;
    if(content.byteLength>250_000||bytes>1_000_000)throw Error('Design documents exceed the receiving context bound. The original captured package is retained.');
    return {path,sha256:hash(content),content:new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(content)};
  });
  if(captured.length>300)throw Error('Design document inventory exceeds its explicit bound.');
  return {version:1,artifactId,draftSha256,contextSha256,files:captured};
}

export function designDocumentFiles(value){
  if(value==null)return {};
  if(value.version!==1||typeof value.artifactId!=='string'||!value.artifactId||value.artifactId.length>150
    ||!/^([a-f0-9]{64})$/.test(value.draftSha256)||value.contextSha256!=null&&!/^[a-f0-9]{64}$/.test(value.contextSha256)
    ||!Array.isArray(value.files)||value.files.length>300)throw Error('Invalid captured design document receipt.');
  const paths=new Set();let bytes=0;const result={};
  for(const file of value.files){
    if(!permitted(file?.path)||paths.has(file.path.toLowerCase())||typeof file.content!=='string')throw Error('Invalid or duplicate design document path.');
    const content=encode(file.content);bytes+=content.length;
    if(content.length>250_000||bytes>1_000_000||hash(content)!==file.sha256)throw Error('Captured design document integrity or size check failed.');
    paths.add(file.path.toLowerCase());result[designDocumentPath(file.path)]=file.content;
  }
  if(!paths.size)return result;
  result['design-documents-receipt.json']=JSON.stringify({...value,files:value.files.map(({content,...file})=>({...file,exportPath:designDocumentPath(file.path)})),
    boundary:'Captured authored design evidence, not accepted requirements, executed implementation or deployment.'},null,2)+'\n';
  return result;
}
