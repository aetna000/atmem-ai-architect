import test from 'node:test';
import assert from 'node:assert/strict';
import {boardGraph,drawioFile} from '../src/drawio-model.mjs';
import {nestDrawingScene,containerDescendants,nativeLayoutChanges} from '../src/drawing-containment.mjs';
import {applyDrawingLayout} from '../src/drawing-layout.mjs';
import {architectureGraph} from '../src/architecture-diagram-geometry.mjs';
import {addDiagram,emptyDiagramModel,diagramProjection} from '../src/architecture-diagrams.mjs';
for(const domain of ['Archive','Equipment'])test(domain+' containment preserves records, wiring and editable export',()=>{
 const node=(id,parent)=>({id,position:{x:0,y:0},data:{kind:'resource',label:domain+' '+id,...(parent?{parentBlockId:parent}:{})}});
 const nodes=[node('a'),node('b','a'),node('c','b'),node('d','a'),node('external')],edges=[{id:'cross',source:'c',target:'external',label:'Publish'},{id:'internal',source:'c',target:'d',label:'Check'}];
 const original=structuredClone({nodes,edges}),scene=boardGraph(nodes,edges),byId=new Map(scene.vertices.map(v=>[v.id,v]));
 assert.deepEqual({nodes,edges},original);assert.deepEqual(scene.wires.map(w=>[w.source,w.target]),edges.map(e=>[e.source,e.target]));
 for(const v of scene.vertices){const p=byId.get(v.containerParentId);if(!p)continue;assert.ok(v.x>p.x&&v.y>=p.y+p.headerHeight);assert.ok(v.x+v.width<p.x+p.width&&v.y+v.height<p.y+p.height);}
 assert.deepEqual(containerDescendants(scene.vertices,'a').map(v=>v.id),['b','c','d']);
 const xml=drawioFile([{id:'page',name:domain,...scene}]);assert.match(xml,/parent="atmem-b"/);assert.match(xml,/source="atmem-c" target="atmem-external"/);
 const resized=applyDrawingLayout(scene,{a:{width:40,height:40}});assert.ok(resized.vertices[0].width>40);assert.ok(resized.vertices[0].height>40);
 const root={atmem:byId.get('a'),g:{x:100,y:120,width:900,height:500}},child={atmem:byId.get('b'),g:{x:28,y:76,width:300,height:250},p:root},leaf={atmem:byId.get('c'),g:{x:28,y:76,width:232,height:100},p:child};root.children=[child];child.children=[leaf];
 const model={getGeometry:c=>c.g,getParent:c=>c.p,isVertex:c=>!!c?.g,getChildCount:c=>c.children?.length||0,getChildAt:(c,i)=>c.children[i]};
 assert.deepEqual(nativeLayoutChanges(model,[root]).map(({id,x,y})=>({id,x,y})),[{id:'a',x:100,y:120},{id:'b',x:128,y:196},{id:'c',x:156,y:272}]);
});
test('invalid and cyclic ownership fails; an absent view parent is not invented',()=>{
 const scene={vertices:[{id:'a',x:0,y:0,width:100,height:100,selectable:true},{id:'b',x:200,y:0,width:100,height:100,selectable:true}],wires:[]};
 assert.throws(()=>nestDrawingScene(scene,id=>id),/itself/);assert.throws(()=>nestDrawingScene(scene,id=>id==='a'?'b':'a'),/cycle/);
 assert.equal(nestDrawingScene(scene,()=> 'outside'),scene);
});
test('component pages display semantic parents as editable containers; sequence stays chronological',()=>{
 for(const kind of ['component','sequence']){
  const {model,view}=addDiagram(emptyDiagramModel(),kind,'Equipment service',true);
  model.elements[1].parentId=model.elements[0].id;
  const scene=architectureGraph(diagramProjection(model,view),view);
  assert.equal(scene.vertices.some(v=>v.container),kind==='component');
 }
});
