"""Actual HTTP contract -> durable jobs -> native tools -> captured package.

In-process ASGI HTTP client, live signed-in native model; no fixture model/backend.
Uses a synthetic non-cloud client project. Independent oracle runs under the same
restricted command policy after the model finishes, never inside its brief.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path.cwd()
sys.path.insert(0,str(ROOT))
OUT = ROOT/'specs/029-general-purpose-engine/evidence/20261111-engineering-jobs'
roots = [Path(sys.executable).resolve().parent]
for name in ['bin','opt','Cellar','lib','share','Frameworks']:
    path = Path('/opt/homebrew')/name
    if path.is_dir(): roots.append(path)
temporary = tempfile.TemporaryDirectory(prefix='atmem-api-control-',dir='/tmp')
os.environ['ATMEM_ARCHITECT_HOME'] = temporary.name
os.environ['ATMEM_ARCHITECT_ENABLE_ENGINEERING'] = '1'
os.environ['ATMEM_ARCHITECT_ENGINEERING_TOOL_ROOTS'] = json.dumps([str(p) for p in roots])
from fastapi.testclient import TestClient
from server.app import app, TOKEN
from server import engineering_routes
from server.engineering_sessions import ProjectScope
from server.codex_worker_policy import PROFILE

project = 'synthetic-measurement-client'
project_path = Path(temporary.name)/'projects'/f'{project}.atforma.json'
project_path.parent.mkdir()
project_path.write_text(json.dumps({'format':'atmem.ai-architect.project','meta':{'name':'Measurement conversion'},
    'design':{'version':1,'revision':1,'requirements':'Preserve the existing telemetry service. Build an independent local conversion library. No cloud or AI dependencies.','provider':'tools','nodes':[],'edges':[]}}))
receipt_path = OUT/'live-api-receipt.json'
receipt_path.unlink(missing_ok=True)
receipt = {'passed':False,'model':'gpt-6.1-sol','effort':'high','cloudOperations':False,
    'boundary':'Real in-process ASGI HTTP contract, durable local control store and live native file/tool turn. Independent library oracle plus captured digest/restart checks; not a hosted/multi-tenant or deployed-system test.'}
try:
    with TestClient(app) as client:
        headers = {'Authorization':f'Bearer {TOKEN}'}
        def post(action,payload):
            response = client.post('/api/engineering/'+action,json={'projectId':project,**payload},headers=headers)
            response.raise_for_status()
            return response.json()
        state = post('create',{'model':receipt['model'],'effort':receipt['effort']})
        session = state['id']
        assert 'handle' not in state and 'workspace' not in state
        intent = '''Build an independent pure-Python measurement.py library with convert(value, source, target).
Support length units mm/cm/m and temperatures C/F, case-sensitive; convert within the same dimension and identity conversion.
Accept finite int/float values (reject booleans); reject unknown/incompatible units, strings and nonfinite numbers with ValueError.
Keep the existing telemetry service unchanged. No cloud, AI, networking or third-party runtime dependencies.
Write and execute meaningful unittest tests and a concise README with local run instructions. Use the supplied composition skill.
Create actual files in this workspace; keep the final reply concise. Do not deploy or install packages.'''
        (OUT/'live-intent.txt').write_text(intent+'\n')
        state = post('start',{'sessionId':session,'text':intent})
        deadline = time.monotonic()+300
        events, cursor = [], 0
        while time.monotonic()<deadline:
            result = post('events',{'sessionId':session,'after':cursor})
            events.extend(result['events'])
            if result['events']: cursor = result['events'][-1]['sequence']
            state = result['session']
            if state['state']=='idle': break
            time.sleep(.5)
        (OUT/'live-events.json').write_text(json.dumps(events,indent=2)+'\n')
        assert state['state']=='idle' and state['last_status']=='completed',state
        worker = engineering_routes.service()
        scope = ProjectScope('local-owner',project)
        async def owned_row(): return worker.store.get(scope,session)
        row = client.portal.call(owned_row)
        native,workspace,_ = worker.backend._owned(scope,row['handle'])
        oracle = '''import math
from measurement import convert
checks=0
def equal(value,source,target,expected):
 global checks
 assert math.isclose(convert(value,source,target),expected,rel_tol=1e-10,abs_tol=1e-10)
 checks+=1
for args in [(1,"m","cm",100),(1250,"mm","m",1.25),(2.5,"cm","mm",25),(-2,"m","cm",-200),(0,"C","F",32),(212,"F","C",100),(-40,"F","C",-40),(5,"mm","mm",5)]:equal(*args)
for args in [(True,"m","cm"),("2","m","cm"),(float("nan"),"m","cm"),(float("inf"),"C","F"),(1,"m","C"),(1,"M","m"),(1,"m","feet")]:
 try:convert(*args)
 except ValueError:checks+=1
 else:raise AssertionError("Invalid input accepted")
print("INDEPENDENT_ORACLE_PASSED",checks)
'''
        (OUT/'independent-oracle.py').write_text(oracle)
        async def run_oracle():
            return await native.request('command/exec',{'command':[str(Path(sys.executable).resolve()),'-c',oracle],
                'cwd':str(workspace),'permissionProfile':PROFILE,'env':{'TMPDIR':str(workspace/'.worker-tmp')},'timeoutMs':30000},timeout=40)
        result = client.portal.call(run_oracle)
        receipt['independentOracle'] = result
        assert result['exitCode']==0 and 'INDEPENDENT_ORACLE_PASSED 15' in result['stdout'],result
        manifest = post('capture',{'sessionId':session})
        download = client.post('/api/engineering/download',json={'projectId':project,'sessionId':session,'artifactId':manifest['id']},headers=headers)
        download.raise_for_status()
        assert hashlib.sha256(download.content).hexdigest()==manifest['sha256']==download.headers['x-artifact-sha256']
        (OUT/'live-generated-package.zip').write_bytes(download.content)
        (OUT/'live-artifact-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        client.portal.call(engineering_routes.close)
        recovered = post('recover',{'sessionId':session})
        assert recovered['id']==session and recovered['last_status']=='completed'
        replay = post('events',{'sessionId':session,'after':0})['events']
        assert sum(event['kind']=='accepted' for event in replay)==1
        assert len(replay)>=len(events)
        receipt.update(passed=True,sessionId=session,artifactSha256=manifest['sha256'],
            generatedFiles=[item['path'] for item in manifest['files'] if item['kind']=='file'],
            durableRestartRecovered=True,acceptedRequests=1,progressEvents=len(replay))
finally:
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    temporary.cleanup()
print(json.dumps(receipt,indent=2))
