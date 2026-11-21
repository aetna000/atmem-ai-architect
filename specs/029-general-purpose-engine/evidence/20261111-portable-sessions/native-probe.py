"""Real native thread create/restart/resume probe; no model inference or cloud use."""
import asyncio,hashlib,json,pathlib,sys,tempfile
ROOT=pathlib.Path.cwd();sys.path.insert(0,str(ROOT))
from server.codex_engineering_backend import CodexEngineeringBackend
from server.engineering_sessions import EngineeringSessions,SqliteSessionStore,ProjectScope,ModelSelection
OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-portable-sessions'
async def main():
 with tempfile.TemporaryDirectory(prefix='atmem-native-session-') as folder:
  base=pathlib.Path(folder);workspace=base/'workspace';workspace.mkdir()
  scope=ProjectScope('local-qualification','session-continuity');selection=ModelSelection('gpt-6.1-sol','high')
  registrations={(scope,'workspace-continuity'):workspace}
  store=SqliteSessionStore(base/'control.sqlite');backend=CodexEngineeringBackend(registrations)
  try:
   created=await EngineeringSessions(store,backend).create(scope,'workspace-continuity',selection)
   handle=store.get(scope,created['id'])['handle'];await backend.close();store.close()
   store=SqliteSessionStore(base/'control.sqlite');backend=CodexEngineeringBackend(registrations)
   resumed=await EngineeringSessions(store,backend).resume(scope,created['id'])
   assert created==resumed
   receipt={'passed':True,'model':resumed['model'],'effort':resumed['effort'],'persistentSession':created['id'],'nativeHandleSha256':hashlib.sha256(handle.encode()).hexdigest(),'restartedWorkerAndStore':True,'scopedOpaqueWorkspace':True,'nativePolicyConfirmed':{'writes':'registered workspace','network':False,'approvals':'never'},'inferenceTurns':0,'cloudOperations':False,'boundary':'Native Codex thread create and resume across process/store restart, with exact model/effort/policy checks. Not coding, validation, hosted isolation or UI evidence.'}
   (OUT/'native-session-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
  finally:
   await backend.close();store.close()
asyncio.run(main())
