import {unzipSync} from 'fflate';
import {ENGINEERING_CONTEXT_BYTES} from './evidence-bounds.mjs';
import {handoffDigest} from './block-handoff.mjs';
import {mergeCapturedEvidence} from './captured-handoff.mjs';
import {readBoundedEvidence} from './evidence-download.mjs';
const SHA=/^[a-f0-9]{64}$/,UUID=/^[a-f0-9-]{36}$/,MAX_BYTES=64_000_000,MAX_FILES=2000;
const decode=bytes=>new TextDecoder('utf-8',{fatal:true}).decode(bytes);
// No extraction or execution. Inspect names/counts/declared expansion before decoding.
export function boundedEvidenceZip(bytes){
 if(bytes.byteLength>MAX_BYTES)throw Error('Capture archive exceeds its byte bound.');
 let count=0,total=0;const names=new Set();
 const files=unzipSync(bytes,{filter:entry=>{
  const name=entry.name,parts=name.replace(/\/$/,'').split('/'),key=name.replace(/\/$/,'').toLowerCase();
  if(!name||name.length>500||/[\\:\x00-\x1f\x7f]/.test(name)||parts.some(part=>!part||part==='.'||part==='..')||names.has(key))throw Error('Capture archive has an unsafe or ambiguous path.');
  names.add(key);total+=entry.originalSize;
  if(++count>MAX_FILES||!Number.isSafeInteger(total)||total>MAX_BYTES)throw Error('Capture archive exceeds its expansion bound.');
  return true;
 }});
 if(Object.keys(files).length!==count||Object.values(files).reduce((sum,body)=>sum+body.byteLength,0)>MAX_BYTES)throw Error('Capture archive inventory differs from its decoded entries.');
 return files;
}

export async function attachCapturedEvidenceFiles(project,original,{session,fetcher=fetch,sourceFile='source-context.json'}={}){
 const source=project.extensions?.architectureDocuments;
 if(!source)return {files:{...original},receipt:{status:'not_applicable'}};
 let files={...original};let receipt={version:1,status:'unavailable',artifactId:source.artifactId,draftSha256:source.draftSha256,submittedContextSha256:source.contextSha256,
  boundary:'Captured code and historical evidence custody only. No implementation acceptance or deployment is inferred.'};
 function finish(){
  files['captured-evidence.json']=JSON.stringify(receipt,null,2)+'\n';
  for(const name of ['handoff-readiness.json','spec-kit/readiness.json'])if(files[name]){
   const readiness=JSON.parse(files[name]);readiness.capturedEvidence={status:receipt.status,artifactId:receipt.artifactId,reason:receipt.reason};
   if(receipt.status!=='verified'&&readiness.status==='design_documented')readiness.status='incomplete_evidence';
   files[name]=JSON.stringify(readiness,null,2)+'\n';
  }
  return {files,receipt};
 }
 if(!session?.token){receipt.reason='session_unavailable';return finish();}
 if(!UUID.test(source.artifactId)||!SHA.test(source.draftSha256)||!SHA.test(source.contextSha256)){receipt.reason='provenance_unbound';return finish();}
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),60000);
 try{
  let response;try{response=await fetcher('/api/design-evidence/capture',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({projectId:project.id,artifactId:source.artifactId,draftSha256:source.draftSha256,contextSha256:source.contextSha256}),signal:controller.signal});}
  catch{receipt.reason=controller.signal.aborted?'retrieval_timeout':'service_unavailable';return finish();}
  if(!response.ok){receipt.reason='retrieval_failed';receipt.httpStatus=response.status;return finish();}
  const h=response.headers;
  if(h.get('content-type')?.split(';')[0]!=='application/zip'||h.get('X-Artifact-Id')!==source.artifactId||h.get('X-Draft-Sha256')!==source.draftSha256||h.get('X-Context-Sha256')!==source.contextSha256||!SHA.test(h.get('X-Artifact-Sha256'))||!SHA.test(h.get('X-Review-Sha256'))||!SHA.test(h.get('X-Evidence-Sha256'))||!SHA.test(h.get('X-Initial-Context-Sha256')))throw Error('Capture response provenance does not match the requested design.');
  const bundle=await readBoundedEvidence(response,MAX_BYTES,'Capture evidence');
  if(handoffDigest(bundle)!==h.get('X-Evidence-Sha256'))throw Error('Capture evidence transport integrity check failed.');
  const contents=boundedEvidenceZip(bundle),expected=['capture.zip','capture-manifest.json','submitted-context.json','initial-context.json','initial-context-receipt.json'];
  if(Object.keys(contents).length!==expected.length||expected.some(name=>!Object.hasOwn(contents,name)))throw Error('Capture evidence bundle has missing or unexpected files.');
  for(const name of ['submitted-context.json','initial-context.json'])if(contents[name].byteLength>ENGINEERING_CONTEXT_BYTES)throw Error('Capture context exceeds its byte bound.');
  const manifest=JSON.parse(decode(contents['capture-manifest.json'])),initialReceipt=JSON.parse(decode(contents['initial-context-receipt.json']));
  if(manifest.sha256!==h.get('X-Artifact-Sha256')||initialReceipt.sha256!==h.get('X-Initial-Context-Sha256'))throw Error('Capture bundle receipts differ from response provenance.');
  const captureFiles=boundedEvidenceZip(contents['capture.zip']),review=captureFiles['architecture.review.md'];
  if(!review||handoffDigest(review)!==h.get('X-Review-Sha256'))throw Error('Capture review integrity check failed.');
  const pinnedReview=source.files?.find(file=>file.path==='architecture.review.md');
  if(pinnedReview&&pinnedReview.sha256!==h.get('X-Review-Sha256'))throw Error('Capture review differs from the pinned authored document.');
  const result=mergeCapturedEvidence({projectId:project.id,documents:source,originalFiles:files,sourceFile,captureFiles,captureArchive:contents['capture.zip'],captureManifest:manifest,submittedContext:contents['submitted-context.json'],initialContext:contents['initial-context.json'],initialReceipt});
  files=result.files;receipt={...result.receipt,status:'verified',transportSha256:h.get('X-Evidence-Sha256')};
  return finish();
 }finally{clearTimeout(timer);}
}
