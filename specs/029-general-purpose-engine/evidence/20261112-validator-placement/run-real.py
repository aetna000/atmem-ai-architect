"""Two actual placed runtimes plus original-worker cleanup after receiver SIGKILL.

Only this experiment's SQLite/source/process/container resources are manipulated.
No inference, owner project, cloud account, host mounts or image pulls.
"""
import argparse,asyncio,hashlib,json,os,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.engineering_artifacts import EngineeringArtifacts
from server.engineering_sessions import SqliteSessionStore,ProjectScope,ModelSelection,SessionError
from server.validation_jobs import ValidationJobs,registered_validators
from server.validation_workers import registered_workers
from server.process_control_observation import PYTHON_PROCESS_CONTROLS

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--attempt',required=True);args=parser.parse_args();assert args.attempt.isalnum()
base=ROOT/'.local/external-artifacts/validator-placement/v1';out=base/('real-'+args.attempt);out.mkdir(mode=0o700)
definitions=json.loads((base/'workers.json').read_text());entries=json.loads((base/'validators.json').read_text())
for entry in entries:
    path=base/('browser-observation-v1.json'if entry['workerId']=='arm-browser'else'amd64-observation-v1.json')
    entry['runtimeReceipt']={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
workers={name:registration.create()for name,registration in registered_workers(definitions).items()}
receipt={'format':'atmem.real-validator-placement','version':1,'attempt':args.attempt,'checks':[],
         'cloudOperations':False,'nativeModelRequests':0,'ownerProjectWrites':0,'resourcesCleaned':False,'passed':False}
client=out/'docker-client';client.mkdir(mode=0o700);(client/'config.json').write_text('{}')
child=None;original=None;peer=None;token=uuid.uuid4().hex
source_paths=[Path(__file__),Path(__file__).with_name('crash-receiver.py'),*[ROOT/'server'/name for name in ['validation_jobs.py','validation_workers.py','runtime_evidence.py','local_validation.py','engineering_routes.py','engineering_tools.py']]]
source_before={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in source_paths}
for path in source_paths:
    destination=out/'source-snapshot'/path.relative_to(ROOT);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(path.read_bytes())
def docker(role,*arguments,check=True):
    result=subprocess.run(['docker','--host',definitions[role]['endpoint'],'--config',str(client),*arguments],capture_output=True)
    if check and result.returncode:raise RuntimeError('Owned Docker '+arguments[0]+' failed')
    return result
def present(role,name):
    names=docker(role,'container','ls','-a','--filter','name=^/'+name+'$','--format','{{.Names}}').stdout.decode().splitlines()
    assert names in [[],[name]];return bool(names)
def verified(name,**facts):
    receipt['checks'].append({'name':name,**facts});(out/'checkpoint.json').write_text(json.dumps(receipt,indent=2)+'\n');print(name,flush=True)

async def positives():
    observation=json.loads((base/'amd64-observation-v1.json').read_text())
    expected_boot=observation['observed']['executionContext']['kernelBootSha256']
    source=out/'source';(source/'tests').mkdir(parents=True);(source/'checks').mkdir()
    (source/'tests/browser.test.mjs').write_text('''import test from 'node:test';import assert from 'node:assert/strict';
test('ARM64 actual sandboxed browser interaction',async()=>{
 assert.equal(process.arch,'arm64');
 const {chromium}=await import(process.env.ATMEM_PLAYWRIGHT_MODULE);
 const browser=await chromium.launch({headless:true,chromiumSandbox:true});
 try{const page=await browser.newPage();await page.setContent('<button>Apply</button><output>pending</output><script>document.querySelector("button").onclick=()=>document.querySelector("output").textContent="applied"</script>');await page.getByRole('button',{name:'Apply'}).click();assert.equal(await page.locator('output').textContent(),'applied');}finally{await browser.close();}
});\n''')
    python='''import os,platform,unittest,json,hashlib
from pathlib import Path
import psycopg
result={}
'''+PYTHON_PROCESS_CONTROLS+'''
class ActualRuntime(unittest.TestCase):
 def test_requested_machine_and_same_observed_boot(self):
  self.assertEqual(platform.machine(),'x86_64');self.assertEqual(result['executionContext']['kernelBootSha256'],EXPECTED_BOOT)
 def test_required_real_process_controls(self):
  self.assertTrue(result['processControls']['noNewPrivileges']['supported']);self.assertTrue(result['processControls']['seccompFilter']['supported'])
 def test_actual_postgresql17_fixture(self):
  with psycopg.connect(os.environ['ATMEM_TEST_POSTGRES_DSN'])as connection:self.assertTrue(connection.execute('SHOW server_version').fetchone()[0].startswith('17.11'))
'''
    (source/'checks/test_amd64.py').write_text('EXPECTED_BOOT='+repr(expected_boot)+'\n'+python)
    store=SqliteSessionStore(out/'positive-control.sqlite');artifacts=EngineeringArtifacts(store);scope=ProjectScope('local-owner','placement-positive-fixture')
    session=store.create(scope,'fixture-source','operator-fixture','no-native-thread',ModelSelection('fixture-no-inference','high'))['id']
    store.reserve(scope,session,'fixture-run','Owned dual-runtime fixture');store.attach_turn(scope,session,'fixture-run','fixture-turn');store.terminal(scope,session,'fixture-run','fixture-turn','completed')
    artifact=artifacts.capture(scope,session,source);jobs=ValidationJobs(store,artifacts,None,registered_validators(entries),workers=workers)
    try:
        catalog=jobs.catalog();assert jobs.worker is None and jobs.available()and all(row['available']for row in catalog)
        (out/'catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
        plan=jobs.plan(scope,session,artifact['id']);assert all(row['state']=='selected'for row in plan['decisions']);(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
        for entry in entries:
            check=await jobs.start(scope,session,artifact['id'],entry['id']);await asyncio.gather(*list(jobs.tasks.values()))
            result=jobs.get(scope,session,check['id']);assert result['result']['status']=='passed',result['result']
            assert result['result']['skipped']==0 and result['result']['testsReported']==(1 if entry['workerId']=='arm-browser'else 3)
            assert result['placement']['workerId']==entry['workerId']
            (out/(entry['id']+'.json')).write_text(json.dumps(result,indent=2)+'\n')
            verified('Actual '+entry['workerId']+' check passed',tests=result['result']['testsReported'],artifactSha256=artifact['sha256'])
        # Facts from the full AMD64 context may not follow an operator typo or
        # a legacy default change, even though the other real worker is present.
        original_entry=next(entry for entry in entries if entry['workerId']=='full-amd64')
        wrong={**original_entry,'id':'wrong-worker-facts','workerId':'arm-browser'}
        missing={**original_entry,'id':'missing-worker-tests','workerId':'missing-worker'}
        legacy={key:value for key,value in {**original_entry,'id':'legacy-wrong-context'}.items()if key!='workerId'}
        jobs.worker=workers['arm-browser']
        for entry in [wrong,missing,legacy]:
            jobs.validators.update(registered_validators([entry]))
            catalog_entry=next(row for row in jobs.catalog()if row['id']==entry['id'])
            assert not catalog_entry['available'] and catalog_entry['contractSha256']is None and 'runtimeEvidence'not in catalog_entry
            try:await jobs.start(scope,session,artifact['id'],entry['id'])
            except SessionError:pass
            else:raise AssertionError('Unqualified placement admitted a real check')
        assert store.db.execute('SELECT count(*)FROM artifact_validation_jobs').fetchone()[0]==2
        verified('Wrong-worker named facts, legacy changed-default context and missing placement rejected before execution',checkRows=2,unexpectedChecks=0)
        receipt['positiveArtifactSha256']=artifact['sha256']
    finally:await jobs.close();store.close()

async def recovery():
    global child,original,peer
    log=(out/'crash-receiver.log').open('wb')
    temporary=out/'receiver-tmp';temporary.mkdir(mode=0o700)
    child=subprocess.Popen([sys.executable,str(Path(__file__).with_name('crash-receiver.py')),'--out',str(out)],stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,env={'PATH':os.environ.get('PATH',''),'TMPDIR':str(temporary),'PYTHONDONTWRITEBYTECODE':'1','LANG':'C.UTF-8'})
    deadline=time.monotonic()+90;state=None
    while time.monotonic()<deadline:
        if child.poll()is not None:raise RuntimeError('Disposable receiver stopped before crash observation')
        try:state=json.loads((out/'crash-state.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):time.sleep(.1);continue
        original='atmem-validator-'+uuid.UUID(state['check']['id']).hex
        if present('full-amd64',original)and b'ATMEM_PLACEMENT_WAITING'in docker('full-amd64','logs',original).stdout:break
        time.sleep(.2)
    else:raise RuntimeError('No confirmed running original check; no crash simulated')
    peer=original
    browser=next(entry for entry in entries if entry['workerId']=='arm-browser')
    docker('arm-browser','run','--pull','never','-d','--name',peer,'--label','atmem.placement='+token,'--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user','65532:65532','--memory','64m','--pids-limit','16','--cpus','0.1','--entrypoint','/usr/bin/python3',browser['image'],'-I','-c','import time;time.sleep(180)')
    child.kill();code=child.wait(timeout=10);assert code<0;log.close()
    store=SqliteSessionStore(out/'crash-control.sqlite');artifacts=EngineeringArtifacts(store);scope=ProjectScope('local-owner',state['project'])
    jobs=ValidationJobs(store,artifacts,workers['arm-browser'],{},workers={'approved-original':workers['full-amd64']})
    try:
        before=jobs.get(scope,state['session'],state['check']['id']);assert before['state']=='recovery_required'
        result=await jobs.recover(scope,state['session'],state['check']['id'])
        assert result['result']['reason']=='supervisor_restart' and not present('full-amd64',original) and present('arm-browser',peer)
        manifest,content=artifacts.get(scope,state['session'],state['artifact']);assert hashlib.sha256(content).hexdigest()==state['check']['artifactSha256']
        assert store.db.execute('SELECT count(*)FROM artifact_validation_jobs').fetchone()[0]==1
        (out/'recovery.json').write_text(json.dumps(result,indent=2)+'\n')
        verified('Actual receiver SIGKILL recovers only original AMD64 container with default changed and validator removed',receiverExitCode=code,originalRemoved=True,peerSameUuidRetained=True,recordedArtifactUnchanged=True,checkRows=1,workReplayed=False)
    finally:await jobs.close();store.close()

async def main():
    try:
        await positives();await recovery();receipt['passed']=True
    except BaseException as error:
        receipt['failureType']=type(error).__name__;receipt['failure']=str(error);raise
    finally:
        if child is not None and child.poll()is None:child.kill();child.wait(timeout=10)
        if original is not None and present('full-amd64',original):workers['full-amd64'].recover(original.removeprefix('atmem-validator-'))
        if peer is not None and present('arm-browser',peer):
            info=json.loads(docker('arm-browser','inspect',peer).stdout)[0];assert info['Config']['Labels'].get('atmem.placement')==token;docker('arm-browser','rm','-f',peer)
        receipt['resourcesCleaned']=(original is None or not present('full-amd64',original))and(peer is None or not present('arm-browser',peer))
        receipt['sourceHashes']=source_before
        receipt['sourcesUnchangedDuringRun']=source_before=={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in source_paths}
        if not receipt['sourcesUnchangedDuringRun']:receipt['passed']=False
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

asyncio.run(main())
