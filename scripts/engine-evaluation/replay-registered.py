"""Replay explicit operator validators on unchanged captured bytes; no inference."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker
from server.validation_jobs import registered_validators
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--artifact',type=Path,required=True)
parser.add_argument('--manifest',type=Path,required=True)
parser.add_argument('--validators',type=Path,required=True)
parser.add_argument('--validator',action='append',required=True)
parser.add_argument('--profiles',type=Path)
parser.add_argument('--endpoint',required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();content=args.artifact.read_bytes();digest=hashlib.sha256(content).hexdigest()
assert digest==json.loads(args.manifest.read_text())['sha256'],'Capture digest mismatch'
validators=registered_validators(json.loads(args.validators.read_text()))
if len(set(args.validator))!=len(args.validator) or any(ident not in validators for ident in args.validator):parser.error('Choose unique registered validators')
out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
worker=DockerValidationWorker(args.endpoint,isolation_profiles=json.loads(args.profiles.read_text()) if args.profiles else None)
results=[]
for ident in args.validator:
    result=worker.run(content,digest,validators[ident].spec)
    (out/(ident+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    results.append({'validatorId':ident,'status':result['status'],'testsReported':result.get('testsReported'),'skipped':result.get('skipped')})
    print(ident,result['status'],result.get('testsReported'),flush=True)
(out/'receipt.json').write_text(json.dumps({'passed':all(r['status']=='passed' for r in results),'artifactSha256':digest,'results':results,'workerIdentitySha256':worker.identity_digest,'policySha256':worker.policy_digest,'inferenceTurns':0,'cloudOperations':False,'boundary':'Explicit operator-registered local check replay against unchanged captured bytes. Generated test success is not independent requirement or complete-system acceptance.'},indent=2)+'\n')
if any(r['status']!='passed' for r in results):raise SystemExit(1)
