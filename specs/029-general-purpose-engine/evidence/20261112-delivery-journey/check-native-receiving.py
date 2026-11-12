from pathlib import Path
import hashlib,io,json,sqlite3,sys
from types import SimpleNamespace
import zipfile
from server.engineering_sessions import SqliteSessionStore,ProjectScope,EngineeringSessions
from server.engineering_artifacts import EngineeringArtifacts
from server.engineering_contexts import EngineeringContexts
from server.engineering_reconciliation import EngineeringReconciliation
from server.engineering_handoff import EngineeringHandoff
from server.validation_jobs import ValidationJobs
root=Path.cwd();out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
source=root/'.local/provider-transfer-preview/c11fdbc-gcp/engineering/control.sqlite'
backup=out/'control.sqlite'
if not backup.exists():
 original=sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True)
 with sqlite3.connect(backup)as destination:original.backup(destination)
 original.close()
store=SqliteSessionStore(backup)
sha='69bdacf7d6813bfdd977b007abe7c94d8c3308cb2e09f9fd09c6cb39cf61031d'
row=store.db.execute('SELECT a.id,a.session,s.tenant,s.project FROM engineering_artifacts a JOIN engineering_sessions s ON s.id=a.session WHERE json_extract(a.manifest,\'$.sha256\')=?',(sha,)).fetchone();assert row
scope=ProjectScope(row['tenant'],row['project']);saved=(root/'.local/provider-transfer-preview/c11fdbc-gcp/projects'/f'{scope.project}.atforma.json').read_bytes()
artifacts=EngineeringArtifacts(store);contexts=EngineeringContexts(store)
checks=ValidationJobs(store,artifacts,None,[])
worker=SimpleNamespace(store=store,artifacts=artifacts,checks=checks,reconciliation=EngineeringReconciliation(store,artifacts,contexts),jobs=SimpleNamespace(state=lambda scope,session:EngineeringSessions._public(store.get(scope,session))))
engine=EngineeringHandoff(worker);report=engine.inspect(scope,saved)
assert report['artifact']['sha256']==sha,report['artifact']['sha256']
assert report['canPackage'],report['relation']
data,manifest=engine.package(scope,saved,row['session'],row['id'],report['savedDesignSha256'])
(out/'handoff.zip').write_bytes(data)
with zipfile.ZipFile(io.BytesIO(data))as receiving:
 original_zip=receiving.read('evidence/original-implementation.zip');assert hashlib.sha256(original_zip).hexdigest()==sha
 files=[entry for entry in manifest['files']if entry['kind']=='file']
 for entry in files:
  content=receiving.read('implementation/'+entry['path']);assert len(content)==entry['bytes'];assert hashlib.sha256(content).hexdigest()==entry['sha256']
 spec=[entry['path']for entry in files if entry['path'].startswith(('spec-kit/','specs/'))];assert spec,spec
 assert {'specs/001-sample-routing/spec.md','specs/001-sample-routing/plan.md','specs/001-sample-routing/tasks.md'}.issubset(spec)
 receipt=json.loads(receiving.read('evidence/artifact-receipt.json'));assert receipt==manifest
 local_checks=json.loads(receiving.read('evidence/local-checks.json'));assert local_checks==report['checks']
 assert receiving.read('design/latest-saved-project.json')==saved
 result={'passed':True,'sourceArtifactSha256':sha,'handoffSha256':hashlib.sha256(data).hexdigest(),'nativeFilesUnpackedAndHashed':len(files),'specKitFiles':spec,'relation':report['relation'],'recordedChecks':len(local_checks),'checkStatuses':[c['result']['status']if c.get('result')else c['state']for c in local_checks],'inputDatabase':'read-only SQLite backup; no source writes','modelCalls':0,'cloudOperations':False,'applicationRetested':False,'boundary':'Receiving byte/file/context/check preservation for a real prior native package; no new full-system acceptance'}
(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
store.close()
