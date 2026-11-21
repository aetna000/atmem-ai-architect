"""Exercise the real server generator/validator with credential-free native tools.

Uses public project input, not precompiled or caller-submitted Terraform. Native
Terraform commands are init -backend=false, validate and mock-provider test only.
"""
import argparse,json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project',type=Path,required=True)
parser.add_argument('--terraform',type=Path,required=True)
parser.add_argument('--mirror',type=Path,required=True)
parser.add_argument('--evidence',type=Path,required=True)
args=parser.parse_args()
if args.evidence.exists():parser.error('Preserve prior evidence; choose a fresh directory.')
args.evidence.mkdir(parents=True)
os.environ['ATMEM_ARCHITECT_TERRAFORM_BIN']=str(args.terraform.resolve());os.environ['ATMEM_ARCHITECT_PROVIDER_CACHE']=str(args.mirror.resolve())
os.environ.pop('ATMEM_ARCHITECT_TFLINT_BIN',None);os.environ.pop('ATFORMA_TFLINT_BIN',None)
from server.terraform_routes import validate,ValidationRequest
start=time.time();result=validate(ValidationRequest(project=json.loads(args.project.read_text())))
(args.evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
checks=result.get('checks',[]);modules={c['moduleId'] for c in checks if c.get('moduleId')};count=sum(c.get('testsReported',0) for c in checks if c.get('stage')=='test')
passed=result['status']=='passed' and len(modules)>=2 and count>0 and all(c['passed'] for c in checks)
for module in modules:
 if {c.get('stage') for c in checks if c.get('moduleId')==module}!={'init','validate','test'}:passed=False
receipt={'passed':passed,'moduleCount':len(modules),'mockTestsReported':count,'elapsedSeconds':round(time.time()-start,2),'artifactDigests':result.get('fileDigests',{}),'boundary':'Real public server generation, independent admission and native cached-provider schemas/mock plans. No model inference, application runtime, account plan or deployment.'}
(args.evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='artifactDigests'}));raise SystemExit(0 if passed else 1)
