"""Private immutable invoice objects with native conditional writes/version reads.

Account identity comes from the verified application membership, never an object
URL or a model. Adapters use operator-owned destinations/workload credentials.
Cloud IAM, versioning, retention and residency require matching infrastructure.
"""
import base64
from email.utils import formatdate
import hashlib
import json
import re
import time
import uuid
from urllib.parse import quote
import requests

LIMIT=10000000
FIELDS={'provider','region','bucket','key','version','sha256'}
class ObjectUnavailable(RuntimeError):pass

def digest_pdf(raw):
    if not isinstance(raw,bytes)or not raw.startswith(b'%PDF-')or len(raw)>LIMIT:raise ValueError('Supply a PDF no larger than 10 MB')
    return hashlib.sha256(raw).hexdigest()

def object_key(account_id,digest):
    if not isinstance(account_id,str)or str(uuid.UUID(account_id))!=account_id:raise ValueError('Use the verified canonical account identity')
    if not isinstance(digest,str)or not re.fullmatch(r'[0-9a-f]{64}',digest):raise ValueError('Invalid invoice content digest')
    return'accounts/'+account_id+'/invoices/'+digest+'.pdf'

class InvoiceObjects:
    def _reference(self,account_id,digest,version):
        if not isinstance(version,str)or not 1<=len(version)<=1024 or version=='null'or any(ord(c)<33 or ord(c)>126 for c in version):raise ObjectUnavailable('A native immutable object version is required')
        if self.provider=='gcp'and not re.fullmatch(r'[1-9][0-9]{0,29}',version):raise ObjectUnavailable('Invalid native object generation')
        return {'provider':self.provider,'region':self.region,'bucket':self.bucket,'key':object_key(account_id,digest),'version':version,'sha256':digest}
    def _check(self,account_id,reference):
        if not isinstance(reference,dict)or set(reference)!=FIELDS:raise ValueError('Use the exact owned object reference')
        expected=self._reference(account_id,reference['sha256'],reference['version'])
        if reference!=expected:raise PermissionError('Object reference is outside the account/destination boundary')
        return expected
    def _content(self,raw,reference):
        if digest_pdf(raw)!=reference['sha256']:raise ObjectUnavailable('Original invoice digest changed')
        return raw

class HttpInvoiceObjects(InvoiceObjects):
    def __init__(self,provider,region,bucket,authorization,*,account=None,session=None):
        if not isinstance(bucket,str)or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',bucket)or'..'in bucket:raise ValueError('Invalid private document destination')
        if not callable(authorization):raise ValueError('Explicit workload identity is required')
        if not isinstance(region,str)or not re.fullmatch(r'[a-z][a-z0-9-]{1,40}',region):raise ValueError('Invalid document region')
        self.provider=provider;self.region=region;self.bucket=bucket;self.authorization=authorization;self.session=session or requests.Session();self.session.trust_env=False
        if provider=='azure':
            if not isinstance(account,str)or not re.fullmatch(r'[a-z0-9]{3,24}',account)or'.'in bucket:raise ValueError('Invalid private Azure storage destination')
            self.origin='https://'+account+'.blob.core.windows.net/'+bucket+'/'
        elif provider=='ibm':
            if not re.fullmatch(r'[a-z]{2}-[a-z]+',region):raise ValueError('Use an explicit regional IBM object destination')
            self.origin='https://s3.'+region+'.cloud-object-storage.appdomain.cloud/'+bucket+'/'
        elif provider=='gcp':
            self.origin='https://storage.googleapis.com/storage/v1/b/'+bucket+'/o/'
            self.upload='https://storage.googleapis.com/upload/storage/v1/b/'+bucket+'/o'
        else:raise ValueError('Unsupported native private object adapter')
    def _headers(self):
        supplied=self.authorization();auth=supplied.get('Authorization')if isinstance(supplied,dict)else None
        if not isinstance(auth,str)or not auth.startswith('Bearer ')or not 8<=len(auth)<=20000 or any(ord(c)<33 or ord(c)>126 for c in auth[7:]):raise PermissionError('Private object workload identity unavailable')
        headers={'Authorization':auth,'Content-Type':'application/pdf'}
        if self.provider=='azure':headers.update({'x-ms-version':'2023-11-03','x-ms-date':formatdate(usegmt=True)})
        return headers
    def _send(self,method,url,*,headers=None,params=None,data=None,limit=LIMIT):
        actual={**self._headers(),**(headers or {})};deadline=time.monotonic()+15
        try:
            with self.session.request(method,url,headers=actual,params=params,data=data,timeout=(2,8),allow_redirects=False,stream=True)as response:
                code=response.status_code
                if code in {401,403}:raise PermissionError('Private object access denied')
                if code in {409,412}:return code,b'',{}
                if code not in {200,201}:raise ObjectUnavailable('Private object operation unavailable')
                raw=bytearray()
                for chunk in response.iter_content(16384):
                    raw.extend(chunk)
                    if len(raw)>limit or time.monotonic()>deadline:raise ObjectUnavailable('Private object response exceeded its boundary')
                return code,bytes(raw),{key.lower():value for key,value in response.headers.items()}
        except(PermissionError,ObjectUnavailable):raise
        except Exception:raise ObjectUnavailable('Private object operation unavailable')from None
    def _version(self,raw,headers):
        if self.provider=='gcp':
            try:
                def unique(pairs):
                    result={}
                    for key,value in pairs:
                        if key in result:raise ValueError('Duplicate metadata field')
                        result[key]=value
                    return result
                return json.loads(raw,object_pairs_hook=unique)['generation']
            except(ValueError,TypeError,KeyError):raise ObjectUnavailable('Native object generation unavailable')from None
        return headers.get('x-ms-version-id'if self.provider=='azure'else'x-amz-version-id')
    def put(self,account_id,raw):
        digest=digest_pdf(raw);key=object_key(account_id,digest)
        if self.provider=='gcp':
            code,body,headers=self._send('POST',self.upload,params={'uploadType':'media','name':key,'ifGenerationMatch':'0','fields':'generation'},data=raw,limit=8192)
        else:
            extra={'If-None-Match':'*','Content-MD5':base64.b64encode(hashlib.md5(raw,usedforsecurity=False).digest()).decode()}
            if self.provider=='azure':extra['x-ms-blob-type']='BlockBlob'
            code,body,headers=self._send('PUT',self.origin+quote(key,safe='/'),headers=extra,data=raw,limit=8192)
        if code in {409,412}:
            # A repeated delivery or lost upload acknowledgement must resolve the
            # exact existing content/version, never overwrite it or guess a token.
            if self.provider=='gcp':_,body,headers=self._send('GET',self.origin+quote(key,safe=''),params={'fields':'generation'},limit=8192)
            else:_,body,headers=self._send('GET',self.origin+quote(key,safe='/'))
        reference=self._reference(account_id,digest,self._version(body,headers))
        # Re-read the pinned native version, including after a conflict. This
        # also verifies missing versioning and mismatched object bytes fail closed.
        self.load(account_id,reference)
        return reference
    def load(self,account_id,reference):
        ref=self._check(account_id,reference);key=ref['key'];version=ref['version']
        if self.provider=='gcp':url=self.origin+quote(key,safe='');params={'alt':'media','generation':version}
        else:url=self.origin+quote(key,safe='/');params={'versionid'if self.provider=='azure'else'versionId':version}
        code,raw,headers=self._send('GET',url,params=params)
        if code!=200:raise ObjectUnavailable('Pinned original invoice unavailable')
        version_header='x-goog-generation'if self.provider=='gcp'else'x-ms-version-id'if self.provider=='azure'else'x-amz-version-id'
        if headers.get(version_header)!=version:raise ObjectUnavailable('Native original version mismatch')
        return self._content(raw,ref)

