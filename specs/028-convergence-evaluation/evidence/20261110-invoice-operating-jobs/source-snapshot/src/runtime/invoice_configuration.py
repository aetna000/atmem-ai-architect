"""Owned non-HTTP deployment and native SQL credential configuration.

Shared by API, worker and fixed operator jobs. Importing this module neither
loads staff JWT/HTTP adapters nor performs cloud requests or secret reads.
"""
import json
from pathlib import Path
from workflow_connection import aws_database,azure_database,gcp_database,ibm_database
from structured_output import _object

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
    if provider=='gcp':
        transport=env.get('DATABASE_TRANSPORT','cloudsql-socket')
        if transport not in {'cloudsql-socket','cloudsql-private-proxy'}:raise ValueError('Use the owned Cloud SQL transport')
        return gcp_database(**common,connection_name=env['DATABASE_CONNECTION_NAME'],service_account_email=env['DATABASE_SERVICE_ACCOUNT'],private_proxy=transport=='cloudsql-private-proxy')
    common.update({'host':env['DATABASE_HOST'],'user':env['DATABASE_USER'],'ca_file':env['DATABASE_CA_FILE']})
    if provider=='aws':return aws_database(**common,region=env['REGION'])
    if provider=='azure':return azure_database(**common,managed_identity_client_id=env['WORKLOAD_IDENTITY_CLIENT_ID'])
    if provider=='ibm':return ibm_database(**common,port=int(env['DATABASE_PORT']),password=mounted_secret(env['DATABASE_PASSWORD_FILE']))
    raise ValueError('Unsupported owned database provider')

def owned_deployment():
    with(Path(__file__).parent/'invoice-deployment.json').open('rb')as stream:raw=stream.read(1025)
    if len(raw)>1024:raise ValueError('Invalid owned invoice deployment metadata')
    deployment=json.loads(raw,object_pairs_hook=_object)
    if not isinstance(deployment,dict)or set(deployment)!={'format','provider'}or deployment['format']!='invoice-workflow-v1':raise ValueError('Invalid owned invoice deployment metadata')
    if deployment['provider']not in {'aws','azure','gcp','ibm'}:raise ValueError('Unsupported owned invoice provider')
    return deployment

