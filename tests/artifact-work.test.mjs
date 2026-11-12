import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {validateImport} from '../src/core.mjs';
import {architectureWork,emptyArchitectureWork,proposeWorkRecords,reviewWorkContext,synchronizeEngineeringIntent,validateArchitectureWork} from '../src/architecture-work.mjs';
import {applyArtifactWork,artifactWorkProjection,verifyArtifactWork} from '../src/artifact-work.mjs';
import {toProjectFile,parseProjectFile} from '../src/project-file.mjs';
import {deliveryPack} from '../src/delivery.mjs';
const sha=value=>createHash('sha256').update(value).digest('hex');
const now=new Date('2026-11-11T12:00:00Z');
function project(domain='wetlands'){
 return validateImport({id:domain+'-project',version:1,revision:1,name:domain,provider:'tools',requirements:'Preserve the client-owned '+domain+' system.',brief:{application:'A local read-only gauge reader.'},
  nodes:['gauge','viewer','catalogue'].map((id,i)=>({id,position:{x:i*100,y:0},data:{kind:'tool',provider:'tools',origin:'existing',label:id,description:'Client-owned '+id,config:{region:'Local'}}})),
  edges:[{id:'flow',source:'gauge',target:'viewer',label:'Read-only readings'}],
  needs:[{id:'depth',source:'user',priority:'must',kind:'functional',status:'open',statement:'Show depth in metres.',links:['gauge','viewer']},{id:'catalogue',source:'user',priority:'must',kind:'functional',status:'open',statement:'Keep the catalogue unchanged.',links:['catalogue']}],
  decisions:[{id:'adr-local',title:'Keep processing local',subject:'local',status:'Accepted',decision:'Client-owned local operation.'}]});
}
const records=()=>[{id:'reader',kind:'implementation',title:'Gauge reader',description:'Read-only mapping.',dependsOn:['block:viewer'],data:{files:['reader.cjs']}},
 {id:'reader-check',kind:'evidence',title:'Check source reference',description:'An unverified reference.',dependsOn:['work:reader'],data:{files:['reader.test.cjs'],reportedStatus:'passed'}}];
