"""Run a reviewed normalized source contract against the bounded AWS catalog."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import boto3
from boto3.dynamodb.types import TypeDeserializer
from botocore.config import Config
from catalog_admin import put_document,delete_document
from connector_sync import fetch_snapshot,synchronize

class Checkpoint:
    def __init__(self,path):self.path=path
    def load(self,source):
        if not self.path.exists():return None
        data=json.loads(self.path.read_text())
        if data['source']!=source:raise ValueError('Checkpoint source mismatch')
        return data['value']
    def save(self,source,value):
        temporary=self.path.with_suffix('.pending')
        descriptor=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(descriptor,'w') as target:json.dump({'source':source,'value':value},target)
        temporary.replace(self.path)
class Store:
    def __init__(self,client,table):self.client=client;self.table=table;self.decoder=TypeDeserializer()
    def get(self,key):
        item=self.client.get_item(TableName=self.table,Key={'recordId':{'S':'DOCUMENT#'+key}},ConsistentRead=True).get('Item')
        return {k:self.decoder.deserialize(v) for k,v in item.items()} if item else None
    def put(self,item,expected):return put_document(self.client,self.table,item,expected)
    def delete(self,key,expected):return delete_document(self.client,self.table,key,expected)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['endpoint','source-id','table','account','region','checkpoint']:parser.add_argument('--'+name,required=True)
    parser.add_argument('--allow-local-fixture',action='store_true')
    parser.add_argument('--confirm-sync',action='store_true',required=True)
    args=parser.parse_args()
    checkpoint=Path(args.checkpoint);checkpoint.parent.mkdir(parents=True,exist_ok=True)
    lock=checkpoint.with_suffix('.lock');descriptor=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(descriptor,'w') as target:target.write(str(os.getpid()))
        snapshot=fetch_snapshot(args.endpoint,os.getenv('ATMEM_SOURCE_TOKEN'),args.allow_local_fixture)
        config=Config(ignore_configured_endpoint_urls=True,connect_timeout=3,read_timeout=10,retries={'total_max_attempts':2})
        session=boto3.Session(region_name=args.region)
        if session.client('sts',config=config).get_caller_identity()['Account']!=args.account:raise ValueError('Account mismatch')
        receipt=synchronize(snapshot,args.source_id,Store(session.client('dynamodb',config=config),args.table),Checkpoint(checkpoint))
        print(json.dumps(receipt))
    finally:lock.unlink()
if __name__=='__main__':main()
