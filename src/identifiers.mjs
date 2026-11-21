import {sha256} from '@noble/hashes/sha2.js';
const hex=bytes=>Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
// Preserve established short addresses. Long Unicode identities use a bounded
// digest token; original identities remain in project/manifest/requirement links.
// Odd-length digest tokens cannot overlap any legacy even-length UTF-8 hex token.
export function identityToken(value){
 if(typeof value!=='string'||!value)throw Error('Use a nonempty component identity.');
 try{encodeURIComponent(value);}catch{throw Error('Use a well-formed Unicode identity; no characters were replaced.');}
 const bytes=new TextEncoder().encode(value);
 return bytes.length<=124?hex(bytes):'d'+hex(sha256(bytes));
}
export const resourceAddress=id=>'block_'+identityToken(id);
export function assertDistinctIdentifiers(ids,token=identityToken){
 const seen=new Map();for(const id of ids){const name=token(id);if(seen.has(name))throw Error(seen.get(name)===id?'Duplicate component identity; no output was overwritten.':'Component namespace collision; retain both original identities and stop generation.');seen.set(name,id);}
}
