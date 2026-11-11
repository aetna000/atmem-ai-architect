"""Actual isolated runtime proof for file selection and completed-turn checks.

Engineering lifecycle is an explicit fixture. No native inference, cloud access,
image download or generated-project acceptance is claimed by these probes.
"""
import argparse,asyncio,hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.engineering_artifacts import EngineeringArtifacts
from server.engineering_finalization import EngineeringFinalization
from server.engineering_jobs import EngineeringJobs
from server.engineering_sessions import EngineeringSessions,ModelSelection,ProjectScope,SqliteSessionStore
from server.local_validation import DockerValidationWorker
from server.validation_jobs import registered_validators,ValidationJobs

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--validators',type=Path,required=True)
parser.add_argument('--isolation-profiles',type=Path,required=True)
parser.add_argument('--endpoint',required=True)
parser.add_argument('--python-validator',required=True)
parser.add_argument('--browser-validator',required=True)
args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
entries=json.loads(args.validators.read_text());selected=[]
for ident,patterns in [(args.python_validator,['test_*.py']),(args.browser_validator,['**/*.test.mjs'])]:
    entry=next(entry for entry in entries if entry['id']==ident)
    selected.append({**entry,'applicability':{'anyOf':patterns}})
validators=registered_validators(selected)
worker=DockerValidationWorker(args.endpoint,isolation_profiles=json.loads(args.isolation_profiles.read_text()))
browser=r'''
import test from 'node:test';import assert from 'node:assert/strict';import http from 'node:http';
const {chromium}=await import(process.env.ATMEM_PLAYWRIGHT_MODULE);
test('Museum notice reaches actual Chromium through local HTTP',async()=>{
 const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end('<!doctype html><button id="show">Show notice</button><output id="notice"></output><script>document.querySelector("#show").onclick=()=>document.querySelector("#notice").textContent="Gallery opens at 10"</script>');});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));let browser;
 try{browser=await chromium.launch({headless:true,chromiumSandbox:true});const page=await browser.newPage();await page.goto(`http://127.0.0.1:${server.address().port}/`);assert.equal(await page.locator('#notice').textContent(),'');await page.locator('#show').click();assert.equal(await page.locator('#notice').textContent(),'Gallery opens at 10');}
 finally{await browser?.close();await new Promise(resolve=>server.close(resolve));}
});
'''
cases=[
    ('rainfall-positive',{'test_rainfall.py':'import unittest\nclass Rainfall(unittest.TestCase):\n def test_total(self):self.assertEqual(sum([2,4,6]),12)\n'},'local_checks_passed',args.python_validator,'passed'),
    ('museum-browser',{'ui/notice.test.mjs':browser},'local_checks_passed',args.browser_validator,'passed'),
    ('retained-failure',{'test_counterexample.py':'import unittest\nclass Counterexample(unittest.TestCase):\n def test_failure(self):self.fail("Deliberate failure must remain visible")\n'},'needs_attention',args.python_validator,'failed'),
    ('zero-tests',{'test_empty.py':'# Matching filename does not prove tests execute\n'},'needs_attention',args.python_validator,'failed'),
    ('skipped-tests',{'test_skipped.py':'import unittest\nclass Missing(unittest.TestCase):\n @unittest.skip("Missing evidence")\n def test_missing(self):pass\n'},'needs_attention',args.python_validator,'incomplete'),
    ('no-applicable-checks',{'README.txt':'No executable tests supplied'},'needs_attention',None,None)]


class FixtureBackend:
    name='explicit-lifecycle-fixture'
    async def close(self):pass


async def run():
    receipts=[]
    for name,files,expected,expected_validator,expected_status in cases:
        caseout=out/name;caseout.mkdir()
        with tempfile.TemporaryDirectory(prefix='atmem-finalization-probe-') as temp:
            root=Path(temp);workspace=root/'work';workspace.mkdir()
            for file,text in files.items():
                target=workspace/file;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
            store=SqliteSessionStore(root/'control.sqlite');scope=ProjectScope('local-owner',name)
            session=store.create(scope,'fixture-workspace','fixture','fixture-handle',ModelSelection('no-inference-fixture','high'))['id']
            store.reserve(scope,session,'fixture-run','Explicit local qualification fixture')
            store.attach_turn(scope,session,'fixture-run','fixture-turn');store.terminal(scope,session,'fixture-run','fixture-turn','completed')
            jobs=EngineeringJobs(EngineeringSessions(store,FixtureBackend()));artifacts=EngineeringArtifacts(store)
            checks=ValidationJobs(store,artifacts,worker,validators)
            finalizer=EngineeringFinalization(jobs,lambda scope,session:artifacts.capture(scope,session,workspace),lambda:checks)
            try:
                finalizer.observe(scope,session);await asyncio.gather(*list(finalizer.tasks.values()))
                result=finalizer.list(scope,session)[0]
                reports=[checks.get(scope,session,ident) for ident in result['checks']]
                (caseout/'finalization.json').write_text(json.dumps(result,indent=2)+'\n')
                (caseout/'reports.json').write_text(json.dumps(reports,indent=2)+'\n')
                (caseout/'events.json').write_text(json.dumps(jobs.journal.read(scope,session),indent=2)+'\n')
                manifest,content=artifacts.get(scope,session,result['artifact']['id'])
                (caseout/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(caseout/'source.zip').write_bytes(content)
                assert result['state']==expected,result
                assert [report['validatorId'] for report in reports]==([expected_validator] if expected_validator else []),reports
                assert all(report['artifactSha256']==hashlib.sha256(content).hexdigest() for report in reports)
                assert all(report['result']['status']==expected_status for report in reports),reports
                finalizer.observe(scope,session)
                assert len(finalizer.list(scope,session))==1 and not finalizer.tasks
                receipts.append({'name':name,'state':result['state'],'checks':[{'validator':r['validatorId'],'status':r['result']['status'],'testsReported':r['result'].get('testsReported'),'skipped':r['result'].get('skipped')}for r in reports],'artifactSha256':manifest['sha256']})
                print(name,result['state'],flush=True)
            finally:
                await finalizer.close();await checks.close();await jobs.close();store.close()
    source={file:hashlib.sha256((ROOT/file).read_bytes()).hexdigest() for file in ['server/engineering_finalization.py','server/validation_applicability.py','server/validation_jobs.py','server/engineering_jobs.py','server/local_validation.py','scripts/engine-evaluation/check-finalization.py']}
    (out/'receipt.json').write_text(json.dumps({'passed':True,'cases':receipts,'sourceSha256':source,'workerIdentitySha256':worker.identity_digest,'policySha256':worker.policy_digest,'registrations':selected,'cloudOperations':False,'boundary':'Explicit completed-lifecycle fixture, actual immutable capture/applicability/durable supervisor and isolated Python/Chromium execution. No native inference, independent client requirement coverage, original-project or release acceptance.'},indent=2)+'\n')


asyncio.run(run())
