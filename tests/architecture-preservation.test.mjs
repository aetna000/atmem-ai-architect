import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {spawnSync} from 'node:child_process';
const before={id:'cold-chain',revision:1,name:'Vaccine custody',provider:'tools',nodes:[{id:'site',position:{x:0,y:0},data:{label:'Clinic',provider:'tools',kind:'resource',origin:'existing'}},{id:'logger',position:{x:50,y:0},data:{label:'Temperature logger',provider:'tools',kind:'resource',origin:'proposed',parentBlockId:'site',buildSpec:{tests:'Restart safely'}}}],
 edges:[{id:'temperature',source:'logger',target:'site',label:'Report reading',interfaceSpec:{failure:'Persist reading'}}],
 needs:[{id:'retain',statement:'Retain every reading.',source:'user',status:'open',links:['logger']}],decisions:[{id:'adr',decision:'Keep clinic data on site'}],openQuestions:[{id:'q',question:'Retention approval pending'}],
 extensions:{designSources:[{sha256:'a'.repeat(64),name:'Clinic brief.txt',text:'Retain every reading.'}]}};
const candidate=()=>{
 const after=structuredClone(before);after.revision=2;after.nodes[1].data.buildSpec.tests='Restart during a network outage';after.edges[0].interfaceSpec.failure='Persist and replay the same reading ID';
 after.extensions.designSources.push({sha256:'c'.repeat(64),name:'Logger recovery.txt',text:'Replay ambiguous deliveries.'});
 after.extensions.architectureDraftQuality={artifactId:'capture',draftSha256:'d'.repeat(64),contextSha256:'b'.repeat(64)};
 after.extensions.architectureAmendments=[{version:1,baseRevision:1,artifactId:'capture',draftSha256:'d'.repeat(64),contextSha256:'b'.repeat(64),
 changes:[{kind:'block',id:'logger',before:before.nodes[1],after:after.nodes[1]},{kind:'interface',id:'temperature',before:before.edges[0],after:after.edges[0]}],coverage:[{id:'retain',sourceSha256:'c'.repeat(64),reference:'Recovery',links:['logger']}]}];return after;
};
function run(value,expected='c'.repeat(64)){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atmem-preserve-'));
 try{const old=path.join(root,'before.json'),next=path.join(root,'after.json');fs.writeFileSync(old,JSON.stringify(before));fs.writeFileSync(next,JSON.stringify(value));return spawnSync(process.execPath,['scripts/verify-architecture-update.mjs',old,next,expected],{encoding:'utf8'});}finally{fs.rmSync(root,{recursive:true,force:true});}
}
test('independent preservation oracle reads raw snapshots and accepts a receipt-bound update in another domain',()=>{
 const result=run(candidate());assert.equal(result.status,0,result.stderr);const report=JSON.parse(result.stdout);assert.equal(report.preservedBlocks,2);assert.equal(report.preservedRequirements,1);assert.equal(report.amendedInterfaces,1);
});
test('independent preservation oracle rejects protected data loss, forged receipt identity and source drift',()=>{
 for(const mutate of [
  p=>p.nodes[1].data.provider='aws',p=>p.nodes[1].data.origin='existing',p=>p.nodes[1].position.x++,
  p=>p.needs[0].statement='Drop readings',p=>p.nodes.splice(0,1),p=>p.edges.splice(0,1),
  p=>p.edges[0].target='logger',p=>p.decisions.splice(0,1),p=>p.openQuestions[0].question='Ignore retention',
  p=>p.extensions.designSources[0].text='Different source',p=>p.extensions.architectureAmendments[0].draftSha256='f'.repeat(64),
  p=>p.extensions.architectureAmendments[0].changes=[],p=>p.needs[0].links.push('unknown'),
 ]){const value=candidate();mutate(value);assert.notEqual(run(value).status,0,mutate.toString());}
 assert.notEqual(run(candidate(),'0'.repeat(64)).status,0);
});
