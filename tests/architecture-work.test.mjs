import test from 'node:test';
import assert from 'node:assert/strict';
import {architectureWork,reviewWorkContext,proposeWorkRecords,synchronizeEngineeringIntent,validateArchitectureWork,emptyArchitectureWork} from '../src/architecture-work.mjs';
import {validateImport} from '../src/core.mjs';
import {toProjectFile,parseProjectFile} from '../src/project-file.mjs';
import {deliveryPack} from '../src/delivery.mjs';
function project(domain='river'){
 return validateImport({id:domain+'-project',version:1,revision:1,name:domain,provider:'tools',requirements:'Preserve the existing '+domain+' system.',
  nodes:['sensor','display','catalog'].map((id,i)=>({id,type:'resource',position:{x:i*100,y:0},data:{kind:'tool',provider:'tools',origin:'existing',label:id,description:id+' responsibility',config:{region:'Local'}}})),
  edges:[{id:'flow',source:'sensor',target:'display',label:'Read-only readings'}],
  needs:[{id:'latency',statement:'Show readings within two seconds.',source:'user',links:['sensor','display'],kind:'functional',priority:'must',status:'open'},{id:'catalog',statement:'Keep the catalogue unchanged.',source:'user',links:['catalog'],kind:'functional',priority:'must',status:'open'}],decisions:[{id:'adr-1',subject:'local-processing',title:'Process locally',decision:'Local processing',status:'Accepted',date:'2026-11-11',reason:'Recorded client choice',revision:1}]});
}
const record=(id,kind,dependsOn,data={})=>({id,kind,title:id,description:'Explicit proposed mapping',source:'agent',agreement:'proposed',dependsOn,data});
const state=p=>p.extensions.architectureWork;
const entity=(p,id)=>architectureWork(p).entities.find(e=>e.id===id);
const now=new Date('2026-11-11T00:00:00Z');
test('legacy projects project lossless sources without inventing deployment units or execution evidence',()=>{
 const p=project(),m=architectureWork(p);assert.equal(m.version,2);assert.equal(m.entities.filter(e=>e.kind==='delivery-unit').length,0);assert.equal(entity(p,'block:sensor').value.origin,'existing');assert.equal(entity(p,'block:sensor').contextStatus,'unreviewed');assert.equal(p.extensions?.architectureWork,undefined);
 assert.match(m.boundary,/not independently verified/);assert.equal(entity(p,'requirement:latency').value.source,'user');
});
test('transitive requirement change affects mapped units/files/evidence and decisions; old scope/history remains',()=>{
 let p=proposeWorkRecords(project(),[record('unit','delivery-unit',['block:sensor']),record('code','implementation',['work:unit'],{files:['app/readings.py']}),record('check','evidence',['work:code'],{level:'local-runtime',reportedStatus:'passed'})]);
 for(const ref of ['work:unit','work:code','work:check','decision:adr-1'])p=reviewWorkContext(p,ref,{now});
 const before=structuredClone(state(p)),q={...p,needs:p.needs.map(r=>r.id==='latency'?{...r,statement:'Show readings within one second.'}:r)};
 for(const ref of ['work:unit','work:code','work:check','decision:adr-1'])assert.equal(entity(q,ref).contextStatus,'changed');
 assert(entity(q,'work:check').changedRefs.includes('requirement:latency'));assert.deepEqual(state(q),before);assert.equal(q.decisions[0].status,'Accepted');assert.equal(entity(q,'work:check').value.data.reportedStatus,'passed');
 const reviewed=reviewWorkContext(q,'work:check',{now:new Date('2026-11-12T00:00:00Z')});assert.equal(entity(reviewed,'work:check').contextStatus,'current');assert.equal(state(reviewed).history.length,1);assert.deepEqual(state(reviewed).history[0],before.bindings.find(b=>b.ref==='work:check'));
 assert.match(entity(reviewed,'work:check').review.scope,/context_review_only/);
});
test('explicitly scoped dependencies avoid invalidation from unrelated requirements and diagram layout',()=>{
 let p=project();p.decisions=[];p=proposeWorkRecords(p,[record('viewer','implementation',['block:display'],{files:['viewer.js']})]);p=reviewWorkContext(p,'work:viewer',{now});
 const q=structuredClone(p);q.nodes[0].position={x:999,y:999};q.nodes[0].data.inputPosition='top';q.needs[1].statement+=' Private catalogue remains external.';
 assert.equal(entity(q,'work:viewer').contextStatus,'current');q.edges[0].label='Changed wire contract';assert.equal(entity(q,'work:viewer').contextStatus,'current');
 const mapped=reviewWorkContext(proposeWorkRecords(q,[record('wire','implementation',['interface:flow'])]),'work:wire',{now});mapped.edges[0].access='read-only-change';assert.equal(entity(mapped,'work:wire').contextStatus,'changed');
});
test('missing and removed references remain visible, including after save/reopen; missing cannot be reviewed',()=>{
 let p=proposeWorkRecords(project(),[record('map','implementation',['block:display'])]);p=reviewWorkContext(p,'work:map',{now});
 p.nodes=p.nodes.filter(n=>n.id!=='display');p.edges=[];assert.equal(entity(p,'work:map').contextStatus,'missing');assert.throws(()=>reviewWorkContext(p,'work:map'),/missing/);
 const reloaded=parseProjectFile(JSON.stringify(toProjectFile(p))).project;assert.equal(entity(reloaded,'work:map').contextStatus,'missing');
 reloaded.extensions.architectureWork.records=[];assert.equal(entity(reloaded,'work:map').contextStatus,'missing');assert.equal(entity(reloaded,'work:map').kind,'removed');
});
test('versioned state round-trips and export projection equals the live model without upgrading proposed claims',()=>{
 let p=proposeWorkRecords(project('library'),[record('lookup','delivery-unit',['block:catalog'],{lifecycle:'reference',owner:null}),record('claim','evidence',['work:lookup'],{reportedStatus:'passed'})]);p=reviewWorkContext(p,'work:claim',{now});
 const file=toProjectFile(p),back=parseProjectFile(JSON.stringify(file)).project;assert.deepEqual(state(back),state(p));assert.deepEqual(architectureWork(back),architectureWork(p));
 const bundle=deliveryPack(back);assert.deepEqual(JSON.parse(bundle['architecture-work.json']),architectureWork(back));assert.equal(entity(back,'work:claim').value.agreement,'proposed');assert.equal(entity(back,'work:claim').review.scope,'context_review_only');
 const legacy=toProjectFile(project());delete legacy.extensions.architectureWork;assert.equal(parseProjectFile(JSON.stringify(legacy)).project.extensions?.architectureWork,undefined);
});
test('project identity, owner, provider, interface and implementation edits invalidate their dependent context',()=>{
 for(const mutate of [p=>p.id='another-project',p=>p.provider='gcp',p=>p.nodes[0].data.origin='proposed',p=>p.nodes[0].data.description+=' new responsibility']){
  let p=reviewWorkContext(proposeWorkRecords(project(),[record('reader','implementation',['block:sensor'],{files:['reader.py']})]),'work:reader',{now});mutate(p);assert.equal(entity(p,'work:reader').contextStatus,'changed');
 }
});
test('engineering intent is lossless, ordered, monotonic across partial replay and excludes internal repairs/model replies',()=>{
 const p=project(),text='Keep the existing river service. '+'😀'.repeat(1500),events=[{sequence:1,kind:'accepted',runId:'run-1',text},{sequence:3,kind:'steering_submitted',requestId:'u1',text:'Use grams, not kilograms.'},{sequence:4,kind:'steering_delivery_uncertain',requestId:'u1'},{sequence:5,kind:'message',text:'I might change providers.'},{sequence:6,kind:'accepted',origin:'automatic_repair',text:'Internal repair is not client intent.'}];
 const q=synchronizeEngineeringIntent(p,'session1',events);assert.deepEqual(state(q).intents.map(i=>i.text),[text,'Use grams, not kilograms.']);assert.deepEqual(state(q).intents.map(i=>i.status),['accepted','uncertain']);
 const accepted=synchronizeEngineeringIntent(q,'session1',[...events,{sequence:7,kind:'steering_accepted',requestId:'u1'}]);assert.equal(state(accepted).intents[1].status,'accepted');assert.strictEqual(synchronizeEngineeringIntent(accepted,'session1',events),accepted);
 const other=synchronizeEngineeringIntent(accepted,'session2',[{sequence:1,kind:'accepted',text:'Keep the other source.'}]);assert.equal(state(other).intents.length,3);
 assert.throws(()=>synchronizeEngineeringIntent(accepted,'session1',[{sequence:1,kind:'accepted',text:'Overwritten history'}]),/changed identity/);
 const bound=reviewWorkContext(proposeWorkRecords(other,[record('work','implementation',['block:sensor'])]),'work:work',{now});const update=synchronizeEngineeringIntent(bound,'session2',[{sequence:8,kind:'steering_submitted',requestId:'u8',text:'A new unclassified demand'}]);assert.equal(entity(update,'work:work').contextStatus,'changed');assert.equal(state(bound).intents.length,3);
});
test('cycles are bounded context relationships, never circular evidence of successful execution',()=>{
 let p=proposeWorkRecords(project(),[record('a','responsibility',['work:b']),record('b','responsibility',['work:a'])]);p=reviewWorkContext(p,'work:a',{now});assert.equal(entity(p,'work:a').contextStatus,'current');assert.equal(entity(p,'work:b').contextStatus,'unreviewed');assert.equal(state(p).snapshots.filter(s=>s.ref==='work:a').length,1);
});
test('invalid/future/colliding/oversized/lossy states and path escapes fail without mutating the original',()=>{
 const p=project();for(const path of ['/host/secret','../outside','dir/../outside','a\\b','./entry'])assert.throws(()=>proposeWorkRecords(p,[record('bad','implementation',[],{files:[path]})]),/relative/);
 assert.throws(()=>proposeWorkRecords(p,[record('x','interface',[]),record('x','interface',[])]),/overwrite/);assert.equal(p.extensions?.architectureWork,undefined);
 for(const bad of [{...emptyArchitectureWork(),version:3},{...emptyArchitectureWork(),unknown:'future'}, {...emptyArchitectureWork(),records:[record('nan','responsibility',[],{value:NaN})]}, {...emptyArchitectureWork(),records:Array.from({length:1001},(_,i)=>record('r'+i,'responsibility',[]))}])assert.throws(()=>validateArchitectureWork(bad));
 let q=reviewWorkContext(proposeWorkRecords(p,[record('x','responsibility',[])]),'work:x',{now});q=structuredClone(q);state(q).bindings[0].snapshotIds.push('missing-snapshot');assert.throws(()=>toProjectFile(q),/retained source/);
 assert.throws(()=>proposeWorkRecords(p,[record('big','responsibility',[],{value:'x'.repeat(1_500_001)})]),/storage bound/);
});
test('real credentials in mapping data still block export rather than expanding the credential boundary',()=>{
 const p=proposeWorkRecords(project(),[record('credentials','implementation',[],{apiKey:'not-a-receiving-input'})]);assert.throws(()=>toProjectFile(p),/looks like a credential/);
});

