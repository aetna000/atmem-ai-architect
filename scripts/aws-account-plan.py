"""Read-only account plan for an already generated, locally reviewed qualification export."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import boto3
from botocore.config import Config

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export',type=Path,required=True)
    parser.add_argument('--region',required=True)
    parser.add_argument('--expected-account-file',type=Path,required=True)
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--reviewed-inputs',type=Path)
    parser.add_argument('--confirm-reviewed-plan',action='store_true',required=True)
    args=parser.parse_args();root=args.export.resolve()
    tf=json.loads((root/'main.tf.json').read_text())
    if tf.get('locals',{}).get('unfinished_work')!=[]:raise SystemExit('Unfinished implementation blocks account planning')
    principal_variables=[k for k in tf['variable'] if k.startswith('principal_')]
    if not any(name.startswith('aws_') for name in tf.get('resource',{})):raise SystemExit('No generated AWS resources to plan')
    expected=json.loads(args.expected_account_file.read_text())['aws_account_id']
    credentials={}
    for line in args.env_file.read_text().splitlines():
        line=line.strip().removeprefix('export ')
        if '=' not in line or line.startswith('#'):continue
        key,value=line.split('=',1)
        if key.strip() in ['AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN']:
            values=shlex.split(value,comments=True)
            if values:credentials[key.strip()]=values[0]
    if not all(credentials.get(k) for k in ['AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY']):raise SystemExit('Explicit AWS credentials are missing')
    session=boto3.Session(aws_access_key_id=credentials['AWS_ACCESS_KEY_ID'],aws_secret_access_key=credentials['AWS_SECRET_ACCESS_KEY'],aws_session_token=credentials.get('AWS_SESSION_TOKEN'),region_name=args.region)
    identity=session.client('sts',config=Config(ignore_configured_endpoint_urls=True,connect_timeout=10,read_timeout=20)).get_caller_identity()
    if identity['Account']!=expected:raise SystemExit('Account mismatch; no Terraform plan attempted')
    if ':user/' not in identity['Arn'] and ':role/' not in identity['Arn']:raise SystemExit('A verified IAM role/user ARN is required; session ARN is not accepted')
    supplied=json.loads(args.reviewed_inputs.read_text()) if args.reviewed_inputs else {}
    if not isinstance(supplied,dict) or set(supplied)-set(tf['variable']):raise SystemExit('Reviewed inputs contain undeclared fields')
    if supplied.get('aws_account_id',expected)!=expected or supplied.get('aws_region',args.region)!=args.region:raise SystemExit('Reviewed target differs from the explicit account/region')
    variables={'aws_region':args.region,'aws_account_id':expected,'review_approved':True,**{key:identity['Arn'] for key in principal_variables},**supplied}
    (root/'reviewed-inputs.tfvars.json').write_text(json.dumps(variables,indent=2)+'\n')
    env={'PATH':os.environ['PATH'],'HOME':str(root),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1','AWS_EC2_METADATA_DISABLED':'true',**credentials}
    binary=str(Path('.venv/bin/terraform').resolve())
    local=subprocess.run([binary,'-chdir='+str(root),'validate','-json'],env=env,text=True,capture_output=True,timeout=60)
    if local.returncode:raise SystemExit('Local provider-schema validation must pass first')
    plan=subprocess.run([binary,'-chdir='+str(root),'plan','-input=false','-no-color','-var-file=reviewed-inputs.tfvars.json','-out=reviewed.tfplan'],env=env,text=True,capture_output=True,timeout=120)
    (root/'account-plan.log').write_text(plan.stdout+'\n'+plan.stderr)
    receipt={'scope':'read-only-account-plan','time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':plan.returncode,'accountSuffix':expected[-4:],'region':args.region,'boundPrincipalCount':len(principal_variables),'configurationSha256':hashlib.sha256((root/'main.tf.json').read_bytes()).hexdigest(),'deployment':'not_run','limitations':'Bound credential identity may have broader existing permissions; this does not prove negative access tests.'}
    if plan.returncode==0:
        show=subprocess.run([binary,'-chdir='+str(root),'show','-json','reviewed.tfplan'],env=env,text=True,capture_output=True,check=True)
        data=json.loads(show.stdout);(root/'account-plan.json').write_text(show.stdout)
        receipt['changes']=[{'type':item['type'],'actions':item['change']['actions']}for item in data.get('resource_changes',[])]
    if plan.returncode==0 and (root/'preflight-aws.py').exists():
        preflight=subprocess.run([str(Path('.venv/bin/python').absolute()),str(root/'preflight-aws.py'),'--plan-json',str(root/'account-plan.json'),'--receipt',str(root/'account-preflight.json')],env=env,text=True,capture_output=True,timeout=120)
        (root/'account-preflight.log').write_text(preflight.stdout+'\n'+preflight.stderr)
        receipt['preflight']='passed' if preflight.returncode==0 else 'blocked'
        receipt['preflightExitCode']=preflight.returncode
    (root/'account-plan-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
    if plan.returncode or receipt.get('preflight')=='blocked':raise SystemExit(1)
if __name__=='__main__':main()
