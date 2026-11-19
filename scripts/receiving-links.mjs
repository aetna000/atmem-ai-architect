import path from 'node:path';
import {strFromU8} from 'fflate';
// Ordinary inline Markdown file links only; no execution, network or host reads.
export function relativeLinkReport(files){
 const missing=[];let checked=0;const names=Object.keys(files);
 for(const [name,body]of Object.entries(files).filter(([name])=>name.endsWith('.md'))){
  const text=typeof body==='string'?body:strFromU8(body);
  for(const match of text.matchAll(/\[[^\]]*\]\(([^\s)]+)\)/g)){
   const href=match[1].replace(/^<|>$/g,'');if(/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(href)||href.startsWith('#')||href.startsWith('/'))continue;
   let local;try{local=decodeURIComponent(href.split('#')[0]);}catch{missing.push({file:name,target:href,reason:'invalid_encoding'});continue;}
   if(!local)continue;checked++;const target=path.posix.normalize(path.posix.join(path.posix.dirname(name),local)).replace(/\/+$/,'');
   if(target.startsWith('../')||target==='..'||target.includes('\\')||target.includes('\0'))missing.push({file:name,target,reason:'outside_package'});
   else if(target!=='.'&&!Object.hasOwn(files,target)&&!names.some(name=>name.startsWith(target+'/')))missing.push({file:name,target,reason:'missing'});
  }
 }
 return {checked,missing,boundary:'Ordinary inline relative file links only; no semantic, anchor or external availability proof.'};
}
