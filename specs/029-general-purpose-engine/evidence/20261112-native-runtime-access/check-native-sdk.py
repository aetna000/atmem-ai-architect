"""Actual restricted native command worker, pinned runtime materialization/import.

No inference, SQL connection, cloud request or registration of private host trees.
"""
import asyncio,hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.codex_worker_policy import CodexWorkerClient,PROFILE
from server.engineering_delivery import seed_delivery
from server.engineering_assets.prepare_tools import python_launcher


async def main():
    config=json.loads((ROOT/'.local/native-runtime-preview/758ce64-work/tools.json').read_text())
    with tempfile.TemporaryDirectory(prefix='atm-sdk-',dir='/tmp')as tmp:
        root=Path(tmp).resolve();pins=seed_delivery(root);tools=root/'.tools';tools.mkdir();binary=tools/'python';binary.write_text(python_launcher(config['tools']['python']));binary.chmod(0o755)
        code=r'''
import hashlib,json,pathlib,sys
root=pathlib.Path.cwd();sys.path.insert(0,str(root/'atmem-tools'))
from importlib.machinery import SourceFileLoader
materialize=SourceFileLoader('materializer',str(root/'atmem-tools/materialize-runtime.py')).load_module().materialize
rows=[]
for provider in ['aws','azure','gcp','ibm']:
 manifest=materialize(root,provider,provider+'-app')
 assert all(hashlib.sha256((root/(provider+'-app')/name).read_bytes()).hexdigest()==digest for name,digest in manifest['files'].items())
 rows.append({'provider':provider,'files':len(manifest['files']),'catalogSha256':manifest['catalogSha256']})
sys.path.insert(0,str(root/'aws-app'))
import workflow_application,workflow_worker,workflow_process_stage,psycopg,procrastinate
assert pathlib.Path(workflow_worker.__file__).parent==root/'aws-app'
assert pathlib.Path(sys.prefix).resolve()==pathlib.Path(sys.argv[1]).resolve()
assert not({'jwt','fastapi','invoice_native','invoice_worker'}&set(sys.modules))
print(json.dumps({'passed':True,'python':sys.version.split()[0],'psycopg':psycopg.__version__,'providers':rows,'sqlConnections':0,'cloudOperations':False}))
'''
        worker=CodexWorkerClient(root,read_roots=config['readRoots'])
        try:
            await worker.start();await worker.verify_worker_tools()
            result=await worker.request('command/exec',{'command':[str(binary),'-I','-c',code,str(Path(config['tools']['python']).parent.parent)],'cwd':str(root),'permissionProfile':PROFILE,'env':{'TMPDIR':str(root/'.worker-tmp'),'OPENSSL_CONF':'/dev/null','PYTHONDONTWRITEBYTECODE':'1'},'timeoutMs':30000,'outputBytesCap':6000},timeout=40)
        finally:await worker.close()
        assert result['exitCode']==0,result
        observed=json.loads(result['stdout'].splitlines()[-1]);assert observed['passed']
        assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest for name,digest in pins.items())
        receipt={'passed':True,'pinnedInputsUnchanged':True,'inputDigests':pins,'observed':observed,'commandResult':result,'workerProfile':PROFILE,'inferenceTurns':0,'boundary':'Actual restricted worker and selected virtualenv import/materialization; no SQL execution, native IdP, managed service, application or system acceptance'}
        (ROOT/'specs/029-general-purpose-engine/evidence/20261112-native-runtime-access/native-sdk-command.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps({'passed':True,'providers':len(observed['providers']),'python':observed['python'],'pinnedInputsUnchanged':True}))


asyncio.run(main())
