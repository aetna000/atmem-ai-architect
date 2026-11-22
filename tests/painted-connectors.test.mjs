import test from 'node:test';import assert from 'node:assert/strict';import {paintedConnectorOverlaps} from '../src/diagram-readability.mjs';
// Native SVG path fixtures; browser integration is exercised separately.
class Point{constructor(x,y){this.x=x;this.y=y;}matrixTransform(m){return{x:m.a*this.x+m.c*this.y+m.e,y:m.b*this.x+m.d*this.y+m.f};}}
function fixture(paths){
 const identity={a:1,b:0,c:0,d:1,e:0,f:0},nodes=new Map(Object.entries(paths).map(([id,d])=>{const path={d,matrix:identity,getAttribute(k){return k==='d'?this.d:k==='fill'?'none':null;},getScreenCTM(){return this.matrix;}};return[id,{path,shape:{node:{querySelectorAll:()=>[path]}}}];}));
 return{nodes,graph:{getModel:()=>({getCell:id=>id}),view:{scale:1,translate:{x:0,y:0},getState:id=>nodes.get(id)}},scene:{wires:Object.keys(paths).map(id=>({id}))}};
}
const original=globalThis.DOMPoint;globalThis.DOMPoint=Point;test.after(()=>{if(original)globalThis.DOMPoint=original;else delete globalThis.DOMPoint;});
test('painted overlap checks retain separate pair totals and exclude crossings and nearby lanes',()=>{
 const {graph,scene}=fixture({a:'M 0 10 L 200 10',b:'M 20 10 L 180 10',c:'M 180 10 L 20 10',nearby:'M 0 20 L 200 20',crossing:'M 100 0 L 100 40'});
 assert.deepEqual(paintedConnectorOverlaps(graph,scene).map(({id,other,pixels})=>({id,other,pixels})),[{id:'b',other:'a',pixels:160},{id:'c',other:'a',pixels:160},{id:'c',other:'b',pixels:160}]);
 assert.equal(paintedConnectorOverlaps(graph,scene,['b']).length,2);
});
test('cell boundaries, negative coordinates and very long segments retain overlap diagnostics',()=>{
 for(const x of [-128.2,127.8]){
  const {graph,scene}=fixture({a:`M ${x} -100 L ${x} 200`,b:`M ${x+.4} -80 L ${x+.4} 180`});
  assert.equal(paintedConnectorOverlaps(graph,scene)[0].pixels,260);
 }
 const {graph,scene}=fixture({a:'M -1000000000 10 L 1000000000 10',b:'M 1 10 L 100 10'});assert.equal(paintedConnectorOverlaps(graph,scene)[0].pixels,99);
});
test('changed painted paths and viewport matrices invalidate cached segment geometry',()=>{
 const {graph,scene,nodes}=fixture({a:'M 0 10 L 200 10',b:'M 20 10 L 180 10'});assert.equal(paintedConnectorOverlaps(graph,scene).length,1);
 nodes.get('b').path.d='M 20 30 L 180 30';assert.equal(paintedConnectorOverlaps(graph,scene).length,0);
 nodes.get('b').path.matrix={a:1,b:0,c:0,d:1,e:0,f:-20};assert.equal(paintedConnectorOverlaps(graph,scene).length,1);
});
