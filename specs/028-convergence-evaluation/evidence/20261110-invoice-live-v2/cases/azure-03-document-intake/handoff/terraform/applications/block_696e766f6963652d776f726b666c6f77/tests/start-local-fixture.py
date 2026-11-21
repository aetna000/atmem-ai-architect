"""Create/reuse only the named, owned local PostgreSQL qualification container.

Requires an existing local Docker daemon and the isolated durable Python runtime.
Never starts a remote daemon, changes Docker contexts, adopts user containers or
prints generated credentials. This database contains synthetic test data only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import psycopg
from psycopg.conninfo import make_conninfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from workflow_database import initialize_database

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--docker-host',required=True,help='unix:///absolute/path/to/local/docker.sock');parser.add_argument('--major',choices=['17','18'],default='17');args=parser.parse_args()
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket():raise ValueError('Supply an existing local Unix Docker socket')
    docker=shutil.which('docker')
    if not docker:raise ValueError('Install Docker CLI first')
    folder=ROOT/'.local/durable-postgres';folder.mkdir(parents=True,exist_ok=True);folder.chmod(0o700);config_path=folder/('fixture-pg18.json'if args.major=='18'else'fixture.json');docker_config=folder/'docker-config';docker_config.mkdir(exist_ok=True);docker_config.chmod(0o700)
    if not(docker_config/'config.json').exists():(docker_config/'config.json').write_text('{}\n')
    def run(*parts,required=True):
        result=subprocess.run([docker,'--config',str(docker_config),'--host',args.docker_host,*parts],capture_output=True,text=True)
        if required and result.returncode:raise RuntimeError('Local fixture Docker operation failed; inspect the owned container locally')
        return result
    arch=json.loads(run('info','--format','{{json .Architecture}}').stdout)
    platform={'aarch64':'linux/arm64','arm64':'linux/arm64','x86_64':'linux/amd64','amd64':'linux/amd64'}.get(arch)
    lock=json.loads((ROOT/'test-fixtures/postgres-qualification-lock.json').read_text())
    if args.major!='17':lock=lock['variants'][args.major]
    if platform not in lock['manifests']:raise ValueError('Local Docker architecture is outside the reviewed fixture lock')
    image=lock['image']+'@'+lock['manifests'][platform];name='atmem-invoice-'+hashlib.sha256(str(ROOT).encode()).hexdigest()[:12]+('-pg18'if args.major=='18'else'');inspection=run('container','inspect',name,required=False)
    if inspection.returncode==0:
        details=json.loads(inspection.stdout)[0]
        if details['Config'].get('Labels',{}).get('org.atmem.purpose')!='durable-qualification'or details['Config']['Image']!=image or not config_path.is_file():raise ValueError('Refusing to adopt an existing or unrecorded container')
        config=json.loads(config_path.read_text())
        if config.get('name')!=name or config.get('image')!=image:raise ValueError('Owned container and private configuration disagree')
        if not details['State']['Running']:run('start',name)
    else:
        if config_path.exists():raise ValueError('Private fixture configuration already exists; reconcile it before creating a replacement container')
        config={'name':name,'image':image,'database':'architect_qualification_'+uuid.uuid4().hex[:12],'user':'qualification_admin','password':secrets.token_urlsafe(36),'marker':secrets.token_hex(32)}
        with tempfile.NamedTemporaryFile(mode='w',prefix='atmem-postgres-env-')as environment:
            os.chmod(environment.name,0o600);environment.write('POSTGRES_USER='+config['user']+'\nPOSTGRES_PASSWORD='+config['password']+'\nPOSTGRES_DB='+config['database']+'\n');environment.flush()
            run('run','-d','--name',name,'--label','org.atmem.purpose=durable-qualification','--memory','256m','--cpus','1','--security-opt','no-new-privileges:true','-p','127.0.0.1::5432','--env-file',environment.name,image,'-c','max_connections=40','-c','shared_buffers=32MB','-c','log_statement=none','-c','log_min_error_statement=panic','-c','log_parameter_max_length_on_error=0')
        details=json.loads(run('container','inspect',name).stdout)[0];bindings=details['NetworkSettings']['Ports']['5432/tcp']
        if len(bindings)!=1 or bindings[0]['HostIp']!='127.0.0.1':raise ValueError('Fixture must bind exclusively to local loopback')
        config['port']=int(bindings[0]['HostPort'])
        # Persist the owned generated credential before bootstrap so a failure is
        # recoverable locally without adopting or guessing another database.
        config_path.write_text(json.dumps(config,indent=2)+'\n');config_path.chmod(0o600)
    bindings=json.loads(run('container','inspect',name).stdout)[0]['NetworkSettings']['Ports']['5432/tcp']
    if bindings!=[{'HostIp':'127.0.0.1','HostPort':str(config['port'])}]:raise ValueError('Fixture loopback binding changed')
    dsn=make_conninfo(host='127.0.0.1',port=config['port'],dbname=config['database'],user=config['user'],password=config['password'],sslmode='disable')
    deadline=time.monotonic()+30
    while True:
        try:conn=psycopg.connect(dsn,connect_timeout=2);break
        except psycopg.OperationalError:
            if time.monotonic()>=deadline:raise RuntimeError('Owned local PostgreSQL did not become ready')from None
            time.sleep(.2)
    with conn:
        exists=conn.execute("SELECT to_regclass('workflow.qualification_guard') IS NOT NULL").fetchone()[0]
        if not exists:
            initialize_database(conn);conn.execute('CREATE TABLE workflow.qualification_guard(marker text PRIMARY KEY)');conn.execute('INSERT INTO workflow.qualification_guard(marker)VALUES(%s)',(config['marker'],))
        elif conn.execute('SELECT marker FROM workflow.qualification_guard').fetchone()!=(config['marker'],):raise ValueError('Refusing an unrecognized database')
        version=conn.execute('SHOW server_version').fetchone()[0]
    print(json.dumps({'ownedLocalFixture':'ready','postgresVersion':version,'image':image,'cloudOperations':False}))

if __name__=='__main__':main()
