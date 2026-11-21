"""Actual native command sandbox checks on synthetic files/loopback; no inference."""
import asyncio,json,pathlib,sys,tempfile
ROOT=pathlib.Path.cwd();sys.path.insert(0,str(ROOT))
from server.codex_app_server import CodexAppServer
from server.codex_engineering_backend import CodexEngineeringBackend
OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-engine-intake-recovery'
async def main():
 with tempfile.TemporaryDirectory(prefix='atmem-native-boundary-') as folder:
  root=pathlib.Path(folder);workspace=root/'workspace';workspace.mkdir();canary=root/'other-project.txt';canary.write_text('SYNTHETIC OTHER PROJECT')
  received=[]
  async def serve(reader,writer):
   received.append(True);writer.close();await writer.wait_closed()
  listener=await asyncio.start_server(serve,'127.0.0.1',0)
  port=listener.sockets[0].getsockname()[1]
  client=CodexAppServer(workspace);checks=[]
  async def check(name,script):
   result=await client.request('command/exec',{'command':[sys.executable,'-c',script],'cwd':str(workspace),'sandboxPolicy':CodexEngineeringBackend._policy(workspace),'timeoutMs':15000})
   checks.append({'name':name,'passed':result['exitCode']==0,'exitCode':result['exitCode'],'stdout':result['stdout'],'stderr':result['stderr']})
  try:
   await client.start()
   await check('registered-workspace-write',"from pathlib import Path;Path('inside.txt').write_text('ok');assert Path('inside.txt').read_text()=='ok'")
   await check('sibling-write-denied',f"from pathlib import Path\np=Path({str(canary)!r})\ntry:p.write_text('CHANGED')\nexcept PermissionError:pass\nelse:raise AssertionError('Sibling write succeeded')")
   await check('loopback-network-denied',f"import socket\ns=socket.socket();s.settimeout(1)\ntry:s.connect(('127.0.0.1',{port}))\nexcept (PermissionError,OSError):pass\nelse:raise AssertionError('Loopback network succeeded')\nfinally:s.close()")
   assert canary.read_text()=='SYNTHETIC OTHER PROJECT'
   await asyncio.sleep(.05)
   result={'passed':all(c['passed'] for c in checks) and not received,'checks':checks,'listenerConnections':len(received),'canaryPreserved':True,'inferenceTurns':0,'cloudOperations':False,'boundary':'Actual command/exec sandbox-policy enforcement on local positive writes, sibling write denial and loopback network denial. Does not establish read isolation, plugin/MCP tool policy, model-selected tool parity, container isolation or hosted tenancy.'}
   (OUT/'sandbox-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert result['passed']
  finally:
   await client.close();listener.close();await listener.wait_closed()
asyncio.run(main())