test('native proposal schema and JavaScript reader agree on non-BMP text units',async()=>{
 const {execFileSync}=await import('node:child_process');
 const rows=[record('unicode','responsibility',[],{units:'Unicode code points'})];rows[0].title='😀'.repeat(200);
 const p=proposeWorkRecords(project(),rows);assert.equal([...state(p).records[0].title].length,200);
 execFileSync('.venv/bin/python',['-c',"import json,sys,jsonschema; s=json.load(open('server/engineering_assets/architecture_work.schema.json')); jsonschema.validate(json.load(sys.stdin),s)"],{input:JSON.stringify({version:1,records:state(p).records})});
 assert.throws(()=>proposeWorkRecords(project(),[{...rows[0],title:'😀'.repeat(201)}]),/work title/);
});
test('late/out-of-order event pages preserve per-session client sequence order',()=>{
 let p=synchronizeEngineeringIntent(project(),'s',[{sequence:20,kind:'accepted',text:'Later request'}]);
 p=synchronizeEngineeringIntent(p,'s',[{sequence:1,kind:'accepted',text:'Original request'}]);
 assert.deepEqual(state(p).intents.map(i=>i.sequence),[1,20]);
});

test('context snapshots deduplicate shared long intent without deleting prior review associations',()=>{
 let p=project();p.requirements='Shared intent '+ 'x'.repeat(50000);p=proposeWorkRecords(p,Array.from({length:20},(_,i)=>record('r'+i,'implementation',['block:sensor'])));
 for(let i=0;i<20;i++)p=reviewWorkContext(p,'work:r'+i,{now});
 assert.equal(state(p).snapshots.filter(s=>s.ref==='intent:project').length,1);assert.equal(state(p).bindings.length,20);assert(JSON.stringify(state(p)).length<100000);
});
test('non-JSON proposal values and UTF-8 oversized project files are refused without normalization or clipping',()=>{
 const p=project();assert.throws(()=>proposeWorkRecords(p,[record('nan','responsibility',[],{target:NaN})]),/lossless finite JSON/);
 assert.throws(()=>proposeWorkRecords(p,[record('missing','responsibility',[],{target:undefined})]),/lossless finite JSON/);
 const large=project();large.nodes=Array.from({length:70},(_,i)=>({...large.nodes[0],id:'node-'+i,data:{...large.nodes[0].data,description:'😀'.repeat(8000)}}));large.edges=[];
 assert.throws(()=>toProjectFile(large),/2 MB/);assert.equal(large.nodes[0].data.description.length,16000);
 assert.throws(()=>parseProjectFile(JSON.stringify({data:'😀'.repeat(500001)})),/2 MB/);
});

