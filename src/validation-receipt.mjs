import {moduleValidationCoverage} from './terraform-validation-coverage.mjs';
export async function verifiedReceipt(files,result){
 if(!result?.fileDigests)return null;
 const names=Object.keys(files).sort(),recorded=Object.keys(result.fileDigests).sort();
 if(JSON.stringify(names)!==JSON.stringify(recorded))return null;
 for(const name of names){const bytes=new TextEncoder().encode(files[name]);const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(hash!==result.fileDigests[name])return null;}
 let modules=[];if(files['generation-quality.json']){try{modules=JSON.parse(files['generation-quality.json']).modules||[];}catch{return null;}}
 result=moduleValidationCoverage(result,modules);
 return {version:1,status:result.status,scope:'configuration_and_available_generated_local_tests',cloudPlan:'not_run',deployment:'not_run',fileDigests:result.fileDigests,checks:result.checks||[],message:result.message||'',generatedAt:result.generatedAt||new Date().toISOString()};
}
