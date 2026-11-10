"""Exact AWS native-plan operator commands and real local SQL, never cloud auth."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
PROBE=r'''
import base64,hashlib,io,json,os,re,sys,uuid
from contextlib import redirect_stdout
from pathlib import Path
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
packet=json.load(sys.stdin);checks=[];stage='image_files'
try:
 for name,digest in packet['files'].items():assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest()==digest
 sys.path.insert(0,'/app')
 import invoice_operator_job as job
 from invoice_operator_core import validate_deployment
 env=packet['environment'];os.environ.update(env)
 deployment=job.deployment_input(env,'aws');scope=validate_deployment(deployment)
 stage='native_preview'
 for action in ['initialize','maintain','monitor']:
  output=io.StringIO()
  with redirect_stdout(output):assert job.main([action])==0
  assert json.loads(output.getvalue())=={'format':'invoice-operator-v1','action':action,'status':'preview','willWrite':False}
 checks.append('three-exact-native-command-previews-no-SQL')
 c=packet['fixture'];assert c['name']in {'atmem-durable-qualification','atmem-durable-qualification-pg18'}and re.fullmatch(r'architect_qualification_[a-z0-9]{1,32}',c['database'])
 dsn=make_conninfo(host='127.0.0.1',port=c['port'],dbname=c['database'],user=c['user'],password=c['password'],sslmode='disable')
 stage='owned_fixture_guard'
 with psycopg.connect(dsn)as conn:assert conn.execute('SELECT marker FROM workflow.qualification_guard').fetchone()[0]==c['marker']
 database='architect_qualification_'+uuid.uuid4().hex[:16];created=False;new_roles=[]
 try:
  stage='fresh_database'
  with psycopg.connect(dsn,autocommit=True)as owner:
   if owner.execute("SELECT 1 FROM pg_roles WHERE rolname='rds_iam'").fetchone()is None:owner.execute('CREATE ROLE rds_iam NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
   for binding in deployment['bindings'].values():
    if owner.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(binding['name'],)).fetchone()is None:new_roles.append(binding['name'])
   owner.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)));created=True
  def connect(override=None):
   assert override is None
   return psycopg.connect(make_conninfo(dsn,dbname=database))
  stage='bootstrap'
  assert job.run_action('initialize',connect,deployment)['initialized'];checks.append('owned-schema-and-native-profile-runtime-grants')
  assert job.run_action('initialize',connect,deployment)['initialized'];checks.append('owned-bootstrap-retry')
  assert job.run_action('monitor',connect,deployment)['status']=='ok';checks.append('empty-read-only-monitor')
  stage='expired_and_young_work'
  with connect()as conn:
   conn.execute("INSERT INTO workflow.memberships(account_id,subject,roles)VALUES(%s,'image-fixture-staff',ARRAY['user'])",(scope['account_id'],))
   for key,age in [('expired',93),('young',0)]:conn.execute("INSERT INTO workflow.operations(id,account_id,workflow_key,kind,dedup_key,created_by,source_ref,destination_contract,state,created_at)VALUES(%s,%s,%s,'document',%s,'image-fixture-staff','{}'::jsonb,'{}'::jsonb,'pending',clock_timestamp()-make_interval(days=>%s))",(str(uuid.uuid4()),scope['account_id'],scope['namespace']+'.extract',key,age))
  result=job.run_action('monitor',connect,deployment);assert result['status']=='attention'and result['retentionOverdue']==1;checks.append('monitor-detects-overdue-record')
  result=job.run_action('maintain',connect,deployment);assert result['status']=='ok'and result['purgedOperations']==1;checks.append('bounded-expired-only-maintenance')
  result=job.run_action('monitor',connect,deployment);assert result['status']=='ok'and result['states']=={'pending':1};checks.append('young-work-preserved-monitor-recovers')
  stage='runtime_denials'
  for purpose,binding in deployment['bindings'].items():
   with connect()as conn:
    conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(binding['name'])))
    try:conn.execute('DELETE FROM workflow.events');raise AssertionError('Runtime must not delete audit data')
    except psycopg.errors.InsufficientPrivilege:pass
   checks.append(purpose+'-runtime-audit-deletion-denied')
 finally:
  if created:
   with psycopg.connect(dsn,autocommit=True)as owner:
    owner.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
    for name in new_roles:owner.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(name)))
 print(json.dumps({'passed':True,'checks':checks,'imageFiles':len(packet['files']),'cloudOperations':False}))
except Exception:
 print(json.dumps({'passed':False,'code':'operator-image-check-failed','stage':stage,'checks':checks}));sys.exit(1)
'''

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--image',required=True);parser.add_argument('--native',required=True);parser.add_argument('--postgres-config',required=True);parser.add_argument('--docker-host',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    source=Path(args.source).resolve();native=Path(args.native).resolve();out=Path(args.out).resolve();fixture_path=Path(args.postgres_config).resolve()
    if any(not path.is_relative_to(ROOT/'.local')for path in [source,native,out,fixture_path])or out.exists()or not re.fullmatch('sha256:[0-9a-f]{64}',args.image):raise ValueError('Use exact local source/image/native evidence and a fresh local output')
    qualification=json.loads((native/'qualification.json').read_text());assert qualification['passed']and qualification['provider']=='aws'
    log=native/'provider-mocks.log';assert any(check['name']=='provider-mocks'and check['logSha256']==digest(log)for check in qualification['checks'])
    source_hashes={str(file.relative_to(source)):digest(file)for file in source.rglob('*')if file.is_file()}
    prefix=source.relative_to(native).as_posix()+'/'
    assert all(qualification['sourceHashes'].get(prefix+name)==sha for name,sha in source_hashes.items())
    plans=[event['test_plan']for line in log.read_text().splitlines()if (event:=json.loads(line)).get('type')=='test_plan'and event.get('@testrun')=='private_database_and_parser'];assert len(plans)==1
    tasks=[resource['change']['after']for resource in plans[0]['resource_changes']if resource['type']=='aws_ecs_task_definition'and '_operator_'in resource['address']];assert len(tasks)==3
    environment=None;commands=[]
    for task in tasks:
        containers=json.loads(task['container_definitions']);container=next(row for row in containers if row['name']=='operator');command=container['command'];assert command[:3]==['python','-I','/app/invoice_operator_job.py']and command[-1]=='--execute';commands.append(command[3])
        assert container['readonlyRootFilesystem']and not task['task_role_arn'];assert [secret['name']for secret in container['secrets']]==['DATABASE_PASSWORD'];assert container['secrets'][0]['valueFrom'].endswith(':password::')
        env={row['name']:row['value']for row in container['environment']};assert len(env)==len(container['environment'])
        if environment is None:environment=env
        else:assert env==environment
    assert sorted(commands)==['initialize','maintain','monitor']
    fixture=json.loads(fixture_path.read_text());assert fixture.get('name')in {'atmem-durable-qualification','atmem-durable-qualification-pg18'}and re.fullmatch('architect_qualification_[a-z0-9]{1,32}',fixture.get('database',''))and re.fullmatch('[0-9a-f]{64}',fixture.get('marker',''))
    files={name:sha for name,sha in source_hashes.items()if'/'not in name and(name.endswith('.py')or name in ['workflow_schema.sql','invoice-deployment.json','rds-global-ca.pem'])};assert len(files)>30
    tool_hash=digest(Path(__file__));out.mkdir();docker_env={'PATH':os.environ['PATH'],'DOCKER_HOST':args.docker_host,'DOCKER_CONFIG':str(ROOT/'.local/qualification-docker-config')}
    command=['docker','run','--rm','--platform','linux/amd64','--network','host','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--memory','512m','--cpus','1','--pids-limit','32','--cap-drop','ALL','--security-opt','no-new-privileges:true','-i',args.image,'python','-I','-c',PROBE]
    result=subprocess.run(command,env=docker_env,input=json.dumps({'environment':environment,'files':files,'fixture':fixture}).encode(),capture_output=True,timeout=90)
    for secret in [fixture['password'],fixture['marker']]:assert secret.encode()not in result.stdout+result.stderr
    (out/'stdout.log').write_bytes(result.stdout);(out/'stderr.log').write_bytes(result.stderr)
    try:probe=json.loads(result.stdout)
    except Exception:probe={'passed':False}
    passed=result.returncode==0 and probe.get('passed')is True and len(probe.get('checks',[]))==9 and tool_hash==digest(Path(__file__))and all(digest(source/name)==sha for name,sha in source_hashes.items())
    receipt={'kind':'exact-native-aws-operator-image-and-local-sql','passed':passed,'image':args.image,'probe':probe,'sourceHashes':source_hashes,'nativeReceiptSha256':digest(native/'qualification.json'),'nativePlanSha256':digest(log),'qualifierSha256':tool_hash,'cloudOperations':False,'boundary':'Actual immutable Linux image and native mock-plan command/configuration bytes; real owned loopback SQL schema/grants/monitoring/retention. Internal Python connection injection substitutes only the fixture transport/admin credential. No AWS identity, TLS network, EventBridge scheduling, alert delivery, cloud deployment or complete medium-project acceptance.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':passed,'probe':probe,'receipt':str(out/'receipt.json')}));sys.exit(0 if passed else 1)
