from .generation_lint import lint_generated
from .settings import setting
"""Local schema validation of server-generated Terraform. Never plan/apply or read cloud credentials."""
import asyncio
import re
import json
import hashlib
import sys
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import base64
import binascii
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from .request_uploads import RequestUploads, MAX_BYTES
from typing import Literal

router = APIRouter()
LOCK = asyncio.Lock()
ROOT = Path(__file__).resolve().parent.parent
UPLOADS = RequestUploads()

class UploadStart(BaseModel):
    model_config = ConfigDict(extra='forbid')
    bytes: int = Field(gt=0, le=MAX_BYTES, strict=True)
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')

class UploadId(BaseModel):
    model_config = ConfigDict(extra='forbid')
    uploadId: str = Field(pattern=r'^[a-f0-9]{48}$')

class UploadChunk(UploadId):
    index: int = Field(ge=0, strict=True)
    data: str = Field(min_length=1, max_length=174764)

@router.post('/api/terraform/uploads/start')
async def upload_start(payload: UploadStart):
    try:
        return UPLOADS.start(payload.bytes, payload.sha256)
    except ValueError as error:
        raise HTTPException(409, str(error))

@router.post('/api/terraform/uploads/chunk')
async def upload_chunk(payload: UploadChunk):
    try:
        return UPLOADS.append(payload.uploadId, payload.index, base64.b64decode(payload.data, validate=True))
    except (ValueError, binascii.Error) as error:
        raise HTTPException(422, str(error))

@router.post('/api/terraform/uploads/cancel')
async def upload_cancel(payload: UploadId):
    UPLOADS.cancel(payload.uploadId)
    return {'cancelled': True}

class ValidationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    project: dict
    environment: Literal['staging', 'production'] = 'staging'

