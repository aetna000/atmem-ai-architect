import fs from 'node:fs';
import path from 'node:path';
import {createServer} from 'node:http';
import {createHmac, randomBytes, timingSafeEqual} from 'node:crypto';
import {setTimeout as delay} from 'node:timers/promises';

const randomId = () => randomBytes(32).toString('hex');
const receiptPath = home => path.join(home, 'instance.json');
const validId = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);

function readReceipt(home) {
  try {
    const receipt = JSON.parse(fs.readFileSync(receiptPath(home), 'utf8'));
    if (!validId(receipt.key) || !Number.isSafeInteger(receipt.pid) || receipt.pid < 1 ||
        ![receipt.port, receipt.controlPort].every(port => Number.isInteger(port) && port > 0 && port < 65536)) {
      throw Error('Invalid instance receipt.');
    }
    return receipt;
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw Error(`Cannot read Architect instance receipt at ${receiptPath(home)}.`, {cause: error});
  }
}

function sign(key, message) {
  return createHmac('sha256', key).update(message).digest('hex');
}

function matches(value, expected) {
  return validId(value) && timingSafeEqual(Buffer.from(value), Buffer.from(expected));
}

async function control(receipt, action) {
  const nonce = randomId();
  const response = await fetch(`http://127.0.0.1:${receipt.controlPort}/${action}`, {
    method: action === 'stop' ? 'POST' : 'GET',
    headers: {'X-Architect-Nonce': nonce, Authorization: sign(receipt.key, `${action}:${nonce}`)},
    redirect: 'error',
    signal: AbortSignal.timeout(1200),
  });
  if (!response.ok) throw Error('Instance control request failed.');
  const body = await response.text();
  if (!matches(response.headers.get('X-Architect-Proof'), sign(receipt.key, `${nonce}:${body}`))) {
    throw Error('Instance identity could not be verified.');
  }
  return JSON.parse(body);
}

function processExists(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error.code !== 'ESRCH';
  }
}

export async function inspectInstance(home) {
  const receipt = readReceipt(home);
  if (!receipt) return {state: 'stopped'};
  try {
    return {...await control(receipt, 'status'), receipt};
  } catch {
    return {state: processExists(receipt.pid) ? 'unverified' : 'stale', receipt};
  }
}

// Serialize receipt changes across launchers. A private, atomic rename keeps
// readers from seeing partial JSON. The short lock is never held during setup.
async function updateReceipt(home, update) {
  const lock = path.join(home, 'instance.lock');
  for (let attempt = 0; ; attempt++) {
    try {
      fs.mkdirSync(lock, {mode: 0o700});
      break;
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
      if (attempt === 20) {
        throw Error(`Another launcher is updating ${receiptPath(home)}. Retry shortly. If interrupted, check for running sessions before removing ${lock}.`);
      }
      await delay(50);
    }
  }
  try {
    update(readReceipt(home));
  } finally {
    fs.rmdirSync(lock);
  }
}

export async function manageInstance(home, {port, version, memoryVersion, instanceId, onStop}) {
  fs.mkdirSync(home, {recursive: true, mode: 0o700});
  const receipt = {key: randomId(), pid: process.pid, port};
  const details = {state: 'starting', port, version, memoryVersion, instanceId, pid: process.pid, startedAt: new Date().toISOString()};
  const server = createServer((request, response) => {
    const action = request.method === 'GET' && request.url === '/status' ? 'status'
      : request.method === 'POST' && request.url === '/stop' ? 'stop' : null;
    const nonce = request.headers['x-architect-nonce'];
    if (!action || request.headers.origin || !validId(nonce) ||
        !matches(request.headers.authorization, sign(receipt.key, `${action}:${nonce}`))) {
      response.writeHead(403).end();
      return;
    }
    if (action === 'stop') details.state = 'stopping';
    const body = JSON.stringify(details);
    response.writeHead(200, {'Content-Type': 'application/json', 'X-Architect-Proof': sign(receipt.key, `${nonce}:${body}`)});
    response.end(body, action === 'stop' ? onStop : undefined);
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  receipt.controlPort = server.address().port;

  try {
    await updateReceipt(home, current => {
      if (current && processExists(current.pid)) {
        throw Error('Another Architect launcher owns this data directory. Run atmemai status.');
      }
      const temporary = path.join(home, `instance-${randomId()}.tmp`);
      try {
        fs.writeFileSync(temporary, JSON.stringify(receipt), {mode: 0o600, flag: 'wx'});
        fs.renameSync(temporary, receiptPath(home));
      } finally {
        fs.rmSync(temporary, {force: true});
      }
    });
  } catch (error) {
    server.close();
    throw error;
  }
  return {
    ready(pid) {
      if (details.state === 'starting') Object.assign(details, {state: 'running', serverPid: pid});
    },
    async close() {
      server.close();
      await updateReceipt(home, current => {
        if (current?.key === receipt.key) fs.unlinkSync(receiptPath(home));
      });
    },
  };
}

export async function stopInstance(home, receipt) {
  await control(receipt, 'stop');
  // Keep the old owner in place until the web server has actually shut down.
  for (let attempt = 0; attempt < 150; attempt++) {
    if (readReceipt(home)?.key !== receipt.key) return;
    await delay(200);
  }
  throw Error('Architect is still shutting down. Check atmemai status and try again.');
}
