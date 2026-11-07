// Local dictation only. Transcripts stay in the composer until the user presses Send.
export function resample(samples, rate) {
  if (rate === 16000) return new Float32Array(samples);
  const ratio = rate / 16000, out = new Float32Array(Math.floor(samples.length / ratio));
  for (let n=0;n<out.length;n++) {
    const at=n*ratio, left=Math.floor(at), fraction=at-left;
    out[n]=samples[left]*(1-fraction)+(samples[Math.min(left+1,samples.length-1)]||0)*fraction;
  }
  return out;
}
export function wav(parts, length) {
  const data=new ArrayBuffer(44+length*2), view=new DataView(data);
  const text=(at,s)=>{for(let n=0;n<s.length;n++)view.setUint8(at+n,s.charCodeAt(n));};
  text(0,'RIFF');view.setUint32(4,36+length*2,true);text(8,'WAVE');text(12,'fmt ');
  view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);
  view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);
  view.setUint16(34,16,true);text(36,'data');view.setUint32(40,length*2,true);
  let at=44;
  for(const part of parts)for(const sample of part){
    if(at>=data.byteLength)break;
    const value=Math.max(-1,Math.min(1,sample));view.setInt16(at,value<0?value*32768:value*32767,true);at+=2;
  }
  return new Blob([data],{type:'audio/wav'});
}
export async function microphoneCapture({onSamples}) {
  let stream, context, processor, source, mute;
  const stop=()=>{
    if(processor){processor.onaudioprocess=null;processor.disconnect();}
    source?.disconnect();mute?.disconnect();stream?.getTracks().forEach(t=>t.stop());
    if(context && context.state!=='closed')void context.close().catch(()=>{});
  };
  try {
    if(!navigator.mediaDevices?.getUserMedia)throw Error('Microphone capture is not supported in this browser.');
    stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true}});
    const Audio=window.AudioContext||window.webkitAudioContext;
    if(!Audio)throw Error('Audio capture is not supported in this browser.');
    context=new Audio({sampleRate:16000});await context.resume();
    source=context.createMediaStreamSource(stream);
    // Kept for broad Safari/Chromium support. It never sends audio to browser speech services.
    processor=context.createScriptProcessor(4096,1,1);mute=context.createGain();mute.gain.value=0;
    processor.onaudioprocess=e=>onSamples(resample(e.inputBuffer.getChannelData(0),context.sampleRate));
    source.connect(processor);processor.connect(mute);mute.connect(context.destination);
    return {stop};
  } catch(error) {stop();throw error;}
}
export class VoiceDictation {
  constructor({capture=microphoneCapture,transcribe,onDraft=()=>{},onState=()=>{},onError=()=>{},base='',
    intervalMs=1000,schedule=(fn,ms)=>setTimeout(fn,ms),clear=id=>clearTimeout(id)}) {
    Object.assign(this,{capture,transcribe,onDraft,onState,onError,base,intervalMs,schedule,clear});
    this.base=base.trim()?base.trim()+' ':'';this.draft=base;this.epoch=0;this.phase='off';
  }
  state(phase){this.phase=phase;this.onState(phase);}
  async start(){
    const token=++this.epoch;this.parts=[];this.length=0;this.processed=0;this.heard=false;this.running=true;
    this.controller=new AbortController();this.state('starting');
    try {
      const mic=await this.capture({onSamples:part=>{
        if(!this.running||token!==this.epoch)return;
        const remaining=960000-this.length;
        if(remaining<=0)return;
        const bounded=part.slice(0,remaining);
        this.parts.push(bounded);this.length+=bounded.length;
        if(bounded.some(x=>Math.abs(x)>.02))this.heard=true;
        if(this.length>=960000)void this.finish();
      }});
      if(token!==this.epoch||!this.running){mic.stop();return;}
      this.mic=mic;this.state('listening');this.tick();
    } catch(error){if(token===this.epoch)this.fail(error?.name==='NotAllowedError'
      ?'Microphone access is blocked. Allow it for this site in your browser settings.'
      :'Could not open the microphone. Check your browser and system microphone settings.');}
  }
  tick(){
    this.timer=this.schedule(()=>{
      if(!this.running)return;
      void this.update().catch(()=>{});
      this.tick();
    },this.intervalMs);
  }
  async update(final=false){
    if(this.pending){await this.pending;if(!final)return;}
    const token=this.epoch, length=this.length;
    if(!this.running&&!final)return;
    if(length<1600||length===this.processed||!this.heard)return;
    const work=(async()=>{
      try {
        const text=await this.transcribe(wav(this.parts,length),this.controller.signal);
        if(token!==this.epoch)return;
        this.processed=length;
        if(typeof text!=='string')throw Error('invalid transcript');
        this.draft=this.base+text.trim();this.onDraft(this.draft);
      } catch(error){
        if(token===this.epoch){this.fail(error.message||'Local transcription failed. Nothing has been sent.');throw error;}
      }
    })();
    this.pending=work;
    try{await work;}finally{if(this.pending===work)this.pending=null;}
  }
  async finish(){
    if(this.finishing)return this.finishing;
    if(!this.running)return this.phase==='error'?null:this.draft;
    this.running=false;this.clear(this.timer);this.mic?.stop();this.state('transcribing');
    const token=this.epoch;
    this.finishing=(async()=>{
      try {
        await this.update(true);
        if(token!==this.epoch)return null;
        this.parts=[];this.state('off');return this.draft;
      } catch {return null;}finally{this.finishing=null;}
    })();
    return this.finishing;
  }
  cancel(){
    this.epoch++;this.running=false;this.clear(this.timer);this.controller?.abort();this.mic?.stop();
    this.parts=[];this.state('off');
  }
  fail(message){this.cancel();this.state('error');this.onError(message);}
}
