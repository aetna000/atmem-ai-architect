from .generation_lint import lint_generated
from .settings import setting
"""Local schema validation of server-generated Terraform. Never plan/apply or read cloud credentials."""
import asyncio
import json
import hashlib
import sys
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import Literal

router = APIRouter()
LOCK = asyncio.Lock()
ROOT = Path(__file__).resolve().parent.parent

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
        if cache.is_dir():env['TF_PLUGIN_CACHE_DIR']=str(cache)
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