def validate(payload):
    binary = setting('TERRAFORM_BIN') or shutil.which('terraform', path=str(ROOT/'.venv'/'bin')+os.pathsep+os.getenv('PATH', ''))
    if not binary:
        return {'status': 'unavailable', 'checks': [], 'message': 'Terraform is not installed. Install Terraform or set ATMEM_ARCHITECT_TERRAFORM_BIN for the local service. No CLI validation was run.'}
    node = shutil.which('node')
    if not node:
        return {'status': 'unavailable', 'checks': [], 'message': 'Node is unavailable to the local service.'}
    with tempfile.TemporaryDirectory(prefix='atforma-validate-') as folder:
        env = {'PATH': os.getenv('PATH', ''), 'HOME': folder, 'TMPDIR': folder, 'TF_IN_AUTOMATION': '1', 'CHECKPOINT_DISABLE': '1', 'AWS_EC2_METADATA_DISABLED': 'true'}
        cache=Path(setting('PROVIDER_CACHE') or ROOT/'.local/provider-cache')
        if cache.is_dir():
            env['TF_PLUGIN_CACHE_DIR']=str(cache)
            mirror=Path(folder)/'.atmem-provider-mirror.tfrc'
            mirror.write_text('provider_installation { filesystem_mirror { path = '+json.dumps(str(cache.resolve()))+' } }\n')
            env['TF_CLI_CONFIG_FILE']=str(mirror)
        generated = subprocess.run([node, str(ROOT/'scripts/terraform-render.mjs')], input=json.dumps(payload.model_dump()), capture_output=True, text=True, timeout=20, env=env, cwd=ROOT)
        if generated.returncode:
            raise ValueError('The project could not be converted to the trusted Terraform draft.')
        files = json.loads(generated.stdout)
        for name, content in files.items():
            relative=Path(name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in name or not isinstance(content,str):
                raise ValueError('Invalid generated artifact path')
            target=Path(folder)/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(content)
        file_digests={name:hashlib.sha256(content.encode()).hexdigest() for name,content in files.items()}

        checks = []
        quality=json.loads(files['generation-quality.json']) if 'generation-quality.json' in files else None
        if quality:
            fatal=quality.get('fatalFindings',[])
            checks.append({'name':'Independent generation consistency','passed':not fatal,'output':json.dumps(fatal) if fatal else 'No provider, missing-resource or unsafe-generation inconsistencies detected.'})
            if fatal:return {'status':'failed','checks':checks,'fileDigests':file_digests,'message':'Generation consistency failed; repair the generator before validation.'}

        if 'build-runtime.py' in files:
            result=subprocess.run([sys.executable,'-I','build-runtime.py'],cwd=folder,env=env,capture_output=True,text=True,timeout=120)
            checks.append({'name':'Deterministic application build','passed':result.returncode==0,'output':(result.stdout+'\n'+result.stderr)[-16000:]})
            if result.returncode:return {'status':'failed','checks':checks,'fileDigests':file_digests,'message':'Application build failed before provider initialization.'}
        for name, args in [('Provider initialization', ['init', '-backend=false', '-input=false', '-no-color']), ('Terraform schema validation', ['validate', '-json'])]:
            result = subprocess.run([binary, f'-chdir={folder}', *args], env=env, capture_output=True, text=True, timeout=120)
            checks.append({'name': name, 'passed': result.returncode == 0, 'output': (result.stdout+'\n'+result.stderr)[-16000:]})
            if result.returncode:
                return {'status': 'failed', 'checks': checks, 'message': 'Terraform checks failed. Review the diagnostics.'}
        lint_binary=setting('TFLINT_BIN')
        if lint_binary:
            lint=lint_generated(folder,lint_binary)
            checks.append(lint)
            if not lint['passed']:return {'status':'failed','checks':checks,'fileDigests':file_digests,'message':'Independent Terraform lint found issues. Regenerate after fixing the compiler.'}
        # Modules are derived by the server generator and independently admitted
        # against project ownership before any provider is initialized.
        for unit in quality.get('modules',[]) if quality else []:
            path=unit.get('path','')
            if not isinstance(path,str) or not re.fullmatch(r'units/unit_[0-9a-f]+',path):raise ValueError('Invalid admitted module path')
            target=Path(folder)/path
            for label,arguments in [('Provider initialization',['init','-backend=false','-input=false','-no-color']),('Terraform schema validation',['validate','-json']),('Generated mock-provider plans',['test','-no-color'])]:
                result=subprocess.run([binary,f'-chdir={target}',*arguments],env=env,capture_output=True,text=True,timeout=120)
                output=result.stdout+'\n'+result.stderr
                passed=result.returncode==0
                count=None
                if arguments[0]=='test':
                    summary=re.search(r'Success!\s+(\d+) passed,\s+(\d+) failed',output)
                    count=int(summary[1]) if summary else 0
                    passed=passed and bool(summary) and count>0 and int(summary[2])==0 and not re.search(r'\b[1-9][0-9]* skipped\b|\.\.\.\s+skip\b',output)
                checks.append({'name':label+' — '+unit['id'],'moduleId':unit['id'],'modulePath':path,'stage':arguments[0],'passed':bool(passed),'output':output[-16000:],**({'testsReported':count} if count is not None else {})})
                if not passed:return {'status':'failed','checks':checks,'fileDigests':file_digests,'message':'A required module check failed or reported no executed tests. No cloud deployment was attempted.'}
            if lint_binary:
                lint=lint_generated(target,lint_binary);lint['name']+=' — '+unit['id'];checks.append(lint)
                if not lint['passed']:return {'status':'failed','checks':checks,'fileDigests':file_digests,'message':'Independent module lint found issues. Repair the compiler and regenerate.'}
        local_tests=[]
        if any(name.startswith('app-tests/') and name.endswith('_test.py') for name in files):
            local_tests.append(('Generated application acceptance tests',[sys.executable,'-I','-m','unittest','discover','-s','app-tests','-p','*_test.py','-v']))
        if any(name.startswith('tests/') and name.endswith('.tftest.hcl') for name in files):
            local_tests.append(('Generated mock-provider plans',[binary,f'-chdir={folder}','test','-no-color']))
        for name,args in local_tests:
            result=subprocess.run(args,cwd=folder,env=env,capture_output=True,text=True,timeout=120)
            checks.append({'name':name,'passed':result.returncode==0,'output':(result.stdout+'\n'+result.stderr)[-16000:]})
            if result.returncode:return {'status':'failed','checks':checks,'fileDigests':file_digests,'message':'Generated acceptance checks failed. No cloud deployment was attempted.'}
        return {'status': 'passed', 'checks': checks, 'fileDigests':file_digests, 'message': 'Provider schema and available generated local tests passed. Mock plans are not account plans. No cloud deployment was run.'}


@router.post('/api/terraform/validate')
async def validate_route(payload: ValidationRequest):
    if LOCK.locked():
        raise HTTPException(409, 'A Terraform validation is already running.')
    async with LOCK:
        try:
            return await asyncio.to_thread(validate, payload)
        except subprocess.TimeoutExpired:
            raise HTTPException(504, 'Terraform validation timed out. No deployment was attempted.')
        except (ValueError, OSError):
            raise HTTPException(422, 'Could not validate the generated Terraform draft. Check the project and local Terraform installation.')

@router.post('/api/terraform/validate-upload')
async def validate_upload(payload: UploadId):
    if LOCK.locked():
        raise HTTPException(409, 'A Terraform validation is already running.')
    try:
        request = ValidationRequest.model_validate_json(UPLOADS.take(payload.uploadId))
    except (ValueError, ValidationError):
        raise HTTPException(422, 'The upload is incomplete, changed, or is not a valid project validation request.')
    return await validate_route(request)
