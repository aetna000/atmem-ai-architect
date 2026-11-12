"""Provider-native database configuration and reviewed public origins.

No cloud request, secret read, HTTP or JWT adapter is loaded at import.
"""
from pathlib import Path
from workflow_profile import owned_origin
from workflow_connection import aws_database,azure_database,gcp_database,ibm_database

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

def native_identity_realm(provider,settings):
    """Issuer identity from owned settings, never unverified token claims.

    Native verifiers separately enforce client/audience/scope. Changing those
    controls must not rename a person within the same issuer's membership.
    """
    if provider=='aws':return 'https://cognito-idp.'+settings['REGION']+'.amazonaws.com/'+settings['POOL_ID']
    if provider=='azure':return 'https://login.microsoftonline.com/'+settings['TENANT_ID']+'/v2.0'
    if provider=='gcp':return 'https://cloud.google.com/iap'
    if provider=='ibm':return settings['APPID_ISSUER']
    raise ValueError('Unsupported owned identity provider')
