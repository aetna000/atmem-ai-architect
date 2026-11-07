"""Authorized, bounded live test of a prompt-derived storage export with full cleanup."""
import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import uuid
import time
import boto3
from botocore import UNSIGNED
from botocore.config import Config

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('storage_verify',ROOT/'scripts/aws-storage-verify.py')
verification=importlib.util.module_from_spec(spec);spec.loader.exec_module(verification)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True);parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--expected-account-file',type=Path,required=True)
    parser.add_argument('--confirm-live-test-and-cleanup',action='store_true',required=True)
    args=parser.parse_args();run_id=uuid.uuid4().hex[:12]
    root=ROOT/'.local/live-storage'/run_id;root.mkdir(parents=True)
    receipt={'scope':'fresh isolated synthetic storage test','region':'ap-southeast-2','status':'in_progress','runId':run_id,'budgetAllocation':'planned AUD 1 allocation within the user-authorized total 20; bounded synthetic requests, no compute or model calls','events':[]}
    def save(event,**details):
        receipt['events'].append({'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':event,**details})
        temporary=root/'receipt.pending';temporary.write_text(json.dumps(receipt,indent=2)+'\n');temporary.replace(root/'receipt.json')
    credentials={}
    for line in args.env_file.read_text().splitlines():
        line=line.strip().removeprefix('export ')
        if '=' not in line or line.startswith('#'):continue
        key,value=line.split('=',1)
        if key.strip() in ['AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN']:
            parts=shlex.split(value,comments=True)
            if parts:credentials[key.strip()]=parts[0]
    expected=json.loads(args.expected_account_file.read_text())['aws_account_id']
    config=Config(ignore_configured_endpoint_urls=True,connect_timeout=5,read_timeout=20,retries={'total_max_attempts':2})
    session=boto3.Session(aws_access_key_id=credentials['AWS_ACCESS_KEY_ID'],aws_secret_access_key=credentials['AWS_SECRET_ACCESS_KEY'],aws_session_token=credentials.get('AWS_SESSION_TOKEN'),region_name='ap-southeast-2')
    sts=session.client('sts',config=config);identity=sts.get_caller_identity()
    if identity['Account']!=expected or ':user/' not in identity['Arn']:raise SystemExit('Expected verified qualification IAM user/account')
    # Render the same project through the product compiler; never patch Terraform.
    render='import fs from "node:fs";import {terraformSketch} from "./src/terraform.mjs";process.stdout.write(JSON.stringify(terraformSketch(JSON.parse(fs.readFileSync(process.argv[1],"utf8")),"qualification")));'
    generated=subprocess.run(['node','--input-type=module','-e',render,str(args.project.resolve())],cwd=ROOT,capture_output=True,text=True,check=True)
    files=json.loads(generated.stdout);tf=json.loads(files['main.tf.json'])
    allowed={'terraform_data','aws_s3_bucket','aws_s3_bucket_public_access_block','aws_s3_bucket_server_side_encryption_configuration','aws_s3_bucket_versioning','aws_s3_bucket_ownership_controls','aws_s3_bucket_policy'}
    if tf['locals']['unfinished_work'] or set(tf['resource'])-allowed or len(tf['resource'].get('aws_s3_bucket',{}))!=1:raise SystemExit('Only the complete one-bucket qualification is authorized by this runner')
    for name,content in files.items():
        target=root/name
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Unsafe generated path')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content)
    env={'PATH':os.environ['PATH'],'HOME':str(root),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1','AWS_EC2_METADATA_DISABLED':'true',**credentials}
    binary=str(ROOT/'.venv/bin/terraform')
    def terraform(label,*arguments,timeout=180):
        result=subprocess.run([binary,'-chdir='+str(root),*arguments],env=env,capture_output=True,text=True,timeout=timeout)
        (root/(label+'.log')).write_text(result.stdout+'\n'+result.stderr)
        save(label,exitCode=result.returncode)
        if result.returncode:raise RuntimeError(label+' failed; inspect retained evidence')
        return result.stdout
    role_name='atmem-qualification-'+run_id;iam=session.client('iam',config=config)
    role_attempted=False;applied_attempted=False;tests_passed=False;cleanup_passed=True
    try:
        terraform('init','init','-backend=false','-input=false','-no-color')
        terraform('validate','validate','-no-color')
        terraform('mock-tests','test','-no-color')
        save('operator-create-pending',roleName=role_name);role_attempted=True
        role=iam.create_role(RoleName=role_name,AssumeRolePolicyDocument=json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'AWS':identity['Arn']},'Action':'sts:AssumeRole'}]}),Tags=[{'Key':'ManagedBy','Value':'AtMem AI Architect'},{'Key':'QualificationRun','Value':run_id}])['Role']
        save('operator-created',roleName=role_name)
        values={'aws_account_id':expected,'aws_region':'ap-southeast-2','review_approved':True,**{key:role['Arn'] for key in tf['variable'] if key.startswith('principal_')}}
        (root/'reviewed-inputs.tfvars.json').write_text(json.dumps(values,indent=2));(root/'reviewed-inputs.tfvars.json').chmod(0o600)
        terraform('plan','plan','-input=false','-no-color','-var-file=reviewed-inputs.tfvars.json','-out=reviewed.tfplan')
        plan=json.loads(terraform('show-plan','show','-json','reviewed.tfplan'))
        changes=plan.get('resource_changes',[])
        if len(changes)!=7 or any(item['type'] not in allowed or item['change']['actions']!=['create'] for item in changes):raise RuntimeError('Plan differs from reviewed fresh-storage scope')
        assumed=None
        for attempt in range(6):
            try:
                assumed=sts.assume_role(RoleArn=role['Arn'],RoleSessionName='storage-qualification',DurationSeconds=900)['Credentials'];break
            except Exception:
                if attempt==5:raise
                time.sleep(5)
        save('reviewed-create-only-plan',resourceCount=len(changes));applied_attempted=True
        terraform('apply','apply','-input=false','-no-color','reviewed.tfplan')
        outputs=json.loads(terraform('outputs','output','-json'));bucket=next(iter(outputs['buckets']['value'].values()))['name'];save('bucket-created',bucket=bucket)
        if iam.list_role_policies(RoleName=role_name)['PolicyNames'] or iam.list_attached_role_policies(RoleName=role_name)['AttachedPolicies']:raise RuntimeError('Qualification role has unexpected policies')
        operator_session=boto3.Session(aws_access_key_id=assumed['AccessKeyId'],aws_secret_access_key=assumed['SecretAccessKey'],aws_session_token=assumed['SessionToken'],region_name='ap-southeast-2')
        result=verification.verify(session.client('s3',config=config),session.client('s3',config=config.merge(Config(signature_version=UNSIGNED))),bucket,expected,lambda value:save('object-journal',details=value),operator_session.client('s3',config=config))
        (root/'application-tests.json').write_text(json.dumps(result,indent=2));tests_passed=result['status']=='passed' and result['cleanup']=='created_versions_deleted';save('live-access-tests',passed=tests_passed)
        if tests_passed:
            refreshed=terraform('refresh-plan','plan','-input=false','-no-color','-detailed-exitcode','-var-file=reviewed-inputs.tfvars.json')
    except Exception as error:
        receipt['failureType']=type(error).__name__;save('test-failed',errorType=type(error).__name__)
    finally:
        if applied_attempted:
            try:
                terraform('destroy-plan','plan','-destroy','-input=false','-no-color','-var-file=reviewed-inputs.tfvars.json','-out=cleanup.tfplan')
                destroy=json.loads(terraform('show-destroy','show','-json','cleanup.tfplan'))
                if any(item['type'] not in allowed or item['change']['actions'] not in [['delete'],['no-op']] for item in destroy.get('resource_changes',[])):raise RuntimeError('Cleanup plan exceeds run scope')
                terraform('destroy','apply','-input=false','-no-color','cleanup.tfplan')
                state=terraform('remaining-state','state','list')
                if state.strip():raise RuntimeError('Run state still contains resources')
            except Exception as error:cleanup_passed=False;save('cleanup-failed',errorType=type(error).__name__)
        if role_attempted:
            try:
                existing=iam.get_role(RoleName=role_name)['Role']
                if not any(tag['Key']=='QualificationRun' and tag['Value']==run_id for tag in existing.get('Tags',[])):raise RuntimeError('Role ownership check failed')
                iam.delete_role(RoleName=role_name);save('operator-deleted')
            except iam.exceptions.NoSuchEntityException:save('operator-absent')
            except Exception as error:cleanup_passed=False;save('operator-cleanup-failed',errorType=type(error).__name__)
        receipt['status']='passed' if tests_passed and cleanup_passed and 'failureType' not in receipt else 'failed';receipt['cleanup']='passed' if cleanup_passed else 'failed';save('finished')
    print(json.dumps({'status':receipt['status'],'cleanup':receipt['cleanup'],'receipt':str(root/'receipt.json')}))
    if receipt['status']!='passed':raise SystemExit(1)
if __name__=='__main__':main()
