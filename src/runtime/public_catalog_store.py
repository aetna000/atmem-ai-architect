"""Native conditional public-catalog storage, with explicit workload credentials.

The API runtime gets read-only IAM. A separate authorized editor invokes save.
No private-source connector, request-supplied identity or arbitrary URL is admitted.
"""
import json
import re
import time
import requests
from public_faq import MAX_CATALOG_BYTES,CatalogChanged,CatalogUnavailable,object_pairs,parse_catalog

KEY='catalog.json'
ETAG=re.compile(r'"[A-Za-z0-9_-]{1,160}"')

def valid_bucket(value):
    return isinstance(value,str) and re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',value) and '..' not in value

def response_bytes(response,limit,deadline):
    raw=bytearray()
    for chunk in response.iter_content(16384):
        raw.extend(chunk)
        if len(raw)>limit or time.monotonic()>deadline:raise CatalogUnavailable('Catalog response boundary exceeded')
    return bytes(raw)

class HttpCatalogStore:
    def __init__(self,provider,location,bucket,authorization,*,session=None,account=None):
        if not valid_bucket(bucket):raise ValueError('Invalid public catalog bucket/container')
        self.provider=provider;self.bucket=bucket;self.authorization=authorization;self.session=session or requests.Session();self.session.trust_env=False
        if provider=='gcp':
            self.url='https://storage.googleapis.com/storage/v1/b/'+bucket+'/o/'+KEY
            self.upload_url='https://storage.googleapis.com/upload/storage/v1/b/'+bucket+'/o'
        elif provider=='azure':
            if not isinstance(account,str) or not re.fullmatch(r'[a-z0-9]{3,24}',account) or not re.fullmatch(r'[a-z0-9](?:[a-z0-9]|-(?!-)){1,61}[a-z0-9]',bucket):raise ValueError('Invalid Azure storage destination')
            self.url='https://'+account+'.blob.core.windows.net/'+bucket+'/'+KEY
        elif provider=='ibm':
            if not isinstance(location,str) or not re.fullmatch(r'[a-z]{2}-[a-z]+',location):raise ValueError('Invalid IBM regional storage location')
            self.url='https://s3.'+location+'.cloud-object-storage.appdomain.cloud/'+bucket+'/'+KEY
        else:raise ValueError('Unsupported native catalog storage')

    def _headers(self):
        headers=dict(self.authorization())
        auth=headers.get('Authorization','')
        if not isinstance(auth,str) or not auth.startswith('Bearer ') or len(auth)<=7:raise PermissionError('Missing catalog workload identity')
        headers['Content-Type']='application/json'
        if self.provider=='azure':headers['x-ms-version']='2023-11-03'
        return headers

    def _request(self,method,url,headers,*,params=None,data=None,limit=MAX_CATALOG_BYTES):
        deadline=time.monotonic()+(12 if method in {'PUT','POST'} else 5)
        with self.session.request(method,url,headers=headers,params=params,data=data,timeout=(2,8) if method in {'PUT','POST'} else (1,3),allow_redirects=False,stream=True) as response:
            if response.status_code in {401,403}:raise PermissionError('Catalog access denied')
            if response.status_code in {409,412}:raise CatalogChanged('Catalog changed; reload before editing')
            if response.status_code not in {200,201}:raise CatalogUnavailable('Catalog operation unavailable')
            return response_bytes(response,limit,deadline),dict(response.headers)

    def load(self):
        headers=self._headers()
        if self.provider=='gcp':
            raw,_=self._request('GET',self.url,headers,params={'fields':'generation'},limit=4096)
            try:version=json.loads(raw,object_pairs_hook=object_pairs)['generation']
            except (ValueError,KeyError,TypeError):raise CatalogUnavailable('Missing catalog generation') from None
            if not isinstance(version,str) or not re.fullmatch(r'[1-9][0-9]{0,29}',version):raise CatalogUnavailable('Invalid catalog generation')
            raw,_=self._request('GET',self.url,headers,params={'alt':'media','generation':version})
        else:
            raw,metadata=self._request('GET',self.url,headers)
            version=next((v for k,v in metadata.items() if k.lower()=='etag'),None)
            if not isinstance(version,str) or not ETAG.fullmatch(version):raise CatalogUnavailable('Missing authoritative catalog ETag')
        # A missing/denied object is unavailable, not evidence of an empty catalog.
        # Editors explicitly seed even an empty validated public manifest.
        return parse_catalog(raw,version)

    def save(self,raw,expected_version):
        parse_catalog(raw,'editor-preflight')
        headers=self._headers()
        if self.provider=='gcp':
            if not isinstance(expected_version,str) or not re.fullmatch(r'0|[1-9][0-9]{0,29}',expected_version):raise ValueError('Use the exact generation, or 0 for initial creation')
            result,_=self._request('POST',self.upload_url,headers,params={'uploadType':'media','name':KEY,'ifGenerationMatch':expected_version},data=raw,limit=8192)
            try:version=json.loads(result,object_pairs_hook=object_pairs)['generation']
            except (ValueError,KeyError,TypeError):raise CatalogUnavailable('Missing written catalog generation') from None
            if not isinstance(version,str) or not re.fullmatch(r'[1-9][0-9]{0,29}',version):raise CatalogUnavailable('Invalid written catalog generation')
        else:
            if expected_version is None:headers['If-None-Match']='*'
            elif isinstance(expected_version,str) and ETAG.fullmatch(expected_version):headers['If-Match']=expected_version
            else:raise ValueError('Use the exact ETag, or null for initial creation')
            if self.provider=='azure':headers['x-ms-blob-type']='BlockBlob'
            _,metadata=self._request('PUT',self.url,headers,data=raw,limit=8192)
            version=next((v for k,v in metadata.items() if k.lower()=='etag'),None)
            if not isinstance(version,str) or not ETAG.fullmatch(version):raise CatalogUnavailable('Missing written catalog ETag')
        return version

