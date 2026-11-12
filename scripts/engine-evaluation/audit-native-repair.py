"""Independent binding/behavior audit for the explicit rainfall repair fixture."""
import argparse,asyncio,hashlib,io,json,sqlite3,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.codex_worker_policy import CodexWorkerClient
from server.local_validation import DockerValidationWorker,ValidationSpec
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run',type=Path,required=True);parser.add_argument('--home',type=Path,required=True)
parser.add_argument('--tools',type=Path,required=True);parser.add_argument('--endpoint',required=True)
args=parser.parse_args();run=args.run.resolve();live=json.loads((run/'live.json').read_text())
def sha(value):return hashlib.sha256(value).hexdigest()
ORACLE=r'''
import random
from rainfall import total_mm
checks=0
def equal(values,expected):
 global checks
 before=list(values);assert total_mm(values)==expected,(values,expected);assert values==before;checks+=1
equal([],0);equal([9],9);equal([3,7,11],21);equal([0]*366,0);equal([1]*366,366);equal([10**400,0],10**400)
rng=random.Random(7159)
for size in range(1,80):
 values=[rng.randrange(10000)/8 for _ in range(size)];equal(values,sum(values))
for value in [True,False,None,'1','',{},[],1j,-1,-.1,float('inf'),float('-inf'),float('nan')]:
 try:total_mm([1,2,value])
 except TypeError:checks+=1
 else:raise AssertionError(('invalid reading accepted',repr(value)))
for value in [None,{},(),(1,2),'1',True,1,1.0,range(3)]:
 try:total_mm(value)
 except TypeError:checks+=1
 else:raise AssertionError(('non-list accepted',repr(value)))
try:total_mm([0]*367)
except ValueError:checks+=1
else:raise AssertionError('limit ignored')
print('INDEPENDENT_RAINFALL_PASSED',checks)
'''


