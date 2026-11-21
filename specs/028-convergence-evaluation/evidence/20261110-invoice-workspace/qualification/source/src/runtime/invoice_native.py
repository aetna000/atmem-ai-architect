"""Native invoice API composition; operator config, never request-selected adapters.

API identity has document upload/read and its own SQL login, not model execution,
dispatch credentials, schema ownership or worker queue mutation. Account creation,
membership admission and native role mapping are separate operator bootstrap work.
"""
import base64
import json
import os
from pathlib import Path
import re
from invoice_identity import native_staff_identity
from invoice_http import create_app
from invoice_object_store import S3InvoiceObjects,HttpInvoiceObjects
from workflow_connection import aws_database,azure_database,gcp_database,ibm_database,google_metadata_token
from workflow_contract import reviewed_contract
from workflow_worker import producer_store
from structured_output import _object

IDENTITY_KEYS={
 'aws':['REGION','POOL_ID','CLIENT_ID','AUTH_ORIGIN','AUTH_SCOPE'],
 'azure':['TENANT_ID','API_CLIENT_ID','SPA_CLIENT_ID'],
 'gcp':['PROJECT_NUMBER','REGION','SERVICE_NAME'],
 'ibm':['APPID_TENANT_ID','APPID_CLIENT_ID','APPID_ISSUER','AUTH_SCOPE']}

def mounted_secret(path,*,maximum=500):
    if not isinstance(path,str)or not Path(path).is_absolute()or type(maximum)is not int or not 1<=maximum<=20000:raise ValueError('Use the owned mounted secret file')
    def read():
        with Path(path).open('rb')as stream:raw=stream.read(maximum+1)
        if not raw or len(raw)>maximum or b'\0'in raw:raise ValueError('Mounted secret is unavailable')
        return raw.decode('utf-8')
    return read

def native_database(provider,environment,role):
    if role not in {'api','worker','migration'}:raise ValueError('Use an owned runtime database role')
    env=environment;common={'database':env['DATABASE_NAME'],'role':role}
    if provider=='gcp':return gcp_database(**common,connection_name=env['DATABASE_CONNECTION_NAME'],service_account_email=env['DATABASE_SERVICE_ACCOUNT'])
    common.update({'host':env['DATABASE_HOST'],'user':env['DATABASE_USER'],'ca_file':env['DATABASE_CA_FILE']})
    if provider=='aws':return aws_database(**common,region=env['REGION'])
    if provider=='azure':return azure_database(**common,managed_identity_client_id=env['WORKLOAD_IDENTITY_CLIENT_ID'])
    if provider=='ibm':return ibm_database(**common,port=int(env['DATABASE_PORT']),password=mounted_secret(env['DATABASE_PASSWORD_FILE']))
    raise ValueError('Unsupported owned database provider')

def native_objects(provider,environment):
    env=environment
    if provider=='aws':return S3InvoiceObjects(env['DOCUMENT_BUCKET'],env['REGION'],env['AWS_ACCOUNT_ID'])
    if provider=='azure':
        from azure.identity import ManagedIdentityCredential
        credential=ManagedIdentityCredential(client_id=env['WORKLOAD_IDENTITY_CLIENT_ID'],retry_total=0,connection_timeout=1,read_timeout=2)
        def authorization():return{'Authorization':'Bearer '+credential.get_token('https://storage.azure.com/.default').token}
        return HttpInvoiceObjects('azure',env['REGION'],env['DOCUMENT_BUCKET'],authorization,account=env['DOCUMENT_ACCOUNT'])
    if provider=='gcp':return HttpInvoiceObjects('gcp',env['REGION'],env['DOCUMENT_BUCKET'],lambda:{'Authorization':'Bearer '+google_metadata_token()})
    if provider=='ibm':
        profile=env['IAM_PROFILE_ID']
        if not re.fullmatch(r'Profile-[A-Za-z0-9-]{1,100}',profile):raise ValueError('Use the dedicated API or worker trusted profile')
        cached={}
        def authorization():
            if'authenticator'not in cached:
                from ibm_cloud_sdk_core.authenticators import ContainerAuthenticator
                auth=ContainerAuthenticator(cr_token_filename='/var/run/secrets/codeengine.cloud.ibm.com/compute-resource-token/token',iam_profile_id=profile,url='https://iam.cloud.ibm.com',disable_ssl_verification=False,proxies={'http':'','https':'','all':''})
                auth.token_manager.http_config={'timeout':(1,2),'allow_redirects':False,'verify':True};cached['authenticator']=auth
            request={'headers':{}};cached['authenticator'].authenticate(request);return request['headers']
        return HttpInvoiceObjects('ibm',env['REGION'],env['DOCUMENT_BUCKET'],authorization)
    raise ValueError('Unsupported owned document provider')

def create_native_api(provider,environment,*,connection=None,objects=None,jwks=None):
    if provider not in IDENTITY_KEYS:raise ValueError('Unsupported owned invoice provider')
    env=environment;identity=native_staff_identity(provider,{key:env[key]for key in IDENTITY_KEYS[provider]},jwks=jwks)
    encoded=env['DESTINATION_CONTRACT_BASE64']
    if not isinstance(encoded,str)or not 1<=len(encoded)<=8192:raise ValueError('Use the owned nonsecret destination identity')
    contract=reviewed_contract(json.loads(base64.b64decode(encoded,validate=True),object_pairs_hook=_object))
    # This factory never reads model configuration or an outbound action secret.
    # Test injection is an internal Python call, not an HTTP or config feature.
    store=producer_store(connection if connection is not None else native_database(provider,env,'api'),destination_contract=contract,namespace=env['WORKFLOW_NAMESPACE'])
    return create_app(identity.verify,store,objects if objects is not None else native_objects(provider,env),account_id=env['ACCOUNT_ID'],public_origin=env['PUBLIC_ORIGIN'],token_header=identity.token_header,web_config=identity.public_configuration)

def app_factory():
    with(Path(__file__).parent/'invoice-deployment.json').open('rb')as stream:raw=stream.read(1025)
    if len(raw)>1024:raise ValueError('Invalid owned invoice deployment metadata')
    deployment=json.loads(raw,object_pairs_hook=_object)
    if not isinstance(deployment,dict)or set(deployment)!={'format','provider'}or deployment['format']!='invoice-workflow-v1':raise ValueError('Invalid owned invoice deployment metadata')
    return create_native_api(deployment['provider'],os.environ)
