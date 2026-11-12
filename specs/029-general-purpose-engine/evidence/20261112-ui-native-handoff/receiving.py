"""Independently run unchanged captured files in the explicit local browser worker."""
import argparse,dataclasses,hashlib,io,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.validation_workers import registered_workers
from server.validation_jobs import registered_validators
out=ROOT/'.local/external-artifacts/ui-native-handoff/v1';evidence=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=out/'independent-v1');args=parser.parse_args()
target=args.output.resolve();target.mkdir(exist_ok=False)
manifest=json.loads((out/'artifact.json').read_text());original=(out/'artifact.zip').read_bytes()
assert hashlib.sha256(original).hexdigest()==manifest['sha256']
data=io.BytesIO();verified=[]
with zipfile.ZipFile(io.BytesIO(original))as client,zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED)as archive:
    for entry in manifest['files']:
        if entry['kind']!='file':continue
        name=entry['path'];assert not name.startswith('/') and '..' not in name.split('/')
        content=client.read(name);assert hashlib.sha256(content).hexdigest()==entry['sha256'];verified.append(name)
        archive.writestr('client/'+name,content)
    for name in ['receiving.test.mjs','independent-cases.json']:archive.writestr('evaluator/'+name,(evidence/name).read_bytes())
payload=data.getvalue();digest=hashlib.sha256(payload).hexdigest();(target/'oracle-package.zip').write_bytes(payload)
workers=registered_workers(json.loads((ROOT/'.local/external-artifacts/validator-placement/v1/workers.json').read_text()))
worker=workers['arm-browser'].create()
registered=registered_validators(json.loads((out/'validators.json').read_text()))['node-browser-tests']
assert registered.runtime_evidence.matches_worker(worker)
spec=dataclasses.replace(registered.spec,name='independent-ui-receiving',command=('/usr/bin/node','--test','--test-reporter=tap','--test-concurrency=1','evaluator/receiving.test.mjs'))
result=worker.run(payload,digest,spec);(target/'check.json').write_text(json.dumps(result,indent=2)+'\n')
receipt={'sourceArtifactSha256':manifest['sha256'],'oraclePackageSha256':digest,'implementationFilesVerified':len(verified),'oracleSha256':hashlib.sha256((evidence/'receiving.test.mjs').read_bytes()).hexdigest(),'caseSha256':hashlib.sha256((evidence/'independent-cases.json').read_bytes()).hexdigest(),'status':result['status'],'testsReported':result['testsReported'],'skipped':result['skipped'],'workerIdentitySha256':worker.identity_digest,'workerPolicySha256':worker.policy_digest,'cloudOperations':False,'boundary':'Clean writable receiving copy/build, manifest hashes and original generated tests, then independent real HTTP/process/Chromium checks on unchanged built source. Local ARM64 pinned image, synthetic operator data and explicit browser fault injection. No original28/provider/account/deployment acceptance.'}
(target/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2));print(result.get('output','')[-16000:])
if result['status']!='passed':raise SystemExit(1)
