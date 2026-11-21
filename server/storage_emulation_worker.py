"""Bounded storage data-plane checks. Never calls a cloud control plane.

SDK clients target only a worker-owned loopback service; IBM uses Moto's S3
protocol model, explicitly not an IBM Cloud emulator. Generated adapters are
server-owned, never submitted as executable code by the caller.
"""
import base64
from contextlib import contextmanager
import importlib.util
import importlib.metadata
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

@contextmanager
def loopback_only(port):
    connect=socket.socket.connect
    connect_ex=socket.socket.connect_ex
    resolve=socket.getaddrinfo
    def allowed(address):
        if not isinstance(address,tuple) or address[0]!='127.0.0.1' or address[1]!=port:
            raise RuntimeError('Network request outside the isolated emulator is forbidden')
    def guarded(sock,address):allowed(address);return connect(sock,address)
    def guarded_ex(sock,address):allowed(address);return connect_ex(sock,address)
    def dns(host,service,*args,**kwargs):
        if host!='127.0.0.1' or int(service)!=port:raise RuntimeError('External DNS is forbidden')
        return resolve(host,service,*args,**kwargs)
    with patch.object(socket.socket,'connect',guarded),patch.object(socket.socket,'connect_ex',guarded_ex),patch.object(socket,'getaddrinfo',dns):yield

@contextmanager
def service(provider,folder):
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    endpoint=f'http://127.0.0.1:{port}'
    env=dict(os.environ)
    if provider=='azure':
        key=base64.b64encode(b'synthetic-local-only-not-a-cloud-key'*2).decode()
        env['AZURITE_ACCOUNTS']='atmememulator:'+key
        command=[str(ROOT/'.local/cloud-emulators/node_modules/.bin/azurite-blob'),'--blobHost','127.0.0.1','--blobPort',str(port),'--inMemoryPersistence','--extentMemoryLimit','32','--disableTelemetry','--silent']
    else:
        key=None
        command=[str(ROOT/'.local/cloud-emulators/fake-gcs/fake-gcs-server'),'-scheme','http','-host','127.0.0.1','-port',str(port),'-backend','memory','-public-host',f'127.0.0.1:{port}','-external-url',endpoint,'-log-level','error']
    with (folder/'emulator.log').open('w') as log:
        proc=subprocess.Popen(command,cwd=folder,env=env,stdout=log,stderr=log)
        try:
            for _ in range(100):
                if proc.poll() is not None:raise RuntimeError('Local storage emulator exited during startup')
                try:
                    with socket.create_connection(('127.0.0.1',port),timeout=.1):break
                except OSError:time.sleep(.1)
            else:raise RuntimeError('Local storage emulator startup timed out')
            with loopback_only(port):yield endpoint,key
        finally:
            proc.terminate()
            try:proc.wait(timeout=3)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)


