"""Run the immutable original application image against an owned private SQL fixture.

No model/source build, cloud request, host port, account lookup or external network.
"""
import argparse,hashlib,json,os,re,secrets,subprocess,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=False)
IMAGE='sha256:de096e0e1d11e6da457fcd92404242c9442d8151aa22cb25456ee3bcce37a8ea'
POSTGRES='docker.io/library/postgres@sha256:996e9dc583ba9f0265a2c75547a9c95fb22c251e394749cab205a0a00e1856a1'
ENDPOINT='unix:///Users/javadtaghia/.avm/c/engine/docker.sock'
config=OUT/'docker-config';config.mkdir();(config/'config.json').write_text('{"auths":{}}\n')
prefix=['docker','--host',ENDPOINT,'--config',str(config)];environment={'PATH':os.environ.get('PATH',''),'DOCKER_HOST':ENDPOINT,'DOCKER_CONFIG':str(config)}
def docker(*args,timeout=30,**kwargs):return subprocess.run([*prefix,*args],env=environment,timeout=timeout,capture_output=True,**kwargs)
def checked(*args,**kwargs):
    result=docker(*args,**kwargs)
    if result.returncode:raise RuntimeError('Owned fixture Docker action failed: '+args[0])
    return result.stdout
def absent(kind,name):
    result=docker(*([kind,'inspect',name]if kind=='network'else['inspect',name]))
    error=result.stderr.lower()
    return result.returncode!=0 and (b'no such object' in error or b'not found' in error)
ident='atmem-azure-journey-'+uuid.uuid4().hex[:12];network=ident+'-net';pg=ident+'-pg';app=ident+'-app';created_network=False;created_pg=False;created_app=False;receipt={'passed':False,'imageId':IMAGE,'postgresImage':POSTGRES,'platform':'linux/amd64','cloudOperations':False}
try:
    for image in [IMAGE,POSTGRES]:
        desc=json.loads(checked('image','inspect','--platform','linux/amd64',image))[0];assert desc['Architecture']=='amd64' and desc['Os']=='linux'
    checked('network','create','--internal',network);created_network=True
    policy=json.loads(checked('network','inspect',network))[0];assert policy['Internal'] is True
    password=secrets.token_urlsafe(32)
    checked('run','-d','--pull','never','--name',pg,'--platform','linux/amd64','--network',network,'--dns','127.0.0.1','--user','999:999','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','512m','--pids-limit','64','--cpus','1','--tmpfs','/tmp:rw,nosuid,nodev,size=32m,mode=1777','--tmpfs','/var/run/postgresql:rw,nosuid,nodev,size=8m,uid=999,gid=999,mode=0775','--tmpfs','/var/lib/postgresql/data:rw,nosuid,nodev,size=192m,uid=999,gid=999,mode=0700','--env','PGDATA=/var/lib/postgresql/data/pgdata','--env','POSTGRES_USER=image_owner','--env','POSTGRES_DB=image_qualification','--env','POSTGRES_PASSWORD='+password,'--env','POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256 --auth-local=scram-sha-256',POSTGRES,'postgres','-c','shared_buffers=16MB','-c','max_connections=32','-c','max_wal_size=64MB','-c','min_wal_size=32MB','-c','jit=off');created_pg=True
    ready=False
    for _ in range(60):
        if docker('exec',pg,'pg_isready','-U','image_owner','-d','image_qualification').returncode==0:ready=True;break
        time.sleep(.25)
    if not ready:
        (OUT/'postgres-startup.log').write_bytes(docker('logs',pg).stdout);raise RuntimeError('Private PostgreSQL fixture did not start')
    pg_ip=json.loads(checked('inspect',pg))[0]['NetworkSettings']['Networks'][network]['IPAddress'];assert pg_ip
    package=ROOT/'.local/external-artifacts/native-azure-labels/v1/unpacked/application'
    sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in package.glob('*.py')}
    # The owned VM deliberately exposes no host source mount. Trusted oracle code
    # is an explicit Python argument; ephemeral SQL credentials arrive on stdin.
    command=['run','--pull','never','--rm','-i','--name',app,'--platform','linux/amd64','--network',network,'--dns','127.0.0.1','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','512m','--pids-limit','96','--cpus','1','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777','--env','PYTHONDONTWRITEBYTECODE=1','--cap-add','SETUID','--cap-add','SETGID','--cap-add','KILL','--entrypoint','python',IMAGE,'-I','-c',Path(__file__).with_name('check-image.py').read_text()]
    lock=(package/'requirements.lock').read_text();pins=dict(re.findall(r'^([A-Za-z0-9_.-]+)==([^\s]+)',lock,re.M))
    inputs={'adminDsn':'host='+pg_ip+' dbname=image_qualification user=image_owner password='+password+' connect_timeout=3','applicationHashes':sources,'auxiliaryHashes':{name:hashlib.sha256((package/name).read_bytes()).hexdigest()for name in ['workflow_schema.sql','requirements.lock']},'runtimePins':pins,'cases':json.loads(Path(__file__).with_name('requirements-cases-v1.json').read_text())};created_app=True
    result=docker(*command,timeout=120,input=json.dumps(inputs).encode());(OUT/'application.stdout').write_bytes(result.stdout);(OUT/'application.stderr').write_bytes(result.stderr)
    if result.returncode:raise RuntimeError('Actual image journey failed; retained private qualification output')
    lines=result.stdout.decode().splitlines();observed=json.loads(next(line for line in reversed(lines)if line.startswith('{')));assert observed['passed']
    receipt.update({'passed':True,'sourceArtifactSha256':'22d35c9d11612c91094b4b1e89b1a429000e5ae0be9dc3a6697758ab8843f7ab','networkInternal':True,'hostPortsPublished':False,'oracleSha256':hashlib.sha256(Path(__file__).with_name('check-image.py').read_bytes()).hexdigest(),'observed':observed,'boundary':'Unchanged emitted Linux AMD64 application image with real HTTP/SQL/queue/UID-separated children/TLS journey. Separate private fixture SQL and synthetic Entra JWKS/CA injection. Not Azure resource/managed authentication or whole-project acceptance.'})
except Exception as error:
    receipt['error']=str(error);raise
finally:
    cleanup=[]
    for name,created in [(app,created_app),(pg,created_pg)]:
        if created:
            docker('rm','-f',name);cleanup.append({'resource':name,'absent':absent('container',name)})
    if created_network:
        checked('network','rm',network);cleanup.append({'resource':network,'absent':absent('network',network)})
    receipt['cleanup']=cleanup;receipt['cleanupConfirmed']=bool(cleanup)and all(r['absent']for r in cleanup)
    receipt['passed']=receipt['passed']and receipt['cleanupConfirmed']
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':receipt['passed'],'cleanupConfirmed':receipt['cleanupConfirmed'],'output':str(OUT)}))
    if not receipt['cleanupConfirmed']:raise RuntimeError('Owned fixture cleanup was not confirmed')
