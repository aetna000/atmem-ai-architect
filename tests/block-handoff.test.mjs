import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createBlockHandoff,blockHandoffExportFiles} from '../src/block-handoff.mjs';
import {toProjectFile} from '../src/project-file.mjs';
import {blockSpecPath} from '../src/block-spec-kit.mjs';
const digest=text=>createHash('sha256').update(text).digest('hex');
const spec={inputs:'Correlated request',outputs:'Durable receipt',behavior:'Accept exactly once',failures:'Reconcile ambiguous timeout',implementation:'Choose runtime in destination',infrastructure:'Portable transactional store',operations:'Restore and audit',tests:'Race duplicates',scenarios:[{name:'Accept',steps:[{sender:'Client',receiver:'Journal',action:'Submit request'}]}]};
const node=(id,parentBlockId)=>({id,type:'resource',position:{x:0,y:0},data:{label:id,kind:'resource',provider:'tools',origin:'proposed',buildSpec:structuredClone(spec),...(parentBlockId?{parentBlockId}:{})}});
function source(){return JSON.stringify(toProjectFile({id:'journal',name:'Research journal',version:1,revision:4,provider:'tools',nodes:[node('System'),node('Journal','System'),node('Receipts','Journal'),node('Search','System')],edges:[{id:'lookup',source:'Search',target:'Journal',label:'Read receipt',interfaceSpec:{transport:'Versioned RPC',input:'Receipt ID',output:'Receipt or missing',authorization:'Tenant-bound reader',failure:'Bounded retry',verification:'Cross-tenant denial'}}],needs:[]}));}
test('external handoff scopes nested modules and independently hashes all exported files',()=>{
 const raw=source(),before=JSON.parse(raw),handoff=createBlockHandoff(raw,'Journal');
 assert.deepEqual(handoff.blockIds,['Journal','Receipts']);
 assert.equal(handoff.sourceSha256,digest(raw));
 assert.equal(handoff.files['source-context.json'],raw);
 assert.equal(handoff.files['project.atmem-ai-architect.json'],undefined,'One exact source snapshot, without an unused duplicate');
 assert.match(handoff.files['SYSTEM_START_HERE.md'],/source-context\.json is the editable source snapshot/);
 assert.match(JSON.parse(handoff.files['spec-kit/tasks.json']).tasks.find(task=>task.id==='TASK-SCOPE').steps[0],/source-context\.json/);
 for(const id of ['Journal','Receipts'])for(const file of ['spec.md','plan.md','tasks.json','testing.md','infrastructure-devops.md','WORK_ORDER.md','1-sequence.mmd','1-events.mmd','1-functional.mmd'])assert.ok(handoff.files[blockSpecPath(id)+'/'+file],file);
 assert.equal(handoff.files[blockSpecPath('Search')+'/WORK_ORDER.md'],undefined);
 for(const value of ['Versioned RPC','Receipt ID','Receipt or missing','Tenant-bound reader','Bounded retry','Cross-tenant denial'])assert.ok(handoff.files[blockSpecPath('Journal')+'/spec.md'].includes(value));
 const files=blockHandoffExportFiles(handoff),manifest=JSON.parse(files['handoff-manifest.json']);
 for(const [name,receipt]of Object.entries(manifest.files)){assert.equal(receipt.sha256,digest(files[name]));assert.equal(receipt.bytes,Buffer.byteLength(files[name]));}
 assert.equal(manifest.implementationExecuted,false);assert.equal(manifest.deploymentExecuted,false);
 assert.equal(JSON.parse(files['handoff-readiness.json']).status,'design_documented');
 assert.deepEqual(JSON.parse(raw),before);
});

test('immutable authored references keep their exact project alias and generated source overrides cannot mismatch the project',async()=>{
 const raw=JSON.parse(source()),content='Read [the project](project.atmem-ai-architect.json).\n';
 raw.extensions.architectureDocuments={version:1,artifactId:'native-capture',draftSha256:'b'.repeat(64),contextSha256:'c'.repeat(64),files:[{path:'README.md',content,sha256:digest(content)}]};
 const text=JSON.stringify(raw),handoff=createBlockHandoff(text,'Journal');assert.equal(handoff.files['NATIVE_DESIGN.md'],content);assert.equal(handoff.files['project.atmem-ai-architect.json'],text);
 const {deliveryPack}=await import('../src/delivery.mjs'),{parseProjectFile}=await import('../src/project-file.mjs'),project=parseProjectFile(text).project;
 const wrong=JSON.parse(text);wrong.meta.name='Another project';assert.throws(()=>deliveryPack(project,null,'local',new Date(),{sourceSnapshotContent:JSON.stringify(wrong)}),/snapshot differs/);
});
test('draft handoff exposes incomplete specs, missing scenarios and undeclared interfaces',()=>{
 const data=JSON.parse(source());delete data.design.nodes[1].data.buildSpec;
 delete data.design.edges[0].interfaceSpec;
 const handoff=createBlockHandoff(JSON.stringify(data),'Journal'),readiness=JSON.parse(handoff.files['handoff-readiness.json']);
 assert.equal(readiness.status,'incomplete_design');assert.equal(readiness.missingSections.length,9);assert.deepEqual(readiness.openInterfaces,['lookup']);
 assert.throws(()=>createBlockHandoff(source(),'missing'),/existing architecture block/);
});

test('scoped handoffs preserve every captured authored document named by the receiving receipt',()=>{
 const raw=JSON.parse(source());const names=['README.md','architecture.coverage.md','architecture.review.md','docs/contract.md','specs/module/spec.md'];
 raw.extensions.architectureDocuments={version:1,artifactId:'native-capture',draftSha256:'b'.repeat(64),contextSha256:'c'.repeat(64),files:names.map(path=>{const content='# '+path+'\nExact reviewed architecture evidence.\n';return {path,content,sha256:digest(content)};})};
 const handoff=createBlockHandoff(JSON.stringify(raw),'Journal'),receipt=JSON.parse(handoff.files['design-documents-receipt.json']);
 for(const file of receipt.files){assert.equal(typeof handoff.files[file.exportPath],'string','Missing authored evidence '+file.exportPath);assert.equal(digest(handoff.files[file.exportPath]),file.sha256);}
});
