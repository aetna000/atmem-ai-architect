"""Native beta profile enforcement and offline toolchain; synthetic canaries only."""
import asyncio,json,os,pathlib,sys,tempfile
from unittest.mock import patch
ROOT=pathlib.Path.cwd();sys.path.insert(0,str(ROOT))
from server.codex_engineering_backend import CodexEngineeringBackend
from server.codex_worker_policy import CodexWorkerClient,PROFILE
from server.engineering_sessions import ModelSelection,ProjectScope
OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-engine-intake-recovery'
async def main():
 with tempfile.TemporaryDirectory(prefix='atmem-profile-',dir='/tmp') as folder:
  base=pathlib.Path(folder);workspace=base/'workspace';workspace.mkdir();sibling=base/'other-project.txt';sibling.write_text('SYNTHETIC PRIVATE CANARY')
  (workspace/'read-escape').symlink_to(sibling)
  terraform=(ROOT/'.venv/bin/terraform').resolve();cache=(ROOT/'.local/provider-cache').resolve()
  roots=[terraform.parent,cache,pathlib.Path(sys.executable).resolve().parent]
  for name in ['bin','opt','Cellar','lib','share','Frameworks']:
   path=pathlib.Path('/opt/homebrew')/name
   if path.is_dir():roots.append(path)
  scope=ProjectScope('local-qualification','worker-read-boundary');choice=ModelSelection('gpt-6.1-sol','high')
  backend=CodexEngineeringBackend({(scope,'workspace-one'):workspace},permission_profile=PROFILE,client_factory=lambda root:CodexWorkerClient(root,read_roots=roots));checks=[];connections=[]
  async def serve(reader,writer):connections.append(True);writer.close();await writer.wait_closed()
  listener=await asyncio.start_server(serve,'127.0.0.1',0);port=listener.sockets[0].getsockname()[1]
  foreign_socket=base/'foreign.sock';unix_listener=await asyncio.start_unix_server(serve,path=str(foreign_socket))
  try:
   with patch.dict(os.environ,{'AWS_PROFILE':'synthetic-canary','ATMEM_SYNTHETIC_SECRET':'synthetic-only'}):
    handle=await backend.create(scope,'workspace-one',choice)
   client,root,_=backend._owned(scope,handle)
   async def command(name,argv,extra_env=None):
    env={'TMPDIR':str(root/'.worker-tmp'),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1',**(extra_env or {})}
    result=await client.request('command/exec',{'command':argv,'cwd':str(root),'permissionProfile':PROFILE,'env':env,'timeoutMs':30000},timeout=40)
    checks.append({'name':name,'passed':result['exitCode']==0,**result});return result
   async def python(name,script):return await command(name,[str(pathlib.Path(sys.executable).resolve()),'-c',script])
   await python('workspace-write-and-temporary-files',"from pathlib import Path;import tempfile,os\np=Path('inside.txt');p.write_text('ok');assert p.read_text()=='ok'\nwith tempfile.TemporaryFile() as f:f.write(b'local')\nassert os.environ.get('AWS_PROFILE') is None\nassert os.environ.get('ATMEM_SYNTHETIC_SECRET') is None")
   for name,path in [('sibling-read',sibling),('symlink-read',root/'read-escape')]:
    await python(name+'-denied',f"from pathlib import Path\ntry:Path({str(path)!r}).read_text()\nexcept PermissionError:pass\nelse:raise AssertionError('Foreign read was allowed')")
   await python('sibling-write-denied',f"from pathlib import Path\ntry:Path({str(sibling)!r}).write_text('CHANGED')\nexcept PermissionError:pass\nelse:raise AssertionError('Foreign write was allowed')")
   await python('loopback-network-denied',f"import socket\ns=socket.socket();s.settimeout(1)\ntry:s.connect(('127.0.0.1',{port}))\nexcept OSError:pass\nelse:raise AssertionError('Network access was allowed')\nfinally:s.close()")
   await python('raw-reserved-ip-denied',"import socket,errno\ns=socket.socket();s.settimeout(1)\ntry:s.connect(('192.0.2.1',80))\nexcept OSError as error:assert error.errno in (errno.EPERM,errno.EACCES),error\nelse:raise AssertionError('Raw IP connection succeeded')\nfinally:s.close()")
   unix_link=root/'.worker-tmp/foreign-link.sock';unix_link.symlink_to(foreign_socket)
   for name,path in [('foreign-unix-socket-denied',foreign_socket),('unix-symlink-escape-denied',unix_link)]:
    await python(name,f"import socket,errno\ns=socket.socket(socket.AF_UNIX);s.settimeout(1)\ntry:s.connect({str(path)!r})\nexcept OSError as error:assert error.errno in (errno.EPERM,errno.EACCES,errno.ENOENT),error\nelse:raise AssertionError('Foreign Unix socket was reachable')\nfinally:s.close()")
   infra=root/'infra';infra.mkdir()
   (infra/'main.tf.json').write_text(json.dumps({'terraform':{'required_providers':{'aws':{'source':'hashicorp/aws','version':'= 6.72.0'}}},'provider':{'aws':{'region':'ap-southeast-2'}},'resource':{'aws_s3_bucket':{'synthetic':{'bucket':'atmem-synthetic-profile-qualification'}}}}))
   (infra/'profile.tftest.hcl').write_text('mock_provider "aws" {}\nrun "synthetic_schema_plan" { command = plan }\n')
   config=root/'terraformrc';config.write_text('provider_installation { filesystem_mirror { path = '+json.dumps(str(cache))+' } }\n')
   env={'TF_CLI_CONFIG_FILE':str(config),'TF_LOG':'DEBUG'}
   for name,args in [('offline-provider-init',['init','-backend=false','-input=false','-no-color']),('native-provider-schema',['validate','-no-color']),('native-provider-mock-plan',['test','-no-color'])]:
    result=await command(name,[str(terraform),f'-chdir={infra}',*args],env)
    if result['exitCode']!=0:break
   tool_policy=await client.verify_worker_tools()
   checks.append({'name':'external-tools-disabled','passed':tool_policy['allDisabled'] and tool_policy['exposedMcpTools']==0,**tool_policy})
   assert sibling.read_text()=='SYNTHETIC PRIVATE CANARY'
   result={'passed':all(c['passed'] for c in checks) and not connections,'checks':checks,'profile':PROFILE,'allowedToolReadRoots':[str(p) for p in roots],'listenerConnections':len(connections),'canaryPreserved':True,'inferenceTurns':0,'cloudOperations':False,'boundary':'Actual local named-profile acknowledgement and command/exec read/write/network/environment enforcement; real cached AWS provider init/schema and mock plan only. Does not establish model-selected-tool parity, hosted tenant isolation, whole-system behavior or cloud deployment.'}
   (OUT/'read-profile-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert result['passed']
  finally:await backend.close();listener.close();unix_listener.close();await listener.wait_closed();await unix_listener.wait_closed()
receipt_path=OUT/'read-profile-receipt.json'
receipt_path.unlink(missing_ok=True)
try:
 asyncio.run(main())
except BaseException as error:
 if not receipt_path.exists():receipt_path.write_text(json.dumps({'passed':False,'errorType':type(error).__name__,'cloudOperations':False},indent=2)+'\n')
 raise
