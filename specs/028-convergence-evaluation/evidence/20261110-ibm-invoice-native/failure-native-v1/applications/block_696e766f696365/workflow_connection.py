"""Provider-native fresh PostgreSQL credentials with explicit transport identity.

No connection or cloud request occurs at import. Constructors accept deployment
configuration, not browser/model input. Managed Cloud SQL Unix transport relies on
the separately configured native connector for upstream TLS; it is never a plain
TCP fallback. IBM database passwords are distinct from IBM control-plane IAM.
"""
from pathlib import Path
import re
import time
import threading
import uuid
from psycopg.conninfo import make_conninfo
from workflow_errors import TemporaryWork

class DatabaseCredentialUnavailable(TemporaryWork):pass

class DatabaseConnection:
    def __init__(self,provider,host,port,database,user,credential,*,ca_file=None,managed_cloudsql=False,managed_proxy_tcp=False,role='worker'):
        if provider not in {'aws','azure','gcp','ibm'}or role not in {'api','worker','migration'}or type(managed_cloudsql)is not bool or type(managed_proxy_tcp)is not bool or(managed_cloudsql and managed_proxy_tcp):raise ValueError('Invalid owned database identity')
        if not isinstance(database,str)or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]{0,62}',database)or not isinstance(user,str)or not 1<=len(user.encode('utf-8'))<=63 or any(ord(c)<33 or ord(c)>126 for c in user):raise ValueError('Use exact native database and role names')
        if type(port)is not int or not 1<=port<=65535 or not callable(credential):raise ValueError('Invalid owned database credential source')
        if managed_proxy_tcp:
            # An explicit compiler-owned same-instance proxy, never a fallback
            # after native TLS failure. The pinned proxy enforces upstream TLS
            # and private-IP connectivity. No configurable TCP host/port here.
            if provider!='gcp'or host!='127.0.0.1'or port!=5432 or ca_file is not None:raise ValueError('Use the exact owned Cloud SQL loopback proxy')
            transport={'sslmode':'disable'}
        elif managed_cloudsql:
            if provider!='gcp'or not isinstance(host,str)or not re.fullmatch(r'/cloudsql/[a-z][a-z0-9-]{4,28}[a-z0-9]:[a-z]+-[a-z]+[1-9][0-9]?:[a-z][a-z0-9-]{0,62}',host)or len((host+'/.s.PGSQL.'+str(port)).encode())>103 or ca_file is not None:raise ValueError('Use the owned Cloud SQL managed Unix socket with upstream connector TLS')
            transport={'sslmode':'disable'}
        else:
            if not isinstance(host,str)or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?',host)or'..'in host:raise ValueError('Use an exact owned native database hostname')
            if not isinstance(ca_file,(str,Path))or not Path(ca_file).is_absolute()or not Path(ca_file).is_file():raise ValueError('Supply the reviewed native CA certificate file')
            if b'-----BEGIN CERTIFICATE-----'not in Path(ca_file).read_bytes():raise ValueError('Native database CA must contain PEM certificates')
            transport={'sslmode':'verify-full','sslrootcert':str(ca_file),'ssl_min_protocol_version':'TLSv1.2'}
        self.provider=provider;self.credential=credential
        self.parameters={'host':host,'port':port,'dbname':database,'user':user,'application_name':'atmem-workflow-'+role,'connect_timeout':5,'gssencmode':'disable','passfile':'/dev/null',**transport}
    def __repr__(self):return'<Reviewed '+self.provider+' database credential factory>'
    def __call__(self):
        try:
            password=self.credential()
            if not isinstance(password,str)or not password or '\0'in password or len(password.encode('utf-8'))>20000:raise ValueError('Invalid credential')
            return make_conninfo(**self.parameters,password=password)
        except Exception:raise DatabaseCredentialUnavailable('Database credential is temporarily unavailable')from None

