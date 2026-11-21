"""Exact pinned proxy startup/shutdown in an offline shared container namespace."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1]
PROBE=r'''
import hashlib,json,os,runpy,sys
from pathlib import Path
from unittest.mock import patch
packet=json.load(sys.stdin)
for name,digest in packet['files'].items():assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest()==digest
os.environ.update(packet['environment']);sys.path.insert(0,'/app')
if packet['mode']=='invalid-deployment':
 os.environ['OPERATOR_DEPLOYMENT_BASE64']='invalid'
 sys.argv=['/app/invoice_operator_job.py','monitor','--execute']
 runpy.run_path('/app/invoice_operator_job.py',run_name='__main__')
else:
 import invoice_operator_job as job
 # Only SQL work is replaced in this isolated network namespace. Exact-image
 # real SQL/metadata admission is qualified separately, against owned PG17/18.
 with patch('invoice_operator_job.run_action',return_value={'status':'ok'}):
  raise SystemExit(job.main(['monitor','--execute']))
'''

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native',required=True);parser.add_argument('--source',required=True);parser.add_argument('--image',required=True);parser.add_argument('--docker-host',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    native=Path(args.native).resolve();source=Path(args.source).resolve();out=Path(args.out).resolve()
    if any(not path.is_relative_to(ROOT/'.local')for path in [native,source,out])or out.exists()or not re.fullmatch('sha256:[0-9a-f]{64}',args.image):raise ValueError('Use exact local source/image/native qualification and a fresh output')
    qualification=json.loads((native/'qualification.json').read_text());assert qualification['passed']and qualification['provider']=='gcp'
    log=native/'provider-mocks.log';assert any(check['name']=='provider-mocks'and check['logSha256']==digest(log)for check in qualification['checks'])
    hashes={str(file.relative_to(source)):digest(file)for file in source.rglob('*')if file.is_file()};prefix=source.relative_to(native).as_posix()+'/'
    assert all(qualification['sourceHashes'].get(prefix+name)==sha for name,sha in hashes.items())
    events=[json.loads(line)for line in log.read_text().splitlines()];plans=[event['test_plan']for event in events if event.get('type')=='test_plan'and event.get('@testrun')=='private_database_and_identity'];assert len(plans)==1
    jobs=[row['change']['after']for row in plans[0]['resource_changes']if row['type']=='google_cloud_run_v2_job'and row['address'].endswith('_operator_monitor[0]')];assert len(jobs)==1
    containers=jobs[0]['template'][0]['template'][0]['containers'];assert len(containers)==2
    proxy=containers[1];lock=json.loads((ROOT/'src/runtime/cloud-sql-proxy-lock.json').read_text());assert proxy['image']==lock['image']
    assert proxy['args'][:-1]==['--private-ip','--address=127.0.0.1','--port=5432','--structured-logs','--lazy-refresh','--health-check','--http-address=127.0.0.1','--http-port=9090','--quitquitquit','--admin-port=9091','--exit-zero-on-sigterm']
    environment={row['name']:row['value']for row in containers[0]['env']};assert environment['OPERATOR_PROXY_SHUTDOWN']=='cloudsql-private-proxy'
    files={name:sha for name,sha in hashes.items()if'/'not in name and(name.endswith('.py')or name in ['workflow_schema.sql','invoice-deployment.json'])};assert len(files)>30
    out.mkdir();tool_hash=digest(Path(__file__));docker_env={'PATH':os.environ['PATH'],'DOCKER_HOST':args.docker_host,'DOCKER_CONFIG':str(ROOT/'.local/qualification-docker-config')};checks=[]
    for mode in ['success','invalid-deployment']:
        name='atmem-invoice-proxy-'+uuid.uuid4().hex[:16];folder=out/mode;folder.mkdir();container_created=False
        try:
            start=subprocess.run(['docker','run','-d','--name',name,'--platform','linux/amd64','--network','none','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=8m','--memory','256m','--cpus','1','--pids-limit','32','--cap-drop','ALL','--security-opt','no-new-privileges:true',proxy['image'],'--token=explicit-synthetic-offline-qualification-token',*proxy['args']],env=docker_env,capture_output=True,timeout=20)
            (folder/'start.stderr.log').write_bytes(start.stderr);assert start.returncode==0;container_created=True
            result=subprocess.run(['docker','run','--rm','--platform','linux/amd64','--network','container:'+name,'--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--memory','512m','--cpus','1','--pids-limit','32','--cap-drop','ALL','--security-opt','no-new-privileges:true','-i',args.image,'python','-I','-c',PROBE],env=docker_env,input=json.dumps({'environment':environment,'files':files,'mode':mode}).encode(),capture_output=True,timeout=45)
            (folder/'stdout.log').write_bytes(result.stdout);(folder/'stderr.log').write_bytes(result.stderr)
            wait=subprocess.run(['docker','wait',name],env=docker_env,capture_output=True,timeout=10);(folder/'proxy-exit.log').write_bytes(wait.stdout+wait.stderr)
            logs=subprocess.run(['docker','logs',name],env=docker_env,capture_output=True,timeout=10);(folder/'proxy.stdout.log').write_bytes(logs.stdout);(folder/'proxy.stderr.log').write_bytes(logs.stderr)
            actual=json.loads(result.stdout);expected={'format':'invoice-operator-v1','action':'monitor','status':'ok'}if mode=='success'else{'format':'invoice-operator-v1','status':'failed','code':'operator_job_failed'}
            passed=result.returncode==(0 if mode=='success'else 1)and actual==expected and wait.returncode==0 and wait.stdout.strip()==b'0'
            checks.append({'mode':mode,'passed':passed,'operatorExit':result.returncode,'proxyExit':wait.stdout.decode().strip()})
        except Exception as error:checks.append({'mode':mode,'passed':False,'failureType':type(error).__name__})
        finally:
            if container_created:subprocess.run(['docker','rm','-f',name],env=docker_env,capture_output=True,timeout=10)
    passed=len(checks)==2 and all(check['passed']for check in checks)and tool_hash==digest(Path(__file__))and all(digest(source/name)==sha for name,sha in hashes.items())
    receipt={'kind':'offline-exact-pinned-proxy-and-operator-job-lifecycle','passed':passed,'image':args.image,'proxyImage':proxy['image'],'proxyArgs':proxy['args'],'checks':checks,'qualifierSha256':tool_hash,'sourceHashes':hashes,'nativeReceiptSha256':digest(native/'qualification.json'),'nativePlanSha256':digest(log),'cloudOperations':False,'boundary':'Two actual immutable Linux images share a network-disabled namespace. Only the proxy credential is explicitly fake. Success substitutes SQL work solely for lifecycle isolation; invalid metadata exercises the real operator CLI error path. Actual SQL/metadata admission is separate. No Cloud SQL certificate/IAM/private connection, Cloud Run orchestration, scheduling or deployment qualification.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':passed,'checks':checks,'receipt':str(out/'receipt.json')}));sys.exit(0 if passed else 1)
