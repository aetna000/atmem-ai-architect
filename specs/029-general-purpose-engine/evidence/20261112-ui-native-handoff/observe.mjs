// Read the existing job only. Observation expiry never authorizes resubmission.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {createHash}from 'node:crypto';
const base='http://127.0.0.1:5298',out='.local/external-artifacts/ui-native-handoff/v1',live=JSON.parse(fs.readFileSync(out+'/live.json')),source=path.resolve('.local/external-artifacts/frozen-provider-eval/board-ui-v1');assert(live.context);
const auth=await(await fetch(base+'/api/session')).json(),sha=b=>createHash('sha256').update(b).digest('hex');
async function post(action,extra={}){const r=await fetch(base+'/api/engineering/'+action,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+auth.token},body:JSON.stringify({...live.context,...extra}),signal:AbortSignal.timeout(90000)});assert(r.ok,action+' HTTP '+r.status);return action==='download'?r:r.json()}
fs.writeFileSync(out+'/catalog.json',JSON.stringify(await post('validators'),null,2)+'\n');
let cursor=0,events=[],settled=false,state,finalizations;const deadline=Date.now()+900000;
while(Date.now()<deadline){
 let page;do{page=await post('events',{after:cursor});events.push(...page.events);if(page.events.length)cursor=page.events.at(-1).sequence;}while(page.events.length===200);
 state=await post('state');finalizations=(await post('finalizations')).finalizations;
 fs.writeFileSync(out+'/events.json',JSON.stringify(events,null,2)+'\n');fs.writeFileSync(out+'/observation.json',JSON.stringify({state,finalizations,cursor,observedAt:new Date().toISOString(),noInferenceSubmitted:true},null,2)+'\n');
 const current=finalizations.findLast(f=>f.runId===state.run);
 console.log(JSON.stringify({run:state.run,state:state.state,status:state.last_status,events:cursor,finalization:current?.state||null}));
 if(state.state==='idle'&&current&&['local_checks_passed','needs_attention','recovery_required'].includes(current.state)){settled=true;break}
 if(state.state==='idle'&&['failed','interrupted'].includes(state.last_status))break;
 await new Promise(r=>setTimeout(r,15000));
}
if(!settled){console.log('Not settled; inspect this same run, never restart because observation expired.');process.exit(2)}
const current=finalizations.findLast(f=>f.runId===state.run);assert(current.artifact);
const artifacts=(await post('artifacts')).artifacts,artifact=artifacts.find(a=>a.id===current.artifact.id);assert(artifact);
const bytes=Buffer.from(await(await post('download',{artifactId:artifact.id})).arrayBuffer());assert.equal(sha(bytes),artifact.sha256);
const hashes=JSON.parse(fs.readFileSync(out+'/source-at-start.json'));const changes=Object.entries(hashes).filter(([f,h])=>sha(fs.readFileSync(path.join(source,f)))!==h).map(([f])=>f);assert.deepEqual(changes,[]);
fs.writeFileSync(out+'/artifact.zip',bytes);fs.writeFileSync(out+'/artifact.json',JSON.stringify(artifact,null,2)+'\n');fs.writeFileSync(out+'/checks.json',JSON.stringify(await post('validation/list',{artifactId:artifact.id}),null,2)+'\n');
const receipt={context:live.context,sourceCommit:live.sourceCommit,model:live.model,effort:live.effort,requestedRun:live.started.run,state,artifactId:artifact.id,artifactSha256:artifact.sha256,finalizationState:current.state,automaticRepairs:events.filter(e=>e.kind==='accepted'&&e.origin==='automatic_repair').length,sourceChanges:changes,cloudOperations:false,independentAcceptance:false};
fs.writeFileSync(out+'/settled.json',JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