class S3InvoiceObjects(InvoiceObjects):
    def __init__(self,bucket,region,owner_account_id,*,client=None):
        if not isinstance(bucket,str)or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',bucket)or'..'in bucket or not isinstance(region,str)or not re.fullmatch(r'[a-z]{2}-[a-z]+-[0-9]',region)or not isinstance(owner_account_id,str)or not re.fullmatch(r'\d{12}',owner_account_id):raise ValueError('Invalid owned regional S3 invoice destination')
        self.provider='aws';self.bucket=bucket;self.region=region;self.owner_account_id=owner_account_id;self.client=client
    def _client(self):
        if self.client is None:
            import boto3
            from botocore.config import Config
            self.client=boto3.client('s3',region_name=self.region,endpoint_url='https://s3.'+self.region+'.amazonaws.com',config=Config(proxies={},connect_timeout=2,read_timeout=8,retries={'total_max_attempts':1}))
        return self.client
    def put(self,account_id,raw):
        digest=digest_pdf(raw);key=object_key(account_id,digest);client=self._client()
        try:reply=client.put_object(Bucket=self.bucket,Key=key,Body=raw,ContentType='application/pdf',ChecksumSHA256=base64.b64encode(hashlib.sha256(raw).digest()).decode(),ExpectedBucketOwner=self.owner_account_id,IfNoneMatch='*')
        except Exception as error:
            code=getattr(error,'response',{}).get('Error',{}).get('Code')
            if code not in {'PreconditionFailed','ConditionalRequestConflict','412','409'}:raise ObjectUnavailable('Private object upload unavailable')from None
            try:reply=client.head_object(Bucket=self.bucket,Key=key,ExpectedBucketOwner=self.owner_account_id)
            except Exception:raise ObjectUnavailable('Existing original invoice unavailable')from None
        reference=self._reference(account_id,digest,reply.get('VersionId'));self.load(account_id,reference);return reference
    def load(self,account_id,reference):
        ref=self._check(account_id,reference)
        try:
            reply=self._client().get_object(Bucket=self.bucket,Key=ref['key'],VersionId=ref['version'],ExpectedBucketOwner=self.owner_account_id);stream=reply['Body']
            try:raw=stream.read(LIMIT+1)
            finally:stream.close()
        except Exception:raise ObjectUnavailable('Pinned original invoice unavailable')from None
        if reply.get('VersionId')!=ref['version']:raise ObjectUnavailable('Native original version mismatch')
        return self._content(raw,ref)
