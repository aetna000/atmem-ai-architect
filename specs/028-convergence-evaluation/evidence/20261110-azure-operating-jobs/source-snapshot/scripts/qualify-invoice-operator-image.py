"""Exact native-plan operator commands and real local SQL, never cloud auth."""
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
from unittest.mock import patch
packet=json.load(sys.stdin);checks=[];stage='image_files'
try:
 for name,digest in packet['files'].items():assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest()==digest
 sys.path.insert(0,'/app')
 import invoice_operator_job as job
 from invoice_operator_core import validate_deployment
 env=packet['environment'];os.environ.update(env)
 provider=packet['provider'];deployment=job.deployment_input(env,provider);scope=validate_deployment(deployment)
 stage='native_preview'
 for action in ['initialize','maintain','monitor']:
  output=io.StringIO()
  with redirect_stdout(output):assert job.main([action])==0
  assert json.loads(output.getvalue())=={'format':'invoice-operator-v1','action':action,'status':'preview','willWrite':False}
 checks.append('three-exact-native-command-previews-no-SQL')
 if provider=='azure':
  stage='scripted_native_managed_identity'
  import http.server,threading,time,urllib.parse
  from psycopg.conninfo import conninfo_to_dict
  from workflow_connection import DatabaseCredentialUnavailable
  requests=[]
  class Metadata(http.server.BaseHTTPRequestHandler):
   def log_message(self,*_):pass
   def do_GET(self):
    query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
    assert self.headers.get('X-IDENTITY-HEADER')=='owned-synthetic-endpoint'
    assert query['resource']==['https://ossrdbms-aad.database.windows.net']
    if query.get('client_id')!=[env['WORKLOAD_IDENTITY_CLIENT_ID']]:
     self.send_response(403);self.end_headers();self.wfile.write(b'{}');return
    requests.append(query);body=json.dumps({'access_token':'synthetic-operator-token-'+str(len(requests)),'expires_on':str(int(time.time())+600),'resource':query['resource'][0],'token_type':'Bearer'}).encode()
    self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  metadata=http.server.ThreadingHTTPServer(('127.0.0.1',0),Metadata);thread=threading.Thread(target=metadata.serve_forever,daemon=True);thread.start()
  os.environ.update({'IDENTITY_ENDPOINT':'http://127.0.0.1:'+str(metadata.server_port)+'/msi/token','IDENTITY_HEADER':'owned-synthetic-endpoint'})
  try:
   tokens=[]
   for database in ['postgres',None]:
    with patch('invoice_operator_job.psycopg.connect')as transport:
     job.native_connect('azure',env,deployment)(database);settings=conninfo_to_dict(transport.call_args.args[0])
    assert settings['sslmode']=='verify-full'and settings['ssl_min_protocol_version']=='TLSv1.2'and settings['user']==env['DATABASE_USER']and settings['dbname']==(database or'invoice')
    tokens.append(settings['password'])
   assert tokens==['synthetic-operator-token-1','synthetic-operator-token-2'];checks.append('actual-Azure-SDK-fresh-operator-tokens-full-TLS-database-selection')
   with patch('invoice_operator_job.psycopg.connect')as transport:
    try:job.native_connect('azure',{**env,'WORKLOAD_IDENTITY_CLIENT_ID':str(uuid.uuid4())},deployment)(None);raise AssertionError('Wrong operator token must fail')
    except DatabaseCredentialUnavailable:pass
    transport.assert_not_called()
   checks.append('unavailable-operator-identity-refuses-SQL-connection')
  finally:metadata.shutdown();metadata.server_close();thread.join(2);os.environ.pop('IDENTITY_ENDPOINT',None);os.environ.pop('IDENTITY_HEADER',None)
 c=packet['fixture'];assert c['name']in {'atmem-durable-qualification','atmem-durable-qualification-pg18'}and re.fullmatch(r'architect_qualification_[a-z0-9]{1,32}',c['database'])
 dsn=make_conninfo(host='127.0.0.1',port=c['port'],dbname=c['database'],user=c['user'],password=c['password'],sslmode='disable')
 stage='owned_fixture_guard'
 with psycopg.connect(dsn)as conn:assert conn.execute('SELECT marker FROM workflow.qualification_guard').fetchone()[0]==c['marker']
 database='architect_qualification_'+uuid.uuid4().hex[:16];created=False;new_roles=[];mapping={};mapping_patch=None
 try:
  stage='fresh_database'
  with psycopg.connect(dsn,autocommit=True)as owner:
   if provider=='aws'and owner.execute("SELECT 1 FROM pg_roles WHERE rolname='rds_iam'").fetchone()is None:owner.execute('CREATE ROLE rds_iam NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
   for binding in deployment['bindings'].values():
    if owner.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(binding['name'],)).fetchone()is None:new_roles.append(binding['name'])
   owner.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)));created=True
  class AzureMappingConnection:
   # Only the native Entra mapping protocol is scripted. PostgreSQL CREATE ROLE,
   # ownership markers, schema, grants and application transactions are real.
   def __init__(self,conn):self.conn=conn
   def __getattr__(self,key):return getattr(self.conn,key)
   def __enter__(self):self.conn.__enter__();return self
   def __exit__(self,*args):return self.conn.__exit__(*args)
   def execute(self,query,parameters=None):
    if query=="SELECT pg_catalog.pgaadauth_create_principal_with_oid(%s,%s,'service',false,false)":
     name,principal=parameters;assert self.conn.info.dbname=='postgres'
     assert any(row['name']==name and row['principal']==principal for row in deployment['bindings'].values())
     mapping[name]=(name,'service',principal,deployment['tenantId'],0,0)
     return self.conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(name)))
    return self.conn.execute(query,parameters)
  if provider=='azure':
   mapping_patch=patch('workflow_role_bootstrap.azure_principal',side_effect=lambda _,name:mapping.get(name));mapping_patch.start()
  def connect(override=None):
   assert override is None or(provider=='azure'and override=='postgres')
   conn=psycopg.connect(make_conninfo(dsn,dbname=override or database))
   return AzureMappingConnection(conn)if provider=='azure'and override else conn
  stage='bootstrap'
  assert job.run_action('initialize',connect,deployment)['initialized'];checks.append('owned-schema-and-native-profile-runtime-grants')
  assert job.run_action('initialize',connect,deployment)['initialized'];checks.append('owned-bootstrap-retry')
  if provider=='azure':assert len(mapping)==2;checks.append('scripted-six-column-Entra-mapping-real-SQL-role-admission')
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
  if mapping_patch:mapping_patch.stop()
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
    parser=argparse.ArgumentParser();parser.add_argument('--provider',choices=['aws','azure'],default='aws');parser.add_argument('--source',required=True);parser.add_argument('--image',required=True);parser.add_argument('--native',required=True);parser.add_argument('--postgres-config',required=True);parser.add_argument('--docker-host',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    source=Path(args.source).resolve();native=Path(args.native).resolve();out=Path(args.out).resolve();fixture_path=Path(args.postgres_config).resolve()
    if any(not path.is_relative_to(ROOT/'.local')for path in [source,native,out,fixture_path])or out.exists()or not re.fullmatch('sha256:[0-9a-f]{64}',args.image):raise ValueError('Use exact local source/image/native evidence and a fresh local output')
    qualification=json.loads((native/'qualification.json').read_text());assert qualification['passed']and qualification['provider']==args.provider
    log=native/'provider-mocks.log';assert any(check['name']=='provider-mocks'and check['logSha256']==digest(log)for check in qualification['checks'])
    source_hashes={str(file.relative_to(source)):digest(file)for file in source.rglob('*')if file.is_file()}
    prefix=source.relative_to(native).as_posix()+'/'
    assert all(qualification['sourceHashes'].get(prefix+name)==sha for name,sha in source_hashes.items())
    run_name={'aws':'private_database_and_parser','azure':'private_data_and_parser'}[args.provider]
    plans=[event['test_plan']for line in log.read_text().splitlines()if (event:=json.loads(line)).get('type')=='test_plan'and event.get('@testrun')==run_name];assert len(plans)==1
    tasks=[resource['change']['after']for resource in plans[0]['resource_changes']if resource['type']==('aws_ecs_task_definition'if args.provider=='aws'else'azapi_resource')and '_operator_'in resource['address']];assert len(tasks)==3
    environment=None;commands=[]
    for task in tasks:
        if args.provider=='aws':
            containers=json.loads(task['container_definitions']);container=next(row for row in containers if row['name']=='operator')
            assert container['readonlyRootFilesystem']and not task['task_role_arn'];assert [secret['name']for secret in container['secrets']]==['DATABASE_PASSWORD'];assert container['secrets'][0]['valueFrom'].endswith(':password::');entries=container['environment']
        else:
            assert task['type']=='Microsoft.App/jobs@2025-07-01';properties=task['body']['properties'];container=properties['template']['containers'][0];configuration=properties['configuration'];assert not configuration.get('secrets')and configuration['replicaTimeout']==900 and configuration['replicaRetryLimit']==0
            assert sorted(row['lifecycle']for row in configuration['identitySettings'])==['Main','None'];entries=container['env'];assert all('secretRef'not in entry for entry in entries)
        command=container['command'];assert command[:3]==['python','-I','/app/invoice_operator_job.py']and command[-1]=='--execute';commands.append(command[3])
        env={row['name']:row['value']for row in entries};assert len(env)==len(entries)
        if environment is None:environment=env
        else:assert env==environment
    assert sorted(commands)==['initialize','maintain','monitor']
    fixture=json.loads(fixture_path.read_text());assert fixture.get('name')in {'atmem-durable-qualification','atmem-durable-qualification-pg18'}and re.fullmatch('architect_qualification_[a-z0-9]{1,32}',fixture.get('database',''))and re.fullmatch('[0-9a-f]{64}',fixture.get('marker',''))
    files={name:sha for name,sha in source_hashes.items()if'/'not in name and(name.endswith('.py')or name in ['workflow_schema.sql','invoice-deployment.json','rds-global-ca.pem'])};assert len(files)>30
    tool_hash=digest(Path(__file__));out.mkdir();docker_env={'PATH':os.environ['PATH'],'DOCKER_HOST':args.docker_host,'DOCKER_CONFIG':str(ROOT/'.local/qualification-docker-config')}
    command=['docker','run','--rm','--platform','linux/amd64','--network','host','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--memory','512m','--cpus','1','--pids-limit','32','--cap-drop','ALL','--security-opt','no-new-privileges:true','-i',args.image,'python','-I','-c',PROBE]
    result=subprocess.run(command,env=docker_env,input=json.dumps({'provider':args.provider,'environment':environment,'files':files,'fixture':fixture}).encode(),capture_output=True,timeout=90)
    for secret in [fixture['password'],fixture['marker']]:assert secret.encode()not in result.stdout+result.stderr
    (out/'stdout.log').write_bytes(result.stdout);(out/'stderr.log').write_bytes(result.stderr)
    try:probe=json.loads(result.stdout)
    except Exception:probe={'passed':False}
    passed=result.returncode==0 and probe.get('passed')is True and len(probe.get('checks',[]))==({'aws':9,'azure':12}[args.provider])and tool_hash==digest(Path(__file__))and all(digest(source/name)==sha for name,sha in source_hashes.items())
    receipt={'kind':'exact-native-operator-image-and-local-sql','provider':args.provider,'passed':passed,'image':args.image,'probe':probe,'sourceHashes':source_hashes,'nativeReceiptSha256':digest(native/'qualification.json'),'nativePlanSha256':digest(log),'qualifierSha256':tool_hash,'cloudOperations':False,'boundary':'Actual immutable Linux image and native mock-plan command/configuration bytes; real owned loopback SQL schema/grants/monitoring/retention. Internal Python connection injection substitutes fixture transport/admin credential. Azure additionally uses actual SDK with scripted loopback metadata responses and scripted six-column native Entra mapping over real SQL role creation. No cloud identity, TLS network, KQL execution, scheduling, alert delivery, account plan, deployment or complete medium-project acceptance.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':passed,'probe':probe,'receipt':str(out/'receipt.json')}));sys.exit(0 if passed else 1)