async def main():
 db=sqlite3.connect('file:'+str(args.home.resolve()/'engineering/control.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 row=dict(db.execute('select * from engineering_sessions where id=?',(live['sessionId'],)).fetchone())
 finalizations=[{**dict(r),'payload':json.loads(r['payload'])} for r in db.execute('select * from engineering_finalizations where session=? order by rowid',(row['id'],))]
 assert len(finalizations)==2 and [r['state'] for r in finalizations]==['repair_finished','local_checks_passed']
 parent,child=finalizations;assert parent['payload']['repair']['runId']==child['run'] and parent['payload']['repair']['attempt']==1
 sources=[];archives=[]
 for item in finalizations:
  raw=db.execute('select * from engineering_artifacts where session=? and id=?',(row['id'],item['payload']['artifact']['id'])).fetchone()
  manifest=json.loads(raw['manifest']);content=bytes(raw['archive']);assert sha(content)==manifest['sha256']==item['payload']['artifact']['sha256']
  sources.append(manifest);archives.append(content)
  target=run/('initial-failed-package' if item==parent else 'automatic-final-package');target.mkdir(exist_ok=True)
  if (target/'artifact.zip').exists():assert (target/'artifact.zip').read_bytes()==content
  (target/'artifact.json').write_text(json.dumps(manifest,indent=2)+'\n');(target/'artifact.zip').write_bytes(content)
 with zipfile.ZipFile(io.BytesIO(archives[0])) as initial,zipfile.ZipFile(io.BytesIO(archives[1])) as final:
  test_names=[name for name in initial.namelist() if name.startswith('test_') and name.endswith('.py')]
  assert test_names and set(test_names)=={name for name in final.namelist() if name.startswith('test_') and name.endswith('.py')}
  unchanged={name:sha(initial.read(name)) for name in test_names};assert all(initial.read(name)==final.read(name) for name in test_names)
  changed=[name for name in initial.namelist() if name in final.namelist() and initial.read(name)!=final.read(name)]
  assert [name for name in changed if name!='README.md']==['rainfall.py'],changed
 assert sha((run/'artifact.zip').read_bytes())==sources[1]['sha256']==live['artifactSha256']
 calls=[];pages=[]
 for raw in db.execute('select * from engineering_tool_calls where session=? order by rowid',(row['id'],)):
  request=json.loads(raw['request']);result=json.loads(raw['result']) if raw['result'] else None
  calls.append({'tool':request['tool'],'turnIdentitySha256':sha(raw['turn'].encode()),'state':raw['state'],'success':result['success'] if result else None,'requestSha256':sha(raw['request'].encode()),'resultSha256':sha(raw['result'].encode()) if raw['result'] else None})
  if request['tool']=='atmem_check_read' and result and result['success']:
   value=json.loads(result['contentItems'][0]['text']);page=value.get('result',{}).get('outputPage')
   if page:pages.append({'checkId':request['arguments']['checkId'],'offset':page['offset'],'nextOffset':page['nextOffset'],'outputSha256':page['sha256'],'totalCharacters':page['totalCharacters']})
 failed_check=parent['payload']['checks'][0]
 assert any(page['checkId']==failed_check and page['offset']==0 and page['nextOffset'] is None for page in pages)
 runs=[dict(r) for r in db.execute('select id,turn,status from engineering_runs where session=? order by rowid',(row['id'],))]
 assert len(runs)==2 and runs[0]['id']==parent['run'] and runs[1]['id']==child['run']
 workspace=db.execute('select path from engineering_workspaces where id=?',(row['workspace'],)).fetchone()[0]
 config=json.loads(args.tools.read_text());worker=CodexWorkerClient(workspace,read_roots=config['readRoots'])
 try:
  await worker.start();await worker.verify_worker_tools()
  history=await worker.request('thread/turns/list',{'threadId':row['handle'],'limit':100,'sortDirection':'desc','itemsView':'notLoaded'})
  statuses={turn['id']:turn['status'] for turn in history['data']}
 finally:await worker.close()
 native=[{'runId':item['id'],'turnIdentitySha256':sha(item['turn'].encode()),'storedStatus':item['status'],'nativeStatus':statuses.get(item['turn'])} for item in runs]
 assert all(item['storedStatus']==item['nativeStatus']=='completed' for item in native)
 validator=DockerValidationWorker(args.endpoint);results=[]
 spec=ValidationSpec('independent-rainfall','sha256:48d884813cf44e927cf64c5529dd630dd3b18338c6dc727991eef9b71e934a20',('/usr/local/bin/python3','-c',ORACLE))
 for label,manifest,archive,expected in zip(['before','after'],sources,archives,['failed','passed']):
  result=validator.run(archive,manifest['sha256'],spec);(run/('independent-'+label+'.json')).write_text(json.dumps(result,indent=2)+'\n')
  assert result['status']==expected,result
  results.append({'phase':label,'status':result['status'],'artifactSha256':manifest['sha256'],'output':result['output']})
 assert 'INDEPENDENT_RAINFALL_PASSED 108' in results[-1]['output'],results[-1]
 (run/'independent-oracle.py').write_text(ORACLE)
 receipt={'passed':True,'sourceCommit':live['sourceCommit'],'sessionId':row['id'],'projectId':row['project'],'model':row['model'],'effort':row['effort'],'nativeTurns':native,'automaticRepairs':1,'unchangedTestSha256':unchanged,'changedFiles':changed,'calls':calls,'reportPages':pages,'independentOracleSha256':sha(ORACLE.encode()),'independentResults':results,'finalCheckedSha256':sources[1]['sha256'],'finalDownloadedMatchesCheckedBytes':True,'sourceChangedDuringRun':live['sourceChangedDuringRun'],'cloudOperations':False,'boundary':'Explicit deliberate-defect qualification through real primary UI/API/native thread; same-model bounded repair, full failed report read and unchanged generated tests. Independent isolated numeric/input/boundary behavior fails old bytes and passes repaired bytes. Not an uncoached architecture, hidden holdout, 28-case acceptance or quality advantage.'}
 (run/'binding-audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'nativeTurns':len(native),'calls':len(calls),'unchangedTests':len(unchanged),'independentOutput':results[-1]['output']},indent=2))


asyncio.run(main())
