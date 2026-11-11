// Observe/reconcile an existing owned job. Never create/start/replay client work.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';import {execFileSync} from 'node:child_process';
const args=Object.fromEntries(process.argv.slice(2).reduce((out,item,i,all)=>item.startsWith('--')?[...out,[item.slice(2),all[i+1]]]:out,[]));
for(const key of ['project','session','output','source-root'])if(!args[key])throw Error('Missing --'+key);
const out=path.resolve(args.output);if(fs.existsSync(out))throw Error('Choose a fresh output to preserve prior evidence');fs.mkdirSync(out,{recursive:true});
const base=args.base||'http://127.0.0.1:5274',root=path.resolve(args['source-root']),seconds=Number(args.seconds||900),sha=value=>createHash('sha256').update(value).digest('hex');assert(Number.isInteger(seconds)&&seconds>=30&&seconds<=1800);
const source={};for(const dir of ['server','src','knowledge'])for(const file of fs.readdirSync(path.join(root,dir),{recursive:true})){const relative=path.join(dir,file),full=path.join(root,relative);if(fs.statSync(full).isFile()&&/\.(py|jsx|mjs|css|json)$/.test(file)&&!file.includes('__pycache__'))source[relative]=sha(fs.readFileSync(full));}
source['agent-skills/specialists/composition/SKILL.md']=sha(fs.readFileSync(path.join(root,'agent-skills/specialists/composition/SKILL.md')));
fs.writeFileSync(path.join(out,'source-at-start.json'),JSON.stringify(source,null,2)+'\n');
const auth=await(await fetch(base+'/api/session')).json(),context={projectId:args.project,sessionId:args.session};
const live={...context,sourceCommit:execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),startedAt:new Date().toISOString(),status:'observing',observationSeconds:seconds,cloudOperations:false};
const persist=()=>fs.writeFileSync(path.join(out,'live.json'),JSON.stringify(live,null,2)+'\n');persist();
async function post(action,extra={}){const response=await fetch(base+'/api/engineering/'+action,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+auth.token},body:JSON.stringify({...context,...extra}),signal:AbortSignal.timeout(90000)});if(!response.ok)throw Error('Existing-job request '+action+' failed with '+response.status);return action==='download'?response:response.json();}
try{
 live.before=await post('state');assert.equal(live.before.state,'idle','Observe active work separately; this driver only reconciles an existing idle completion');assert.equal(live.before.last_status,'completed');persist();
 await post('recover');
 if(args.recheck==='true'){
  const existing=(await post('finalizations')).finalizations.findLast(item=>item.runId===live.before.run);
  assert(existing?.artifact,'Explicit recheck requires the existing completed artifact');
  live.recheck=await post('recheck',{runId:live.before.run,artifactId:existing.artifact.id});persist();
 }
 let latest,done=false;const deadline=Date.now()+seconds*1000;
 while(Date.now()<deadline){live.job=await post('state');live.finalizations=(await post('finalizations')).finalizations;latest=live.finalizations.findLast(item=>item.runId===live.job.run);persist();if(live.job.state==='idle'&&latest&&['local_checks_passed','needs_attention','recovery_required'].includes(latest.state)){done=true;break;}await new Promise(resolve=>setTimeout(resolve,1000));}
 if(!done)throw Error('Existing finalization has not settled. Inspect/recover the same run; no work was replayed or interrupted.');
 for(const finalization of live.finalizations){if(!finalization.artifact)continue;const folder=path.join(out,finalization.runId);fs.mkdirSync(folder);const artifacts=(await post('artifacts')).artifacts;const artifact=artifacts.find(a=>a.id===finalization.artifact.id);assert(artifact);fs.writeFileSync(path.join(folder,'artifact.json'),JSON.stringify(artifact,null,2)+'\n');const content=Buffer.from(await(await post('download',{artifactId:artifact.id})).arrayBuffer());assert.equal(sha(content),artifact.sha256);fs.writeFileSync(path.join(folder,'artifact.zip'),content);fs.writeFileSync(path.join(folder,'checks.json'),JSON.stringify(await post('validation/list',{artifactId:artifact.id}),null,2)+'\n');}
 const finalArtifact=live.finalizations.findLast(item=>item.runId===live.job.run)?.artifact;if(finalArtifact){fs.copyFileSync(path.join(out,live.job.run,'artifact.json'),path.join(out,'artifact.json'));fs.copyFileSync(path.join(out,live.job.run,'artifact.zip'),path.join(out,'artifact.zip'));}
 let cursor=0,events=[];while(true){const result=await post('events',{after:cursor});events.push(...result.events);if(result.events.length)cursor=result.events.at(-1).sequence;if(result.events.length<200)break;}
 fs.writeFileSync(path.join(out,'events.json'),JSON.stringify(events,null,2)+'\n');live.automaticRepairs=events.filter(e=>e.kind==='accepted'&&e.origin==='automatic_repair').length;live.sourceChangedDuringRun=Object.entries(source).filter(([file,digest])=>sha(fs.readFileSync(path.join(root,file)))!==digest).map(([file])=>file);assert.deepEqual(live.sourceChangedDuringRun,[]);live.status='settled_evidence_captured';live.artifactSha256=finalArtifact?.sha256;live.independentAcceptance='not_established';persist();console.log(JSON.stringify(live,null,2));
}catch(error){live.status='requires_inspection';live.error=error.message;persist();console.error(error.message);process.exitCode=1;}
