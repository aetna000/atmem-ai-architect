import test from 'node:test';import assert from 'node:assert/strict';
import {readCanvasView,saveCanvasView,arrangeOverview} from '../src/canvas-view.mjs';import {systemView} from '../src/levels.mjs';
const project=()=>({id:'one',nodes:[{id:'a',data:{kind:'resource',label:'Client'}},{id:'b',data:{kind:'resource',label:'App'}}],edges:[{id:'flow',source:'a',target:'b',label:'Send request'}]});
const storage=()=>{const data=new Map();return {getItem:k=>data.get(k),setItem:(k,v)=>data.set(k,v)};};
test('Components is the default; preferences and overview positions persist per project',()=>{
 const p=project(),s=storage();assert.equal(readCanvasView(p,s).level,'flow');saveCanvasView(p,{level:'system',positions:{'layer:component:a':{x:50,y:20}}},s);assert.equal(readCanvasView(p,s).level,'system');assert.equal(readCanvasView({...p,id:'two'},s).level,'flow');assert.equal(readCanvasView(p,s).positions['layer:component:a'].x,50);
});
test('stale detail selection and malformed storage fall back to Components',()=>{
 const p=project(),s=storage();saveCanvasView(p,{level:'block',selected:'deleted',focus:'gone'},s);assert.equal(readCanvasView(p,s).level,'flow');assert.equal(readCanvasView(p,s).focus,null);assert.equal(readCanvasView(p,{getItem:()=>{throw Error('unavailable')}}).level,'flow');
});
test('overview arrangement changes its projection only and uses measured card bounds',()=>{
 const p=project(),before=structuredClone(p),view=systemView(p),projection=structuredClone(view);const positions=arrangeOverview(view,Object.fromEntries(view.nodes.map(n=>[n.id,{width:500,height:350}])));assert.equal(Object.keys(positions).length,2);assert.deepEqual(p,before);assert.deepEqual(view,projection);assert.ok(positions[view.nodes[1].id].x>=positions[view.nodes[0].id].x+500);
});
