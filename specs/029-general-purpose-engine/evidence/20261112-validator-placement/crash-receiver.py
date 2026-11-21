"""Disposable real receiver, intentionally killed by its owning evaluator only."""
import argparse,asyncio,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.engineering_artifacts import EngineeringArtifacts
from server.engineering_sessions import SqliteSessionStore,ProjectScope,ModelSelection
from server.validation_jobs import ValidationJobs,registered_validators
from server.validation_workers import registered_workers

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
out=args.out.resolve();base=ROOT/'.local/external-artifacts/validator-placement/v1'

async def main():
    scope=ProjectScope('local-owner','placement-recovery-fixture')
    store=SqliteSessionStore(out/'crash-control.sqlite');artifacts=EngineeringArtifacts(store)
    session=store.create(scope,'fixture-source','operator-fixture','no-native-thread',ModelSelection('fixture-no-inference','high'))['id']
    store.reserve(scope,session,'fixture-run','Owned receiver-crash experiment');store.attach_turn(scope,session,'fixture-run','fixture-turn');store.terminal(scope,session,'fixture-run','fixture-turn','completed')
    source=out/'crash-source';(source/'checks').mkdir(parents=True)
    (source/'checks/test_wait.py').write_text("import time,unittest\nclass Waiting(unittest.TestCase):\n def test_wait(self):\n  print('ATMEM_PLACEMENT_WAITING',flush=True)\n  time.sleep(180)\n")
    artifact=artifacts.capture(scope,session,source)
    entries=[entry for entry in json.loads((base/'validators.json').read_text())if entry['workerId']=='full-amd64']
    workers={name:registration.create()for name,registration in registered_workers(json.loads((base/'workers.json').read_text())).items()if name=='full-amd64'}
    jobs=ValidationJobs(store,artifacts,None,registered_validators(entries),workers=workers)
    try:
        check=await jobs.start(scope,session,artifact['id'],entries[0]['id'])
        (out/'crash-state.json').write_text(json.dumps({'project':scope.project,'session':session,'artifact':artifact['id'],'check':check},indent=2)+'\n')
        await asyncio.sleep(600)
    finally:
        await jobs.close();store.close()

asyncio.run(main())
