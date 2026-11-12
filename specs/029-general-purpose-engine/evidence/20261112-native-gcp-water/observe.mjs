// Observe only. Expiry/failure never restarts, interrupts or resubmits inference.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {createHash}from 'node:crypto';
const root='.local/external-artifacts/native-gcp-water/v1/native-run',base='http://127.0.0.1:5289',live=JSON.parse(fs.readFileSync(root+'/live.json')),source=path.resolve('.local/external-artifacts/frozen-provider-eval/c11fdbc');
const sha=b=>createHash('sha256').update(b).digest('hex'),sourceHashes=JSON.parse(fs.readFileSync(root+'/source-at-start.json'));const auth=await(await fetch(base+'/api/session')).json();
async function post(action,extra={}){const r=await fetch(base+'/api/engineering/'+action,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+auth.token},body:JSON.stringify({...live.context,...extra}),signal:AbortSignal.timeout(90000)});if(!r.ok)throw Error(action+' HTTP'+r.status);return action==='download'?r:r.json();}
let cursor=0,events=[],state,finalizations,settled=false;const deadline=Date.now()+900000;
while(Date.now()<deadline){
 let page;do{page=await post('events',{after:cursor});events.push(...page.events);if(page.events.length)cursor=page.events.at(-1).sequence;}while(page.events.length===200);
 state=await post('state');finalizations=(await post('finalizations')).finalizations;
 fs.writeFileSync(root+'/events.json',JSON.stringify(events,null,2)+'\n');fs.writeFileSync(root+'/observation.json',JSON.stringify({state,finalizations,cursor,observedAt:new Date().toISOString(),noInferenceSubmitted:true},null,2)+'\n');
 const current=finalizations.findLast(f=>f.runId===state.run);
 if(state.state==='idle'&&current&&['local_checks_passed','needs_attention','recovery_required'].includes(current.state)){settled=true;break;}
 console.log('Observed existing run',state.run,state.state,'events',cursor,current?.state||'native turn');await new Promise(r=>setTimeout(r,30000));
}
if(!settled){console.log('Observation expired; inspect the same existing run. No restart or interruption.');process.exit(2);}
const current=finalizations.findLast(f=>f.runId===state.run);assert(current.artifact);
const artifacts=(await post('artifacts')).artifacts,artifact=artifacts.find(a=>a.id===current.artifact.id);assert(artifact);
const bytes=Buffer.from(await(await post('download',{artifactId:artifact.id})).arrayBuffer());assert.equal(sha(bytes),artifact.sha256);
const changed=Object.entries(sourceHashes).filter(([file,hash])=>sha(fs.readFileSync(path.join(source,file)))!==hash).map(([file])=>file);assert.deepEqual(changed,[]);
fs.writeFileSync(root+'/artifact.zip',bytes);fs.writeFileSync(root+'/artifact.json',JSON.stringify(artifact,null,2)+'\n');fs.writeFileSync(root+'/checks.json',JSON.stringify(await post('validation/list',{artifactId:artifact.id}),null,2)+'\n');
fs.writeFileSync(root+'/settled.json',JSON.stringify({context:live.context,sourceCommit:live.sourceCommit,requestedRun:live.started.run,state,artifactId:artifact.id,artifactSha256:artifact.sha256,finalizationState:current.state,sourceChangedDuringRun:changed,automaticRepairs:events.filter(e=>e.kind==='accepted'&&e.origin==='automatic_repair').length,cloudOperations:false,independentAcceptance:false},null,2)+'\n');console.log('Settled',state.last_status,current.state,'artifact',artifact.sha256);
