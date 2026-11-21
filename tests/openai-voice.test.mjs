import test from 'node:test';
import assert from 'node:assert/strict';
import {OpenAIVoice} from '../src/openai-voice.mjs';

function fixture(overrides={}){
 const events=[],states=[],errors=[],transcripts=[],requests=[],timers=new Map();let timerId=0,stopped=0,closed=0;
 const stream={getTracks:()=>[{stop:()=>stopped++}]};
 const channel={readyState:'connecting',send:raw=>events.push(JSON.parse(raw)),close(){this.readyState='closed'}};
 const pc={connectionState:'new',addTrack(){},createDataChannel:()=>channel,createOffer:async()=>({sdp:'synthetic-offer'}),setLocalDescription:async()=>{},setRemoteDescription:async()=>{channel.readyState='open';channel.onopen?.()},close:()=>closed++};
 const player={play:async()=>{},pause(){},srcObject:null};
 const options={session:{token:'local-session'},media:{getUserMedia:async()=>stream},peer:()=>pc,audio:()=>player,
  fetcher:async(url,request)=>{requests.push({url,request});return url.startsWith('/api/')?Response.json({value:'ek_synthetic'}):new Response('synthetic-answer')},
  onState:value=>states.push(value),onError:value=>errors.push(value),onTranscript:(text,meta)=>transcripts.push({text,meta}),
  schedule:(fn,ms)=>{timers.set(++timerId,{fn,ms});return timerId},clear:id=>timers.delete(id),...overrides};
 const engine=new OpenAIVoice(options);
 return {engine,events,states,errors,transcripts,requests,timers,pc,channel,stream,player,counts:()=>({stopped,closed})};
}
const emit=(f,value)=>f.engine.receive(JSON.stringify(value));

test('WebRTC uses ephemeral credentials, explicit readout and no autonomous architecture response',async()=>{
 const f=fixture();await f.engine.start();
 assert.equal(f.states.at(-1),'listening');assert.equal(f.events.length,0);
 assert.equal(f.requests[0].request.headers.Authorization,'Bearer local-session');
 assert.equal(f.requests[1].url,'https://api.openai.com/v1/realtime/calls');
 assert.equal(f.requests[1].request.headers.Authorization,'Bearer ek_synthetic');
 const text='Keep café 🍊 and every requirement.\n'.repeat(1000);
 assert.equal(f.engine.speak(text),true);assert.equal(f.events[0].type,'response.create');
 assert.equal(f.events[0].response.conversation,'none');assert.equal(f.events[0].response.input[0].content[0].text,text);
 assert.equal(f.events[0].response.tools,undefined);
 f.engine.stop();assert.deepEqual(f.counts(),{stopped:1,closed:1});assert.equal(f.timers.size,0);
});

test('completed transcripts preserve committed order and duplicates cannot resend a turn',async()=>{
 const f=fixture();await f.engine.start();
 for(const id of ['one','two'])emit(f,{type:'input_audio_buffer.committed',item_id:id});
 emit(f,{type:'conversation.item.input_audio_transcription.completed',item_id:'two',transcript:'Keep existing ownership.'});assert.equal(f.transcripts.length,0);
 emit(f,{type:'conversation.item.input_audio_transcription.completed',item_id:'one',transcript:'Use the selected cloud.'});
 emit(f,{type:'conversation.item.input_audio_transcription.completed',item_id:'two',transcript:'Keep existing ownership.'});
 assert.deepEqual(f.transcripts,[{text:'Use the selected cloud.',meta:{ordered:true}},{text:'Keep existing ownership.',meta:{ordered:true}}]);
 assert.equal(f.events.length,0);f.engine.stop();
});

