import {handoffDigest} from './block-handoff.mjs';
import {readBoundedEvidence} from './evidence-download.mjs';
const SHA=/^[a-f0-9]{64}$/,UUID=/^[a-f0-9-]{36}$/;
// Source hashes identify the captured proposal, not an approval of current edits.
export async function attachReviewedDraftFiles(project,original,{session,fetcher=fetch}={}){
 const files={...original},source=project.extensions?.architectureDocuments;
 if(!source)return {files,receipt:{status:'not_applicable'}};
 const receipt={version:1,status:'unavailable',artifactId:source.artifactId,draftSha256:source.draftSha256,contextSha256:source.contextSha256,path:'architecture.canvas.json',
  boundary:'Exact captured proposal bytes and review seal only. Current canonical design, implementation and deployment require separate review.'};
 function finish(){
  files['design-evidence.json']=JSON.stringify(receipt,null,2)+'\n';
  if(files['handoff-readiness.json']){const ready=JSON.parse(files['handoff-readiness.json']);ready.reviewedDraft=receipt;
   if(receipt.status!=='verified'&&ready.status==='design_documented')ready.status='incomplete_evidence';
   files['handoff-readiness.json']=JSON.stringify(ready,null,2)+'\n';
  }
  return {files,receipt};
 }
 if(!session?.token){receipt.reason='session_unavailable';return finish();}
 if(!UUID.test(source.artifactId)||!SHA.test(source.draftSha256)||!SHA.test(source.contextSha256)){receipt.reason='provenance_unbound';return finish();}
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
 try{
  let response;try{response=await fetcher('/api/design-evidence/draft',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({projectId:project.id,artifactId:source.artifactId,draftSha256:source.draftSha256,contextSha256:source.contextSha256}),signal:controller.signal});}
  catch{receipt.reason=controller.signal.aborted?'retrieval_timeout':'service_unavailable';return finish();}
  if(!response.ok){receipt.reason='retrieval_failed';receipt.httpStatus=response.status;return finish();}
  const headers=response.headers;
  if(headers.get('content-type')?.split(';')[0]!=='application/json'||headers.get('X-Artifact-Id')!==source.artifactId||headers.get('X-Draft-Sha256')!==source.draftSha256||headers.get('X-Context-Sha256')!==source.contextSha256||!SHA.test(headers.get('X-Artifact-Sha256'))||!SHA.test(headers.get('X-Review-Sha256')))throw Error('Reviewed draft response does not match its requested provenance.');
  const review=source.files?.find(file=>file.path==='architecture.review.md');
  if(review&&review.sha256!==headers.get('X-Review-Sha256'))throw Error('Reviewed draft seal does not match the captured review document.');
  const bytes=await readBoundedEvidence(response,2_000_000,'Reviewed draft');
  if(handoffDigest(bytes)!==source.draftSha256)throw Error('Reviewed draft byte integrity check failed.');
  const text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes),value=JSON.parse(text);
  if(!value||value.version!==1)throw Error('Reviewed draft is not a supported JSON proposal.');
  // A decoded/re-encoded string can alter BOM bytes; retain the original bytes.
  files[receipt.path]=bytes;receipt.status='verified';receipt.bytes=bytes.length;
  receipt.artifactSha256=headers.get('X-Artifact-Sha256');receipt.reviewSha256=headers.get('X-Review-Sha256');
  const note='\n## Captured proposal\n\nThe original reviewed proposal is architecture.canvas.json; design-evidence.json records its byte custody. Use the current canonical project snapshot for accepted state. The captured review does not approve later edits or prove execution.\n';
  if(files['READ_ME_FIRST.md']){files['READ_ME_FIRST.md']+=note;files['START_HERE.md']=files['READ_ME_FIRST.md'];}else if(files['START_HERE.md'])files['START_HERE.md']+=note;
  return finish();
 }finally{clearTimeout(timer);}
}
