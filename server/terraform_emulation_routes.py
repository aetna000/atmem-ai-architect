"""Terraform apply emulation endpoint: server-generated Terraform, real CLI and
provider, loopback cloud API. A bounded local worker; a hosted adapter must add
its own tenant identity and container isolation.
"""
import asyncio
import collections
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import tempfile
import threading
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from .settings import setting

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / 'server' / 'terraform_emulator.py'
TIMEOUT_SECONDS = 1500
router = APIRouter()
LOCK = asyncio.Lock()


class TerraformEmulationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    project: dict
    environment: Literal['staging', 'production'] = 'staging'


def runtime_python():
    configured = setting('TERRAFORM_EMULATOR_PYTHON')
    return Path(configured) if configured else ROOT / '.local/terraform-emulator-runtime' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def unavailable(message, status='unavailable', **extra):
    return {'version': 1, 'kind': 'terraform-apply-emulation', 'status': status, 'stages': [], 'resources': [], 'cloudOperations': False, 'terraformApply': 'not_run', 'message': message, **extra}


def emulate_terraform(payload, progress=None):
    if setting('EMULATION_ENABLED') == '0':
        return unavailable('Local emulation is disabled on this server.')
    python = runtime_python()
    image=setting('TERRAFORM_EMULATOR_IMAGE')
    if setting('REQUIRE_EMULATION_SANDBOX')=='1' and not image:
        return unavailable('The isolated emulator worker is not configured.')
    if not image and not python.is_file():
        return unavailable('The Terraform emulator runtime is not installed. Run python3 scripts/setup-terraform-emulator.py.')
    terraform = setting('TERRAFORM_BIN') or shutil.which('terraform', path=str(ROOT / '.venv' / 'bin') + os.pathsep + os.getenv('PATH', ''))
    node = shutil.which('node')
    if not terraform or not node:
        return unavailable('Terraform 1.7+ and Node are required on the server for apply emulation.')
    with tempfile.TemporaryDirectory(prefix='atmem-tf-emulation-') as folder:
        source = Path(folder) / 'generated'
        source.mkdir()
        # The generator sees no credentials, profiles, endpoint overrides or model keys.
        clean = {'PATH': os.getenv('PATH', ''), 'HOME': folder, 'TMPDIR': folder}
        generated = subprocess.run([node, str(ROOT / 'scripts/terraform-render.mjs')], input=json.dumps(payload.model_dump()), capture_output=True, text=True, cwd=ROOT, env=clean, timeout=30)
        if generated.returncode:
            raise ValueError('Invalid project for generation')
        files = json.loads(generated.stdout)
        for name, content in files.items():
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in name or not isinstance(content, str):
                raise ValueError('Unsafe generated path')
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        digests = {name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items()}
        metadata = {
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'designRevision': payload.project.get('revision'),
            'environment': payload.environment,
            'workerDigest': hashlib.sha256(WORKER.read_bytes() + WORKER.with_name('terraform_emulator_engines.py').read_bytes()).hexdigest(),
            'fileDigests': digests,
            'artifactDigest': hashlib.sha256(json.dumps(digests, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        }
        unfinished = json.loads(files['main.tf.json']).get('locals', {}).get('unfinished_work')
        if unfinished:
            return {**unavailable('Resolve the generated implementation gaps before emulation.'), **metadata, 'status': 'blocked', 'blockers': unfinished}
        if image:
            from hosted.terraform_emulation import run_isolated
            result=run_isolated(files,image=image,endpoint=setting('ENGINEERING_VALIDATOR_ENDPOINT'),progress=progress)
            if result.get('status')=='passed' or result.get('fileDigests'):
                if result.get('fileDigests')!=digests:raise ValueError('Isolated worker artifact changed')
            return {**result,**metadata,'completedAt':datetime.now(timezone.utc).isoformat()}
        cache = setting('PROVIDER_CACHE') or str(ROOT / '.local/provider-cache')
        report_path = Path(folder) / 'report.json'
        environment = {**clean, 'ATMEM_ARCHITECT_TERRAFORM_BIN': terraform, 'PYTHONHASHSEED': '0'}
        command = [str(python), '-I', str(WORKER), '--dir', str(source), '--provider-cache', cache, '--report', str(report_path), '--progress']
        process = subprocess.Popen(command, cwd=folder, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, start_new_session=True)
        # Terraform, the provider plugin and the loopback API die with the group.
        expired = threading.Event()

        def stop():
            expired.set()
            from .terraform_emulator import stop_process_tree
            stop_process_tree(process)
        watchdog = threading.Timer(TIMEOUT_SECONDS, stop)
        watchdog.start()
        try:
            for line in process.stderr:
                if progress and line.startswith('{'):
                    try:
                        progress(json.loads(line))
                    except ValueError:
                        pass
            process.wait()
        finally:
            watchdog.cancel()
            stop()
        if expired.is_set() and not report_path.is_file():
            raise subprocess.TimeoutExpired(command, TIMEOUT_SECONDS)
        try:
            text = report_path.read_text()
            if len(text) > 4_000_000:
                raise ValueError('Emulation report exceeds bound')
            result = json.loads(text)
        except (OSError, json.JSONDecodeError):
            return {**unavailable('The isolated worker failed without a valid report; no success was recorded.'), **metadata, 'status': 'failed'}
        if process.returncode and result.get('status') == 'passed':
            raise ValueError('Worker exit contradicts report')
        # The worker hashes its private copy; it must equal what the server generated.
        worker_digests = result.get('fileDigests', {})
        if any(worker_digests.get(name) != digest for name, digest in digests.items()):
            raise ValueError('Worker ran different files than the server generated')
        return {**result, **metadata, 'completedAt': datetime.now(timezone.utc).isoformat()}


JOBS = collections.OrderedDict()
JOB_LIMIT = 8


@router.post('/api/terraform/emulate', status_code=202)
async def start_emulation(payload: TerraformEmulationRequest):
    """Start one apply emulation. Poll the returned job for stage progress."""
    if LOCK.locked():
        raise HTTPException(409, 'A Terraform emulation is already running. Try again after it finishes.')
    await LOCK.acquire()
    job = {'jobId': secrets.token_urlsafe(16), 'state': 'running', 'events': [], 'report': None, 'projectId':payload.project.get('id')}
    JOBS[job['jobId']] = job
    while len(JOBS) > JOB_LIMIT:
        JOBS.popitem(last=False)
    loop = asyncio.get_running_loop()
    threading.Thread(target=lambda: _finish(loop, job, payload), daemon=True).start()
    return {'jobId': job['jobId'], 'state': 'running'}


def _finish(loop, job, payload):
    # The lock belongs to the event loop; release it there.
    try:
        job['report'] = emulate_terraform(payload, job['events'].append)
    except subprocess.TimeoutExpired:
        job['report'] = unavailable('Terraform emulation timed out; the worker was stopped and no pass was recorded.', status='failed')
    except (ValueError, OSError, RuntimeError):
        job['report'] = unavailable('The generated project could not be emulated. Review the design and worker installation.', status='failed')
    finally:
        job['state'] = 'finished'
        loop.call_soon_threadsafe(LOCK.release)


@router.get('/api/terraform/emulate/{job_id}')
async def emulation_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, 'Unknown or expired Terraform emulation.')
    return {'jobId': job_id, 'state': job['state'], 'events': job['events'][-2000:], 'report': job['report']}


class EmulationStatusRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    jobId: str
    projectId: str


@router.post('/api/terraform/emulate/status')
async def owned_emulation_status(payload:EmulationStatusRequest):
    job=JOBS.get(payload.jobId)
    if not job or job.get('projectId')!=payload.projectId:
        raise HTTPException(404,'Unknown or expired Terraform emulation.')
    return await emulation_status(payload.jobId)