test('uncertain transcript order and failed recognition require manual review',async()=>{
 const f=fixture();await f.engine.start();
 emit(f,{type:'conversation.item.input_audio_transcription.completed',item_id:'unknown',transcript:'Preserve this complete draft.'});
 emit(f,{type:'input_audio_buffer.committed',item_id:'failed'});emit(f,{type:'input_audio_buffer.committed',item_id:'next'});
 emit(f,{type:'conversation.item.input_audio_transcription.completed',item_id:'next',transcript:'Do not lose the next requirement.'});
 emit(f,{type:'conversation.item.input_audio_transcription.failed',item_id:'failed'});
 assert.equal(f.transcripts.length,2);assert.ok(f.transcripts.every(t=>t.meta.ordered===false));assert.match(f.errors.at(-1),/Review/);f.engine.stop();
});

test('explicit stop retains recognized words waiting behind an unfinished earlier transcript as a manual draft',async()=>{
 const f=fixture();await f.engine.start();
 for(const id of ['one','two'])emit(f,{type:'input_audio_buffer.committed',item_id:id});
 emit(f,{type:'conversation.item.input_audio_transcription.completed',item_id:'two',transcript:'Keep the complete second demand.'});
 assert.equal(f.transcripts.length,0);f.engine.stop({preservePending:true});
 assert.deepEqual(f.transcripts,[{text:'Keep the complete second demand.',meta:{ordered:false}}]);
});

test('stop during microphone permission releases a late stream without connecting or delivering late words',async()=>{
 let release,requested;const gate=new Promise(resolve=>{release=resolve}),called=new Promise(resolve=>{requested=resolve});
 const f=fixture({media:{getUserMedia:()=>{requested();return gate}}});const pending=f.engine.start();await called;
 f.engine.stop();release(f.stream);await pending;
 assert.deepEqual(f.counts(),{stopped:1,closed:0});assert.equal(f.requests.length,1);assert.equal(f.errors.length,0);
});

test('setup and handshake failures clean up and never fall back to browser speech',async()=>{
 const missing=fixture({fetcher:async()=>Response.json({detail:'Configure the voice API key.'},{status:503})});await missing.engine.start();
 assert.match(missing.errors.at(-1),/Configure/);assert.deepEqual(missing.counts(),{stopped:0,closed:0});
 const failed=fixture({fetcher:async url=>url.startsWith('/api/')?Response.json({value:'ek_test'}):new Response('private upstream diagnostic',{status:403})});await failed.engine.start();
 assert.match(failed.errors.at(-1),/could not connect/);assert.doesNotMatch(failed.errors.at(-1),/private/);assert.deepEqual(failed.counts(),{stopped:1,closed:1});
 const denied=fixture({media:{getUserMedia:async()=>{const error=Error('denied');error.name='NotAllowedError';throw error}}});await denied.engine.start();assert.match(denied.errors.at(-1),/Microphone access is blocked/);assert.deepEqual(denied.counts(),{stopped:0,closed:0});
});

test('blocked playback has an explicit retry and never prevents written chat or microphone cleanup',async()=>{
 const player={play:async()=>{throw Error('user gesture required')},pause(){}};
 const f=fixture({audio:()=>player});await f.engine.start();assert.equal(await f.engine.resumeAudio(),false);assert.match(f.errors.at(-1),/Enable voice playback/);
 player.play=async()=>{};assert.equal(await f.engine.resumeAudio(),true);assert.equal(f.errors.at(-1),'');f.engine.stop();assert.equal(f.counts().stopped,1);
});

test('audio interruption cancels readout and a disconnected channel cannot fail the Architect request',async()=>{
 const f=fixture();await f.engine.start();
 emit(f,{type:'response.created',response:{id:'failed-readout'}});emit(f,{type:'response.done',response:{id:'failed-readout',status:'failed'}});assert.match(f.errors.at(-1),/written reply is unchanged/);
 emit(f,{type:'response.created',response:{id:'readout'}});emit(f,{type:'output_audio_buffer.started'});
 f.engine.interrupt();assert.deepEqual(f.events.map(e=>e.type),['response.cancel','output_audio_buffer.clear']);
 f.channel.send=()=>{throw Error('connection closed')};assert.equal(f.engine.speak('An already written Architect reply.'),false);assert.match(f.errors.at(-1),/written Architect reply is unchanged/);
});
