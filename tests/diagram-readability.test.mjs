import test from 'node:test';
import assert from 'node:assert/strict';
import {compactNodeLabel,wrapDiagramText,diagramReferenceRows} from '../src/diagram-labels.mjs';
import {architectureGraph} from '../src/architecture-diagram-geometry.mjs';
import {graphMermaid,drawioFile} from '../src/drawio-model.mjs';
import {diagramCatalogue,diagramProjection,addDiagram,emptyDiagramModel} from '../src/architecture-diagrams.mjs';

test('long unbroken names, Unicode and paragraphs wrap without losing characters',()=>{
 const source='Clinical eligibility確認'.repeat(12)+'\nA second paragraph';
 const lines=wrapDiagramText(source,28);assert.ok(lines.every(l=>Array.from(l).length<=28));
 assert.equal(lines.join('').replace(/\s/g,''),source.replace(/\s/g,''));
});
test('every notation keeps full property and relationship content outside its compact labels',()=>{
 for(const type of diagramCatalogue){
  const {model,view}=addDiagram(emptyDiagramModel(),type.id,type.title,true);
  if(!view.elementIds.length)continue;
  const node=model.elements.find(n=>n.id===view.elementIds[0]),full='Confirm tenant consent and record the clinical result before exchanging identifiable data. '.repeat(7);
  node.details.push({name:'Clinical requirement',value:full});
  const scene=architectureGraph(diagramProjection(model,view),view),shown=scene.vertices.find(v=>v.id===node.id);
  assert.ok(shown.detailBody.includes(full),type.id+' retains the complete property');
  assert.ok(shown.body.split('\n').every(l=>l.length<=45),type.id+' explicit wrapped lines');
  assert.ok(scene.wires.every((w,i)=>w.body===String(i+1)),type.id+' numbered connectors');
  assert.deepEqual(diagramReferenceRows(scene).map(r=>r.recordId),scene.wires.map(w=>w.recordId||w.id));
  assert.match(drawioFile([{id:view.id,name:view.name,...scene}]),/atmemRecord=/);
 }
});
test('compact labels do not replace full names in element Mermaid or erase parallel messages',()=>{
 const nodes=[{id:'patient',name:'Patient consent and eligibility portal',kind:'actor',details:[]},{id:'clinic',name:'Clinical review service',kind:'component',details:[{name:'Policy',value:'Never send identifiable data without consent'}]}];
 const edges=[1,2].map(i=>({id:'exchange-'+i,from:'patient',to:'clinic',name:'Check consent and eligibility '+i,kind:'call',details:[{name:'Timeout',value:'Hold pending manual review'}]}));
 const scene=architectureGraph({type:{layout:'timeline'},nodes,edges,parentOf:()=>undefined},{kind:'sequence'});
 assert.deepEqual(scene.wires.map(w=>w.body),['1','2']);assert.equal(diagramReferenceRows(scene).length,2);
 assert.match(graphMermaid(scene,{timeline:true}),/Check consent and eligibility 2/);
 assert.ok(scene.wires[0].detailBody.includes('Hold pending manual review'));
 assert.equal(nodes[0].name,'Patient consent and eligibility portal');
 assert.ok(compactNodeLabel('Short title','Component').height>=96);
});

test('the router transfers to clinical integrations and rejects trapped overlapping ports',async()=>{
 const {routeDiagramWires}=await import('../src/diagram-routing.mjs');
 const vertices=[{id:'clinic',x:0,y:0,width:160,height:90},{id:'pharmacy',x:600,y:0,width:160,height:90},{id:'private-store',x:260,y:-30,width:200,height:170}];
 const wires=[{id:'rx',source:'clinic',target:'pharmacy',style:''}];
 const routed=routeDiagramWires({vertices,wires});assert.ok(routed.wires[0].points.length>=4);assert.ok(!routed.wires[0].routingIssue);
 const route=routed.wires[0].points;assert.ok(route.some(p=>p.y<=-48||p.y>=158),'route goes around the store');
 const trapped=routeDiagramWires({vertices:[vertices[0],{...vertices[1],x:70},vertices[2]],wires});
 assert.ok(trapped.wires[0].routingIssue,'an obstructed port cannot silently pass');
});
test('presentation changes round-trip independently of semantic properties and reject invalid dimensions',async()=>{
 const {applyDrawingLayout,updateDrawingLayout,validateDrawingLayouts}=await import('../src/drawing-layout.mjs');
 const {toProjectFile,parseProjectFile}=await import('../src/project-file.mjs');
 const properties='A complete clinic safety contract';
 let layout=updateDrawingLayout(undefined,'board',[{id:'clinic',x:90,y:70,width:320,height:150,rotation:30}]);
 const scene={vertices:[{id:'clinic',name:'Clinic',body:'Clinic',detailBody:properties,x:0,y:0,width:200,height:100,style:''}],wires:[]};
 const shown=applyDrawingLayout(scene,layout.pages.board);assert.equal(shown.vertices[0].rotation,30);assert.equal(shown.vertices[0].detailBody,properties);assert.equal(scene.vertices[0].x,0);
 const p={id:'clinic-layout',version:1,revision:1,name:'Clinic',provider:'tools',nodes:[],edges:[],extensions:{drawingLayouts:layout}};
 assert.deepEqual(parseProjectFile(JSON.stringify(toProjectFile(p))).project.extensions.drawingLayouts,layout);
 assert.throws(()=>updateDrawingLayout(layout,'board',[{id:'clinic',width:-1}]),/limits/);
 assert.throws(()=>validateDrawingLayouts({version:1,pages:{board:{clinic:{rotation:Infinity}}}}),/limits/);
 assert.equal(updateDrawingLayout(layout,'board',null).pages.board,undefined);
});

