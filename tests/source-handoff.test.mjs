import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {attachHandoffSourceFigures} from '../src/source-handoff.mjs';
const pixels=new Uint8Array([137,80,78,71,13,10,26,10]);
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const source='a'.repeat(64),manifest='b'.repeat(64),image=sha(pixels);
function handoff(){return {projectId:'project-one',blockId:'journal',blockIds:['journal'],files:{'source-context.json':JSON.stringify({extensions:{designSources:[{sha256:source,figureEvidence:{manifestSha256:manifest,figures:[{id:'figure-1',mime:'image/png',bytes:pixels.length,sha256:image,status:'available',locations:['paragraph:3']},{id:'figure-2',status:'unavailable',reason:'External image link'}]}}]}}),'handoff-readiness.json':JSON.stringify({status:'design_documented',missingSections:[],sourceFigures:[]}),'READ_ME_FIRST.md':'Module spec','START_HERE.md':'Module spec'}};}
const response=(body=pixels,headers={})=>new Response(body,{headers:{'Content-Type':'image/png','X-Source-Sha256':source,'X-Manifest-Sha256':manifest,'X-Figure-Sha256':image,...headers}});
test('portable source evidence carries exact pixels, locators and independent binary manifest hashes',async()=>{
 const input=handoff(),before=structuredClone(input);let calls=0;
 const result=await attachHandoffSourceFigures(input,{session:{token:'fixture'},fetcher:async(url,options)=>{calls++;assert.equal(url,'/api/design-sources/figure');assert.equal(options.headers.Authorization,'Bearer fixture');assert.deepEqual(JSON.parse(options.body),{projectId:'project-one',sourceSha256:source,manifestSha256:manifest,figureId:'figure-1'});return response();}});
 assert.equal(calls,1);assert.deepEqual(input,before);
 const readiness=JSON.parse(result.files['handoff-readiness.json']);assert.deepEqual(readiness.sourceFigures[0].locations,['paragraph:3']);assert.equal(readiness.sourceFigures[1].exportStatus,'source_unavailable');assert.equal(readiness.sourceEvidence.complete,false);
 const path=readiness.sourceFigures[0].path;assert.deepEqual(result.files[path],pixels);
 const manifestFile=JSON.parse(result.files['handoff-manifest.json']);assert.equal(manifestFile.files[path].sha256,sha(pixels));assert.equal(manifestFile.files[path].bytes,pixels.length);
 assert.equal(manifestFile.implementationExecuted,false);
});
test('offline and unavailable services retain explicit missing evidence without invented pixels',async()=>{
 for(const config of [{},{session:{token:'fixture'},fetcher:async()=>new Response(null,{status:409})},{session:{token:'fixture'},fetcher:async()=>{throw Error('Offline');}}]){
  const {files}=await attachHandoffSourceFigures(handoff(),config),readiness=JSON.parse(files['handoff-readiness.json']);assert.equal(readiness.sourceEvidence.embedded,0);assert.equal(readiness.sourceEvidence.complete,false);assert.equal(Object.keys(files).some(path=>path.endsWith('.png')),false);
 }
});
test('an offline handoff recovers matching retained pixels under a different name',async()=>{
 const input=handoff();input.files['attachments/retained.png']=pixels;
 input.files['attachments/lookalike.png']=new Uint8Array(pixels.length);
 const {files}=await attachHandoffSourceFigures(input,{fetcher:()=>assert.fail('Unexpected network call')});
 const receipt=JSON.parse(files['source-figures.json']);
 assert.equal(receipt.embedded,1);assert.deepEqual(files[receipt.figures[0].path],pixels);
 delete input.files['attachments/retained.png'];
 assert.equal(JSON.parse((await attachHandoffSourceFigures(input,{})).files['source-figures.json']).embedded,0);
});
test('successful HTTP cannot substitute image bytes, provenance, type or oversized streaming content',async()=>{
 for(const make of [()=>response(new Uint8Array([0])),()=>response(pixels,{'X-Source-Sha256':'c'.repeat(64)}),()=>response(pixels,{'Content-Type':'text/html'}),()=>response(pixels,{'Content-Length':String(4*1024*1024)}),()=>response(new Uint8Array(3*1024*1024+1))]){
  await assert.rejects(()=>attachHandoffSourceFigures(handoff(),{session:{token:'fixture'},fetcher:async()=>make()}),/provenance|integrity|bound/);
 }
});
