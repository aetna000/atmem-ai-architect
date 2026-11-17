import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {historicalSection,sectionDigest,progress,readSelection} from '../../src/maintenance/model.mjs';
import {toProjectFile,fromProjectFile} from '../../src/project-file.mjs';
import {template} from '../../src/core.mjs';

test('cross-language export hashes survive JSON integer/float serialization',()=>{
 const fixture=fs.readFileSync(new URL('./fixtures/portable-section.json',import.meta.url),'utf8');
 const section=JSON.parse(fixture);assert.equal(sectionDigest(section.aggregate),section.sha256);
 const historic=historicalSection(section);assert.equal(historic.aggregate.jobs[0].status,'historical');assert.equal(historic.aggregate.jobs[0].receipts[0].status,'historical');assert.equal(sectionDigest(historic.aggregate),historic.sha256);
 const p=template('aws');p.extensions={maintenance:section};
 assert.equal(fromProjectFile(p).project.extensions.maintenance.aggregate.jobs[0].status,'historical');
 const portable=toProjectFile(p);assert.equal(portable.formatVersion,'4.0.0');
 assert.equal(fromProjectFile(portable).project.extensions.maintenanceNeedsImport,true);
 assert.throws(()=>fromProjectFile({...portable,extensions:{}}),/format 4.0.0/);
 assert.throws(()=>fromProjectFile({...portable,formatVersion:'4.1.0'}),/format 4.1.0/);
 for(const version of ['2.0.0','2.1.0','2.2.0','2.3.0']){
  const file={...toProjectFile(p),formatVersion:version};const back=fromProjectFile(file).project;
  assert.equal(back.extensions.maintenance.aggregate.jobs[0].status,'historical');assert.equal(back.nodes.length,p.nodes.length);
 }
 assert.throws(()=>historicalSection({...section,sha256:'a'.repeat(64)}));
});
test('source selection excludes sensitive files and never truncates oversize data',async()=>{
 const file=(name,text)=>({name,webkitRelativePath:'repo/'+name,size:new TextEncoder().encode(text).length,arrayBuffer:async()=>new TextEncoder().encode(text).buffer});
 const selected=await readSelection([file('main.tf','terraform {}'),file('.env','SECRET=x'),file('a.tfvars','secret=1'),file('.terraform/cache','binary'),file('.github/workflows/deploy.yml','on: push')]);
 assert.deepEqual(Object.keys(selected),['main.tf','.github/workflows/deploy.yml']);
 await assert.rejects(()=>readSelection([file('large.tf','x'.repeat(2_000_001))]),/exceeds limits/);
 await assert.rejects(()=>readSelection([file('../escape.tf','x')]),/Invalid source/);
 const bom=await readSelection([file('main.tf','\uFEFF# preserve original bytes\nterraform {}')]);
 assert.equal(bom['main.tf'].charCodeAt(0),0xFEFF);
 await assert.rejects(()=>readSelection([{name:'main.tf',webkitRelativePath:'repo/main.tf',size:2,arrayBuffer:async()=>Uint8Array.of(0xc3,0x28).buffer}]),/Invalid bytes were rejected/);
});
test('progress reports actual phases without fabricated percentages or passed warnings',()=>{
 assert.equal(progress({status:'checking',phase:'candidate',receipts:[{kind:'baseline'}]}).active,true);
 assert.equal(progress({status:'blocked',phase:'blocked'}).done,false);
 assert.equal(progress({status:'historical',phase:'historical'}).done,false);
 assert.equal(progress({status:'ready_for_review',phase:'ready_for_review'}).done,true);
 assert.equal(progress({status:'checking',phase:'control'}).label,'Confirming upgrade break');
 assert.equal(progress({status:'historical',phase:'reproduce_checks',receipts:[{kind:'candidate',status:'historical'}]}).completed.size,0);
 assert.equal(progress({status:'historical',phase:'reproduce_checks'}).label,'Imported evidence · recheck required');
});

test('folder selection retains Terraform tests for explicit unsupported checks rather than silently omitting them',async()=>{
 const text='run "acceptance" { command = plan }';
 const selected=await readSelection([{name:'acceptance.tftest.hcl',webkitRelativePath:'repo/acceptance.tftest.hcl',size:text.length,arrayBuffer:async()=>new TextEncoder().encode(text).buffer}]);
 assert.deepEqual(selected,{'acceptance.tftest.hcl':text});
});