async function receipt(p,{id='receipt-one',artifact='artifact-one',sessionId='session-wetlands',runId='run-one',proposal=records(),files,events}={}){
 const content=JSON.stringify(toProjectFile(p,now));
 const payload={format:'atmem.architecture-proposal',version:1,projectId:p.id,sessionId,runId,artifactId:artifact,artifactSha256:sha(artifact),proposalSha256:sha(JSON.stringify(proposal)),
  context:{id:'context-'+id,revision:1,sha256:sha(content),projectId:p.id,content},
  events:events||[{sequence:1,kind:'accepted',runId,text:'Build the read-only local reader.'}],
  proposal:{version:1,records:proposal},files:files||['reader.cjs','reader.test.cjs'].map(path=>({path,bytes:100,sha256:sha(artifact+path)})),definitionSha256:sha('reconciliation-definition'),boundary:'artifact_file_binding_only'};
 const encoded=JSON.stringify(payload);
 return verifyArtifactWork({status:'prepared',id,sha256:sha(encoded),content:encoded});
}
test('artifact reconciliation preserves design/ownership and links exact files without trusting pass claims',async()=>{
 const p=project(),original=structuredClone(p),r=await receipt(p),next=applyArtifactWork(p,p.id,r,{now});
 assert.deepEqual(p,original);for(const key of ['nodes','edges','provider','needs','decisions','requirements'])assert.deepEqual(next[key],p[key]);
 const state=next.extensions.architectureWork;assert.equal(state.version,2);assert.equal(state.artifactMappings.length,1);
 assert(state.records.every(r=>r.source==='agent'&&r.agreement==='proposed'));assert.equal(state.records[1].data.reportedStatus,'passed');
 assert.equal(architectureWork(next).entities.find(e=>e.id==='work:reader-check').contextStatus,'unreviewed');
 const view=artifactWorkProjection(next);assert.equal(view.mappings[0].contextStatus,'current');assert.match(view.boundary,/not execution/);
 assert.equal(view.coverage.find(r=>r.ref==='requirement:depth').status,'file_reference_linked');assert.equal(view.coverage.find(r=>r.ref==='requirement:catalogue').status,'unmapped');
 assert.equal(view.mappings[0].files[0].sha256,r.payload.files[0].sha256);
});
test('structured brief changes invalidate both reviews and generated mapping context',async()=>{
 let p=applyArtifactWork(project(),project().id,await receipt(project()),{now});p=reviewWorkContext(p,'work:reader',{now});
 const changed={...p,brief:{...p.brief,application:'Publish writable remote readings instead.'}};
 assert.equal(architectureWork(changed).entities.find(e=>e.id==='work:reader').contextStatus,'changed');
 assert.equal(artifactWorkProjection(changed).mappings[0].contextStatus,'changed');
 assert.equal(changed.decisions[0].status,'Accepted');
});
test('meaningful annotations and interface contracts participate without turning notes into physical units',async()=>{
 const p=project();p.nodes.push({id:'constraint-note',position:{x:0,y:0},data:{kind:'note',provider:'tools',label:'Preserve read-only access.'}});p.edges[0].data={contract:{access:'read-only'}};
 const r=await receipt(p),bound=applyArtifactWork(p,p.id,r),changed=structuredClone(bound);changed.nodes.at(-1).data.label='Read/write access requires a new client decision.';
 assert.equal(artifactWorkProjection(changed).mappings[0].contextStatus,'changed');assert(!architectureWork(bound).entities.some(e=>e.id==='block:constraint-note'));
 const altered=structuredClone(bound);altered.edges[0].data.contract.access='write';assert.equal(artifactWorkProjection(altered).mappings[0].contextStatus,'changed');
 const moved=structuredClone(bound);moved.nodes.at(-1).position.x=700;assert.equal(artifactWorkProjection(moved).mappings[0].contextStatus,'current');
});
test('requirement/provider/ownership/interface and newer client changes reject stale asynchronous imports atomically',async()=>{
 const p=project(),r=await receipt(p);
 for(const change of [q=>q.needs[0].statement='Use centimetres.',q=>q.provider='aws',q=>q.nodes[0].data.origin='new',q=>q.edges[0].label='Allow writes',q=>q.brief.application='Change scope']){
  const q=structuredClone(p);change(q);const before=structuredClone(q);assert.throws(()=>applyArtifactWork(q,q.id,r),/design changed/);assert.deepEqual(q,before);
 }
 const newer=synchronizeEngineeringIntent(p,'session-wetlands',[...r.payload.events,{sequence:2,kind:'steering_submitted',requestId:'new-update',text:'Keep a second audit log.'},{sequence:3,kind:'steering_accepted',requestId:'new-update'}]);
 assert.throws(()=>applyArtifactWork(newer,newer.id,r),/design changed/);
});
test('layout-only movement remains compatible and a switched-project callback changes nothing',async()=>{
 const p=project(),r=await receipt(p),moved=structuredClone(p);moved.nodes[0].position.x=999;moved.nodes[0].data.inputPosition='bottom';
 assert.equal(applyArtifactWork(moved,moved.id,r).extensions.architectureWork.artifactMappings.length,1);
 const other=project('library');assert.strictEqual(applyArtifactWork(other,p.id,r),other);assert.throws(()=>applyArtifactWork(other,other.id,r),/different project/);
});
test('a second generation explicitly revises only its own proposed mappings and retains prior values and hashes',async()=>{
 const p=project(),first=await receipt(p);let current=applyArtifactWork(p,p.id,first,{now});
 const revised=records();revised[0].data.files=['reader-v2.cjs'];
 const second=await receipt(current,{id:'receipt-two',artifact:'artifact-two',runId:'run-two',proposal:revised,files:['reader-v2.cjs','reader.test.cjs'].map(path=>({path,bytes:200,sha256:sha(path)})),events:[...first.payload.events,{sequence:2,kind:'accepted',runId:'run-two',text:'Reconcile the current local implementation.'}]});
 const next=applyArtifactWork(current,current.id,second,{now:new Date('2026-11-11T13:00:00Z')});
 const state=next.extensions.architectureWork;assert.equal(state.artifactMappings.length,2);assert.deepEqual(state.artifactMappings[0].records[0].data.files,['reader.cjs']);assert.deepEqual(state.records[0].data.files,['reader-v2.cjs']);
 assert.deepEqual(artifactWorkProjection(next).mappings.map(m=>m.contextStatus),['superseded','current']);
 assert.equal(state.artifactMappings[0].artifactSha256,first.payload.artifactSha256);assert.strictEqual(applyArtifactWork(next,next.id,second),next);
});
test('unbound/manual/accepted or locally edited mapping collisions cannot be overwritten',async()=>{
 const p=project(),r=await receipt(p);
 const manual=proposeWorkRecords(p,[records()[0]]);assert.throws(()=>applyArtifactWork(manual,manual.id,r),/conflicts/);
 let next=applyArtifactWork(p,p.id,r),edited=structuredClone(next);edited.extensions.architectureWork.records[0].description='A local change the agent must not erase.';
 const follow=await receipt(next,{id:'receipt-two',artifact:'artifact-two'});assert.throws(()=>applyArtifactWork(edited,edited.id,follow),/conflicts/);
 const accepted=structuredClone(next);accepted.extensions.architectureWork.records[0].agreement='accepted';assert.throws(()=>applyArtifactWork(accepted,accepted.id,follow),/conflicts/);
});
test('missing source or file references and duplicate identities are rejected without scope deletion',async()=>{
 const p=project();
 for(const update of [r=>r[0].dependsOn=['block:missing'],r=>r[0].data.files=['missing.cjs'],r=>r[0].data.files=[],r=>r.push(r[0])]){
  const list=records();update(list);const r=await receipt(p,{proposal:list});assert.throws(()=>applyArtifactWork(p,p.id,r));assert.equal(p.extensions?.architectureWork,undefined);
 }
});
test('receipt and saved context tampering is rejected before model application',async()=>{
 const r=await receipt(project()),content=JSON.stringify(r.payload);
 await assert.rejects(()=>verifyArtifactWork({status:'prepared',id:r.id,sha256:'0'.repeat(64),content}),/digest/);
 const wrong=structuredClone(r.payload);wrong.context.content+=' ';const raw=JSON.stringify(wrong);
 await assert.rejects(()=>verifyArtifactWork({status:'prepared',id:r.id,sha256:sha(raw),content:raw}),/context digest/);
});
test('version1 state migrates without dropping review history and future versions remain explicit failures',()=>{
 let p=proposeWorkRecords(project(),[{...records()[0],source:'agent',agreement:'proposed'}]);p=reviewWorkContext(p,'work:reader',{now});
 const current=p.extensions.architectureWork,legacy=structuredClone(current);delete legacy.artifactMappings;legacy.version=1;
 const migrated=validateArchitectureWork(legacy);assert.deepEqual(migrated,{...legacy,version:2,artifactMappings:[]});assert.deepEqual(migrated.snapshots,current.snapshots);
 assert.throws(()=>validateArchitectureWork({...emptyArchitectureWork(),version:3}),/Unsupported/);
});
test('save/reopen, Design/Build projection, delivery and compiler/Spec Kit exports agree without clearing gaps',async()=>{
 const p=project(),next=applyArtifactWork(p,p.id,await receipt(p),{now});
 const back=parseProjectFile(JSON.stringify(toProjectFile(next,now))).project;
 assert.deepEqual(artifactWorkProjection(back),artifactWorkProjection(next));
 const files=deliveryPack(back),view=artifactWorkProjection(back);
 assert.deepEqual(JSON.parse(files['architecture-artifact-mappings.json']),view);assert.deepEqual(JSON.parse(files['spec-kit/artifact-mappings.json']),view);
 const quality=JSON.parse(files['generation-quality.json']);assert.equal(quality.artifactMappings.references[0].artifactId,view.mappings[0].artifactId);assert.equal(quality.deploymentCandidate,false);assert.equal(quality.validation.runtime,'not_run');
});