def run(folder):
    folder=Path(folder);plan=json.loads((folder/'resource-schedule.json').read_text());provider=plan.get('provider')
    checks=[];limitations=['Local API checks do not validate Terraform apply, real IAM, account policy, region availability, networking, billing or production operations.','Synthetic client credentials are not deployment identities.','Only the explicit private object storage contract is exercised; other provider services are not emulated.']
    def check(name,fn):
        try:fn();checks.append({'name':name,'passed':True})
        except Exception as error:checks.append({'name':name,'passed':False,'errorType':type(error).__name__,'message':str(error)[:500]})
    def equal(actual,expected):
        if actual!=expected:raise AssertionError(f'Expected {expected!r}, received {actual!r}')
    spec=importlib.util.spec_from_file_location('generated_storage_client',folder/'storage_client.py');client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
    stores=plan.get('storageContracts',[])
    if provider not in ('azure','gcp','ibm') or not 1<=len(stores)<=10:raise ValueError('Unsupported storage scope')
    backend={'azure':'azurite','gcp':'fake-gcs-server','ibm':'moto-s3-compatibility'}[provider]
    versions={'azure':'3.37.0','gcp':'1.56.1','ibm':'5.2.5'}
    if provider=='azure':
        installed=json.loads((ROOT/'.local/cloud-emulators/node_modules/azurite/package.json').read_text())['version']
        if installed!=versions[provider]:raise RuntimeError('Azurite version differs from the qualified backend')
    if provider=='gcp':
        location=ROOT/'.local/cloud-emulators/fake-gcs';receipt=json.loads((location/'receipt.json').read_text())
        if receipt.get('version')!=versions[provider] or receipt.get('binarySha256')!=hashlib.sha256((location/'fake-gcs-server').read_bytes()).hexdigest():raise RuntimeError('GCS emulator installation integrity mismatch; rerun setup')
    if provider=='ibm':versions[provider]=importlib.metadata.version('moto')
    sdk_name={'azure':'azure-storage-blob','gcp':'google-cloud-storage','ibm':'boto3'}[provider]

    data='Synthetic document — café\n'.encode()
    if provider=='azure':
        from azure.storage.blob import BlobServiceClient
        from azure.core.exceptions import ResourceNotFoundError,ResourceExistsError
        with service(provider,folder) as (endpoint,key):
            # Pin an API version implemented by the installed emulator, never skip checks.
            sdk=BlobServiceClient(endpoint+'/atmememulator',credential={'account_name':'atmememulator','account_key':key},api_version='2025-11-05',retry_total=0,connection_timeout=3,read_timeout=3)
            for i,store in enumerate(stores):
                container=sdk.create_container(f'documents-{i}')
                def roundtrip():client.azure_put(container,'report.txt',data);equal(client.azure_get(container,'report.txt'),data)
                check(f'{store["id"]}: generated upload/read preserves UTF-8 bytes',roundtrip)
                def overwrite():client.azure_put(container,'report.txt',b'updated');equal(client.azure_get(container,'report.txt'),b'updated');equal([b.name for b in container.list_blobs()],['report.txt'])
                check(f'{store["id"]}: overwrite and listing',overwrite)
                def deletion():
                    client.azure_delete(container,'report.txt')
                    try:client.azure_get(container,'report.txt')
                    except ResourceNotFoundError:return
                    raise AssertionError('Deleted object remained readable')
                check(f'{store["id"]}: deletion and missing-object error',deletion)
                container.delete_container()
            sdk.close()
        limitations.append('Azure Entra authorization, custom role enforcement, storage-account versioning and soft-delete retention remain unverified; Azurite CRUD does not establish these behaviors.')
    elif provider=='gcp':
        from google.cloud import storage
        from google.auth.credentials import AnonymousCredentials
        from google.api_core.exceptions import NotFound,PreconditionFailed
        with service(provider,folder) as (endpoint,_):
            sdk=storage.Client(project='synthetic-qualification',credentials=AnonymousCredentials(),client_options={'api_endpoint':endpoint})
            for i,store in enumerate(stores):
                bucket=storage.Bucket(sdk,f'atmem-documents-{i}');bucket.versioning_enabled=True;bucket=sdk.create_bucket(bucket,timeout=5,retry=None)
                state={}
                def roundtrip():state['generation']=client.gcp_put(bucket,'report.txt',data,0);equal(client.gcp_get(bucket,'report.txt'),data)
                check(f'{store["id"]}: generated upload/read preserves UTF-8 bytes',roundtrip)
                def conditional():
                    try:client.gcp_put(bucket,'report.txt',b'bad overwrite',0)
                    except PreconditionFailed:equal(client.gcp_get(bucket,'report.txt'),data);return
                    raise AssertionError('Stale generation precondition accepted')
                check(f'{store["id"]}: stale write rejected without changing data',conditional)
                def recovery():client.gcp_put(bucket,'report.txt',b'updated',state['generation']);equal(client.gcp_get(bucket,'report.txt',state['generation']),data);equal(client.gcp_get(bucket,'report.txt'),b'updated')
                check(f'{store["id"]}: overwritten generation remains recoverable',recovery)
                def deletion():
                    client.gcp_delete(bucket,'report.txt')
                    try:client.gcp_get(bucket,'report.txt')
                    except NotFound:return
                    raise AssertionError('Deleted object remained current')
                check(f'{store["id"]}: deletion and missing-object error',deletion)
                for blob in bucket.list_blobs(versions=True):blob.delete(timeout=5,retry=None)
                bucket.delete(timeout=5,retry=None)
            sdk.close()
        limitations.append('GCP IAM, public-access prevention and signed URL authentication are not enforced by this test backend.')
    else:
        from moto import mock_aws
        import boto3
        # Moto intercepts S3 requests; deny all real sockets, including loopback.
        with mock_aws(),loopback_only(0):
            sdk=boto3.client('s3',region_name='us-east-1',aws_access_key_id='testing',aws_secret_access_key='testing')
            for i,store in enumerate(stores):
                bucket=f'atmem-documents-{i}';sdk.create_bucket(Bucket=bucket);sdk.put_bucket_versioning(Bucket=bucket,VersioningConfiguration={'Status':'Enabled'});state={}
                def roundtrip():state['version']=client.ibm_put(sdk,bucket,'report.txt',data)['VersionId'];equal(client.ibm_get(sdk,bucket,'report.txt'),data)
                check(f'{store["id"]}: generated S3-compatible upload/read preserves bytes',roundtrip)
                def recovery():state['new']=client.ibm_put(sdk,bucket,'report.txt',b'updated')['VersionId'];equal(client.ibm_get(sdk,bucket,'report.txt',state['version']),data);equal(client.ibm_get(sdk,bucket,'report.txt'),b'updated')
                check(f'{store["id"]}: prior object version recovery',recovery)
                def deletion():
                    client.ibm_delete(sdk,bucket,'report.txt',state['new']);client.ibm_delete(sdk,bucket,'report.txt',state['version']);equal(sdk.list_object_versions(Bucket=bucket).get('Versions',[]),[])
                check(f'{store["id"]}: exact-version cleanup',deletion);sdk.delete_bucket(Bucket=bucket)
            sdk.close()
        limitations.append('This is S3 protocol compatibility coverage, not IBM COS service emulation: IBM IAM, OAuth/HMAC behavior, endpoints and COS-specific errors require IBM validation.')
    return {'status':'passed' if checks and all(c['passed'] for c in checks) else 'failed','backend':backend,'backendVersion':versions[provider],'sdk':{'name':sdk_name,'version':importlib.metadata.version(sdk_name)},'checks':checks,'capabilities':[{'service':provider+' object storage','mode':'generated-client data-plane checks'}],'limitations':limitations,'message':'Generated client functions exercised against local storage APIs. Review the unverified boundaries before planning deployment.'}

if __name__=='__main__':
    try:result=run(sys.argv[1])
    except Exception as error:result={'status':'failed','checks':[],'message':f'{type(error).__name__}: {str(error)[:500]}'}
    print(json.dumps(result));sys.exit(0 if result['status']=='passed' else 1)
