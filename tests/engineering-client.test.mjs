import test from 'node:test';
import assert from 'node:assert/strict';
import {engineeringCall,engineeringConversation,mergeEngineeringEvents,verifiedEngineeringDownload} from '../src/engineering-client.mjs';

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

test('native conversation retains complete ordered requests and streamed replies without promoting uncertain delivery',()=>{
  const text='Preserve every line.\n'.repeat(2000);
  const events=[{sequence:1,kind:'accepted',runId:'run-one',text},{sequence:2,kind:'message',runId:'run-one',text:'First '},{sequence:3,kind:'progress',text:'commandExecution'},{sequence:4,kind:'message',runId:'run-one',text:'reply.'},{sequence:5,kind:'steering_submitted',requestId:'change',text:'Keep existing records.'},{sequence:6,kind:'steering_delivery_uncertain',requestId:'change'},{sequence:7,kind:'message',runId:'run-one',text:'Observed follow-up.'}];
  const conversation=engineeringConversation([...events,events[0]]);
  assert.equal(conversation.length,4);assert.equal(conversation[0].text,text);assert.equal(conversation[1].text,'First reply.');assert.equal(conversation[2].status,'uncertain');assert.equal(conversation[3].text,'Observed follow-up.');
  assert.equal(engineeringConversation([...events,{sequence:8,kind:'steering_accepted',requestId:'change'}])[2].status,'accepted');
  assert.deepEqual(engineeringConversation([{sequence:1,kind:'accepted'},{sequence:2,kind:'completed'}]),[],'legacy events without request text are not invented into messages');
});

test('automatic repair intent remains durable progress rather than an invented client message',()=>{
  const events=[{sequence:1,kind:'accepted',text:'Preserve all customer records.',runId:'client'},
    {sequence:2,kind:'accepted',origin:'automatic_repair',text:'Internal evidence repair prompt.',runId:'repair'},
    {sequence:3,kind:'message',text:'Repaired the connection failure.',runId:'repair'}];
  assert.deepEqual(engineeringConversation(events).map(entry=>[entry.role,entry.text]),[
    ['user','Preserve all customer records.'],['assistant','Repaired the connection failure.']]);
});
