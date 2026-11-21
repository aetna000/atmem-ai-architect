"""Run the unchanged captured Google package on the separately observed AMD64 guest."""
from pathlib import Path
import argparse,hashlib,json,sys
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--attempt",choices=["v1","v2"],default="v1")
parser.add_argument("--timeout-seconds",type=int,choices=[120,300],default=120)
args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.validation_jobs import registered_validators,ValidationJobs
from server.local_validation import DockerValidationWorker
from types import SimpleNamespace
bulk=ROOT/'.local/external-artifacts/native-amd64-runtime/v1'
entries=json.loads((ROOT/'.local/external-artifacts/native-gcp-water/v1/validators-observed.json').read_text())
entries[0]['timeoutSeconds']=args.timeout_seconds
path=bulk/'runtime-controls-v1.json';entries[0]['runtimeReceipt']={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
registrations=registered_validators(entries);registered=registrations['python-sql-gcp-tests']
worker=DockerValidationWorker('unix:///Users/javadtaghia/.avm/c/amd64/validator.sock')
controller=ValidationJobs.__new__(ValidationJobs);controller.worker=worker;controller.validators=registrations
(bulk/('catalog-'+args.attempt+'.json')).write_text(json.dumps(controller.catalog(),indent=2)+'\n')
content=(ROOT/'.local/external-artifacts/native-gcp-water/v1/native-run/artifact.zip').read_bytes();sha=hashlib.sha256(content).hexdigest()
assert sha=='69bdacf7d6813bfdd977b007abe7c94d8c3308cb2e09f9fd09c6cb39cf61031d'
assert registered.spec.timeout_seconds==args.timeout_seconds and registered.spec.executable_scratch
result=worker.run(content,sha,registered.spec)
with (bulk/('generated-tests-'+args.attempt+'.json')).open('x') as target:target.write(json.dumps(result,indent=2)+'\n')
print(json.dumps({key:value for key,value in result.items() if key not in {'output','command'}}))
if result['status']!='passed':raise SystemExit('Unchanged package failed; complete receipt retained')
