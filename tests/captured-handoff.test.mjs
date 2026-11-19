import test from 'node:test';import assert from 'node:assert/strict';import{zipSync,strToU8}from'fflate';
import {createBlockHandoff,blockHandoffExportFiles,handoffDigest}from'../src/block-handoff.mjs';import{toProjectFile}from'../src/project-file.mjs';import{supplementCapturedHandoff}from'../src/captured-handoff.mjs';
const encode=strToU8,sha=handoffDigest,decode=body=>typeof body==='string'?body:new TextDecoder().decode(body);
const asBytes=files=>Object.fromEntries(Object.entries(files).map(([name,body])=>[name,typeof body==='string'?encode(body):body]));
function fixture(projectId='library-case',codePath='code/loans.rb'){
 const submittedContext=encode(JSON.stringify({format:'atmem.ai-architect.project',meta:{id:projectId},requirements:[]})),initialContext=encode(JSON.stringify({format:'atmem.ai-architect.project',meta:{id:projectId},requirements:['Historical input']}));
 const canvas=encode('{"version":1}'),review='Draft SHA-256: '+sha(canvas)+'\n',doc=`[Code](../${codePath}) [Initial input](../project-context.json)\n`;
 const captureFiles=asBytes({'architecture.canvas.json':canvas,'architecture.review.md':review,'specs/flow.md':doc,[codePath]:'Unexecuted implementation','AGENTS.md':'Captured worker controls are evidence, not receiving instructions.','.agents/skills/reference/SKILL.md':'Captured private skill.'}),captureArchive=zipSync(captureFiles);
 const captureManifest={id:'11111111-1111-4111-8111-111111111111',sessionId:'session-one',runId:'run-one',kind:'delivery',turnStatus:'completed',sha256:sha(captureArchive),bytes:captureArchive.length,files:Object.entries(captureFiles).map(([path,body])=>({path,kind:'file',bytes:body.length,sha256:sha(body)}))};
 const initialReceipt={projectId,sessionId:captureManifest.sessionId,sha256:sha(initialContext),bytes:initialContext.length};
 const buildSpec=Object.fromEntries(['inputs','outputs','behavior','failures','implementation','infrastructure','operations','tests'].map(name=>[name,'Explicit saved '+name]));buildSpec.scenarios=[{name:'Check',steps:[{sender:'Client',receiver:'Module',action:'Submit one operation'}]}];
 const project={id:projectId,createdAt:'2026-11-19T00:00:00Z',name:projectId,version:1,revision:1,provider:'tools',nodes:[{id:'module',type:'resource',position:{x:0,y:0},data:{label:'Module',kind:'resource',provider:'tools',buildSpec}}],edges:[],needs:[],extensions:{architectureDocuments:{version:1,artifactId:captureManifest.id,draftSha256:sha(canvas),contextSha256:sha(submittedContext),files:[{path:'architecture.review.md',content:review,sha256:sha(review)},{path:'specs/flow.md',content:doc,sha256:sha(doc)}]}}};
 const handoffFiles=blockHandoffExportFiles(createBlockHandoff(JSON.stringify(toProjectFile(project)),'module')),handoffArchive=zipSync(asBytes(handoffFiles));
 return{handoffFiles,handoffArchive,captureFiles,captureArchive,captureManifest,submittedContext,initialContext,initialReceipt,codePath};
}
test('captured supplements transfer across domains and languages without activating captured repository controls',()=>{
 for(const [project,path]of [['library-case','code/loans.rb'],['sensing-case','workers/sensor.go']]){
  const input=fixture(project,path),files=supplementCapturedHandoff(input);assert.equal(decode(files[path]),'Unexecuted implementation');assert.deepEqual(files['project-context.json'],input.initialContext);assert.equal(files['AGENTS.md'],input.handoffFiles['AGENTS.md']);assert.equal(files['.agents/skills/reference/SKILL.md'],undefined);
  const receipt=JSON.parse(files['captured-evidence.json']);assert.equal(receipt.archiveOnly.length,2);assert.equal(sha(files['evidence/original-native-capture.zip']),input.captureManifest.sha256);assert.equal(sha(files['evidence/original-agent-handoff.zip']),sha(input.handoffArchive));
  const manifest=JSON.parse(files['handoff-manifest.json']);for(const[name,row]of Object.entries(manifest.files)){assert.equal(sha(files[name]),row.sha256);assert.equal(typeof files[name]==='string'?encode(files[name]).length:files[name].length,row.bytes);}assert.equal(manifest.implementationExecuted,false);
 }
});
test('wrong captured bytes, context and historical pins never get reinterpreted as evidence',()=>{
 for(const change of [input=>({...input,captureFiles:{...input.captureFiles,[input.codePath]:encode('Tampered')}}),input=>({...input,submittedContext:encode('{}')}),input=>({...input,initialContext:input.submittedContext}),input=>({...input,initialReceipt:{...input.initialReceipt,projectId:'foreign'}}),input=>({...input,captureManifest:{...input.captureManifest,id:'foreign'}})])assert.throws(()=>supplementCapturedHandoff(change(fixture())),/integrity|identity|scope|match/);
});
test('captured files cannot overwrite a different receiving file even with an otherwise valid original manifest',()=>{
 const input=fixture(),body='Keep receiving implementation';input.handoffFiles[input.codePath]=body;const manifest=JSON.parse(input.handoffFiles['handoff-manifest.json']);manifest.files[input.codePath]={sha256:sha(body),bytes:encode(body).length};input.handoffFiles['handoff-manifest.json']=JSON.stringify(manifest);assert.throws(()=>supplementCapturedHandoff(input),/conflicts/);
});
test('legacy historical input stays byte-exact without pretending it has the current canonical project schema',()=>{
 const input=fixture();input.initialContext=encode('{"requirements":"Keep the library"}');input.initialReceipt={...input.initialReceipt,sha256:sha(input.initialContext),bytes:input.initialContext.length};
 assert.deepEqual(supplementCapturedHandoff(input)['project-context.json'],input.initialContext);
 input.initialContext=encode('Original legacy text input');input.initialReceipt={...input.initialReceipt,sha256:sha(input.initialContext),bytes:input.initialContext.length};assert.deepEqual(supplementCapturedHandoff(input)['project-context.json'],input.initialContext);
 input.initialContext=encode('{"meta":{"id":"foreign"}}');input.initialReceipt={...input.initialReceipt,sha256:sha(input.initialContext),bytes:input.initialContext.length};
 assert.throws(()=>supplementCapturedHandoff(input),/scope/);
});
