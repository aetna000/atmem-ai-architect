import assert from 'node:assert/strict';
import test from 'node:test';
import {addDiagram,appendDiagramProposal,diagramCatalogue,diagramProjection,emptyDiagramModel,validateDiagramModel} from '../src/architecture-diagrams.mjs';
import {architectureDiagramHandoff} from '../src/architecture-diagram-handoff.mjs';
import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';

const record=(id,kind,name=id,details=[])=>({id,name,kind,basis:'proposed',source:'',details});
const relation=(id,kind,from,to,details=[])=>({...record(id,kind,id,details),from,to});
const view=(kind,elementIds=[],relationIds=[],gaps=[])=>({id:'view-'+kind,name:kind,kind,elementIds,relationIds,gaps});

test('all 28 types can be authored and round-tripped in an editable project',()=>{
  let model=emptyDiagramModel();
  for(const type of diagramCatalogue)model=addDiagram(model,type.id,type.title,true).model;
  validateDiagramModel(model,{complete:true});
  const project={id:crypto.randomUUID(),name:'Clinic referral',version:1,revision:1,nodes:[],edges:[],
    provider:'aws',requirements:'Referrals with audited status',extensions:{architectureDiagrams:model}};
  assert.deepEqual(fromProjectFile(toProjectFile(project)).project.extensions.architectureDiagrams,model);
  assert.equal(new Set(model.views.map(row=>row.kind)).size,28);
  for(const row of model.views)assert.ok(diagramProjection(model,row).nodes.length);
});

test('shared identity survives a rename, and positions belong to one view',()=>{
  const actor=record('patient','actor','Patient');
  const system=record('clinic','system','Clinic referral');
  const component=record('referral-api','component','Referral API');
  const proposal={...emptyDiagramModel(),elements:[actor,system,component],views:diagramCatalogue.map(({id})=>
    id==='context'?view(id,[actor.id,system.id]):id==='sequence'?view(id,[actor.id,component.id]):view(id,[],[],['Confirm scope.']))};
  const merged=appendDiagramProposal(emptyDiagramModel(),proposal);
  const pinned={...merged,views:merged.views.map(row=>row.kind==='context'?{...row,positions:{patient:{x:120,y:20}}}:row),
    elements:merged.elements.map(row=>row.id===actor.id?{...row,name:'Referring patient'}:row)};
  validateDiagramModel(pinned);
  const sequence=pinned.views.find(row=>row.kind==='sequence');
  assert.equal(diagramProjection(pinned,sequence).nodes[0].name,'Referring patient');
  assert.equal(sequence.positions,undefined);
  assert.match(architectureDiagramHandoff('Referral',2,pinned),/Referring patient/);
});

test('reject hidden endpoints, ownership cycles and a partial generated set',()=>{
  const model={...emptyDiagramModel(),elements:[record('x','package'),record('y','package')],
    relations:[relation('depx','dependency','x','y')],views:[view('package',['x'],['depx'])]};
  assert.throws(()=>validateDiagramModel(model),/hidden endpoint/);
  model.views[0].elementIds.push('y');
  assert.throws(()=>validateDiagramModel(model,{complete:true}),/28/);
  validateDiagramModel(model);
  model.elements[0].parentId='y';
  model.elements[1].parentId='x';
  assert.throws(()=>validateDiagramModel(model),/cycle/);
});

test('cycles, missing process boundaries and incompatible routes produce review items',()=>{
  const elements=[record('web','package'),record('core','package'),record('external','actor'), record('db','store'),
    record('route','route','Route',[{name:'Method',value:'GET'},{name:'Path',value:'/referrals'}]),
    record('create','operation','Create referral',[{name:'Method',value:'POST'},{name:'Path',value:'/referrals'}])];
  const relations=[relation('p-to-c','dependency','web','core'),relation('c-to-p','dependency','core','web'),
    relation('raw','data-flow','external','db'),relation('route-match','routes-to','route','create')];
  const views=[view('package',['web','core'],['p-to-c','c-to-p']),view('data-flow',['external','db'],['raw']),view('api',['route','create'],['route-match'])];
  const model=validateDiagramModel({version:1,elements,relations,views});
  assert.match(diagramProjection(model,views[0]).diagnostics.join(),/Cycle/);
  assert.match(diagramProjection(model,views[1]).diagnostics.join(),/through a process/);
  assert.match(diagramProjection(model,views[2]).diagnostics.join(),/matching route method/);
});
