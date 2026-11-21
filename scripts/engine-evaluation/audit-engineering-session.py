"""Read-only native/history/artifact binding, optionally verifying capture identity.

No inference or work replay. All source/behavior acceptance remains separately scoped.
"""
import argparse,asyncio,hashlib,json,sqlite3,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.codex_worker_policy import CodexWorkerClient
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--home',type=Path,required=True);parser.add_argument('--tools',type=Path,required=True);parser.add_argument('--base');args=parser.parse_args()
def sha(value):return hashlib.sha256(value).hexdigest()


async def main():
 run=args.run.resolve();live=json.loads((run/'live.json').read_text());manifest=json.loads((run/'artifact.json').read_text());assert sha((run/'artifact.zip').read_bytes())==manifest['sha256'];assert live['sourceChangedDuringRun']==[]
 db=sqlite3.connect('file:'+str(args.home.resolve()/'engineering/control.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 row=dict(db.execute('select * from engineering_sessions where id=? and project=?',(live['sessionId'],live['projectId'])).fetchone());assert row['state']=='idle'
 runs=[dict(r) for r in db.execute('select id,turn,status from engineering_runs where session=? order by rowid',(row['id'],))]
 calls=[];pages=[]
 for raw in db.execute('select * from engineering_tool_calls where session=? order by rowid',(row['id'],)):
  request=json.loads(raw['request']);result=json.loads(raw['result']) if raw['result'] else None
  calls.append({'tool':request['tool'],'turnIdentitySha256':sha(raw['turn'].encode()),'state':raw['state'],'success':result['success'] if result else None,'requestSha256':sha(raw['request'].encode()),'resultSha256':sha(raw['result'].encode()) if raw['result'] else None})
  if request['tool']=='atmem_check_read' and result and result['success']:
   page=(json.loads(result['contentItems'][0]['text']).get('result') or {}).get('outputPage')
   if page:pages.append({'checkId':request['arguments']['checkId'],'offset':page['offset'],'nextOffset':page['nextOffset'],'outputSha256':page['sha256'],'totalCharacters':page['totalCharacters']})
 original=db.execute('select manifest from engineering_artifacts where session=? and run=? order by rowid limit 1',(row['id'],runs[0]['id'])).fetchone();original=json.loads(original['manifest'])
 assert original['pinnedInputs']==manifest['pinnedInputs']
 old_files={item['path']:item.get('sha256') for item in original['files'] if item['kind']=='file'};new_files={item['path']:item.get('sha256') for item in manifest['files'] if item['kind']=='file'}
 removed=sorted(set(old_files)-set(new_files));changed=sorted(name for name in old_files.keys()&new_files.keys() if old_files[name]!=new_files[name]);assert not removed
 workspace=db.execute('select path from engineering_workspaces where id=?',(row['workspace'],)).fetchone()[0];config=json.loads(args.tools.read_text());worker=CodexWorkerClient(workspace,read_roots=config['readRoots'])
 try:
  await worker.start();await worker.verify_worker_tools();history=await worker.request('thread/turns/list',{'threadId':row['handle'],'limit':100,'sortDirection':'desc','itemsView':'notLoaded'});observed={item['id']:item['status'] for item in history['data']}
 finally:await worker.close()
 native=[{'runId':item['id'],'turnIdentitySha256':sha(item['turn'].encode()),'storedStatus':item['status'],'nativeStatus':observed.get(item['turn'])} for item in runs];assert all(item['storedStatus']==item['nativeStatus']=='completed' for item in native)
 recapture=None
 if args.base:
  auth=json.load(urllib.request.urlopen(args.base+'/api/session'));context={'projectId':row['project'],'sessionId':row['id']}
  request=urllib.request.Request(args.base+'/api/engineering/capture',data=json.dumps(context).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+auth['token']})
  captured=json.load(urllib.request.urlopen(request));assert captured['id']==manifest['id'] and captured['sha256']==manifest['sha256'];recapture={'sameArtifactId':True,'sameSha256':True}
 receipt={'passed':True,'sourceCommit':live['sourceCommit'],'projectId':row['project'],'sessionId':row['id'],'model':row['model'],'effort':row['effort'],'nativeTurns':native,'calls':calls,'reportPages':pages,'originalPinnedInputsPreserved':True,'originalArtifactSha256':original['sha256'],'finalArtifactSha256':manifest['sha256'],'removedFiles':removed,'changedFiles':changed,'recapture':recapture,'sourceChangedDuringRun':[],'cloudOperations':False,'boundary':'Actual stored project/selection/pins, exact native terminal history, tool callback/report paging and immutable package/capture identity. No model turn is submitted; file preservation and native completion do not establish semantic or whole-system acceptance.'}
 (run/'session-binding-audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'nativeTurns':len(native),'calls':len(calls),'changedFiles':changed,'recapture':recapture},indent=2))


asyncio.run(main())
