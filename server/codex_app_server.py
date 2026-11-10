"""Persistent Codex protocol transport for the engineering-session foundation.

Not a sandbox, execution policy or public endpoint. Callers must separately qualify
workspace isolation and tools before exposing engineering turns to the product.
Uses the official signed-in CLI; never reads or extracts account tokens.
"""
import asyncio
import json
import os
from pathlib import Path
import signal
from .local_providers import account_environment


class ProtocolError(RuntimeError):
    pass


class CodexAppServer:
    def __init__(self, workspace, *, command=None, event_limit=4096):
        self.workspace = Path(workspace).resolve(strict=True)
        if not self.workspace.is_dir():
            raise ValueError('Codex workspace must be an existing directory')
        self.command = command or ['codex', 'app-server', '--listen', 'stdio://',
                                   '-c', 'analytics.enabled=false']
        self.events = asyncio.Queue(maxsize=event_limit)
        self.process = None
        self.pending = {}
        self.serial = 0
        self.failure = None
        self.reader = self.stderr_reader = None
        self.write_lock = asyncio.Lock()

    async def start(self):
        if self.process is not None:
            raise ProtocolError('Codex transport has already started')
        env = account_environment()
        # Authentication remains CLI-owned. Do not forward deployment credentials.
        for key in list(env):
            if key.startswith(('AWS_', 'AZURE_', 'GOOGLE_', 'GCLOUD_', 'IBM_', 'WATSONX_', 'TF_')) or key in {'KUBECONFIG', 'DOCKER_HOST', 'DOCKER_CONFIG', 'CLOUDSDK_CONFIG', 'GOOGLE_APPLICATION_CREDENTIALS'}:
                env.pop(key, None)
        self.process = await asyncio.create_subprocess_exec(
            *self.command, cwd=self.workspace, env=env,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE, limit=8_000_000, start_new_session=True)
        self.reader = asyncio.create_task(self._read())
        self.stderr_reader = asyncio.create_task(self._drain_stderr())
        try:
            result = await self.request('initialize', {'clientInfo': {
                'name': 'atmem_ai_architect', 'title': 'AtMem AI Architect',
                'version': json.loads((Path(__file__).resolve().parents[1] / 'package.json').read_text())['version']}})
            await self._write({'method': 'initialized', 'params': {}})
            return result
        except BaseException:
            await self.close()
            raise

    async def _write(self, message):
        if self.failure:
            raise ProtocolError(self.failure)
        if not self.process or self.process.returncode is not None:
            raise ProtocolError('Codex transport is not running')
        wire = json.dumps(message, allow_nan=False, separators=(',', ':')).encode() + b'\n'
        if len(wire) > 8_000_000:
            raise ValueError('Codex protocol message exceeds the explicit bound')
        async with self.write_lock:
            self.process.stdin.write(wire)
            await self.process.stdin.drain()

    async def request(self, method, params=None, *, timeout=30):
        if not isinstance(method, str) or not method:
            raise ValueError('A protocol method is required')
        self.serial += 1
        ident = self.serial
        future = asyncio.get_running_loop().create_future()
        self.pending[ident] = future
        try:
            await self._write({'id': ident, 'method': method, 'params': params or {}})
            return await asyncio.wait_for(future, timeout)
        except BaseException:
            # _fail may settle this future while a write is failing. Consume its
            # exception so cancellation/transport errors never leak orphan futures.
            if future.done() and not future.cancelled():
                future.exception()
            raise
        finally:
            self.pending.pop(ident, None)
            if not future.done():
                future.cancel()
        # A timeout/cancel only stops waiting; it does not cancel a Codex turn.
        # Engineering callers must use turn/interrupt and observe its terminal event.

    def _fail(self, reason):
        self.failure = reason
        for future in self.pending.values():
            if not future.done():
                future.set_exception(ProtocolError(reason))

    async def _read(self):
        try:
            while line := await self.process.stdout.readline():
                message = json.loads(line)
                if not isinstance(message, dict):
                    raise ProtocolError('Codex returned an invalid protocol envelope')
                if 'method' in message:
                    if 'id' in message:
                        # No automatic approvals or dynamic tool execution in this
                        # foundation. Unsupported server requests fail closed.
                        await self._write({'id': message['id'], 'error': {
                            'code': -32601, 'message': 'Client handler is not enabled'}})
                    else:
                        self.events.put_nowait(message)
                elif 'id' in message:
                    future = self.pending.get(message['id'])
                    if future and not future.done():
                        if 'error' in message:
                            code = message['error'].get('code') if isinstance(message['error'], dict) else None
                            future.set_exception(ProtocolError(f'Codex request rejected (code {code})'))
                        elif 'result' in message:
                            future.set_result(message['result'])
                        else:
                            raise ProtocolError('Codex response contains neither result nor error')
                else:
                    raise ProtocolError('Codex protocol envelope has no method or id')
            self._fail('Codex transport closed; pending work is not confirmed complete')
        except asyncio.CancelledError:
            raise
        except Exception:
            self._fail('Codex protocol failed or event capacity was exceeded; no completion is inferred')
            if self.process.returncode is None:
                self.process.terminate()

    async def _drain_stderr(self):
        # Do not leak credentials, local paths or provider diagnostic bodies into
        # public reports. Drain to avoid deadlock; qualification stores safe receipts.
        while await self.process.stderr.read(65536):
            pass

    async def close(self):
        if not self.process:
            return
        self._fail('Codex transport closed; pending work is not confirmed complete')
        if self.process.returncode is None:
            self.process.stdin.close()
            try:
                await asyncio.wait_for(self.process.wait(), 2)
            except asyncio.TimeoutError:
                try:
                    os.killpg(self.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(self.process.wait(), 2)
                except asyncio.TimeoutError:
                    try:
                        os.killpg(self.process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    await self.process.wait()
        for task in (self.reader, self.stderr_reader):
            if task:
                task.cancel()
        await asyncio.gather(*(t for t in (self.reader, self.stderr_reader) if t), return_exceptions=True)
