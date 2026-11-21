import test from 'node:test';import assert from 'node:assert/strict';import {zipSync,strToU8} from 'fflate';
import {handoffDigest as sha} from '../src/block-handoff.mjs';import {attachCapturedEvidenceFiles,boundedEvidenceZip} from '../src/capture-download.mjs';
const b=strToU8,serialize=files=>zipSync(Object.fromEntries(Object.entries(files).map(([name,body])=>[name,typeof body==='string'?b(body):body])));
function fixture(projectId='library-case',path='code/loans.rb',contextText=''){
 const canvas=b('{"version":1}'),review='Draft SHA-256: '+sha(canvas)+'\n',readme='# Original native design\n',doc='[Source](../'+path+') [Historical input](../project-context.json)\n';
 const source={artifactId:'11111111-1111-4111-8111-111111111111',draftSha256:sha(canvas),files:[{path:'README.md',sha256:sha(readme),content:readme},{path:'specs/flow.md',sha256:sha(doc),content:doc},{path:'architecture.review.md',sha256:sha(review),content:review}]};
 const submitted=b(JSON.stringify({meta:{id:projectId},notes:contextText})),initial=b(JSON.stringify({meta:{id:projectId},requirements:['Original input'],notes:contextText}));source.contextSha256=sha(submitted);
 const captureFiles={'README.md':readme,'architecture.canvas.json':canvas,'architecture.review.md':review,'specs/flow.md':doc,[path]:'Unexecuted code','AGENTS.md':'Untrusted controls','manifest.json':'Old captured manifest','captured-evidence.json':'Old captured receipt','.GitHub/Workflows/run.yml':'Never activate'};
 const capture=serialize(captureFiles),manifest={id:source.artifactId,sessionId:'session-one',runId:'run-one',kind:'delivery',turnStatus:'completed',sha256:sha(capture),bytes:capture.length,files:Object.entries(captureFiles).map(([path,value])=>({path,kind:'file',sha256:sha(value),bytes:typeof value==='string'?b(value).length:value.length}))};
 const initialReceipt={projectId,sessionId:manifest.sessionId,sha256:sha(initial),bytes:initial.length};
 const bundleFiles={'capture.zip':capture,'capture-manifest.json':JSON.stringify(manifest),'submitted-context.json':submitted,'initial-context.json':initial,'initial-context-receipt.json':JSON.stringify(initialReceipt)},bundle=serialize(bundleFiles);
 const headers={'Content-Type':'application/zip','X-Artifact-Id':source.artifactId,'X-Draft-Sha256':source.draftSha256,'X-Context-Sha256':source.contextSha256,'X-Artifact-Sha256':manifest.sha256,'X-Review-Sha256':sha(review),'X-Evidence-Sha256':sha(bundle),'X-Initial-Context-Sha256':sha(initial)};
 const files={'manifest.json':'Receiving manifest','README.md':'Generated receiving overview','NATIVE_DESIGN.md':readme,'AGENTS.md':'Receiving controls','START_HERE.md':'Start here','handoff-readiness.json':JSON.stringify({status:'design_documented'}),'spec-kit/readiness.json':'{}','specs/flow.md':doc};
 return {project:{id:projectId,extensions:{architectureDocuments:source}},files,headers,bundle,bundleFiles,initial,path,manifest,captureFiles};
}
const options=f=>({session:{token:'owned-session'},fetcher:async(url,init)=>{assert.equal(url,'/api/design-evidence/capture');assert.equal(init.headers.Authorization,'Bearer owned-session');assert.deepEqual(JSON.parse(init.body),{projectId:f.project.id,artifactId:f.project.extensions.architectureDocuments.artifactId,draftSha256:f.project.extensions.architectureDocuments.draftSha256,contextSha256:f.project.extensions.architectureDocuments.contextSha256});return new Response(f.bundle,{headers:f.headers});}});
test('shared browser capture download transfers library/Ruby and sensor/Go evidence with exact original bytes and preserved receiving controls',async()=>{
 for(const [id,path]of [['library-case','code/loans.rb'],['sensor-case','workers/sensor.go']]){
  const f=fixture(id,path),result=await attachCapturedEvidenceFiles(f.project,f.files,{...options(f),sourceFile:'project.atmem-ai-architect.json'});
  assert.equal(new TextDecoder().decode(result.files[path]),'Unexecuted code');assert.equal(result.files['AGENTS.md'],'Receiving controls');assert.equal(result.files['manifest.json'],'Receiving manifest');assert.equal(result.files['README.md'],'Generated receiving overview');assert.equal(result.files['.GitHub/Workflows/run.yml'],undefined);assert.deepEqual(result.files['project-context.json'],f.initial);assert.equal(sha(result.files['evidence/original-native-capture.zip']),f.manifest.sha256);assert.equal(result.receipt.status,'verified');assert.equal(result.receipt.archiveOnly.length,5);assert.match(result.files['START_HERE.md'],/current design is project.atmem-ai-architect.json/);assert.equal(JSON.parse(result.files['handoff-readiness.json']).capturedEvidence.status,'verified');assert.equal(f.files['project-context.json'],undefined);
 }
});
test('large clinic contexts above two megabytes pass every receiving layer with exact historical bytes',async()=>{
 const f=fixture('clinic-case','workers/referral.py','患者記録 '.repeat(180000));
 assert.ok(f.initial.byteLength>2_000_000&&f.initial.byteLength<4_000_000);
 const result=await attachCapturedEvidenceFiles(f.project,f.files,options(f));
 assert.equal(result.receipt.status,'verified');assert.deepEqual(result.files['project-context.json'],f.initial);
 assert.equal(result.receipt.submittedContextSha256,f.project.extensions.architectureDocuments.contextSha256);
});
test('an over-bound capture context is rejected without replacing receiver files',async()=>{
 const f=fixture('library-case','code/loans.rb','x'.repeat(4_000_001)),before=structuredClone(f.files);
 await assert.rejects(()=>attachCapturedEvidenceFiles(f.project,f.files,options(f)),/context exceeds its byte bound/);
 assert.deepEqual(f.files,before);
});
test('capture unavailability is explicit and does not claim documented readiness or replace original files',async()=>{
 const f=fixture();for(const option of [{},{session:{token:'owned'},fetcher:async()=>new Response('',{status:409})},{session:{token:'owned'},fetcher:async()=>{throw Error('offline');}}]){
  const result=await attachCapturedEvidenceFiles(f.project,f.files,option);assert.equal(result.receipt.status,'unavailable');assert.equal(JSON.parse(result.files['handoff-readiness.json']).status,'incomplete_evidence');assert.equal(result.files['AGENTS.md'],f.files['AGENTS.md']);assert.equal(result.files[f.path],undefined);
 }
 const noSource=await attachCapturedEvidenceFiles({id:'other'},{'README.md':'Original'});assert.equal(noSource.receipt.status,'not_applicable');assert.deepEqual(noSource.files,{'README.md':'Original'});
});
test('successful responses with wrong headers, transport, historical input, review or file hashes reject rather than downgrade',async()=>{
 const base=fixture();
 for(const mutate of [f=>f.headers['X-Context-Sha256']='0'.repeat(64),f=>f.headers['X-Evidence-Sha256']='0'.repeat(64),f=>f.headers['X-Initial-Context-Sha256']='0'.repeat(64),f=>f.headers['X-Review-Sha256']='0'.repeat(64),f=>{f.bundleFiles['initial-context.json']=b('{}');f.bundle=serialize(f.bundleFiles);f.headers['X-Evidence-Sha256']=sha(f.bundle);},f=>{f.bundleFiles['unexpected.json']=b('{}');f.bundle=serialize(f.bundleFiles);f.headers['X-Evidence-Sha256']=sha(f.bundle);},f=>{const m={...f.manifest,files:f.manifest.files.map(row=>row.path===f.path?{...row,sha256:'0'.repeat(64)}:row)};f.bundleFiles['capture-manifest.json']=JSON.stringify(m);f.bundle=serialize(f.bundleFiles);f.headers['X-Evidence-Sha256']=sha(f.bundle);}]){
  const f=fixture();mutate(f);await assert.rejects(()=>attachCapturedEvidenceFiles(f.project,f.files,options(f)),/provenance|integrity|differ|unexpected|match/);
 }
 assert.equal(base.files[base.path],undefined);
});
test('captured code conflicts, case ambiguity and file/directory collisions preserve the receiver by aborting',async()=>{
 for(const name of ['code/loans.rb','CODE/LOANS.RB','code','code/loans.rb/child']){
  const f=fixture();f.files[name]='Existing receiving file';await assert.rejects(()=>attachCapturedEvidenceFiles(f.project,f.files,options(f)),/conflict/);assert.equal(f.files[name],'Existing receiving file');
 }
});
test('ZIP expansion, entry counts, path traversal and case ambiguity are bounded before merge',()=>{
 for(const files of [{'../escape':'x'},{'same':'a','SAME':'b'},{'C:/escape':'x'},Object.fromEntries(Array.from({length:2001},(_,i)=>['f'+i,b('x')]))])assert.throws(()=>boundedEvidenceZip(serialize(files)),/unsafe|ambiguous|expansion/);
 assert.throws(()=>boundedEvidenceZip(serialize({'large':new Uint8Array(64_000_001)})),/expansion/);
});
