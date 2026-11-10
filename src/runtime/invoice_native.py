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
from workflow_connection import google_metadata_token
from invoice_configuration import owned_deployment,native_database,mounted_secret
from workflow_contract import reviewed_contract
from workflow_worker import producer_store
from structured_output import _object
from invoice_runtime_secrets import prepare_runtime_environment

IDENTITY_KEYS={
 'aws':['REGION','POOL_ID','CLIENT_ID','AUTH_ORIGIN','AUTH_SCOPE'],
 'azure':['TENANT_ID','API_CLIENT_ID','SPA_CLIENT_ID'],
 'gcp':['PROJECT_NUMBER','REGION','SERVICE_NAME'],
 'ibm':['APPID_TENANT_ID','APPID_CLIENT_ID','APPID_ISSUER','AUTH_SCOPE']}

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

def destination_contract(environment):
    encoded=environment['DESTINATION_CONTRACT_BASE64']
    if not isinstance(encoded,str)or not 1<=len(encoded)<=8192:raise ValueError('Use the owned nonsecret destination identity')
    return reviewed_contract(json.loads(base64.b64decode(encoded,validate=True),object_pairs_hook=_object))

def native_public_origin(provider,environment):
    env=environment
    if provider!='ibm'or env.get('PUBLIC_ORIGIN_MODE')!='code-engine-default':return env['PUBLIC_ORIGIN']
    # Fixed native platform metadata, never request Host/Forwarded headers. This
    # avoids an app -> own endpoint -> app configuration cycle in Terraform.
    region=env['REGION'];app=env.get('CE_APP');domain=env.get('CE_DOMAIN');subdomain=env.get('CE_SUBDOMAIN')
    if(env.get('CE_REGION')!=region or not isinstance(region,str)or not re.fullmatch(r'[a-z]{2}-[a-z]+',region)
       or not isinstance(app,str)or not re.fullmatch(r'[a-z][a-z0-9-]{0,61}[a-z0-9]',app)or app!=env.get('SERVICE_NAME')
       or domain!=region+'.codeengine.appdomain.cloud'or not isinstance(subdomain,str)or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,61}[a-z0-9]',subdomain)):
        raise ValueError('Native Code Engine origin differs from the owned app/region')
    origin='https://'+app+'.'+subdomain+'.'+domain
    if'PUBLIC_ORIGIN'in env and env['PUBLIC_ORIGIN']!=origin:raise ValueError('Explicit and native public origins disagree')
    return origin

def create_native_api(provider,environment,*,connection=None,objects=None,jwks=None):
    if provider not in IDENTITY_KEYS:raise ValueError('Unsupported owned invoice provider')
    env=prepare_runtime_environment(provider,environment,'api');identity=native_staff_identity(provider,{key:env[key]for key in IDENTITY_KEYS[provider]},jwks=jwks);contract=destination_contract(env)
    # This factory never reads model configuration or an outbound action secret.
    # Test injection is an internal Python call, not an HTTP or config feature.
    store=producer_store(connection if connection is not None else native_database(provider,env,'api'),destination_contract=contract,namespace=env['WORKFLOW_NAMESPACE'])
    return create_app(identity.verify,store,objects if objects is not None else native_objects(provider,env),account_id=env['ACCOUNT_ID'],public_origin=native_public_origin(provider,env),token_header=identity.token_header,web_config=identity.public_configuration)

def app_factory():return create_native_api(owned_deployment()['provider'],os.environ)