test('Design consultation receives complete native intent/proposed work with uncertainty and no internal repair text',async()=>{
 const {agentContext}=await import('../src/local-agent.mjs');let p=synchronizeEngineeringIntent(project(),'s',[{sequence:1,kind:'accepted',text:'Client wants read-only microgram readings.'},{sequence:2,kind:'accepted',origin:'automatic_repair',text:'PRIVATE-INTERNAL-REPAIR-INSTRUCTION'}]);
 p=proposeWorkRecords(p,[record('assumption','assumption',[],{owner:null,statement:'Unconfirmed volumes'}),record('requirement','requirement',[],{priority:'must',statement:'Proposed operating bound'})]);
 const output=JSON.stringify(agentContext(p));assert.match(output,/Client wants read-only microgram readings/);assert.match(output,/Unconfirmed volumes/);assert.match(output,/proposed/);assert.match(output,/not verified execution/);assert.doesNotMatch(output,/PRIVATE-INTERNAL-REPAIR-INSTRUCTION/);
 assert.equal(p.needs.length,2);assert.equal(p.decisions[0].status,'Accepted');
});

test('late project callbacks cannot contaminate another project or overwrite newer requirements',async()=>{
 const {applyArchitectureChange}=await import('../src/architecture-work.mjs');const old=project('river'),other=project('library');
 assert.strictEqual(synchronizeEngineeringIntent(other,'old-session',[{sequence:1,kind:'accepted',text:'Old private client context'}],old.id),other);
 const pending={kind:'propose',records:[record('later','implementation',['block:sensor'])]};assert.strictEqual(applyArchitectureChange(other,old.id,pending),other);
 const latest=structuredClone(old);latest.needs[0].statement='Newer user demand arrived during file read.';const next=applyArchitectureChange(latest,old.id,pending);assert.equal(next.needs[0].statement,latest.needs[0].statement);assert.equal(state(next).records.length,1);assert.deepEqual(next.nodes,latest.nodes);
});
test('recording review rejects a context that changed after the displayed source snapshot',async()=>{
 const {applyArchitectureChange,workContextIdentity}=await import('../src/architecture-work.mjs');const p=proposeWorkRecords(project(),[record('mapping','implementation',['block:sensor'])]);const change={kind:'review',ref:'work:mapping',expectedContext:workContextIdentity(p,'work:mapping')};
 const latest=structuredClone(p);latest.needs[0].statement='Changed before review applied.';assert.throws(()=>applyArchitectureChange(latest,p.id,change),/Work context changed/);assert.equal(state(latest).bindings.length,0);assert.equal(entity(applyArchitectureChange(p,p.id,change),'work:mapping').contextStatus,'current');
});
