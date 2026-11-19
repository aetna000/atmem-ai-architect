import test from 'node:test';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {attachReviewedDraftFiles} from '../src/reviewed-draft.mjs';
const bytes=new TextEncoder().encode(' {\n "version": 1, "title": "Archive — café", "sourceSlots": [1]\n}\n'),hash=body=>createHash('sha256').update(body).digest('hex');
const artifactId='11111111-1111-4111-8111-111111111111',draftSha256=hash(bytes),contextSha256='c'.repeat(64),reviewSha256='d'.repeat(64);
const project={id:'project-one',extensions:{architectureDocuments:{artifactId,draftSha256,contextSha256,files:[{path:'architecture.review.md',sha256:reviewSha256}]}}};
const files={'READ_ME_FIRST.md':'Read the current canonical project.','START_HERE.md':'Read the current canonical project.','handoff-readiness.json':JSON.stringify({status:'design_documented'})};
const response=(body=bytes,headers={})=>new Response(body,{headers:{'Content-Type':'application/json','X-Artifact-Id':artifactId,'X-Artifact-Sha256':'a'.repeat(64),'X-Draft-Sha256':draftSha256,'X-Context-Sha256':contextSha256,'X-Review-Sha256':reviewSha256,...headers}});
test('original reviewed bytes are retained without JSON reserialization and source inputs stay immutable',async()=>{
 const before=structuredClone(files);let calls=0;const result=await attachReviewedDraftFiles(project,files,{session:{token:'fixture'},fetcher:async(url,options)=>{calls++;assert.equal(url,'/api/design-evidence/draft');assert.equal(options.headers.Authorization,'Bearer fixture');assert.deepEqual(JSON.parse(options.body),{projectId:project.id,artifactId,draftSha256,contextSha256});return response();}});
 assert.equal(calls,1);assert.deepEqual(result.files['architecture.canvas.json'],bytes);assert.equal(hash(result.files['architecture.canvas.json']),draftSha256);assert.equal(result.receipt.status,'verified');assert.equal(result.receipt.bytes,bytes.length);assert.deepEqual(files,before);assert.match(result.files['READ_ME_FIRST.md'],/does not approve later edits/);assert.equal(JSON.parse(result.files['handoff-readiness.json']).reviewedDraft.status,'verified');
});
test('offline and missing captures keep evidence explicitly incomplete without a counterfeit draft',async()=>{
 for(const config of [{},{session:{token:'fixture'},fetcher:async()=>new Response(null,{status:409})},{session:{token:'fixture'},fetcher:async()=>{throw Error('Offline');}}]){
  const result=await attachReviewedDraftFiles(project,files,config);assert.equal(result.receipt.status,'unavailable');assert.equal(result.files['architecture.canvas.json'],undefined);assert.equal(JSON.parse(result.files['handoff-readiness.json']).status,'incomplete_evidence');
 }
 const plain=await attachReviewedDraftFiles({id:'plain'},files,{fetcher:()=>{throw Error('Must not fetch');}});assert.equal(plain.receipt.status,'not_applicable');assert.equal(plain.files['design-evidence.json'],undefined);
});
test('wrong bytes, context, review, MIME or oversized successful responses abort export',async()=>{
 for(const make of [()=>response('{}'),()=>response(bytes,{'X-Context-Sha256':'0'.repeat(64)}),()=>response(bytes,{'X-Review-Sha256':'0'.repeat(64)}),()=>response(bytes,{'Content-Type':'text/html'}),()=>response(bytes,{'Content-Length':'2000001'}),()=>response(new Uint8Array(2_000_001))])await assert.rejects(()=>attachReviewedDraftFiles(project,files,{session:{token:'fixture'},fetcher:async()=>make()}),/integrity|provenance|review document|bound/);
});
