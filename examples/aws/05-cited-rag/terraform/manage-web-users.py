"""Explicit user onboarding/disable for the generated Cognito pool and catalog.

No invitation email is sent. Passwords come from a terminal prompt, never argv or
Terraform state. The user enrolls their own software-token MFA at first sign-in.
"""
import argparse
import getpass
import json
from pathlib import Path
import re
import boto3
from botocore.config import Config


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['pool','table','account','region','username','receipt']:parser.add_argument('--'+name,required=True)
    parser.add_argument('--subject');parser.add_argument('--employee-region')
    parser.add_argument('--disable',action='store_true');parser.add_argument('--confirm-change',action='store_true',required=True)
    args=parser.parse_args()
    if not args.disable and (not args.subject or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',args.subject) or not args.employee_region or not re.fullmatch(r'[A-Z]{2}',args.employee_region)):parser.error('Create requires an authoritative subject and two-letter employee region')
    session=boto3.Session(region_name=args.region);config=Config(ignore_configured_endpoint_urls=True,connect_timeout=3,read_timeout=10,retries={'total_max_attempts':2})
    if session.client('sts',config=config).get_caller_identity()['Account']!=args.account:raise SystemExit('Account mismatch')
    cognito=session.client('cognito-idp',config=config);db=session.client('dynamodb',config=config)
    pool=cognito.describe_user_pool(UserPoolId=args.pool)['UserPool']
    if pool.get('UserPoolTags',{}).get('ManagedBy')!='AtMem AI Architect':raise SystemExit('Pool is not a generated AtMem target')
    receipt=Path(args.receipt);receipt.parent.mkdir(parents=True,exist_ok=True)
    record={'status':'in_progress','operation':'disable' if args.disable else 'create','pool':args.pool,'username':args.username}
    def save():receipt.write_text(json.dumps(record,indent=2)+'\n');receipt.chmod(0o600)
    save()
    if args.disable:
        user=cognito.admin_get_user(UserPoolId=args.pool,Username=args.username)
        subject=next(a['Value'] for a in user['UserAttributes'] if a['Name']=='sub')
        db.update_item(TableName=args.table,Key={'recordId':{'S':'IDENTITY#COGNITO#'+subject}},UpdateExpression='SET enabled = :disabled',ConditionExpression='attribute_exists(recordId)',ExpressionAttributeValues={':disabled':{'BOOL':False}})
        record['directoryDisabled']=True;save()
        cognito.admin_disable_user(UserPoolId=args.pool,Username=args.username)
    else:
        password=getpass.getpass('Temporary password (not logged): ')
        user=cognito.admin_create_user(UserPoolId=args.pool,Username=args.username,TemporaryPassword=password,MessageAction='SUPPRESS')['User']
        subject=next(a['Value'] for a in user['Attributes'] if a['Name']=='sub')
        record['userCreated']=True;record['subjectId']=subject;save()
        db.put_item(TableName=args.table,Item={'recordId':{'S':'IDENTITY#COGNITO#'+subject},'kind':{'S':'IDENTITY'},'enabled':{'BOOL':True},'subject':{'S':args.subject},'employeeRegion':{'S':args.employee_region}},ConditionExpression='attribute_not_exists(recordId)')
    record['status']='completed';save();print(json.dumps({'status':'completed','receipt':str(receipt)}))
if __name__=='__main__':main()
