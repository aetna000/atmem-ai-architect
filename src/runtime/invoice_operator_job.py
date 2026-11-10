"""Fixed native operator job entrypoint. Not an HTTP server or model tool.

The emitted task supplies owned nonsecret deployment metadata and a separate
operator identity. Credentials are platform secret references, never Terraform
values. Execution is explicit; preview makes no SDK, secret-file or SQL calls.
"""
import argparse
import base64
from contextlib import contextmanager
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
import psycopg
from invoice_operator_core import validate_deployment,initialize_runtime
from invoice_maintenance import maintain,monitor
from invoice_configuration import owned_deployment,native_database,mounted_secret
from structured_output import _object
from workflow_connection import DatabaseConnection

def deployment_input(environment,provider):
    encoded=environment.get('OPERATOR_DEPLOYMENT_BASE64')
    if not isinstance(encoded,str)or not 1<=len(encoded)<=16000:raise ValueError('Use the emitted bounded operator deployment')
    deployment=json.loads(base64.b64decode(encoded,validate=True),object_pairs_hook=_object)
    validate_deployment(deployment)
    if deployment['provider']!=provider:raise ValueError('Operator provider differs from the bundled deployment')
    return deployment

@contextmanager
def private_environment(provider,environment):
    env=dict(environment)
    if any(key.startswith(('MODEL_','DESTINATION_','PARSER_','DOCUMENT_'))for key in env):raise ValueError('Operator must not receive application/model/action authority')
    if provider not in {'aws','azure','gcp','ibm'}:raise ValueError('Use the owned operator provider')
    if provider not in {'aws','ibm'}and any(key in env for key in ['DATABASE_PASSWORD','DATABASE_PASSWORD_FILE']):raise ValueError('Use native workload database identity')
    if provider!='ibm'and any(key in env for key in ['API_DATABASE_PASSWORD','WORKER_DATABASE_PASSWORD','API_DATABASE_PASSWORD_FILE','WORKER_DATABASE_PASSWORD_FILE']):raise ValueError('Runtime passwords are IBM-only bindings')
    directory=Path(tempfile.mkdtemp(prefix='atmem-private-operator-'));directory.chmod(0o700)
    try:
        for key,maximum in [('DATABASE_PASSWORD',500),('API_DATABASE_PASSWORD',500),('WORKER_DATABASE_PASSWORD',500),('DATABASE_CA_PEM',256000)]:
            if key not in env:continue
            pointer='DATABASE_CA_FILE'if key=='DATABASE_CA_PEM'else key+'_FILE';value=env[key]
            if pointer in env or not isinstance(value,str)or not value or len(value.encode())>maximum or'\0'in value:raise ValueError('Invalid or conflicting native operator secret injection')
            if key=='DATABASE_CA_PEM'and'-----BEGIN CERTIFICATE-----'not in value:raise ValueError('Use the native database CA certificate')
            path=directory/key.lower();descriptor=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            with os.fdopen(descriptor,'wb')as stream:stream.write(value.encode())
            env[pointer]=str(path);env.pop(key)
            if environment is os.environ:os.environ.pop(key,None)
        yield env
    finally:shutil.rmtree(directory,ignore_errors=True)

def native_connect(provider,env,deployment):
    def connect(database=None):
        settings={**env,**({'DATABASE_NAME':database}if database else{})}
        if provider=='aws':
            host=settings['DATABASE_HOST'];region=settings['REGION']
            if not re.fullmatch(r'[a-z]{2}-[a-z]+-[0-9]',region)or not host.endswith('.'+region+'.rds.amazonaws.com'):raise ValueError('Use the owned regional RDS endpoint')
            factory=DatabaseConnection('aws',host,5432,settings['DATABASE_NAME'],settings['DATABASE_USER'],mounted_secret(settings['DATABASE_PASSWORD_FILE']),ca_file=settings['DATABASE_CA_FILE'],role='migration')
        else:factory=native_database(provider,settings,'migration')
        if factory.parameters['user']in {row['name']for row in deployment['bindings'].values()}:raise PermissionError('Do not run an operator job as API or worker')
        for attempt in range(3):
            try:return psycopg.connect(factory())
            except psycopg.OperationalError as error:
                # Only retry connection establishment before any transaction.
                # Cold proxy certificate/network setup can be transient; SQL
                # permission/authentication/schema failures are never repaired
                # by bypassing TLS, changing identities or replaying statements.
                state=error.sqlstate
                if provider!='gcp'or attempt==2 or(state is not None and not(state.startswith('08')or state=='57P03')):raise
                time.sleep(attempt+1)
    return connect

