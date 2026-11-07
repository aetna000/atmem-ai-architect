"""Explicitly authorized synthetic S3 verification; deletes only versions this run creates."""
import argparse
import hashlib
import json
from pathlib import Path
import uuid
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError


def verify(s3, anonymous, bucket, account, journal=None, operator=None):
    operator = operator or s3
    checks = []
    versions = []
    attempted = 0
    key = 'atmem-qualification/' + str(uuid.uuid4()) + '.txt'
    target = {'Bucket': bucket, 'ExpectedBucketOwner': account}
    def record(stage):
        if journal:journal({'status':'in_progress','stage':stage,'objectKey':key,'writesAttempted':attempted,'createdVersionIds':list(versions)})
    record('preflight')
    def check(name, passed):
        checks.append({'name': name, 'passed': bool(passed)})
    try:
        block = s3.get_public_access_block(**target)['PublicAccessBlockConfiguration']
        check('all-public-access-blocks', all(block.get(k) is True for k in ['BlockPublicAcls','IgnorePublicAcls','BlockPublicPolicy','RestrictPublicBuckets']))
        check('versioning-enabled', s3.get_bucket_versioning(**target).get('Status') == 'Enabled')
        rules = s3.get_bucket_encryption(**target)['ServerSideEncryptionConfiguration']['Rules']
        check('default-encryption', any(r.get('ApplyServerSideEncryptionByDefault',{}).get('SSEAlgorithm') in ['AES256','aws:kms','aws:kms:dsse'] for r in rules))
        ownership = s3.get_bucket_ownership_controls(**target)['OwnershipControls']['Rules']
        check('bucket-owner-enforced', any(r.get('ObjectOwnership') == 'BucketOwnerEnforced' for r in ownership))
        policy = json.loads(s3.get_bucket_policy(**target)['Policy'])
        statements=policy.get('Statement',[])
        def transport_deny(statement):
            resources=statement.get('Resource',[])
            if isinstance(resources,str):resources=[resources]
            actions=statement.get('Action',[])
            if isinstance(actions,str):actions=[actions]
            covers_bucket=any(r.startswith('arn:') and r.endswith(':::'+bucket) for r in resources)
            covers_objects=any(r.startswith('arn:') and r.endswith(':::'+bucket+'/*') for r in resources)
            return statement.get('Effect')=='Deny' and statement.get('Principal')=='*' and 's3:*' in actions and covers_bucket and covers_objects and str(statement.get('Condition',{}).get('Bool',{}).get('aws:SecureTransport')).lower()=='false'
        check('deny-insecure-transport-policy', any(transport_deny(s) for s in statements))
        if not all(c['passed'] for c in checks):
            return {'status':'failed','checks':checks,'writesPerformed':False,'cleanup':'not_needed'}
        for payload in [b'synthetic qualification document\n', b'synthetic updated document\n']:
            attempted += 1
            record('write_pending')
            response=operator.put_object(**target,Key=key,Body=payload,ContentType='text/plain')
            version=response.get('VersionId')
            if not version or version=='null':
                # Preflight required versioning; if it changed mid-run, never delete an unknown version.
                raise RuntimeError('Versioned write did not return a version ID; manual cleanup of this run key required')
            versions.append(version)
            record('version_created')
            stream=operator.get_object(**target,Key=key,VersionId=version)['Body']
            try:body=stream.read()
            finally:stream.close()
            check(f'round-trip-version-{len(versions)}',hashlib.sha256(body).digest()==hashlib.sha256(payload).digest())
        check('distinct-version-ids',len(set(versions))==2)
        if operator is not s3:
            listing=operator.list_objects_v2(**target,Prefix=key,MaxKeys=1)
            check('scoped-operator-list',any(item.get('Key')==key for item in listing.get('Contents',[])))
            try:
                operator.delete_object(**target,Key=key,VersionId=versions[0])
                check('scoped-operator-delete-denied',False)
            except ClientError as error:
                check('scoped-operator-delete-denied',error.response.get('Error',{}).get('Code') in ['AccessDenied','403'])

        try:
            anonymous.get_object(Bucket=bucket,Key=key)
            check('anonymous-read-denied',False)
        except ClientError as error:
            check('anonymous-read-denied',error.response.get('Error',{}).get('Code') in ['AccessDenied','403'])
    except Exception as error:
        checks.append({'name':'verification-completed','passed':False,'errorType':type(error).__name__})
    finally:
        record('cleanup_pending')
        failures=[]
        for version in versions:
            try:s3.delete_object(**target,Key=key,VersionId=version)
            except Exception:failures.append(version)
        if failures:checks.append({'name':'cleanup-created-versions','passed':False,'remainingVersionIds':failures,'key':key})
    return {'status':'passed' if all(c['passed'] for c in checks) else 'failed','checks':checks,'writesAttempted':attempted,'objectKey':key if attempted else None,'cleanup':('uncertain_write' if attempted>len(versions) else 'failed' if failures else 'created_versions_deleted' if versions else 'not_needed'),'limitations':'Tests anonymous denial, not every authenticated principal; does not destroy infrastructure.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True);parser.add_argument('--region',required=True)
    parser.add_argument('--account',required=True);parser.add_argument('--bucket',required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--confirm-test-writes',action='store_true',required=True)
    args=parser.parse_args()
    if not args.account.isdigit() or len(args.account)!=12:parser.error('Expected twelve-digit account ID')
    session=boto3.Session(profile_name=args.profile,region_name=args.region)
    config=Config(connect_timeout=5,read_timeout=20,retries={'max_attempts':2},ignore_configured_endpoint_urls=True)
    account=session.client('sts',config=config).get_caller_identity()['Account']
    if account!=args.account:raise SystemExit('Account mismatch; no S3 operations performed')
    s3=session.client('s3',config=config)
    location=s3.get_bucket_location(Bucket=args.bucket,ExpectedBucketOwner=account).get('LocationConstraint') or 'us-east-1'
    if location=='EU':location='eu-west-1'
    if location!=args.region:raise SystemExit('Bucket region mismatch; no test writes performed')
    anonymous=session.client('s3',config=config.merge(Config(signature_version=UNSIGNED)))
    args.receipt.parent.mkdir(parents=True,exist_ok=True)
    def journal(data):
        data.update({'account':account,'region':args.region,'bucket':args.bucket,'evidenceKind':'live-aws-synthetic-test'})
        temporary=args.receipt.with_suffix(args.receipt.suffix+'.tmp');temporary.write_text(json.dumps(data,indent=2)+'\n');temporary.replace(args.receipt)
    try:result=verify(s3,anonymous,args.bucket,account,journal)
    except Exception as error:result={'status':'failed','errorType':type(error).__name__,'message':'Verification failed; inspect target permissions and retained test objects before rerun.'}
    result.update({'account':account,'region':args.region,'bucket':args.bucket,'evidenceKind':'live-aws-synthetic-test'})
    args.receipt.parent.mkdir(parents=True,exist_ok=True);args.receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'receipt':str(args.receipt)}))
    if result['status']!='passed':raise SystemExit(1)

if __name__=='__main__':main()
