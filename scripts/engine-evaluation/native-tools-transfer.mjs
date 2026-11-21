// Explicit native tool qualification fixture, not an uncoached architecture/holdout run.
import fs from 'node:fs';
import path from 'node:path';
import {randomUUID,createHash} from 'node:crypto';
import {toProjectFile} from '../../src/project-file.mjs';
const args=Object.fromEntries(process.argv.slice(2).reduce((out,item,i,all)=>item.startsWith('--')?[...out,[item.slice(2),all[i+1]]]:out,[]));
const base=args.base||'http://127.0.0.1:5274',out=path.resolve(args.output);if(fs.existsSync(out))throw Error('Preserve prior evidence; select a new output.');fs.mkdirSync(out,{recursive:true});
const auth=await(await fetch(base+'/api/session')).json();
async function post(action,payload){const r=await fetch(base+'/api/'+action,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+auth.token},body:JSON.stringify(payload),signal:AbortSignal.timeout(90000)});const v=await r.json();if(!r.ok)throw Error(typeof v.detail==='string'?v.detail:'HTTP '+r.status);return v;}
const initial='This is an explicit local native-tool qualification fixture, not a cloud architecture. Build a small standard-library-only Python module distance.py exposing convert(value, source, destination). Initially support exactly m and ft (1 ft = 0.3048 m); reject other units, booleans, nonnumeric/nonfinite and negative values. No cloud services. Supply executable tests and a short README. Before coding use the offered atmem tools: inspect the check catalog and existing artifact list, search reviewed engineering evidence for interface validation or data lifetime, and read one complete record to qualify provenance retrieval. Explain if its cloud/domain scope does not apply; do not force a cloud pattern into this module. Verify actual module behavior with native tools. Preserve backend-supplied files.';
const repair='The next client requirement is centimetre support: add cm as both source and destination (100 cm = 1 m), preserving m/ft behavior and all validation rules. Use the offered atmem check tools to inspect the previous immutable package and the registered distance-centimetres check result before editing. That check describes the new requirement and fails the earlier package; this is requirement evolution, not an initial implementation defect. Repair the working source and tests, run local checks, and make clear that a check on old immutable bytes does not validate the new working files. Preserve backend-supplied evidence and instructions.';
let context=args.context?JSON.parse(fs.readFileSync(args.context,'utf8')):null;
try{
 if(!context){const project={id:randomUUID(),version:1,revision:1,name:'Native tool transfer — distance module',provider:'tools',requirements:initial,nodes:[],edges:[]};await post('projects/save',{id:project.id,file:toProjectFile(project)});const state=await post('engineering/create',{projectId:project.id,model:'gpt-6.1-sol',effort:'high'});context={projectId:project.id,sessionId:state.id};}
 fs.writeFileSync(path.join(out,'context.json'),JSON.stringify(context,null,2)+'\n');
 if(args.check){
  const artifacts=(await post('engineering/artifacts',context)).artifacts;const artifact=artifacts[0];if(!artifact)throw Error('A settled package is required.');
  let check=await post('engineering/validation/start',{...context,artifactId:artifact.id,validatorId:args.check});
  for(let i=0;i<100&&check.state!=='finished';i++){await new Promise(r=>setTimeout(r,200));check=await post('engineering/validation/get',{...context,checkId:check.id});}
  fs.writeFileSync(path.join(out,'check.json'),JSON.stringify(check,null,2)+'\n');console.log('Check',check.state,check.result?.status);process.exit(check.state==='finished'?0:1);
 }
 let state=await post('engineering/state',context);if(state.state!=='idle')throw Error('Existing job requires observation/recovery; no new turn was replayed.');
 const text=args.context?repair:initial;fs.writeFileSync(path.join(out,'intent.txt'),text);
 state=await post('engineering/start',{...context,text});let cursor=0;const events=[];const deadline=Date.now()+420000;let lastLog=0;
 while(Date.now()<deadline){const page=await post('engineering/events',{...context,after:cursor});state=page.session;for(const event of page.events){events.push(event);cursor=event.sequence;fs.appendFileSync(path.join(out,'events.jsonl'),JSON.stringify(event)+'\n');}fs.writeFileSync(path.join(out,'live.json'),JSON.stringify({context,state,events:events.length},null,2)+'\n');if(state.state==='idle')break;if(Date.now()-lastLog>30000){console.log('Observed',state.state,'events',events.length);lastLog=Date.now();}await new Promise(r=>setTimeout(r,500));}
 if(state.state==='running'){await post('engineering/interrupt',context);for(let i=0;i<30;i++){state=await post('engineering/recover',context);if(state.state==='idle')break;await new Promise(r=>setTimeout(r,1000));}}
 if(state.state!=='idle')throw Error('Unsettled native work; inspect existing run.');
 const artifact=await post('engineering/capture',context);fs.writeFileSync(path.join(out,'artifact.json'),JSON.stringify(artifact,null,2)+'\n');
 const response=await fetch(base+'/api/engineering/download',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+auth.token},body:JSON.stringify({...context,artifactId:artifact.id})});if(!response.ok)throw Error('Download failed');const bytes=Buffer.from(await response.arrayBuffer());if(createHash('sha256').update(bytes).digest('hex')!==artifact.sha256)throw Error('Digest mismatch');fs.writeFileSync(path.join(out,'artifact.zip'),bytes);
 fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({context,state,artifactId:artifact.id,artifactSha256:artifact.sha256,cloudOperations:false,scope:'Explicit native tool qualification fixture; no uncoached/holdout/28-case acceptance or quality advantage inferred.'},null,2)+'\n');console.log('Captured',state.last_status,artifact.files.length,'entries');
}catch(error){fs.writeFileSync(path.join(out,'error.json'),JSON.stringify({message:error.message,context},null,2)+'\n');console.error(error.message);process.exitCode=1;}
