import test from 'node:test';
import assert from 'node:assert/strict';
import {engineeringCall,mergeEngineeringEvents,verifiedEngineeringDownload} from '../src/engineering-client.mjs';

test('engineering protocol sends only scoped intent and server token',async()=>{
  const text='Keep every line.\n'.repeat(1000);let request;
  const result=await engineeringCall({token:'local-token'},'start',{projectId:'project-one',sessionId:'public-session',text},{fetcher:async(url,options)=>{request={url,...options};return Response.json({state:'running'});}});
  assert.equal(result.state,'running');assert.equal(request.url,'/api/engineering/start');
  assert.equal(request.headers.Authorization,'Bearer local-token');assert.equal(JSON.parse(request.body).text,text);
  assert.equal(Object.hasOwn(JSON.parse(request.body),'workspace'),false);
});
test('event cursors deduplicate polls while preserving ordered content',()=>{
  const events=mergeEngineeringEvents([{sequence:4,kind:'message',text:'all original text'}],[{sequence:5,kind:'completed'},{sequence:4,kind:'message',text:'all original text'}]);
  assert.deepEqual(events.map(e=>e.sequence),[4,5]);assert.equal(events[0].text,'all original text');
});
test('API rejection retains actionable detail and does not resubmit',async()=>{
  let calls=0;
  await assert.rejects(engineeringCall({token:'local'},'start',{}, {fetcher:async()=>{calls++;return Response.json({detail:'Recover this job before submitting more work.'},{status:409});}}),/Recover this job/);
  assert.equal(calls,1);
});
test('immutable download checks bytes against both receipt and response digest',async()=>{
  const bytes=new TextEncoder().encode('exact package bytes');
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
  const fetcher=async()=>new Response(bytes,{headers:{'X-Artifact-Sha256':digest}});
  const blob=await verifiedEngineeringDownload({token:'local'},{artifactId:'public-artifact'},{sha256:digest},{fetcher});
  assert.equal(await blob.text(),'exact package bytes');
  await assert.rejects(verifiedEngineeringDownload({token:'local'},{},{sha256:'incorrect'},{fetcher}),/digest did not match/);
});
