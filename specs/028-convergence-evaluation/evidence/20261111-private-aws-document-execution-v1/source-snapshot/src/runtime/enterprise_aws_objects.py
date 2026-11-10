"""Bounded, owner-checked temporary S3 document bytes, not a source connector."""
import base64
import hashlib
import re
import threading
from enterprise_document_contract import MAX_INPUT
from enterprise_document_job import MAX_ENVELOPE
from enterprise_sources import SourceUnavailable


def object_key(identifier,side):
    if not isinstance(identifier,str)or not re.fullmatch('[0-9a-f]{64}',identifier)or side not in {'input','result'}:
        raise ValueError('Use the owned per-file object identity')
    return 'document-jobs/'+identifier+'/'+side


def etag(value):
    if not isinstance(value,str)or not re.fullmatch(r'"[0-9a-f]{32}(?:-[1-9][0-9]{0,4})?"',value):
        raise SourceUnavailable('document_object_unavailable')
    return value


class S3DocumentObjects:
    def __init__(self,bucket,region,account,*,client=None):
        if (not isinstance(bucket,str)or not re.fullmatch('[a-z0-9][a-z0-9-]{1,61}[a-z0-9]',bucket)or
            not isinstance(region,str)or not re.fullmatch(r'(?:af|ap|ca|eu|il|me|mx|sa|us)-(?:east|west|south|north|central|southeast|southwest|northeast|northwest)-[1-9]',region)or
            not isinstance(account,str)or not re.fullmatch('[0-9]{12}',account)):
            raise ValueError('Use an owned regional temporary bucket')
        self.bucket,self.region,self.account=bucket,region,account
        self.client=client;self._lock=threading.Lock()

    def _client(self):
        if self.client is None:
            with self._lock:
                if self.client is None:
                    import boto3
                    from botocore.config import Config
                    self.client=boto3.Session().client('s3',region_name=self.region,
                        endpoint_url='https://s3.'+self.region+'.amazonaws.com',
                        config=Config(proxies={},connect_timeout=2,read_timeout=8,retries={'total_max_attempts':1},
                                      s3={'addressing_style':'virtual'}))
        return self.client

    def owner(self):return {'Bucket':self.bucket,'ExpectedBucketOwner':self.account}

    def preflight(self):
        """No payload mutation if native placement or no-history policy changed."""
        try:
            client=self._client();where=client.get_bucket_location(**self.owner()).get('LocationConstraint')
            region='us-east-1'if where is None else'eu-west-1'if where=='EU'else where
            history=client.get_bucket_versioning(**self.owner())
            if region!=self.region or history.get('Status')is not None or history.get('MFADelete')is not None:raise ValueError()
        except Exception:raise SourceUnavailable('document_object_policy_unavailable')from None

    def put(self,identifier,side,raw):
        key=object_key(identifier,side);maximum=MAX_INPUT if side=='input'else MAX_ENVELOPE
        if not isinstance(raw,bytes)or not 0<len(raw)<=maximum:raise ValueError('Use bounded owned document bytes')
        self.preflight()
        try:
            value=self._client().put_object(**self.owner(),Key=key,Body=raw,IfNoneMatch='*',
                ContentType='application/octet-stream',ServerSideEncryption='AES256',
                ChecksumSHA256=base64.b64encode(hashlib.sha256(raw).digest()).decode())
            if value.get('VersionId')not in {None,'null'}or value.get('ServerSideEncryption')!='AES256':raise ValueError()
            return etag(value.get('ETag'))
        except Exception:raise SourceUnavailable('document_object_unavailable')from None

    def load(self,identifier,side,condition=None):
        key=object_key(identifier,side);maximum=MAX_INPUT if side=='input'else MAX_ENVELOPE
        extra={}if condition is None else {'IfMatch':etag(condition)}
        self.preflight()
        stream=None
        try:
            value=self._client().get_object(**self.owner(),Key=key,**extra);stream=value['Body']
            if (value.get('VersionId')not in {None,'null'}or value.get('ServerSideEncryption')!='AES256'or
                type(value.get('ContentLength'))is not int or not 0<value['ContentLength']<=maximum or
                (condition is not None and value.get('ETag')!=condition)):raise ValueError()
            raw=stream.read(maximum+1)
            if not isinstance(raw,bytes)or len(raw)!=value['ContentLength']or not 0<len(raw)<=maximum:raise ValueError()
            return raw
        except Exception:raise SourceUnavailable('document_object_unavailable')from None
        finally:
            if stream is not None:
                try:stream.close()
                except Exception:raise SourceUnavailable('document_object_unavailable')from None

    def delete(self,identifier,side):
        key=object_key(identifier,side)
        # Never treat a delete marker as erasure of retained object versions.
        self.preflight()
        try:
            value=self._client().delete_object(**self.owner(),Key=key)
            if value.get('DeleteMarker')or value.get('VersionId')not in {None,'null'}:raise ValueError()
        except Exception:raise SourceUnavailable('document_cleanup_unavailable')from None
