import test from 'node:test';import assert from 'node:assert/strict';
import {systemDescription,systemDescriptionMarkdown,requirementExplanation} from '../src/system-description.mjs';
import {CLOUD_STORAGE_SCENARIOS} from '../src/cloud-storage-scenarios.mjs';
import {solutionSpecification} from '../src/delivery.mjs';
test('system documentation covers every actual component and connection without inventing targets',()=>{
 const p=structuredClone(CLOUD_STORAGE_SCENARIOS[0].project);const before=structuredClone(p);const d=systemDescription(p);
 assert.equal(d.components.length,p.nodes.length);assert.equal(d.flows.length,p.edges.length);assert.match(d.components[1].boundary,/Existing system/);
 const md=systemDescriptionMarkdown(p);assert.match(md,/Inputs:/);assert.match(md,/Outputs:/);assert.match(md,/Implementation considerations/);assert.ok(solutionSpecification(p).includes(md));assert.deepEqual(p,before);
 assert.ok(!md.includes('99.99%'));assert.match(requirementExplanation({statement:'Every answer shows its sources'}),/reader can check/);
});
