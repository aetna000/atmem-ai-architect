import test from 'node:test';
import assert from 'node:assert/strict';
import {boardGraph,drawioFile,graphMermaid} from '../src/drawio-model.mjs';
import {applyDrawingLayout,updateDrawingLayout,validateDrawingLayouts} from '../src/drawing-layout.mjs';
import {createDrawingGroup,updateDrawingGroups,ungroupDrawing,validateDrawingGroups} from '../src/drawing-groups.mjs';
import {toProjectFile,parseProjectFile} from '../src/project-file.mjs';
import {drawioHandoffFiles} from '../src/drawio-handoff.mjs';
for(const domain of ['Archive','Workshop'])test(domain+' visual grouping keeps component identity, ownership, specs and interfaces',()=>{
 const project={id:'visual-group-project',version:1,revision:1,name:domain,provider:'tools',nodes:['a','b','c'].map((id,i)=>({id,position:{x:i*300,y:70},data:{kind:'resource',provider:'tools',label:domain+' '+id,description:'A specific responsibility',...(id==='b'?{parentBlockId:'a'}:{})}})),edges:[{id:'wire',source:'a',target:'c',label:'Publish'}]};
 const original=structuredClone(project),scene=boardGraph(project.nodes,project.edges);
 let {groups,id}=createDrawingGroup([],scene,['a','c'],'Operating team','@visual-group-team');
 let layout=updateDrawingGroups(undefined,'board/full',groups);layout=updateDrawingLayout(layout,'board/full',[{id:'a',x:100,y:200}]);assert.deepEqual(layout.groups['board/full'],groups);
 const grouped=applyDrawingLayout(scene,layout.pages['board/full'],groups),row=grouped.vertices.find(v=>v.id===id);
 assert.equal(row.visualGroup,true);assert.equal(grouped.vertices.find(v=>v.id==='a').containerParentId,id);assert.equal(grouped.vertices.find(v=>v.id==='b').containerParentId,'a');assert.equal(grouped.vertices.find(v=>v.id==='c').containerParentId,id);assert.deepEqual(project,original);
 const saved={...project,extensions:{drawingLayouts:layout}};const reopened=parseProjectFile(JSON.stringify(toProjectFile(saved))).project;assert.deepEqual(reopened.extensions.drawingLayouts,layout);assert.deepEqual(reopened.nodes.map(n=>n.data.parentBlockId),project.nodes.map(n=>n.data.parentBlockId));
 assert.ok(!graphMermaid(grouped).includes('Operating team'),'A visual group is not turned into an architecture component by Mermaid');
 const native=drawioHandoffFiles(saved)['architecture.drawio'];assert.match(native,/parent="atmem-%40visual-group-team"/);assert.match(native,/source="atmem-a" target="atmem-c"/);
 assert.throws(()=>createDrawingGroup(groups,grouped,[id,'b'],'Invalid redundant group'),/independent/);
 // A true second group with two distinct roots can be nested and ungrouped losslessly.
 assert.deepEqual(ungroupDrawing(groups,id),[]);assert.deepEqual(project,original);
});
test('groups reject cycles, duplicate owners, duplicate IDs and empty names',()=>{
 const a='@visual-group-a',b='@visual-group-b';
 for(const groups of [[{id:a,name:'A',memberIds:[a]}],[{id:a,name:'A',memberIds:[b]},{id:b,name:'B',memberIds:[a]}],[{id:a,name:'A',memberIds:['x']},{id:b,name:'B',memberIds:['x']}],[{id:a,name:' ',memberIds:['x']}],[{id:a,name:'A',memberIds:['x']},{id:a,name:'B',memberIds:['y']}]])assert.throws(()=>validateDrawingGroups({page:groups}));
 assert.throws(()=>validateDrawingLayouts({version:1,pages:{},groups:[]}));
});

test('grouping members of an existing group creates a visual subgroup and ungrouping restores them',()=>{
 const scene={vertices:['a','b','c'].map((id,i)=>({id,name:id,body:id,x:i*200,y:100,width:150,height:80,selectable:true})),wires:[]};
 const outer=createDrawingGroup([],scene,['a','b','c'],'Team','@visual-group-team'),shown=applyDrawingLayout(scene,undefined,outer.groups);
 const inner=createDrawingGroup(outer.groups,shown,['a','b'],'Shift','@visual-group-shift');
 assert.deepEqual(inner.groups.find(g=>g.id===outer.id).memberIds,['c',inner.id]);
 assert.deepEqual(ungroupDrawing(inner.groups,inner.id)[0].memberIds,['c','a','b']);
 const nested=applyDrawingLayout(scene,undefined,inner.groups);assert.equal(nested.vertices.find(v=>v.id===inner.id).containerParentId,outer.id);
 assert.throws(()=>applyDrawingLayout({...scene,vertices:[...scene.vertices,{id:outer.id,name:'Collision'}]},undefined,outer.groups),/conflicts/);
 const layout=updateDrawingGroups({version:1,pages:{page:{[inner.id]:{width:500}}},groups:{page:inner.groups}},'page',outer.groups);assert.equal(layout.pages.page[inner.id],undefined);
});
