"""Prepare fresh local evaluator registrations; no execution, pull or deployment."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.validation_workers import registered_workers
from server.validation_jobs import registered_validators

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--arm-endpoint',required=True);parser.add_argument('--amd64-endpoint',required=True)
parser.add_argument('--browser-policy',type=Path,required=True);args=parser.parse_args()
here=Path(__file__).resolve().parent;base=ROOT/'.local/external-artifacts/validator-placement/v1'
workers=json.loads((here/'workers.example.json').read_text())
workers['arm-browser']['endpoint']=args.arm_endpoint;workers['full-amd64']['endpoint']=args.amd64_endpoint
workers['arm-browser']['isolationProfiles']['chromium-userns-v1']['path']=str(args.browser_policy.resolve(strict=True))
validators=json.loads((here/'validators.example.json').read_text())
for registration in registered_workers(workers).values():registration.create()
registered_validators(validators)
files={'workers.json':workers,'validators.json':validators,'browser-profiles.json':workers['arm-browser']['isolationProfiles']}
if any((base/name).exists()for name in files):raise ValueError('Preserve existing evaluator inputs; use a fresh receiving checkout/bulk directory')
base.mkdir(parents=True,exist_ok=True,mode=0o700)
for name,value in files.items():(base/name).write_text(json.dumps(value,indent=2)+'\n')
print('Prepared source-only evaluator registrations; observe both actual contexts before running tests.')
