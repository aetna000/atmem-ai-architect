// Resume observation only. Never submit/start/replay/interrupt a native turn.
import fs from 'node:fs';import {createHash}from 'node:crypto';
const base='http://127.0.0.1:5287',evidence='specs/029-general-purpose-engine/evidence/20261112-native-runtime-access',out='.local/external-artifacts/native-runtime-access/v1';
const context=JSON.parse(fs.readFileSync(evidence+'/context-v1.json')),prior=JSON.parse(fs.readFileSync(out+'/live.json'));
const auth=await(await fetch(base+'/api/session')).json();async function post(action,payload){const response=await fetch(base+'/api/'+action,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+auth.token},body:JSON.stringify(payload),signal:AbortSignal.timeout(90000)});const value=await response.json();if(!response.ok)throw Error(JSON.stringify(value.detail||value));return value;}
let state=await post('engineering/state',context),cursor=prior.cursor;console.log('Existing session',context.sessionId,'state',state.state);if(state.state==='running'&&state.run!==prior.state.run)throw Error('Unexpected different run; no work submitted');
let lastLog=0;
while(state.state!=='idle'){
 const page=await post('engineering/events',{...context,after:cursor});state=page.session;for(const event of page.events){cursor=event.sequence;fs.appendFileSync(out+'/events.jsonl',JSON.stringify(event)+'\n');}fs.writeFileSync(out+'/live.json',JSON.stringify({context,state,cursor},null,2)+'\n');
 if(state.state==='idle')break;if(Date.now()-lastLog>30000){console.log('Observed same run',state.state,'cursor',cursor);lastLog=Date.now();}await new Promise(resolve=>setTimeout(resolve,1000));
}
const artifact=await post('engineering/capture',context);fs.writeFileSync(evidence+'/artifact-v1.json',JSON.stringify(artifact,null,2)+'\n');
const response=await fetch(base+'/api/engineering/download',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+auth.token},body:JSON.stringify({...context,artifactId:artifact.id})});if(!response.ok)throw Error('Download failed');const bytes=Buffer.from(await response.arrayBuffer());if(createHash('sha256').update(bytes).digest('hex')!==artifact.sha256)throw Error('Digest mismatch');fs.writeFileSync(out+'/artifact.zip',bytes);
fs.writeFileSync(evidence+'/native-run-v1.receipt.json',JSON.stringify({context,state,artifactId:artifact.id,artifactSha256:artifact.sha256,bulk:out,observationResumedWithoutNewTurn:true,cloudOperations:false,boundary:'Actual native session/artifact only; application acceptance is independent'},null,2)+'\n');console.log('Settled',state.last_status,'files',artifact.files.length);
