// Actual browser microphone/WebRTC/RTP/data channel loopback. No OpenAI/model call.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
const base=process.argv[2]||'http://127.0.0.1:5297',out=process.argv[3]||'.local/external-artifacts/openai-voice/v1/webrtc';
fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--autoplay-policy=no-user-gesture-required','--disable-features=WebRtcHideLocalIpsWithMdns','--allow-loopback-in-peer-connection']});
try{
 const page=await browser.newPage({permissions:['microphone','local-network-access']});const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.route('**/__voice_loopback',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><title>Local WebRTC fixture</title><p>Virtual microphone and tone loopback, no model.</p>'}));
 await page.route('https://api.openai.com/**',route=>route.abort('blockedbyclient'));
 await page.goto(base+'/__voice_loopback');
 const receipt=await page.evaluate(async()=>{
  const {OpenAIVoice}=await import('/src/openai-voice.mjs');
  const remote=new RTCPeerConnection(),context=new AudioContext();await context.resume();
  const oscillator=context.createOscillator(),destination=context.createMediaStreamDestination();
  oscillator.connect(destination);oscillator.start();
  for(const track of destination.stream.getTracks())remote.addTrack(track,destination.stream);
  let client,microphone,channel;const states=[],errors=[],transcripts=[],candidates=[],diagnostics=[];
  for(const name of ['connectionstatechange','iceconnectionstatechange','icegatheringstatechange'])remote.addEventListener(name,()=>diagnostics.push({side:'remote',name,connection:remote.connectionState,ice:remote.iceConnectionState,gathering:remote.iceGatheringState}));
  // Two browser peers are full ICE agents; the local fixture forwards candidates.
  // This is fixture signaling, not an extra OpenAI production API request.
  remote.ondatachannel=event=>{channel=event.channel;channel.onopen=()=>{
   channel.send(JSON.stringify({type:'input_audio_buffer.committed',item_id:'local-turn'}));
   channel.send(JSON.stringify({type:'conversation.item.input_audio_transcription.completed',item_id:'local-turn',transcript:'Synthetic transcript over the real data channel.'}));
  }};
  const engine=new OpenAIVoice({session:{token:'local-fixture'},
   peer:()=>{client=new RTCPeerConnection();for(const name of ['connectionstatechange','iceconnectionstatechange','icegatheringstatechange'])client.addEventListener(name,()=>diagnostics.push({side:'client',name,connection:client.connectionState,ice:client.iceConnectionState,gathering:client.iceGatheringState}));client.onicecandidate=event=>{if(event.candidate){if(remote.remoteDescription)void remote.addIceCandidate(event.candidate);else candidates.push(event.candidate)}};return client},
   media:{getUserMedia:async constraints=>{microphone=await navigator.mediaDevices.getUserMedia(constraints);return microphone}},
   onState:value=>states.push(value),onError:value=>{if(value)errors.push(value)},onTranscript:text=>transcripts.push(text),
   fetcher:async(url,request)=>{
    if(url.startsWith('/api/'))return Response.json({value:'ek_local_loopback'});
    if(url!=='https://api.openai.com/v1/realtime/calls')throw Error('Unexpected transport destination');
    await remote.setRemoteDescription({type:'offer',sdp:request.body});
    for(const candidate of candidates.splice(0))await remote.addIceCandidate(candidate);
    await remote.setLocalDescription(await remote.createAnswer());
    if(remote.iceGatheringState!=='complete')await new Promise(resolve=>remote.addEventListener('icegatheringstatechange',()=>{if(remote.iceGatheringState==='complete')resolve()}));
    return new Response(remote.localDescription.sdp);
   }});
  try{
   await engine.start();
   const end=Date.now()+12000;let inputBytes=0,outputBytes=0;
   while(Date.now()<end){
    inputBytes=[...await remote.getStats()].map(([,v])=>v).filter(v=>v.type==='inbound-rtp'&&v.kind==='audio').reduce((n,v)=>n+(v.bytesReceived||0),0);
    outputBytes=[...await client.getStats()].map(([,v])=>v).filter(v=>v.type==='inbound-rtp'&&v.kind==='audio').reduce((n,v)=>n+(v.bytesReceived||0),0);
    if(inputBytes>0&&outputBytes>0&&transcripts.length)break;
    await new Promise(resolve=>setTimeout(resolve,100));
   }
   if(!inputBytes||!outputBytes||!transcripts.length||!states.includes('listening')||errors.length)throw Error(JSON.stringify({inputBytes,outputBytes,transcripts,states,errors,diagnostics}));
   engine.stop();
   return {virtualMicrophoneRtpBytes:inputBytes,receivedToneRtpBytes:outputBytes,realDataChannelTranscript:transcripts[0],microphoneStopped:microphone.getTracks().every(t=>t.readyState==='ended'),clientClosed:client.connectionState==='closed',fixturePermissions:['microphone','local-network-access'],fixtureFlags:['use-fake-ui-for-media-stream','use-fake-device-for-media-stream','autoplay-policy=no-user-gesture-required','disable-features=WebRtcHideLocalIpsWithMdns','allow-loopback-in-peer-connection'],media:'Virtual capture device and generated output tone; autoplay allowed in this fixture',errors,realOpenAICalls:0,scope:'Actual browser media/WebRTC/audio playback transport with local peer and generated tone; no natural voice/listening/account proof'};
  }finally{engine.stop();remote.close();destination.stream.getTracks().forEach(track=>track.stop());oscillator.stop();await context.close();}
 });
 assert.equal(receipt.microphoneStopped,true);assert.equal(receipt.clientClosed,true);assert.deepEqual(errors,[]);
 fs.writeFileSync(out+'/receipt.json',JSON.stringify({base,...receipt},null,2)+'\n');console.log(JSON.stringify(receipt));
}finally{await browser.close()}
