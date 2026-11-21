"""Explicit, conditional catalog writes for a deployment/operator identity.

End-user API roles have no access to these write APIs. Never print document data.
"""
import json
import re
import uuid
import time
from boto3.dynamodb.types import TypeSerializer


def validate_document(value):
    fields={'id','title','text','allowedSubjects','allowedRegions'}
    if not isinstance(value,dict) or not fields.issubset(value) or not set(value).issubset(fields|{'sourceId','authorizationExpiresAt'}):raise ValueError('Supply the exact document and ACL fields')
    if not isinstance(value['id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',value['id']):raise ValueError('Invalid document ID')
    for key,limit in [('title',500),('text',8000)]:
        if not isinstance(value[key],str) or not value[key].strip() or len(value[key].encode('utf-8'))>limit:raise ValueError('Invalid document size')
    for key,pattern in [('allowedSubjects',r'[A-Za-z0-9_-]{1,100}'),('allowedRegions',r'[A-Z]{2}')]:
        items=value[key]
        if not isinstance(items,list) or len(items)>100 or not all(isinstance(x,str) and re.fullmatch(pattern,x) for x in items) or len(set(items))!=len(items):raise ValueError('Invalid explicit access list')
    if 'sourceId' in value or 'authorizationExpiresAt' in value:
        if not isinstance(value.get('sourceId'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',value['sourceId']):raise ValueError('Invalid connector source identity')
        expiry=value.get('authorizationExpiresAt')
        if not isinstance(expiry,int) or isinstance(expiry,bool) or not time.time()<expiry<=time.time()+300:raise ValueError('Connector authorization leases must expire within five minutes')
    return dict(value)


def encode(value):
    serializer=TypeSerializer();return {key:serializer.serialize(item) for key,item in value.items()}


def put_document(client,table,document,expected_revision=None):
    document=validate_document(document);revision=str(uuid.uuid4())
    item={**document,'recordId':'DOCUMENT#'+document['id'],'kind':'DOCUMENT','revision':revision}
    put={'TableName':table,'Item':encode(item)}
    if expected_revision is None:
        put['ConditionExpression']='attribute_not_exists(recordId)'
        operations=[{'Put':put},{'Update':{'TableName':table,'Key':{'recordId':{'S':'CATALOG#metadata'}},'UpdateExpression':'SET documentCount = if_not_exists(documentCount, :zero) + :one','ConditionExpression':'attribute_not_exists(documentCount) OR documentCount < :limit','ExpressionAttributeValues':{':zero':{'N':'0'},':one':{'N':'1'},':limit':{'N':'100'}}}}]
        client.transact_write_items(TransactItems=operations,ClientRequestToken=str(uuid.uuid4()))
    else:
        if not isinstance(expected_revision,str) or not expected_revision:raise ValueError('An expected revision is required')
        client.put_item(**put,ConditionExpression='revision = :expected',ExpressionAttributeValues={':expected':{'S':expected_revision}})
    return {'id':document['id'],'revision':revision}


def delete_document(client,table,document_id,expected_revision):
    if not isinstance(document_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',document_id) or not isinstance(expected_revision,str) or not expected_revision:raise ValueError('Exact document ID and revision are required')
    client.transact_write_items(TransactItems=[{'Delete':{'TableName':table,'Key':{'recordId':{'S':'DOCUMENT#'+document_id}},'ConditionExpression':'revision = :expected','ExpressionAttributeValues':{':expected':{'S':expected_revision}}}},{'Update':{'TableName':table,'Key':{'recordId':{'S':'CATALOG#metadata'}},'UpdateExpression':'SET documentCount = documentCount - :one','ConditionExpression':'documentCount >= :one','ExpressionAttributeValues':{':one':{'N':'1'}}}}],ClientRequestToken=str(uuid.uuid4()))
    return {'id':document_id,'deleted':True}


def main():
    import argparse
    import boto3
    from botocore.config import Config
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table',required=True);parser.add_argument('--region',required=True);parser.add_argument('--account',required=True)
    parser.add_argument('--document');parser.add_argument('--delete-id');parser.add_argument('--expected-revision')
    parser.add_argument('--confirm-write',action='store_true',required=True)
    args=parser.parse_args()
    if bool(args.document)==bool(args.delete_id):parser.error('Choose exactly one document file or delete ID')
    session=boto3.Session(region_name=args.region);config=Config(ignore_configured_endpoint_urls=True,connect_timeout=3,read_timeout=10,retries={'total_max_attempts':2})
    if session.client('sts',config=config).get_caller_identity()['Account']!=args.account:raise SystemExit('Account mismatch')
    client=session.client('dynamodb',config=config)
    if args.document:
        from pathlib import Path
        result=put_document(client,args.table,json.loads(Path(args.document).read_text()),args.expected_revision)
    else:result=delete_document(client,args.table,args.delete_id,args.expected_revision)
    print(json.dumps(result))
if __name__=='__main__':main()
