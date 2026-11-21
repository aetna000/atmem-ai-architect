"""Read-only native-history and durable-call proof for the explicit transfer fixture."""
import asyncio,hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.codex_worker_policy import CodexWorkerClient

def sha(text):return hashlib.sha256(text.encode()).hexdigest()
async def main():
 run=ROOT/'.local/engine-product/native-tools-transfer';context=json.loads((run/'initial/context.json').read_text());config=json.loads((ROOT/'.local/engineering-preview/operator-toolchain.json').read_text());db=sqlite3.connect('file:'+str(ROOT/'.local/engineering-preview/engineering/control.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 row=dict(db.execute('SELECT * FROM engineering_sessions WHERE id=?',(context['sessionId'],)).fetchone());path=db.execute('SELECT path FROM engineering_workspaces WHERE id=?',(row['workspace'],)).fetchone()[0]
 turns=[dict(r) for r in db.execute('SELECT turn,status FROM engineering_runs WHERE session=? ORDER BY rowid',(row['id'],))]
 calls=[]
 for raw in db.execute('SELECT turn,call,request,state,result FROM engineering_tool_calls WHERE session=? ORDER BY rowid',(row['id'],)):
  args=json.loads(raw['request']);result=json.loads(raw['result']) if raw['result'] else None
  calls.append({'turnIdentitySha256':sha(raw['turn']),'callIdentitySha256':sha(raw['call']),'tool':args['tool'],'requestSha256':sha(raw['request']),'state':raw['state'],'success':result['success'] if result else None,'resultSha256':sha(raw['result'])if raw['result']else None})
 worker=CodexWorkerClient(path,read_roots=config['readRoots'])
 try:
  await worker.start();await worker.verify_worker_tools()
  history=await worker.request('thread/turns/list',{'threadId':row['handle'],'limit':100,'sortDirection':'desc','itemsView':'notLoaded'})
  observed={r['id']:r['status']for r in history['data']}
  matched=[{'turnIdentitySha256':sha(r['turn']),'storedStatus':r['status'],'nativeStatus':observed.get(r['turn'])}for r in turns]
 finally:await worker.close()
 receipt={'sourceCommit':'3ef54bc','context':context,'model':row['model'],'effort':row['effort'],'nativeHandleSha256':sha(row['handle']),'turns':matched,'calls':calls,'sameNativeHistoryContainsBothTurns':len(matched)==2 and all(r['nativeStatus']=='completed' and r['storedStatus']=='completed' for r in matched),'cloudOperations':False,'boundary':'Read-only durable control state and exact native history from one stored thread: two real completed native turns across an HTTP/worker restart, successful knowledge and registered-check callbacks. Explicit distance-module qualification fixture, not uncoached architecture, independent holdout, hosted isolation or 28-case acceptance.'}
 (run/'native-history-audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'matchedCompletedTurns':len(matched),'sameThread':receipt['sameNativeHistoryContainsBothTurns'],'tools':[r['tool']for r in calls]},indent=2));assert receipt['sameNativeHistoryContainsBothTurns'] and len(calls)>=8 and all(r['success'] for r in calls)
asyncio.run(main())
