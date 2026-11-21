import {test} from 'node:test';
import assert from 'node:assert/strict';
import {VoiceDictation,wav,resample} from '../src/voice-conversation.mjs';

function fixture(options={}){
 const drafts=[],states=[],errors=[],requests=[];let feed,stops=0,timer;
 const voice=new VoiceDictation({base:'Existing draft',capture:async({onSamples})=>{feed=onSamples;return{stop:()=>stops++};},
  transcribe:async audio=>{requests.push(audio);return requests.length===1?'Use Azure':'Use Azure in Australia';},
  onDraft:s=>drafts.push(s),onState:s=>states.push(s),onError:s=>errors.push(s),
  schedule:fn=>{timer=fn;return 1;},clear:()=>{timer=null;},...options});
 return{voice,drafts,states,errors,requests,feed:()=>feed(new Float32Array(16000).fill(.1)),stops:()=>stops,tick:()=>timer?.()};
}
test('live partial drafts never submit a message and finalisation preserves latest words',async()=>{
 const h=fixture();await h.voice.start();h.feed();await h.voice.update();
 assert.equal(h.drafts[0],'Existing draft Use Azure');assert.equal(h.voice.phase,'listening');
 h.feed();assert.equal(await h.voice.finish(),'Existing draft Use Azure in Australia');
 assert.equal(h.voice.phase,'off');assert.equal(h.stops(),1);assert.equal(h.requests.length,2);
});
test('silence never runs speech recognition or invents a transcript',async()=>{
 const h=fixture();await h.voice.start();await h.voice.update();
 assert.equal(h.requests.length,0);assert.equal(await h.voice.finish(),'Existing draft');
});
test('cancel fences late transcripts and releases the microphone',async()=>{
 let resolve;const h=fixture({transcribe:()=>new Promise(r=>resolve=r)});await h.voice.start();h.feed();
 const pending=h.voice.update();h.voice.cancel();resolve('late');await pending;
 assert.equal(h.drafts.length,0);assert.equal(h.voice.phase,'off');assert.equal(h.stops(),1);
});
test('cancel during microphone permission releases a late microphone stream',async()=>{
 let resolve,stopped=0;const h=fixture({capture:()=>new Promise(r=>resolve=r)});
 const starting=h.voice.start();h.voice.cancel();resolve({stop:()=>stopped++});await starting;
 assert.equal(stopped,1);assert.equal(h.voice.phase,'off');
});
test('failed final transcription does not produce a sendable success',async()=>{
 const h=fixture({transcribe:async()=>{throw Error('Helper unavailable. Nothing sent.')}});
 await h.voice.start();h.feed();assert.equal(await h.voice.finish(),null);
 assert.equal(h.voice.phase,'error');assert.match(h.errors[0],/Nothing sent/);
});
test('finalisation waits for pending partial and transcribes newly captured words',async()=>{
 let resolve,calls=0;const h=fixture({transcribe:()=>++calls===1?new Promise(r=>resolve=r):Promise.resolve('whole sentence')});
 await h.voice.start();h.feed();const partial=h.voice.update();h.feed();const finished=h.voice.finish();
 resolve('partial');await partial;assert.equal(await finished,'Existing draft whole sentence');assert.equal(calls,2);
});
test('microphone permission failures show an actionable persistent error',async()=>{
 const error=Error('denied');error.name='NotAllowedError';const h=fixture({capture:async()=>{throw error}});
 await h.voice.start();assert.equal(h.voice.phase,'error');assert.match(h.errors[0],/blocked/);
});
test('unchanged samples are not transcribed repeatedly',async()=>{
 const h=fixture();await h.voice.start();h.feed();await h.voice.update();await h.voice.update();
 assert.equal(h.requests.length,1);h.voice.cancel();
});
test('WAV framing clips samples and encodes mono signed PCM at 16kHz',async()=>{
 const audio=wav([new Float32Array([-2,0,2])],3),data=new DataView(await audio.arrayBuffer());
 assert.equal(audio.type,'audio/wav');assert.equal(data.getUint32(24,true),16000);
 assert.equal(data.getUint16(22,true),1);assert.equal(data.getInt16(44,true),-32768);
 assert.equal(data.getInt16(48,true),32767);assert.equal(data.getUint32(40,true),6);
});
test('browser audio is resampled to the local engine rate',()=>{
 assert.equal(resample(new Float32Array(48000),48000).length,16000);
 assert.deepEqual([...resample(new Float32Array([.5,-.5]),16000)],[.5,-.5]);
});
