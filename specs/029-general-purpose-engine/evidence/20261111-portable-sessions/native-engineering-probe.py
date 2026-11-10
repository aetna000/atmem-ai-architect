import asyncio,hashlib,json,pathlib,sys,tempfile,time
ROOT=pathlib.Path.cwd();sys.path.insert(0,str(ROOT))
from server.codex_engineering_backend import CodexEngineeringBackend
from server.engineering_sessions import EngineeringSessions,SqliteSessionStore,ProjectScope,ModelSelection
OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-portable-sessions'
async def main():
 with tempfile.TemporaryDirectory(prefix='atmem-native-work-') as folder:
  base=pathlib.Path(folder);workspace=base/'workspace';workspace.mkdir()
  scope=ProjectScope('local-qualification','reservation-domain');selection=ModelSelection('gpt-6.1-sol','high')
  registrations={(scope,'workspace-reservations'):workspace}
  store=SqliteSessionStore(base/'control.sqlite');backend=CodexEngineeringBackend(registrations)
  transcript=[]
  async def consume(engine,session,withhold_completion=False):
   deadline=time.monotonic()+180
   while time.monotonic()<deadline:
    try:
     if withhold_completion:
      raw=await backend.next_event(scope,store.get(scope,session)['handle'])
      event={'kind':raw.kind,'text':raw.text,'withheldFromCoordinator':True}
     else:
      event=await engine.next_event(scope,session)
    except asyncio.TimeoutError:continue
    transcript.append(event)
    print(event['kind'],event['text'][:240],flush=True)
    if event['kind'] in {'completed','failed','interrupted'}:
     assert event['kind']=='completed',event
     return
   raise TimeoutError('Engineering probe exceeded 180s')
  try:
   engine=EngineeringSessions(store,backend)
   created=await engine.create(scope,'workspace-reservations',selection);session=created['id']
   await engine.start(scope,session,'Create reservations.py using only Python standard library. Implement reserve(capacity, booked, requested) returning booked+requested only if all arguments are nonnegative integers (booleans are invalid) and the result does not exceed capacity; otherwise raise ValueError. Add test_reservations.py with success, full-capacity, invalid-input and over-capacity tests, then run python3 -m unittest -v. Use actual file and shell tools. No network, no services, no installations, no subagents. Finish when checks pass.')
   await consume(engine,session,withhold_completion=True)
   assert store.get(scope,session)['state']=='running'
   assert (workspace/'reservations.py').is_file()
   handle=store.get(scope,session)['handle']
   await backend.close();store.close()
   store=SqliteSessionStore(base/'control.sqlite');backend=CodexEngineeringBackend(registrations)
   engine=EngineeringSessions(store,backend);resumed=await engine.resume(scope,session)
   assert resumed['id']==session and resumed['last_status']=='completed'
   await engine.start(scope,session,'Continue the existing workspace: add release(booked, count) to reservations.py. Both inputs must be nonnegative integers (not booleans), count must not exceed booked; return booked-count, else raise ValueError. Preserve reserve and its tests. Add release tests and run the complete Python unit suite. No network, services, installations or subagents.')
   await consume(engine,session)
   # Independent oracle, separate from generated tests and the agent's report.
   oracle='''import reservations as r
assert r.reserve(4,1,3)==4
assert r.release(4,3)==1
for args in [(4,3,2),(4,5,0),(-1,0,0),(4,0,-1),(4,True,1),(4,0,1.5)]:
 try:r.reserve(*args)
 except ValueError:pass
 else:raise AssertionError(args)
for args in [(1,2),(True,0),(1,-1),(1,0.2)]:
 try:r.release(*args)
 except ValueError:pass
 else:raise AssertionError(args)
print('Independent reservation oracle passed')
'''
   proc=await asyncio.create_subprocess_exec(sys.executable,'-c',oracle,cwd=workspace,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
   stdout,stderr=await proc.communicate();assert proc.returncode==0,stderr.decode()
   artifacts={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'text':p.read_text()} for p in workspace.glob('*.py')}
   receipt={'passed':True,'model':selection.model,'effort':selection.effort,'restartedWorkerAndStore':True,'reconciledLostTerminalNotification':True,'nativeHandleSha256':hashlib.sha256(handle.encode()).hexdigest(),'engineeringTurns':2,'cloudOperations':False,'independentOracle':stdout.decode(),'artifacts':artifacts,'events':transcript,'boundary':'Real native model file/tool turns, withheld coordinator completion and history reconciliation after worker/store restart; local generated Python checks and independent oracle. No Terraform quality, UI integration or hosted isolation claim.'}
   (OUT/'native-engineering-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
   print('PASS actual engineering, restart, second turn and oracle',flush=True)
  finally:
   await backend.close();store.close()
asyncio.run(main())
