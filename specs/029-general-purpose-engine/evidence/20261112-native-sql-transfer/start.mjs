// One deliberate new qualification turn after prerequisite implementation.
// No automatic retry, restart or inference on observation timeout.
import fs from 'node:fs';import assert from 'node:assert/strict';
const base='http://127.0.0.1:5287',e='specs/029-general-purpose-engine/evidence/20261112-native-sql-transfer',out='.local/external-artifacts/native-sql-transfer/v1';
assert(!fs.existsSync(out),'Preserve existing run; observe it instead');fs.mkdirSync(out,{recursive:true});
const context=JSON.parse(fs.readFileSync('specs/029-general-purpose-engine/evidence/20261112-native-runtime-access/context-v1.json'));
const auth=await(await fetch(base+'/api/session')).json();
async function post(action,extra={}){const r=await fetch(base+'/api/engineering/'+action,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+auth.token},body:JSON.stringify({...context,...extra}),signal:AbortSignal.timeout(90000)});const v=await r.json();if(!r.ok)throw Error(JSON.stringify(v));return v;}
const before=await post('state');assert.equal(before.state,'idle');assert.equal(before.last_status,'completed');assert.equal(before.model,'gpt-6.1-sol');assert.equal(before.effort,'high');
const catalog=await post('validators');fs.writeFileSync(out+'/catalog.json',JSON.stringify(catalog,null,2)+'\n');
assert(JSON.stringify(catalog).includes('postgresql-server'));assert(JSON.stringify(catalog).includes('17.11'));
const live={context,before,sourceCommit:'746e448',status:'submitting_new_qualification_turn',cloudOperations:false};
fs.writeFileSync(out+'/live.json',JSON.stringify(live,null,2)+'\n');
live.started=await post('start',{text:fs.readFileSync(e+'/request.txt','utf8')});live.status='submitted';
fs.writeFileSync(out+'/live.json',JSON.stringify(live,null,2)+'\n');console.log(JSON.stringify(live));