def aws_database(*,host,region,database,user,ca_file,role='worker',client=None):
    if not isinstance(region,str)or not re.fullmatch(r'[a-z]{2}-[a-z]+-[0-9]',region)or not isinstance(host,str)or not host.endswith('.'+region+'.rds.amazonaws.com'):raise ValueError('Use the actual regional RDS endpoint, not a custom DNS alias')
    cached={'client':client};client_lock=threading.Lock()
    def password():
        if cached['client']is None:
            with client_lock:
                if cached['client']is None:
                    import boto3
                    from botocore.config import Config
                    cached['client']=boto3.Session().client('rds',region_name=region,config=Config(proxies={},connect_timeout=1,read_timeout=2,retries={'total_max_attempts':1}))
        return cached['client'].generate_db_auth_token(DBHostname=host,Port=5432,DBUsername=user,Region=region)
    return DatabaseConnection('aws',host,5432,database,user,password,ca_file=ca_file,role=role)

def azure_database(*,host,database,user,ca_file,managed_identity_client_id,role='worker',credential=None):
    if not isinstance(host,str)or not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,61}[a-z0-9]\.postgres\.database\.azure\.com',host):raise ValueError('Use the actual Azure PostgreSQL endpoint')
    if not isinstance(managed_identity_client_id,str)or str(uuid.UUID(managed_identity_client_id))!=managed_identity_client_id:raise ValueError('Use the dedicated database workload identity client ID')
    cached={'credential':credential}
    def password():
        if cached['credential']is None:
            from azure.identity import ManagedIdentityCredential
            cached['credential']=ManagedIdentityCredential(client_id=managed_identity_client_id,retry_total=0,connection_timeout=1,read_timeout=2)
        access=cached['credential'].get_token('https://ossrdbms-aad.database.windows.net/.default')
        if type(access.expires_on)is not int or access.expires_on<time.time()+30:raise ValueError('Database token is expiring')
        return access.token
    return DatabaseConnection('azure',host,5432,database,user,password,ca_file=ca_file,role=role)

def google_metadata_token(session=None):
    import requests
    import json
    session=session or requests.Session();session.trust_env=False;deadline=time.monotonic()+4
    try:
        with session.get('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',headers={'Metadata-Flavor':'Google'},timeout=(1,2),allow_redirects=False,stream=True)as response:
            if response.status_code!=200 or response.headers.get('Metadata-Flavor')!='Google':raise ValueError('Unverified workload identity')
            raw=bytearray()
            for chunk in response.iter_content(1):
                raw.extend(chunk)
                if len(raw)>8192 or time.monotonic()>deadline:raise ValueError('Workload identity response boundary')
        def unique(pairs):
            value={}
            for key,item in pairs:
                if key in value:raise ValueError('Duplicate credential field')
                value[key]=item
            return value
        value=json.loads(raw,object_pairs_hook=unique)
        if not isinstance(value,dict)or value.get('token_type')!='Bearer'or type(value.get('expires_in'))is not int or value['expires_in']<60 or not isinstance(value.get('access_token'),str)or not value['access_token']:raise ValueError('Unverified workload token')
        return value['access_token']
    except Exception:raise DatabaseCredentialUnavailable('Database workload identity is temporarily unavailable')from None

def gcp_database(*,connection_name,service_account_email,database,role='worker',credential=None,private_proxy=False):
    if not isinstance(connection_name,str)or not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]:[a-z]+-[a-z]+[1-9][0-9]?:[a-z][a-z0-9-]{0,62}',connection_name)or type(private_proxy)is not bool:raise ValueError('Use the owned Cloud SQL connection name and explicit transport')
    if not isinstance(service_account_email,str)or not re.fullmatch(r'[a-z][a-z0-9-]{4,29}@[a-z][a-z0-9-]{4,28}[a-z0-9]\.iam\.gserviceaccount\.com',service_account_email):raise ValueError('Use the owned service account IAM database identity')
    user=service_account_email.removesuffix('.gserviceaccount.com')
    return DatabaseConnection('gcp','127.0.0.1'if private_proxy else'/cloudsql/'+connection_name,5432,database,user,credential or google_metadata_token,managed_cloudsql=not private_proxy,managed_proxy_tcp=private_proxy,role=role)

def ibm_database(*,host,port,database,user,ca_file,password,role='worker'):
    if not isinstance(host,str)or not host.endswith('.databases.appdomain.cloud'):raise ValueError('Use the native IBM database endpoint and its instance CA')
    # The callable retrieves the dedicated nonadministrative SQL role password
    # from its separately authorized secret store. An IAM token is not substituted.
    return DatabaseConnection('ibm',host,port,database,user,password,ca_file=ca_file,role=role)
