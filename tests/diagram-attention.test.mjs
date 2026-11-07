import test from 'node:test';
import assert from 'node:assert/strict';
import { diagramAttention } from '../src/diagram-attention.mjs';
const a={id:'a',data:{label:'A'},position:{x:0,y:0}}, b={...a,id:'b'};
const edge={id:'ab',source:'a',target:'b'};
test('attention targets additions and configuration edits without mutating the project',()=>{
 const before={nodes:[a],edges:[]}, after={nodes:[{...a,data:{...a.data,region:'Sydney'}},b],edges:[edge]};
 const snapshot=JSON.stringify(before);
 assert.deepEqual(diagramAttention(before,after),{nodes:['a','b'],edges:['ab']});
 assert.equal(JSON.stringify(before),snapshot);
 assert.deepEqual(diagramAttention(after,after),{nodes:[],edges:[]});
});
test('removed connections and blocks focus surviving endpoints; empty designs are safe',()=>{
 const before={nodes:[a,b],edges:[edge]};
 assert.deepEqual(diagramAttention(before,{nodes:[a],edges:[]}),{nodes:['a'],edges:[]});
 assert.deepEqual(diagramAttention(before,{nodes:[],edges:[]}),{nodes:[],edges:[]});
});
