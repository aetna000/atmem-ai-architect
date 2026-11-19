import test from 'node:test';
import assert from 'node:assert/strict';
import { fromProjectFile, toProjectFile } from '../src/project-file.mjs';
import { toAgentProject } from '../src/local-agent.mjs';
import { deliveryPack } from '../src/delivery.mjs';
import { validateBlockSpecs, removeBlocks, scenarioDiagrams } from '../src/block-spec.mjs';

const block = (id, data = {}) => ({
  id, type: 'resource', position: { x: 0, y: 0 },
  data: { label: id, kind: 'resource', provider: 'tools', origin: 'proposed', ...data },
});
const interfaceSpec = { transport: 'Local call v1', input: 'Seat ID', output: 'Hold ID', authorization: 'Box office', failure: 'Read state before retry', verification: 'Race the last seat' };
const spec = {
  inputs: 'Versioned hold request and session identifier.',
  outputs: 'Hold reference or unavailable response.',
  behavior: 'Create only one hold per session.',
  failures: 'Read the previous outcome before retrying a timed-out hold.',
  implementation: 'Implement atomic hold creation and lookup.',
  infrastructure: 'Use the reservation service database.',
  operations: 'Exercise expiry and restore against the released build.',
  tests: 'Two simultaneous holds for the last seat produce one winner.',
  scenarios: [{ name: 'Reserve seat', steps: [
    { sender: 'Box office', receiver: 'Reservations', action: 'Request a hold' },
    { sender: 'Reservations', receiver: 'Box office', action: 'Return HoldAccepted or Unavailable' },
  ] }],
};

test('nested reservation specs round trip and reach both Architect and the delivery package', () => {
  const project = {
    id: 'ticketing', version: 1, revision: 2, name: 'Theatre ticketing', provider: 'tools',
    nodes: [block('box-office'), block('reservations', { parentBlockId: 'box-office' }), block('holds', { parentBlockId: 'reservations', buildSpec: spec })],
    edges: [{ id: 'request', source: 'box-office', target: 'holds', label: 'Hold request', interfaceSpec }],
    needs: [{ id: 'seat', statement: 'Allocate a seat once.', links: ['holds'] }],
    openQuestions: [{ id: 'expiry', question: 'How long may a customer hold a seat?', status: 'open', links: ['holds'] }],
  };
  const { project: reopened } = fromProjectFile(toProjectFile(project));
  assert.equal(reopened.nodes[2].data.parentBlockId, 'reservations');
  assert.deepEqual(toAgentProject(reopened).nodes[2].data.buildSpec, spec);
  assert.deepEqual(toAgentProject(reopened).edges[0].interfaceSpec, interfaceSpec);
  const files = deliveryPack(reopened, null);
  const { components } = JSON.parse(files['spec-kit/blocks/index.json']);
  const holds = components.find(row => row.id === 'holds');
  assert.equal(holds.depth, 2);
  assert.deepEqual(holds.missing, []);
  assert.deepEqual(holds.questionIds, ['expiry']);
  assert.deepEqual(holds.requirementIds, ['seat']);
  assert.match(files[holds.path + '/1-sequence.mmd'], /actor0->>actor1: Unclassified#58; Request a hold/);
  assert.match(files[holds.path + '/1-functional.mmd'], /step0 --> step1/);
  assert.match(files[holds.path + '/testing.md'], /one winner/);
  assert.match(files[holds.path + '/plan.md'], /Implement atomic hold creation and lookup/);
  assert.match(files[holds.path + '/plan.md'], /request/);
  assert.match(files[holds.path + '/scenarios.md'], /Event flow/);
  assert.match(files['diagram.mmd'], /subgraph group/);
  assert.match(files['diagram.mmd'], /reservations/);
  assert.match(files[holds.path + '/infrastructure-devops.md'], /restore against the released build/);
  assert.deepEqual(JSON.parse(files['spec-kit/interfaces.json']).interfaces[0].proposedDesignContract, interfaceSpec);
  const tasks = JSON.parse(files['spec-kit/tasks.json']).tasks;
  assert.ok(holds.taskIds.length);
  assert.ok(tasks.some(task => task.specFiles?.includes(holds.path + '/spec.md')));
  assert.match(files['spec-kit/questions.md'], /hold a seat/);
  assert.ok(JSON.parse(files['manifest.json']).files.includes(holds.path + '/testing.md'));
});

test('malformed hierarchy and blank specs fail, while removal preserves descendants', () => {
  const tree = [block('root'), block('middle', { parentBlockId: 'root' }), block('child', { parentBlockId: 'middle' })];
  assert.throws(() => validateBlockSpecs([block('a', { parentBlockId: 'b' }), block('b', { parentBlockId: 'a' })]), /cycle/);
  assert.throws(() => validateBlockSpecs([tree[2]]), /existing component/);
  assert.throws(() => validateBlockSpecs([block('a', { buildSpec: { tests: ' ' } })]), /Invalid block specification/);
  const remaining = removeBlocks(tree, new Set(['middle']));
  assert.equal(remaining[1].data.parentBlockId, 'root');
  validateBlockSpecs(remaining);
  assert.match(scenarioDiagrams({ steps: [{ sender: 'Team A', receiver: 'Team B', action: 'Quote "]\nend; <x>' }] }).functional, /#34;#93; end#59;/);
});

import { blockCheckStatus } from '../src/block-check-status.mjs';
import { blockBuildIntent } from '../src/design-build-flow.mjs';
test('a green block check requires a current scoped receipt with executed and unskipped tests', () => {
  const artifact = { id: 'package', sha256: 'current' };
  const validators = [{ id: 'v', blockId: 'holds', contractSha256: 'contract' }];
  const check = { state: 'finished', blockId: 'holds', validatorId: 'v', contractSha256: 'contract',
    artifactId: 'package', artifactSha256: 'current',
    result: { status: 'passed', artifactSha256: 'current', testsReported: 2, skipped: 0 } };
  assert.equal(blockCheckStatus('holds', artifact, validators, [check]).state, 'passed');
  assert.equal(blockCheckStatus('holds', artifact, validators, [{ ...check, blockId: 'another' }]).state, 'pending');
  assert.equal(blockCheckStatus('holds', artifact, validators, [{ ...check, artifactSha256: 'older' }]).state, 'pending');
  assert.equal(blockCheckStatus('holds', artifact, validators, [{ ...check, result: { ...check.result, skipped: 1 } }]).state, 'pending');
  assert.equal(blockCheckStatus('holds', artifact, validators, [check, { ...check, state: 'running' }]).state, 'pending');
  assert.equal(blockCheckStatus('other', artifact, validators, [check]).state, 'unconfigured');
  const project = { nodes: [block('holds', { buildSpec: spec }), block('other')] };
  assert.match(blockBuildIntent(project, 'holds'), /only block "holds"/);
  assert.match(blockBuildIntent(project, 'holds'), /without asking questions in this build turn/);
  assert.match(blockBuildIntent(project, 'holds'), /continue independent work/);
  assert.doesNotMatch(blockBuildIntent(project, 'holds'), /Stop at a material unanswered/);
  assert.equal(blockBuildIntent(project, 'other'), '');
});
