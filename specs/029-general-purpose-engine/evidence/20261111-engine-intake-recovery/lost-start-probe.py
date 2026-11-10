"""Withhold a real native turn acknowledgement, restart, recover by client identity."""
import asyncio,hashlib,json,pathlib,sys,tempfile,time
ROOT=pathlib.Path.cwd();sys.path.insert(0,str(ROOT))
from server.codex_engineering_backend import CodexEngineeringBackend
from server.engineering_sessions import EngineeringSessions,SqliteSessionStore,ProjectScope,ModelSelection
OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-engine-intake-recovery'
class LostAcknowledgement(CodexEngineeringBackend):
 async def start(self,*args,**kwargs):
  self.actual_turn=await super().start(*args,**kwargs)
  raise TimeoutError('Synthetic lost acknowledgement after actual native acceptance')
async def main():
 with tempfile.TemporaryDirectory(prefix='atmem-start-recovery-') as folder:
  root=pathlib.Path(folder);workspace=root/'workspace';workspace.mkdir()
  scope=ProjectScope('local-qualification','lost-start-identity');choice=ModelSelection('gpt-6.1-sol','high')
  registrations={(scope,'workspace-one'):workspace};store=SqliteSessionStore(root/'control.sqlite');backend=LostAcknowledgement(registrations)
  try:
   engine=EngineeringSessions(store,backend);public=await engine.create(scope,'workspace-one',choice);session=public['id']
   try:await engine.start(scope,session,'Create marker.txt containing exactly acknowledged-once and use python3 to check its contents. No network, no services, no subagents. Finish after the file check.')
   except TimeoutError:pass
   else:raise AssertionError('The acknowledgement was not withheld')
   row=store.get(scope,session);assert row['state']=='starting' and row['turn'] is None
   deadline=time.monotonic()+180;terminal=None
   while time.monotonic()<deadline:
    try:event=await backend.next_event(scope,row['handle'])
    except asyncio.TimeoutError:continue
    if event.kind in {'completed','failed','interrupted'}:terminal=event.kind;break
   assert terminal=='completed',terminal
   assert (workspace/'marker.txt').read_text().strip()=='acknowledged-once'
   real_turn=backend.actual_turn
   await backend.close();store.close()
   store=SqliteSessionStore(root/'control.sqlite');backend=CodexEngineeringBackend(registrations);engine=EngineeringSessions(store,backend)
   recovered=await engine.resume(scope,session);row=store.get(scope,session)
   result={'passed':recovered['state']=='idle' and recovered['last_status']=='completed' and row['turn']==real_turn,
           'inferenceTurns':1,'startRequests':1,'workReplayed':False,'recoveredByClientMessageIdentity':row['turn']==real_turn,
           'model':choice.model,'effort':choice.effort,'nativeTurnSha256':hashlib.sha256(real_turn.encode()).hexdigest(),
           'markerSha256':hashlib.sha256((workspace/'marker.txt').read_bytes()).hexdigest(),'cloudOperations':False,
           'boundary':'Actual native turn acceptance with its acknowledgement withheld from the coordinator, real file/tool work, worker/store restart and UUID-correlated history recovery. No automatic resubmission, UI, Terraform or hosted isolation claim.'}
   (OUT/'lost-start-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert result['passed']
  finally:await backend.close();store.close()
receipt_path=OUT/'lost-start-receipt.json'
receipt_path.unlink(missing_ok=True)
try:
 asyncio.run(main())
except BaseException as error:
 if not receipt_path.exists():receipt_path.write_text(json.dumps({'passed':False,'errorType':type(error).__name__,'cloudOperations':False},indent=2)+'\n')
 raise
