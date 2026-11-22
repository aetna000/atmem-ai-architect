import test from 'node:test';
import assert from 'node:assert/strict';
import {segmentCrossesRect} from '../src/diagram-geometry.mjs';
const box={x:40,y:40,width:20,height:20};
test('connector crossings cover horizontal, vertical, diagonal and reversed paths',()=>{
 for(const [a,b]of [[{x:0,y:50},{x:100,y:50}],[{x:50,y:0},{x:50,y:100}],[{x:0,y:0},{x:100,y:100}],[{x:50,y:50},{x:100,y:100}]]){
  assert.equal(segmentCrossesRect(a,b,box,3),true);assert.equal(segmentCrossesRect(b,a,box,3),true);
 }
});
test('tangent borders, missed corners and empty interiors are not crossings',()=>{
 for(const [a,b]of [[{x:0,y:43},{x:100,y:43}],[{x:0,y:0},{x:40,y:40}],[{x:0,y:0},{x:100,y:20}]])assert.equal(segmentCrossesRect(a,b,box,3),false);
 assert.equal(segmentCrossesRect({x:0,y:0},{x:100,y:100},box,10),false);
});
test('long connectors detect small obstacles between former pixel samples',()=>{
 assert.equal(segmentCrossesRect({x:-1e9,y:0},{x:1e9,y:0},{x:.1,y:-1,width:.2,height:2}),true);
 assert.equal(segmentCrossesRect({x:0,y:10},{x:100,y:10},{x:50,y:11,width:1,height:1}),false);
});
