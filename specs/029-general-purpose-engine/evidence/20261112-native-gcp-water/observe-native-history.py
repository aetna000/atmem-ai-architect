"""Read a separate client's persisted turn history; no inference or replay.

This can differ from the original client's active view. Correlate original live
events; never use this snapshot alone to terminate, recover or replay a live job."""
import asyncio,hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.codex_worker_policy import CodexWorkerClient


async def main():
    evidence=ROOT/'specs/029-general-purpose-engine/evidence/20261112-native-gcp-water';context=json.loads((evidence/'context-v1.json').read_text());home=ROOT/'.local/provider-transfer-preview/c11fdbc-gcp';db=sqlite3.connect('file:'+str(home/'engineering/control.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    row=db.execute('select * from engineering_sessions where id=? and project=?',(context['sessionId'],context['projectId'])).fetchone();workspace=db.execute('select path from engineering_workspaces where id=?',(row['workspace'],)).fetchone()[0];runs=[dict(r)for r in db.execute('select id,turn,status from engineering_runs where session=? order by rowid',(row['id'],))];config=json.loads((home/'tools.json').read_text());worker=CodexWorkerClient(workspace,read_roots=config['readRoots'])
    try:
        await worker.start();await worker.verify_worker_tools();history=await worker.request('thread/turns/list',{'threadId':row['handle'],'limit':100,'sortDirection':'desc','itemsView':'notLoaded'});statuses={item['id']:item['status']for item in history['data']}
    finally:await worker.close()
    receipt={'sessionId':row['id'],'model':row['model'],'effort':row['effort'],'storedState':row['state'],'runs':[{'id':r['id'],'turnSha256':hashlib.sha256(r['turn'].encode()).hexdigest(),'storedStatus':r['status'],'nativeStatus':statuses.get(r['turn'])}for r in runs],'inferenceTurnsSubmitted':0,'boundary':'Read-only original native turn history; no resume, replay, interruption or application acceptance'}
    out=evidence/('native-history-'+sys.argv[1]+'.json');assert not out.exists();out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


asyncio.run(main())
