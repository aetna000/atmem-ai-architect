import test from 'node:test';
import assert from 'node:assert/strict';
import {nestedCanvas,preferredNestedScope} from '../src/nested-canvas.mjs';

const node=(id,parentBlockId)=>({id,data:{label:id,kind:'resource',...(parentBlockId?{parentBlockId}:{})}});
test('nested projection preserves every crossing contract and leaves source untouched',()=>{
  const project={nodes:[node('system'),node('admission','system'),node('allocation','system'),node('seat-lock','allocation'),node('partner')],
    edges:[{id:'request',source:'admission',target:'seat-lock'},{id:'retry',source:'admission',target:'allocation'},
      {id:'publish',source:'seat-lock',target:'partner'},{id:'internal',source:'allocation',target:'seat-lock'}]};
  const original=structuredClone(project);
  const top=nestedCanvas(project);
  assert.deepEqual(top.nodes.map(node=>node.id),['system','partner']);
  assert.deepEqual(top.edges[0].data.sourceEdgeIds,['publish']);
  const middle=nestedCanvas(project,'system');
  assert.equal(middle.edges.find(edge=>edge.source==='admission').label,'2 interfaces');
  assert.deepEqual(middle.edges.flatMap(edge=>edge.data.sourceEdgeIds).sort(),['publish','request','retry']);
  const leaf=nestedCanvas(project,'allocation');
  assert.deepEqual(leaf.nodes.map(node=>node.id),['allocation','seat-lock']);
  assert.ok(leaf.edges.some(edge=>edge.source==='seat-lock'&&edge.target==='allocation'));
  assert.deepEqual(nestedCanvas(project,'*').edges,project.edges);
  assert.deepEqual(project,original);
  assert.throws(()=>nestedCanvas({nodes:[node('broken','missing')],edges:[]}),/existing component/);
  assert.throws(()=>nestedCanvas({...project,edges:[{source:'missing',target:'partner'}]}),/endpoint does not exist/);
  assert.equal(preferredNestedScope(project),'*');
});

test('nested components open visibly while explicit drill-down still preserves contracts',()=>{
  const project={nodes:[node('clinic'),node('triage','clinic'),node('appointments','clinic')],
    edges:[{id:'request-slot',source:'triage',target:'appointments'}]};
  assert.equal(preferredNestedScope(project),'*');
  assert.deepEqual(nestedCanvas(project,preferredNestedScope(project)).nodes,project.nodes);
  const view=nestedCanvas(project,'clinic');
  assert.deepEqual(view.nodes.map(node=>node.id),['triage','appointments']);
  assert.deepEqual(view.edges[0].data.sourceEdgeIds,['request-slot']);
  assert.deepEqual(nestedCanvas(project,null).nodes.map(node=>node.id),['clinic']);
});
