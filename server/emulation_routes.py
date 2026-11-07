"""Provider-neutral emulation endpoint with a bounded local worker adapter.

A hosted adapter must enforce its own tenant identity and container isolation;
this local adapter is protected by the existing loopback session middleware.
"""
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,ConfigDict
from typing import Literal
from .settings import setting

ROOT=Path(__file__).resolve().parents[1]
router=APIRouter()
LOCK=asyncio.Lock()

class EmulationRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    project:dict
    environment:Literal['staging','production']='staging'


def emulate(payload):
    if setting('EMULATION_ENABLED')=='0':
        return {'version':1,'status':'unavailable','checks':[],'message':'Local emulation is disabled on this server.'}
    if importlib.util.find_spec('moto') is None:
        return {'version':1,'status':'unavailable','checks':[],'message':'The emulation worker is not installed on this server. Ask the server operator to enable the optional Moto backend.'}
    node=shutil.which('node')
    if not node:return {'version':1,'status':'unavailable','checks':[],'message':'The server-side generator is unavailable.'}
    with tempfile.TemporaryDirectory(prefix='atmem-emulation-') as folder:
        # No inherited SDK credentials, profiles, endpoint overrides, proxy or model keys.
        env={'PATH':os.getenv('PATH',''),'HOME':folder,'TMPDIR':folder,'AWS_ACCESS_KEY_ID':'testing','AWS_SECRET_ACCESS_KEY':'testing','AWS_DEFAULT_REGION':'ap-southeast-2','AWS_EC2_METADATA_DISABLED':'true','AWS_CONFIG_FILE':str(Path(folder)/'no-config'),'AWS_SHARED_CREDENTIALS_FILE':str(Path(folder)/'no-credentials'),'PYTHONHASHSEED':'0'}
        generated=subprocess.run([node,str(ROOT/'scripts/terraform-render.mjs')],input=json.dumps(payload.model_dump()),capture_output=True,text=True,cwd=ROOT,env=env,timeout=20)
        if generated.returncode:raise ValueError('Invalid project for generation')
        files=json.loads(generated.stdout)
        digests={name:hashlib.sha256(content.encode()).hexdigest() for name,content in files.items()}
        fingerprint=hashlib.sha256(json.dumps(digests,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        worker_digest=hashlib.sha256((ROOT/'server/emulation_worker.py').read_bytes()+(ROOT/'server/emulation_adapters.py').read_bytes()).hexdigest()
        metadata={'version':1,'workerDigest':worker_digest,'designRevision':payload.project.get('revision'),'environment':payload.environment,'artifactDigest':fingerprint,'fileDigests':digests,'cloudOperations':False,'terraformApply':'not_run'}
        tf=json.loads(files['main.tf.json'])
        if tf.get('locals',{}).get('unfinished_work'):
            return {**metadata,'status':'blocked','checks':[],'message':'Resolve the generated implementation gaps before emulation.','blockers':tf['locals']['unfinished_work']}
        for name,content in files.items():
            relative=Path(name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in name or not isinstance(content,str):raise ValueError('Unsafe generated path')
            target=Path(folder)/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content)
        process=subprocess.run([sys.executable,'-I',str(ROOT/'server/emulation_worker.py'),folder],cwd=folder,env=env,capture_output=True,text=True,timeout=90)
        if len(process.stdout)>1_000_000:raise ValueError('Emulation result exceeds bound')
        try:result=json.loads(process.stdout)
        except json.JSONDecodeError:return {**metadata,'status':'failed','checks':[],'message':'The isolated worker failed without a valid report; no success was recorded.'}
        if process.returncode and result.get('status')=='passed':raise ValueError('Worker exit contradicts report')
        return {**result,**metadata,'workspaceCleanup':'passed'}


@router.post('/api/emulation/run')
async def emulate_route(payload:EmulationRequest):
    if LOCK.locked():raise HTTPException(409,'An emulation is already running. Try again after it finishes.')
    async with LOCK:
        try:return await asyncio.to_thread(emulate,payload)
        except subprocess.TimeoutExpired:raise HTTPException(504,'Emulation timed out; the worker was stopped and no pass was recorded.')
        except (ValueError,OSError):raise HTTPException(422,'The generated project could not be emulated. Review the design and worker installation.')
