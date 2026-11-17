import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {template,validateImport} from '../src/core.mjs';
import {toProjectFile,fromProjectFile,reviewDesignSnapshot,reviewDesignContent} from '../src/project-file.mjs';
import {createHash} from 'node:crypto';
import {withConversation} from '../src/conversation.mjs';
import {architectureSources} from '../src/architecture-work.mjs';

const project=()=>({...template('aws'),id:'rules-binding-project',createdAt:'2026-11-18T00:00:00Z'});
test('navigation acknowledgements preserve review binding; actual design/rule edits invalidate it without mutation',()=>{
 const p=project();p.estimate={details:[],usage:{},prices:{}};p.extensions={journey:{review:'2-a-b'}};
 const original=JSON.stringify(p),snapshot=reviewDesignSnapshot(p);
 assert.equal(JSON.stringify(p),original);
 const navigated=structuredClone(p);navigated.extensions.journey.delivery='2-c-d';assert.deepEqual(reviewDesignSnapshot(navigated),snapshot);
 navigated.requirements='New requirement';assert.notDeepEqual(reviewDesignSnapshot(navigated),snapshot);
 const changed=structuredClone(p);changed.extensions.architecturePolicy={content:'Changed approved rules',revision:'b'.repeat(64)};
 assert.notDeepEqual(reviewDesignSnapshot(changed),snapshot);
});
test('saved native design and UI have the same reviewed snapshot across a receiving reopen',()=>{
 const p=project(),saved=toProjectFile(p),reopened=fromProjectFile(saved).project;
 assert.deepEqual(reviewDesignSnapshot(p),reviewDesignSnapshot(reopened));
});
test('approved rule edits change the existing shared dependency source without a second project graph',()=>{
 const p=project();p.extensions={architecturePolicy:{revision:'a'.repeat(64),content:'Approved original rules'}};
 const before=architectureSources(p).find(s=>s.id==='intent:project');
 p.extensions.architecturePolicy={revision:'b'.repeat(64),content:'Revised approved rules'};
 const after=architectureSources(p).find(s=>s.id==='intent:project');
 assert.notDeepEqual(before.value,after.value);
 assert.ok(architectureSources(p).find(s=>s.id==='block:'+p.nodes[0].id).dependsOn.includes('intent:project'));
});
test('browser and server renderer bind identical bytes even for tiny prices and large numeric values',()=>{
 const p=project();p.extensions={tinyPrice:1e-7,largeCount:1e21};
 const rendered=spawnSync(process.execPath,['scripts/terraform-render.mjs'],{input:JSON.stringify({project:p,environment:'staging',review:true}),encoding:'utf8',maxBuffer:8_000_000});
 assert.equal(rendered.status,0,rendered.stderr);
 assert.equal(JSON.parse(rendered.stdout).designSha256,createHash('sha256').update(reviewDesignContent(p)).digest('hex'));
});
test('native coding handoff includes the same specification IDs, infrastructure and approved rule snapshot',()=>{
 const p=project();p.extensions={architecturePolicy:{revision:'a'.repeat(64),recordId:'rec_fixture',content:'---\nschema: atmem-architecture/v1\n---\n'}};
 const result=spawnSync(process.execPath,['scripts/engineering-handoff.mjs'],{input:JSON.stringify(toProjectFile(p)),encoding:'utf8'});
 assert.equal(result.status,0,result.stderr);const files=JSON.parse(result.stdout);
 assert.equal(files['architecture.md'],p.extensions.architecturePolicy.content);
 assert.equal(JSON.parse(files['spec-kit/architecture-rules.json']).revision,p.extensions.architecturePolicy.revision);
 const tasks=JSON.parse(files['spec-kit/tasks.json']);assert.ok(tasks.tasks.length>0);
 assert.ok(Object.keys(files).some(p=>p.startsWith('terraform/')&&p.endsWith('.tf.json')));
});
test('current specification task snapshots drain their full pipe output for larger specifications',()=>{
 const p=project();p.needs=Array.from({length:35},(_,i)=>({id:'requirement-'+i,statement:'Preserve this distinct required behavior '+i+'. '+('Retain the documented contract. '.repeat(10)),priority:'must',kind:'functional',source:'user',status:'Accepted',links:[p.nodes[0].id]}));
 const input=JSON.stringify(toProjectFile(p));
 const result=spawnSync(process.execPath,['scripts/engineering-handoff.mjs','--tasks-only'],{input,encoding:'utf8',maxBuffer:8_000_000});
 assert.equal(result.status,0,result.stderr);assert.ok(result.stdout.length>65536);
 const snapshot=JSON.parse(result.stdout);assert.equal(snapshot.contextSha256.length,64);
 assert.ok(snapshot.tasks.tasks.some(task=>task.requirementIds?.includes('requirement-34')));
});

test('live price coverage and provenance survive receiving reload and server review normalization',()=>{
 const p=project();const evidence={coverageIncomplete:true,planningReference:false,sourceSha256:'a'.repeat(64),hourlyPrice:0.02,hoursPerMonth:730};
 p.estimate={projectSize:'small',usage:{},prices:{'block-0':{price:14.6,currency:'USD',source:'Provider rate',url:'https://example.com/rate',date:'2026-11-18',note:'Storage only',region:'us-east-1',service:'S3',...evidence}},details:[{id:'compute',componentId:'block-0',description:'Compute',quantity:1,unit:'hours',price:0.02,currency:'USD',source:'Provider rate',url:'https://example.com/rate',date:'2026-11-18',note:'Compute only',region:'us-east-1',service:'Compute',...evidence}]};
 const normalized=validateImport(p);assert.equal(normalized.estimate.prices['block-0'].coverageIncomplete,true);assert.equal(normalized.estimate.details[0].sourceSha256,evidence.sourceSha256);
 assert.deepEqual(reviewDesignSnapshot(p),reviewDesignSnapshot(normalized));
 assert.deepEqual(reviewDesignSnapshot(p),reviewDesignSnapshot(fromProjectFile(toProjectFile(p)).project));
});

test('saving the actual engineering handoff with conversation preserves reviewed design identity',()=>{
 const p=project();p.extensions={architecturePolicy:{content:'approved rules',revision:'a'.repeat(64)}};
 const saved=toProjectFile(withConversation(p,[{role:'user',text:'Where are we?'}]));
 assert.equal(reviewDesignContent(p),reviewDesignContent(fromProjectFile(saved).project));
 const changed=structuredClone(p);changed.requirements='A newly accepted requirement';
 assert.notEqual(reviewDesignContent(changed),reviewDesignContent(p));
});
