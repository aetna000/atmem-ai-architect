import test from 'node:test';import assert from 'node:assert/strict';
import {arrangeDrawingScene,arrangementChanges} from '../src/drawing-arrangement.mjs';
import {updateDrawingLayout,applyDrawingLayout} from '../src/drawing-layout.mjs';
for(const domain of ['Archive','Clinic'])test(domain+' arrangement moves only presentation geometry and retains nesting and contracts',()=>{
 const v=(id,parent)=>({id,name:domain+' '+id,body:domain+' '+id,x:40,y:40,width:180,height:100,selectable:true,...(parent?{containerParentId:parent}:{})});
 const scene={vertices:[{...v('system'),container:true,headerHeight:48},v('a','system'),{...v('b','system'),rotation:30},v('outside')],wires:[{id:'exchange',source:'a',target:'outside',body:'1',reference:'1',record:{authorization:'Assigned role only'},style:''}]};
 const before=structuredClone(scene),next=arrangeDrawingScene(scene);assert.deepEqual(scene,before);
 assert.deepEqual(next.vertices.map(v=>[v.id,v.name,v.body,v.containerParentId,v.rotation]),before.vertices.map(v=>[v.id,v.name,v.body,v.containerParentId,v.rotation]));
 assert.deepEqual(next.wires.map(w=>[w.id,w.source,w.target,w.record,w.body]),before.wires.map(w=>[w.id,w.source,w.target,w.record,w.body]));
 const parent=next.vertices.find(v=>v.id==='system'),a=next.vertices.find(v=>v.id==='a'),b=next.vertices.find(v=>v.id==='b');
 for(const child of [a,b]){assert.ok(child.x>=parent.x);assert.ok(child.y>=parent.y+parent.headerHeight);assert.ok(child.x+child.width<=parent.x+parent.width);assert.ok(child.y+child.height<=parent.y+parent.height);}
 assert.ok(a.x+a.width<=b.x||b.x+b.width<=a.x||a.y+a.height<=b.y||b.y+b.height<=a.y);
 const layout=updateDrawingLayout(null,'board/full',arrangementChanges(next));assert.equal(Object.keys(layout.pages['board/full']).length,4);
 const restored=applyDrawingLayout(scene,layout.pages['board/full']);assert.deepEqual(restored.vertices.map(v=>v.id),scene.vertices.map(v=>v.id));
});
test('ordered timelines and cyclic containment reject rearrangement without removing records',()=>{
 const scene={vertices:[{id:'a',body:'A',x:0,y:0,width:100,height:80},{id:'b',body:'B',x:200,y:0,width:100,height:80}],wires:[]};
 assert.throws(()=>arrangeDrawingScene({...scene,timeline:true}),/chronological/);
 assert.throws(()=>arrangeDrawingScene({...scene,ordered:true}),/chronological/);
 assert.throws(()=>arrangeDrawingScene({...scene,vertices:[...scene.vertices.map((v,i)=>({...v,containerParentId:i?'a':'b'})),{id:'root',body:'Root',x:0,y:0,width:100,height:80}]}),/cycle/);
 assert.throws(()=>arrangeDrawingScene(scene,{spacing:Infinity}),/Invalid/);
});
test('arrangement preserves missing endpoint failures rather than dropping the connector',()=>{
 const result=arrangeDrawingScene({vertices:[{id:'a',name:'A',body:'A',x:0,y:0,width:100,height:80}],wires:[{id:'broken',source:'a',target:'missing',body:'1'}]});
 assert.equal(result.wires.length,1);assert.ok(result.wires[0].routingIssue);
});
