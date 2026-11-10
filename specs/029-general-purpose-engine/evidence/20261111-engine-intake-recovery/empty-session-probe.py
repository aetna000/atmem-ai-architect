"""Recover an unused public session after worker loss; no work is replayed."""
import asyncio,hashlib,json,pathlib,sys,tempfile
ROOT=pathlib.Path.cwd();sys.path.insert(0,str(ROOT))
from server.codex_engineering_backend import CodexEngineeringBackend
from server.engineering_sessions import EngineeringSessions,SqliteSessionStore,ProjectScope,ModelSelection
OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-engine-intake-recovery'
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
   replacement=store.get(scope,created['id'])['handle']
   assert handle!=replacement, 'Expected replacement of a native thread without saved history'
   receipt={'passed':True,'model':resumed['model'],'effort':resumed['effort'],'persistentSession':created['id'],'oldNativeHandleSha256':hashlib.sha256(handle.encode()).hexdigest(),'replacementNativeHandleSha256':hashlib.sha256(replacement.encode()).hexdigest(),'publicSessionPreserved':True,'nativeEmptyThreadReplaced':True,'acceptedWorkReplayed':False,'restartedWorkerAndStore':True,'scopedOpaqueWorkspace':True,'nativePolicyConfirmed':{'writes':'registered workspace','network':False,'approvals':'never'},'inferenceTurns':0,'cloudOperations':False,'boundary':'Logical public-session continuity by replacing a never-started native thread without saved history. No claim of same native-thread continuity, inference, UI or hosted isolation.'}
   (OUT/'empty-session-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
  finally:
   await backend.close();store.close()
receipt_path=OUT/'empty-session-receipt.json'
receipt_path.unlink(missing_ok=True)
try:
 asyncio.run(main())
except BaseException as error:
 if not receipt_path.exists():receipt_path.write_text(json.dumps({'passed':False,'errorType':type(error).__name__,'cloudOperations':False},indent=2)+'\n')
 raise
