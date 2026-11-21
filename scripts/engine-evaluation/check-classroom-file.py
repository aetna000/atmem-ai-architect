"""Independent local-file/readiness transfer oracle on immutable exported bytes."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker
from server.validation_jobs import registered_validators
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--validators',type=Path,required=True);parser.add_argument('--profiles',type=Path,required=True);parser.add_argument('--endpoint',required=True);parser.add_argument('--output',type=Path);args=parser.parse_args()
run=args.run.resolve();manifest=json.loads((run/'artifact.json').read_text());content=(run/'artifact.zip').read_bytes();assert hashlib.sha256(content).hexdigest()==manifest['sha256']
script=Path(__file__).with_name('classroom-file-oracle.mjs').read_text();entry=next(e for e in json.loads(args.validators.read_text())if e['id']=='node-browser-tests').copy();entry.update(id='independent-classroom-file',command=['/usr/bin/node','--input-type=module','-e',script],timeoutSeconds=90)
worker=DockerValidationWorker(args.endpoint,isolation_profiles=json.loads(args.profiles.read_text()));result=worker.run(content,manifest['sha256'],registered_validators([entry])[entry['id']].spec)
result.update(oracleSha256=hashlib.sha256(script.encode()).hexdigest(),boundary='Separately authored actual exported static-file Chromium/OS file-read, validation/math/security/storage and delayed initialization/cancellation/latest-file checks. A FileReader wrapper delays native read completion and ignores abort deliberately; unchanged application must invalidate old callbacks. Ephemeral HTTP serves only actual local assets for a script-startup prerequisite probe. No cloud or original28/holdout-generalization acceptance.')
target=args.output.resolve() if args.output else run/'independent-file-viewer.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['output']);assert result['status']=='passed',result