def runtime_passwords(environment,deployment):
    def password(purpose,principal):
        if purpose not in deployment['bindings']or deployment['bindings'][purpose]['principal']!=principal:raise ValueError('Use the exact owned native password binding')
        path=Path(environment[purpose.upper()+'_DATABASE_PASSWORD_FILE']);metadata=path.stat()
        import stat
        if not path.is_absolute()or not stat.S_ISREG(metadata.st_mode)or metadata.st_uid!=os.geteuid()or metadata.st_mode&0o077 or not 24<=metadata.st_size<=500:raise ValueError('Use a private separately supplied native runtime password')
        return path.read_text()
    return password

def run_action(action,connect,deployment,*,passwords=None):
    validate_deployment(deployment)
    if action=='initialize':return {'status':'ok',**initialize_runtime(connect,deployment,passwords=passwords)}
    if action=='maintain':return maintain(connect,deployment)
    if action=='monitor':return monitor(connect,deployment)
    raise ValueError('Unsupported operator job action')

@contextmanager
def private_proxy_job(provider,environment):
    mode=environment.get('OPERATOR_PROXY_SHUTDOWN')
    if mode is None:
        yield;return
    if provider!='gcp'or mode!='cloudsql-private-proxy'or environment.get('DATABASE_TRANSPORT')!='cloudsql-private-proxy':raise ValueError('Use the emitted Google job proxy lifecycle')
    try:
        # Stable GA job containers can start concurrently. Wait for the pinned
        # proxy's own startup endpoint rather than depending on beta ordering.
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            startup=http.client.HTTPConnection('127.0.0.1',9090,timeout=1)
            try:
                startup.request('GET','/startup');response=startup.getresponse()
                if response.status==200 and len(response.read(2049))<=2048:break
            except (OSError,http.client.HTTPException):pass
            finally:startup.close()
            time.sleep(0.2)
        else:raise TimeoutError('Private SQL proxy did not finish startup')
        yield
    finally:
        # Fixed same-instance loopback endpoint; no configurable URL, redirects,
        # ambient HTTP proxy or outbound credentials. A failed shutdown must not
        # produce an ok receipt while the sidecar keeps the job running.
        connection=http.client.HTTPConnection('127.0.0.1',9091,timeout=2)
        try:
            connection.request('POST','/quitquitquit',body=b'')
            response=connection.getresponse()
            if response.status!=200 or len(response.read(2049))>2048:raise ValueError('Private SQL proxy did not confirm shutdown')
        finally:connection.close()

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['initialize','maintain','monitor']);parser.add_argument('--execute',action='store_true');args=parser.parse_args(argv)
    provider=owned_deployment()['provider']
    if not args.execute:
        deployment_input(os.environ,provider)
        print(json.dumps({'format':'invoice-operator-v1','action':args.action,'status':'preview','willWrite':False}));return 0
    def deadline(*_):raise TimeoutError('Operator execution deadline')
    with private_proxy_job(provider,os.environ):
        deployment=deployment_input(os.environ,provider)
        previous=signal.signal(signal.SIGALRM,deadline);signal.alarm(900)
        try:
            with private_environment(provider,os.environ)as env:
                result=run_action(args.action,native_connect(provider,env,deployment),deployment,passwords=runtime_passwords(env,deployment)if provider=='ibm'else None)
        finally:signal.alarm(0);signal.signal(signal.SIGALRM,previous)
    print(json.dumps({'format':'invoice-operator-v1','action':args.action,**result}))
    return 0 if result['status']=='ok'else 2

if __name__=='__main__':
    try:sys.exit(main())
    except Exception:
        # Driver/SDK exceptions can contain sensitive endpoints, SQL or values.
        print(json.dumps({'format':'invoice-operator-v1','status':'failed','code':'operator_job_failed'}));sys.exit(1)
