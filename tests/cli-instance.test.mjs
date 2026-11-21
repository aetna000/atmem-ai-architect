import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {test} from 'node:test';
import {inspectInstance, manageInstance, stopInstance} from '../cli/instance.mjs';

test('instance ownership serializes launches and accepts only authenticated stop requests', async t => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'atmem-instance-'));
  let active;
  t.after(async () => {
    await active?.close();
    fs.rmSync(home, {recursive: true, force: true});
  });
  assert.deepEqual(await inspectInstance(home), {state: 'stopped'});
  const details = {port: 5174, version: 'test', memoryVersion: 'test'};
  let stopped = false;
  active = await manageInstance(home, {...details, onStop: () => {
    stopped = true;
    void active.close();
  }});
  active.ready(12345);

  const instance = await inspectInstance(home);
  assert.equal(instance.state, 'running');
  assert.equal(instance.serverPid, 12345);
  await assert.rejects(manageInstance(home, details), /owns this data directory/);

  const response = await fetch(`http://127.0.0.1:${instance.receipt.controlPort}/stop`, {method: 'POST'});
  assert.equal(response.status, 403);
  assert.equal(stopped, false);

  await stopInstance(home, instance.receipt);
  assert.equal(stopped, true);
  assert.deepEqual(await inspectInstance(home), {state: 'stopped'});
});
