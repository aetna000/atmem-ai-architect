"""Turn native platform secret injections into private runtime files, never exports.

The infrastructure supplies secret references, not values in Terraform/source.
Platforms resolve them at startup. Rotation requires the documented workload
rollout; this module does not claim cloud-mounted files refresh automatically.
The untrusted parser never receives these values or this directory.
"""
import atexit
import os
from pathlib import Path
import shutil
import tempfile

def prepare_runtime_environment(provider,environment,role):
    if provider not in {'aws','azure','gcp','ibm'}or role not in {'api','worker'}:raise ValueError('Use the owned native workload and role')
    env=dict(environment)
    if role=='api'and any(name in env for name in ['DESTINATION_TOKEN','DESTINATION_TOKEN_FILE']):raise ValueError('Do not inject outbound credentials into the API')
    if provider!='ibm'and'DATABASE_PASSWORD'in env:raise ValueError('IAM database workloads must not receive a SQL password')
    mapping={'DATABASE_CA_PEM':('DATABASE_CA_FILE','database-ca.pem',256000),'DATABASE_PASSWORD':('DATABASE_PASSWORD_FILE','database-password',500),'DESTINATION_TOKEN':('DESTINATION_TOKEN_FILE','destination-token',16000)}
    selected=[]
    for name,(pointer,filename,maximum)in mapping.items():
        if name not in env:continue
        value=env[name]
        if pointer in env or not isinstance(value,str)or not value or len(value.encode('utf-8'))>maximum or'\0'in value:raise ValueError('Invalid or conflicting native secret injection')
        if name=='DESTINATION_TOKEN'and any(ord(c)<33 or ord(c)>126 for c in value):raise ValueError('Use the owned opaque action token')
        if name=='DATABASE_CA_PEM'and'-----BEGIN CERTIFICATE-----'not in value:raise ValueError('Use the native database CA certificate')
        selected.append((name,pointer,filename,value))
    if not selected:return env
    directory=Path(tempfile.mkdtemp(prefix='atmem-private-runtime-'));directory.chmod(0o700)
    try:
        for name,pointer,filename,value in selected:
            path=directory/filename
            # Private at creation, even under a permissive inherited umask.
            descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(descriptor,'wb')as stream:stream.write(value.encode('utf-8'))
            env[pointer]=str(path);env.pop(name)
            if environment is os.environ:os.environ.pop(name,None)
        atexit.register(shutil.rmtree,directory,ignore_errors=True)
        return env
    except BaseException:shutil.rmtree(directory,ignore_errors=True);raise