class S3CatalogStore:
    def __init__(self,bucket,region,account_id,*,client=None):
        if not valid_bucket(bucket) or not isinstance(region,str) or not re.fullmatch(r'[a-z]{2}-[a-z]+-[0-9]',region) or not isinstance(account_id,str) or not re.fullmatch(r'[0-9]{12}',account_id):raise ValueError('Invalid regional S3 catalog destination')
        self.bucket=bucket;self.account_id=account_id;self.region=region;self.client=client
    def _client(self):
        if self.client is None:
            import boto3
            from botocore.config import Config
            self.client=boto3.client('s3',region_name=self.region,endpoint_url='https://s3.'+self.region+'.amazonaws.com',config=Config(signature_version='s3v4',proxies={},connect_timeout=1,read_timeout=3,retries={'total_max_attempts':1}))
        return self.client
    def load(self):
        # SDK maps permission/not-found failures to exceptions; never fall back to
        # an old collection or treat an inaccessible object as an empty source.
        reply=self._client().get_object(Bucket=self.bucket,Key=KEY,ExpectedBucketOwner=self.account_id)
        body=reply['Body']
        try:raw=body.read(MAX_CATALOG_BYTES+1)
        finally:body.close()
        version=reply.get('ETag')
        if not isinstance(version,str) or not ETAG.fullmatch(version):raise CatalogUnavailable('Missing authoritative S3 ETag')
        return parse_catalog(raw,version)
    def save(self,raw,expected_version):
        parse_catalog(raw,'editor-preflight')
        condition={'IfNoneMatch':'*'} if expected_version is None else {'IfMatch':expected_version}
        if expected_version is not None and (not isinstance(expected_version,str) or not ETAG.fullmatch(expected_version)):raise ValueError('Use the exact S3 ETag, or null for initial creation')
        try:reply=self._client().put_object(Bucket=self.bucket,Key=KEY,Body=raw,ContentType='application/json',ExpectedBucketOwner=self.account_id,**condition)
        except Exception as error:
            code=getattr(error,'response',{}).get('Error',{}).get('Code')
            if code in {'PreconditionFailed','ConditionalRequestConflict','412','409'}:raise CatalogChanged('Catalog changed; reload before editing') from None
            raise
        version=reply.get('ETag')
        if not isinstance(version,str) or not ETAG.fullmatch(version):raise CatalogUnavailable('Missing written S3 ETag')
        return version