test('rotated clinical nodes route around their painted bounds and timeline layout edits do not mutate their baseline',async()=>{
 const {routeDiagramWires}=await import('../src/diagram-routing.mjs');
 const {applyDrawingLayout}=await import('../src/drawing-layout.mjs');
 const scene={vertices:[{id:'a',x:0,y:0,width:200,height:100,rotation:30},{id:'b',x:700,y:0,width:200,height:100},{id:'c',x:300,y:-30,width:180,height:150,rotation:45}],wires:[{id:'w',source:'a',target:'b',style:''}]};
 assert.ok(!routeDiagramWires(scene).wires[0].routingIssue);
 const timeline={timeline:true,vertices:[{id:'a',body:'Caller',x:0,y:0,width:200,height:100,style:''},{id:'@lifeline-a',x:100,y:100,width:1,height:300,selectable:false}],wires:[]};
 const before=structuredClone(timeline);applyDrawingLayout(timeline,{a:{x:80,y:20,width:250,height:120,rotation:0}});assert.deepEqual(timeline,before);
});

test('a moved derived port changes sides, nested moves stay absolute, and group frames follow members',async()=>{
 const {routeDiagramWires}=await import('../src/diagram-routing.mjs');
 const {applyDrawingLayout,movedDrawingCell}=await import('../src/drawing-layout.mjs');
 const initial=routeDiagramWires({vertices:[{id:'a',x:0,y:0,width:160,height:100},{id:'b',x:500,y:0,width:160,height:100}],wires:[{id:'link',source:'a',target:'b',style:''}]});
 assert.match(initial.wires[0].style,/exitX=1;/);
 const moved=routeDiagramWires({...initial,vertices:initial.vertices.map(v=>v.id==='a'?{...v,x:900}:v)});
 assert.match(moved.wires[0].style,/exitX=0;/);assert.equal((moved.wires[0].style.match(/exitX=/g)||[]).length,1);
 assert.deepEqual(movedDrawingCell({id:'child',offset:{x:300,y:150}},{x:450,y:250}),{id:'child',x:450,y:250});
 assert.deepEqual(movedDrawingCell({id:'child',offset:{x:300,y:150}},{x:450,y:250},{absolute:false}),{id:'child',x:150,y:100});
 const scene={vertices:[{id:'frame',memberIds:['owner','child'],selectable:false,x:0,y:0,width:500,height:500},{id:'owner',body:'Owner',x:10,y:10,width:160,height:100},{id:'child',body:'Child',x:10,y:200,width:160,height:100}],wires:[]};
 const changed=applyDrawingLayout(scene,{child:{x:900,y:700}}),frame=changed.vertices[0];assert.ok(frame.x+frame.width>=1060&&frame.y+frame.height>=800);assert.equal(scene.vertices[0].width,500);
});
test('an invisible canvas is deferred rather than passing a readability gate',async()=>{
 const {inspectDiagramReadability}=await import('../src/diagram-readability.mjs');
 const result=inspectDiagramReadability({getModel:()=>({}),container:{getClientRects:()=>[],clientWidth:0,clientHeight:0}},{vertices:[],wires:[]});
 assert.equal(result.passed,false);assert.equal(result.deferred,true);
});

test('editable diagrams carry the verified connector waypoints and numeric label offsets',()=>{
 const scene={id:'clinic',name:'Clinical handoff',vertices:[{id:'a',body:'Clinic',name:'Clinic',x:0,y:0,width:200,height:100,style:''},{id:'b',body:'Pharmacy',name:'Pharmacy',x:500,y:0,width:200,height:100,style:''}],wires:[{id:'rx',source:'a',target:'b',body:'1',reference:'1',detailBody:'Confirm consent before dispensing',labelOffset:{x:6.5,y:-12},points:[{x:260,y:55},{x:400,y:55}],style:''}]};
 const xml=drawioFile([scene]);assert.match(xml,/<mxPoint x="6.5" y="-12" as="offset"\/>/);assert.match(xml,/<mxPoint x="260" y="55"\/>/);assert.match(xml,/atmemDescription="Confirm consent before dispensing"/);assert.match(xml,/source="atmem-a" target="atmem-b"/);
});

test('readable initial focus selects connected context instead of an isolated first card',async()=>{
 const {readableDiagramFocus}=await import('../src/diagram-focus.mjs');
 const node=(id,x,y)=>({id,x,y,width:200,height:90});
 const scene={vertices:[node('isolated',0,0),node('clinic',2000,0),node('review',2300,0),node('pharmacy',2600,0)],wires:[{source:'clinic',target:'review'},{source:'review',target:'pharmacy'}]};
 assert.equal(readableDiagramFocus(scene,900,400).id,'review');
 assert.equal(readableDiagramFocus({...scene,timeline:true},900,400).id,'isolated');
});
