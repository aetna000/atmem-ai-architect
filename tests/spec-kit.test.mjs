import test from 'node:test';
import assert from 'node:assert/strict';
import {deliveryPack} from '../src/delivery.mjs';
const node=(id,label,provider='aws',origin='proposed')=>({id,type:'resource',position:{x:0,y:0},data:{label,provider,origin,kind:'resource',description:`Responsibility for ${label}`,config:{region:'To be selected',classification:'Internal',timeout:5000}}});
const project=()=>({id:'kit',version:1,revision:3,name:'Knowledge assistant',provider:'aws',requirements:'Answer employee questions with sources',nodes:[node('files','Amazon S3'),node('model','Amazon Bedrock')],edges:[{id:'read',source:'files',target:'model',label:'approved document chunks'}],needs:[{id:'need-1',statement:'Answer only from authorized documents',kind:'functional',category:'security',source:'user',status:'open',priority:'must',links:['files','model']},{id:'need-2',statement:'Response target to agree',kind:'nonfunctional',category:'performance',source:'agent',status:'open',priority:'should',links:[]}],extensions:{requirementNumbers:{'need-1':1,'need-2':2}},decisions:[],assumptions:[],openQuestions:[{id:'q1',question:'Which users need access?',status:'open'}]});
function tasks(p){return JSON.parse(deliveryPack(p,null)['spec-kit/tasks.json']).tasks;}

test('kit covers every component, edge and requirement without changing source requirements',()=>{
 const p=project(),before=JSON.stringify(p),files=deliveryPack(p,null),list=JSON.parse(files['spec-kit/tasks.json']).tasks;
 assert.equal(JSON.stringify(p),before);
 assert.equal(list.filter(t=>t.phase==='Components').length,2);
 assert.equal(list.filter(t=>t.phase==='Contracts').length,1);
 assert.equal(list.filter(t=>t.phase==='Integration').length,1);
 assert.equal(list.filter(t=>t.phase==='Acceptance').length,2);
 for(const t of list){assert.equal(t.status,'todo');assert.ok(t.steps.length>=3);assert.ok(t.outputs.length);assert.ok(t.acceptance.length);}
 assert.match(files['spec-kit/questions.md'],/Confirm REQ-002/);assert.match(files['spec-kit/questions.md'],/Confirm cloud provider/);
 assert.match(files['spec-kit/context.json'],/Proposed; needs confirmation/);
 assert.match(files['specification.md'],/Implementation specification and coding-agent handoff/);
 const manifest=JSON.parse(files['manifest.json']);assert.equal(JSON.parse(files['spec-kit/tasks.json']).snapshotId,manifest.snapshotId);
 assert.deepEqual(manifest.files.sort(),Object.keys(files).sort());
 assert.match(files['AGENTS.md'],/No exported artifact proves deployment/);
});
test('task dependencies form an executable DAG even if the diagram has cycles',()=>{
 const p=project();p.edges.push({id:'reply',source:'model',target:'files',label:'cited answer'});
 const list=tasks(p),done=new Set();
 while(done.size<list.length){const ready=list.filter(t=>!done.has(t.id)&&t.dependsOn.every(id=>done.has(id)));assert.ok(ready.length,'must have an actionable task');ready.forEach(t=>done.add(t.id));}
 assert.equal(new Set(list.map(t=>t.id)).size,list.length);
});
test('task IDs survive reorder and rename; regenerated tasks follow new scope',()=>{
 const p=project(),before=tasks(p).map(t=>t.id).sort();p.nodes.reverse();p.nodes[0].data.label='Renamed model';
 assert.deepEqual(tasks(p).map(t=>t.id).sort(),before);
 const files=deliveryPack(p,null);assert.match(files['spec-kit/tasks.md'],/Renamed model/);
 p.nodes.push(node('new','New API'));assert.equal(tasks(p).filter(t=>t.phase==='Components').length,3);
});
test('all clouds and existing systems retain honest implementation boundaries',()=>{
 for(const provider of ['aws','azure','gcp','ibm']){
  const p=project();p.nodes=[node('existing','Existing documents',provider,'existing'),node('new','Cloud runtime',provider)];p.edges=[];
  const list=tasks(p),existing=list.find(t=>t.phase==='Components'&&t.componentIds.includes('existing'));
  assert.match(existing.steps.join(' '),/do not recreate/);
  assert.match(list.find(t=>t.phase==='Components'&&t.componentIds.includes('new')).steps.join(' '),/has not generated this implementation/);
 }
});
test('empty project creates clarification work, not invented cloud components',()=>{
 const p=project();p.nodes=[];p.edges=[];p.needs=[];
 const files=deliveryPack(p,null),list=JSON.parse(files['spec-kit/tasks.json']).tasks;
 assert.equal(list.filter(t=>t.phase==='Components').length,0);assert.match(files['spec-kit/questions.md'],/Define the system components/);
});
