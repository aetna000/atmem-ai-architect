"""Execute the delivered receiving verifier in clean CPython with immutable input."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec
content=(ROOT/'.local/external-artifacts/native-gcp-water/v1/native-run/artifact.zip').read_bytes();sha=hashlib.sha256(content).hexdigest();assert sha=='69bdacf7d6813bfdd977b007abe7c94d8c3308cb2e09f9fd09c6cb39cf61031d'
spec=ValidationSpec('receiving-verify-dependencies','sha256:48d884813cf44e927cf64c5529dd630dd3b18338c6dc727991eef9b71e934a20',('/usr/local/bin/python3','-I','/work/source/scripts/verify_artifacts.py'),platform='linux/amd64',timeout_seconds=30)
result=DockerValidationWorker('unix:///Users/javadtaghia/.avm/c/amd64/validator.sock').run(content,sha,spec)
with (ROOT/'.local/external-artifacts/native-amd64-runtime/v1/receiving-build-v1/dependency-verifier-v1.json').open('x')as target:target.write(json.dumps(result,indent=2)+'\n')
assert result['status']=='passed',result;print(result['output'])
