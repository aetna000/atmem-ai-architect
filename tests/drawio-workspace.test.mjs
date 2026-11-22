import assert from 'node:assert/strict';
import test from 'node:test';
import {boardGraph,drawioFile,graphMermaid} from '../src/drawio-model.mjs';
import {drawioHandoffFiles} from '../src/drawio-handoff.mjs';
import {addDiagram,diagramCatalogue,diagramProjection,emptyDiagramModel,validateDiagramModel} from '../src/architecture-diagrams.mjs';
import {architectureGraph} from '../src/architecture-diagram-geometry.mjs';
import {applyMermaidPage} from '../src/mermaid-page.mjs';

test('native Board and all 28 architecture pages export in one editable document',()=>{
  const project={name:'Eligibility & intake',nodes:[
    {id:'intake',position:{x:10,y:20},data:{label:'Record "request"',kind:'source',provider:'tools'}},
    {id:'review',position:{x:265,y:20},data:{label:'Authorise <review>',kind:'guard',provider:'tools'}},
  ],edges:[{id:'review-wire',source:'intake',target:'review',label:'Check & record'}]};
  let model=emptyDiagramModel();
  for(const kind of diagramCatalogue)model=addDiagram(model,kind.id,kind.title,true).model;
  const files=drawioHandoffFiles(project,model);
  const native=files['architecture.drawio'];
  assert.equal((native.match(/<diagram /g)||[]).length,29);
  assert.match(native,/source="atmem-intake" target="atmem-review"/);
  assert.match(native,/Check &amp; record/);
  assert.match(native,/Authorise &lt;review&gt;/);
  assert.equal(Object.keys(files).filter(path=>path.endsWith('.mmd')).length,29);
  assert.match(graphMermaid(boardGraph(project.nodes,project.edges),{selected:'review-wire'}),/n1 -->\|"Check #38; record"\| n2/);
  assert.equal(drawioFile([]),'<mxfile host="AtMem Architect"></mxfile>\n');
});

test('editing Mermaid keeps shared record identity and technical details, and removes only page membership',()=>{
  const {model,view}=addDiagram(emptyDiagramModel(),'sequence','Eligibility',true);
  const [first,second]=view.elementIds;
  const wire=model.relations[0];
  model.elements[1].details=[{name:'Responsibility',value:'Check tenant access'}];
  model.elements[1].source='Scope §4';
  model.views.push({...view,id:'other-view',name:'Shared journey'});
  const scene=architectureGraph(diagramProjection(model,view),view);
  const proposed=applyMermaidPage(model,{timeline:true,nodes:[{id:'n1',name:'Caller'},{id:'n2',name:'Eligibility service'}],
    edges:[{from:'n1',to:'n2',name:'Check eligibility',kind:'call'}]},{view,scene});
  assert.deepEqual(proposed.view.elementIds,[first,second]);
  assert.equal(proposed.model.relations[0].id,wire.id);
  assert.equal(proposed.model.elements[1].details[0].value,'Check tenant access');
  assert.equal(proposed.model.elements[1].source,'Scope §4');
  const changedScene=architectureGraph(diagramProjection(proposed.model,proposed.view),proposed.view);
  const removed=applyMermaidPage(proposed.model,{timeline:true,nodes:[{id:'n1',name:'Caller'}],edges:[]},{view:proposed.view,scene:changedScene});
  assert.deepEqual(removed.view.elementIds,[first]);
  assert.deepEqual(removed.model.views[1].elementIds,[first,second]);
  assert.equal(removed.model.relations.length,1);
  assert.throws(()=>applyMermaidPage(model,{timeline:true,nodes:[{id:'n1',name:'Caller'}],
    edges:[{from:'n1',to:'missing',name:'Broken'}]},{view,scene}),/two elements/);
  assert.throws(()=>validateDiagramModel({...model,views:[{...view,drawioShapes:{[first]:'untrusted-scheme'}}]}),/Invalid diagram shape/);
});

test('editable cells carry the named block properties without changing labels or losing wire endpoints',()=>{
  const input='Validate "referral" & tenant\nCheck access';
  const project={nodes:[{id:'referral',position:{x:0,y:0},data:{kind:'source',label:'Referral',
    buildSpec:{inputs:input,failures:'Queue for review'},drawingFill:'#efddee'}},
    {id:'review',position:{x:300,y:0},data:{kind:'guard',label:'Review'}}],
    edges:[{id:'review-edge',source:'referral',target:'review'}]};
  const {vertices}=boardGraph(project.nodes,project.edges);
  assert.deepEqual(vertices[0].properties,{inputs:input,failures:'Queue for review'});
  const file=drawioHandoffFiles(project)['architecture.drawio'];
  assert.match(file,/<object id="atmem-referral" label="Referral" inputs="Validate &quot;referral&quot; &amp; tenant&#10;Check access" failures="Queue for review">/);
  assert.match(file,/fillColor=#efddee/);
  assert.match(file,/source="atmem-referral" target="atmem-review"/);
  assert.doesNotMatch(file,/inputs="undefined"/);
});

test('selection and callback changes reuse geometry; content and position changes invalidate it',async()=>{
 const {boardSceneKey}=await import('../src/drawio-model.mjs');
 const nodes=[{id:'a',selected:false,position:{x:0,y:0},data:{label:'Intake',onOpen:()=>{}}}];
 const key=boardSceneKey(nodes,[]);
 assert.equal(boardSceneKey([{...nodes[0],selected:true,data:{...nodes[0].data,onOpen:()=>{}}}],[]),key);
 assert.notEqual(boardSceneKey([{...nodes[0],data:{label:'Changed responsibility'}}],[]),key);
 assert.notEqual(boardSceneKey([{...nodes[0],position:{x:100,y:0}}],[]),key);
 assert.notEqual(boardSceneKey(nodes,[{id:'wire',source:'a',target:'b'}]),key);
});
