"""Read-only evidence binding for the explicit native working/browser fixture."""
import asyncio,hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.codex_worker_policy import CodexWorkerClient

def sha(value):return hashlib.sha256(value.encode()).hexdigest()
async def main():
 run=ROOT/'.local/engine-product/native-working-browser';live=json.loads((run/'live.json').read_text());db=sqlite3.connect('file:'+str(ROOT/'.local/engineering-preview/engineering/control.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;row=dict(db.execute('select * from engineering_sessions where id=?',(live['sessionId'],)).fetchone());path=db.execute('select path from engineering_workspaces where id=?',(row['workspace'],)).fetchone()[0]
 calls=[]
 for raw in db.execute('select turn,call,request,state,result from engineering_tool_calls where session=? order by rowid',(row['id'],)):
  request=json.loads(raw['request']);result=json.loads(raw['result'])if raw['result']else None;calls.append({'tool':request['tool'],'turnIdentitySha256':sha(raw['turn']),'callIdentitySha256':sha(raw['call']),'requestSha256':sha(raw['request']),'state':raw['state'],'success':result['success']if result else None,'resultSha256':sha(raw['result'])if raw['result']else None})
 checkpoints=[]
 for raw in db.execute('select manifest,archive from engineering_checkpoints where session=? order by rowid',(row['id'],)):
  manifest=json.loads(raw['manifest']);assert hashlib.sha256(bytes(raw['archive'])).hexdigest()==manifest['sha256'];checkpoints.append({key:manifest[key]for key in ['id','kind','runId','turnStatus','sha256','bytes']})
 deliveries=[json.loads(raw['manifest'])for raw in db.execute('select manifest from engineering_artifacts where session=?',(row['id'],))]
 checks=[]
 for raw in db.execute('select * from artifact_validation_jobs where session=? order by rowid',(row['id'],)):
  result=json.loads(raw['result'])if raw['result']else {};checks.append({'id':raw['id'],'sourceId':raw['artifact'],'sourceKind':'working_checkpoint' if any(c['id']==raw['artifact']for c in checkpoints)else'delivery','artifactSha256':raw['artifact_sha256'],'validator':raw['validator'],'contractSha256':raw['contract_sha256'],'state':raw['state'],'status':result.get('status'),'testsReported':result.get('testsReported'),'skipped':result.get('skipped'),'runtimeImageId':result.get('imageId'),'runtimeConfigImageId':result.get('runtimeConfigImageId'),'isolationProfile':result.get('isolationProfile')})
 config=json.loads((ROOT/'.local/engineering-preview/operator-toolchain.json').read_text());worker=CodexWorkerClient(path,read_roots=config['readRoots'])
 try:
  await worker.start();await worker.verify_worker_tools();history=await worker.request('thread/turns/list',{'threadId':row['handle'],'limit':100,'sortDirection':'desc','itemsView':'notLoaded'});observed={r['id']:r['status']for r in history['data']};runs=[dict(r)for r in db.execute('select turn,status from engineering_runs where session=?',(row['id'],))]
 finally:await worker.close()
 native=[{'turnIdentitySha256':sha(r['turn']),'storedStatus':r['status'],'nativeStatus':observed.get(r['turn'])}for r in runs];independent=json.loads((run/'independent-browser.json').read_text());delivery=deliveries[0]
 receipt={'sourceCommit':'838762a','projectId':row['project'],'sessionId':row['id'],'model':row['model'],'effort':row['effort'],'calls':calls,'nativeTurns':native,'checkpoints':checkpoints,'deliveryCount':len(deliveries),'deliverySha256':delivery['sha256'],'lastWorkingCheckpointMatchesDelivery':bool(checkpoints)and checkpoints[-1]['sha256']==delivery['sha256'],'checks':checks,'independentStatus':independent['status'],'independentOracleSha256':independent['oracleSha256'],'sourceChangedDuringRun':live['sourceChangedDuringRun'],'cloudOperations':False,'scope':'Explicit native working/browser-tool qualification, not an uncoached architecture or hidden holdout. Two in-progress immutable snapshots and one separate settled delivery; seven generated HTTP/Chromium tests and 20 separately authored final-artifact checks. No 28-case/release acceptance or hosted-isolation claim.'}
 (run/'binding-audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
 assert len(native)==1 and native[0]['nativeStatus']=='completed' and all(c['success']for c in calls) and len(checkpoints)==2 and len(deliveries)==1 and receipt['lastWorkingCheckpointMatchesDelivery'] and receipt['sourceChangedDuringRun']==[] and independent['artifactSha256']==delivery['sha256'] and independent['status']=='passed'
 assert len([c for c in calls if c['tool']=='atmem_check_working'])==2 and all(c['kind']=='working_checkpoint'and c['turnStatus']=='in_progress'for c in checkpoints)
 print(json.dumps({'calls':len(calls),'workingCheckpoints':len(checkpoints),'deliveries':len(deliveries),'sameFinalBytes':receipt['lastWorkingCheckpointMatchesDelivery'],'independent':independent['status']},indent=2))
asyncio.run(main())
