"""Inspect exact emitted delivery-image bytes, dependencies and native API startup.

Network-disabled loopback only. Synthetic config never requests a cloud token or
database connection. Worker/SQL/model/hosting integration requires separate checks.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
PROBE=r'''
import hashlib,http.client,importlib.metadata,importlib.util,json,os,socket,sys,threading,time
from pathlib import Path
import certifi,uvicorn
sys.path.insert(0,'/app')
packet=json.load(sys.stdin)
for name,digest in packet['files'].items():
 assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest()==digest,name
normalize=lambda name:name.lower().replace('_','-').replace('.','-')
installed={normalize(d.metadata['Name']):d.version for d in importlib.metadata.distributions()}
for name,version in packet['dependencies'].items():assert installed.get(normalize(name))==version,(name,version,installed.get(normalize(name)))
assert importlib.util.find_spec('pip')is None
assert not Path('/usr/local/lib/python3.13/ensurepip').exists()
import procrastinate,psycopg,psycopg_pool,invoice_native,invoice_worker
provider=packet['provider']
if provider=='aws':import boto3
elif provider=='azure':import azure.identity
elif provider=='ibm':import ibm_cloud_sdk_core
env=packet['environment']
if'DATABASE_CA_FILE'not in env:env['DATABASE_CA_FILE']=certifi.where()
os.environ.update(env)
assert invoice_native.owned_deployment()['provider']==provider
app=invoice_native.app_factory()
if packet.get('workerEnvironment')is not None:
 worker=invoice_worker.create_native_worker(provider,{**packet['workerEnvironment'],'DESTINATION_TOKEN':'explicit-synthetic-qualification-token'})
 assert worker.processor.timeout_seconds==180 and worker.deliver.timeout_seconds==45
 assert'DATABASE_HOST'not in worker.processor.environment and'DATABASE_HOST'not in worker.deliver.environment
 assert'DESTINATION_TOKEN_FILE'not in worker.processor.environment and'MODEL_ID'not in worker.deliver.environment
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False));thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
try:
 deadline=time.monotonic()+10
 while not server.started:
  if time.monotonic()>deadline:raise RuntimeError('Native API did not become live')
  time.sleep(.02)
 client=http.client.HTTPConnection('127.0.0.1',port,timeout=2);client.request('GET','/healthz');response=client.getresponse();assert response.status==200 and json.loads(response.read())=={'status':'running'};client.close()
 client=http.client.HTTPConnection('127.0.0.1',port,timeout=2);client.request('GET','/api/session');response=client.getresponse();assert response.status==403;response.read();client.close()
 print(json.dumps({'provider':provider,'checkedImageFiles':len(packet['files']),'checkedPinnedDependencies':len(packet['dependencies']),'installedDependencies':installed,'health':'live','signedOutPrivateApi':403,'cloudRequests':'none; network-disabled namespace'}))
finally:server.should_exit=True;thread.join(timeout=3)
'''
QUEUE_PROBE=r'''
import hashlib,json,os,sys,unittest
from pathlib import Path,PurePosixPath
packet=json.load(sys.stdin);root=Path('/tmp/qualification');root.mkdir()
for name,source in packet['tests'].items():
 path=PurePosixPath(name)
 if path.is_absolute()or '..'in path.parts:raise ValueError('Unsafe qualification path')
 target=root.joinpath(*path.parts);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source)
config=root/'.local/durable-postgres/fixture.json';config.parent.mkdir(parents=True);config.write_text(json.dumps(packet['fixture']));config.chmod(0o600)
os.environ['ATMEM_WORKFLOW_TEST_CONFIG']=str(config)
sys.path[:0]=['/app',str(root/'tests/runtime')]
from durable_restricted_worker_acceptance import RestrictedWorkerTests
suite=unittest.defaultTestLoader.loadTestsFromTestCase(RestrictedWorkerTests)
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.testsRun==5
raise SystemExit(0 if result.wasSuccessful()else 1)
'''

def environment(provider):
    import base64
    tenant='11111111-1111-1111-1111-111111111111';api='22222222-2222-2222-2222-222222222222';spa='33333333-3333-3333-3333-333333333333'
    contract={'id':'normalized-action-v1','endpointSha256':'a'*64,'scope':'synthetic-team','mappingVersion':1}
    common={'ACCOUNT_ID':'44444444-4444-4444-4444-444444444444','PUBLIC_ORIGIN':'https://invoice.example.test','WORKFLOW_NAMESPACE':'invoice','DESTINATION_CONTRACT_BASE64':base64.b64encode(json.dumps(contract).encode()).decode(),'DATABASE_NAME':'invoice','DATABASE_USER':'invoice_api','DOCUMENT_BUCKET':'private-invoices'}
    settings={
      'aws':{'REGION':'ap-southeast-2','AWS_ACCOUNT_ID':'123456789012','POOL_ID':'ap-southeast-2_Fixture','CLIENT_ID':'fixtureclient123','AUTH_ORIGIN':'https://invoicefixture.auth.ap-southeast-2.amazoncognito.com','AUTH_SCOPE':'invoice/process','DATABASE_HOST':'fixture.abcdef.ap-southeast-2.rds.amazonaws.com'},
      'azure':{'REGION':'australiaeast','TENANT_ID':tenant,'API_CLIENT_ID':api,'SPA_CLIENT_ID':spa,'WORKLOAD_IDENTITY_CLIENT_ID':api,'DOCUMENT_ACCOUNT':'invoicefixture','DATABASE_HOST':'invoice-fixture.postgres.database.azure.com'},
      'gcp':{'REGION':'australia-southeast1','PROJECT_NUMBER':'123456789012','SERVICE_NAME':'invoice-api','DATABASE_CONNECTION_NAME':'fixture-project:australia-southeast1:invoice-db','DATABASE_SERVICE_ACCOUNT':'invoice-api@fixture-project.iam.gserviceaccount.com'},
      'ibm':{'REGION':'au-syd','APPID_TENANT_ID':tenant,'APPID_CLIENT_ID':api,'APPID_ISSUER':'https://au-syd.appid.cloud.ibm.com/oauth/v4/'+tenant,'AUTH_SCOPE':'invoice/process','DATABASE_HOST':'fixture.databases.appdomain.cloud','DATABASE_PORT':'30426','DATABASE_PASSWORD_FILE':'/tmp/unread-synthetic-secret','IAM_PROFILE_ID':'Profile-synthetic'}}
    return{**common,**settings[provider]}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--provider',choices=['aws','azure','gcp','ibm'],required=True);parser.add_argument('--source',required=True);parser.add_argument('--image',required=True);parser.add_argument('--docker-host',required=True);parser.add_argument('--out',required=True);parser.add_argument('--postgres-config');parser.add_argument('--terraform-plan-log');args=parser.parse_args();source=Path(args.source).resolve();out=Path(args.out).resolve()
    if not source.is_relative_to(ROOT/'.local')or not out.is_relative_to(ROOT/'.local')or out.exists()or not re.fullmatch(r'sha256:[0-9a-f]{64}',args.image):raise ValueError('Use exact local emitted sources/image and a fresh evidence directory')
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket():raise ValueError('Use the owned local Docker socket')
    out.mkdir(parents=True);files={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in source.iterdir()if p.is_file()and(p.suffix in {'.py','.sql','.html','.css','.js','.pem'}or p.name in {'invoice-deployment.json','requirements.lock'})}
    dependencies=dict(re.findall(r'(?m)^([A-Za-z0-9_.-]+)==([^\s\\]+)',(source/'requirements.lock').read_text()))
    if len(files)<20 or len(dependencies)<25:raise ValueError('Incomplete emitted invoice application')
    source_hashes={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()};checks=[];test_hashes={};runtime_environment=environment(args.provider);worker_environment=None;plan_evidence=None
    if args.provider=='aws':runtime_environment['DATABASE_CA_FILE']='/app/rds-global-ca.pem'
    if args.terraform_plan_log:
        plan_path=Path(args.terraform_plan_log).resolve()
        if args.provider not in {'aws','azure'}or not plan_path.is_relative_to(ROOT/'.local')or plan_path.name!='provider-mocks.log':raise ValueError('Use the exact local qualified native mock plan log')
        qualification=json.loads((plan_path.parent/'qualification.json').read_text())
        if qualification.get('passed')is not True or qualification.get('provider')!=args.provider:raise ValueError('Native Terraform qualification must pass first')
        if not any(check.get('name')=='provider-mocks'and check.get('logSha256')==hashlib.sha256(plan_path.read_bytes()).hexdigest()for check in qualification['checks']):raise ValueError('Native plan log no longer matches its receipt')
        relative=source.relative_to(plan_path.parent).as_posix()+'/'
        for name,digest in source_hashes.items():
            if qualification['sourceHashes'].get(relative+name)!=digest:raise ValueError('Image source is not the exact qualified Terraform package')
        events=[json.loads(line)for line in plan_path.read_text().splitlines()if line.strip()]
        run_name='private_database_and_parser'if args.provider=='aws'else'private_data_and_parser'
        plans=[event['test_plan']for event in events if event.get('type')=='test_plan'and event.get('@testrun')==run_name]
        if len(plans)!=1:raise ValueError('Expected one admitted application-release mock plan')
        task_type='aws_ecs_task_definition'if args.provider=='aws'else'azapi_resource'
        tasks=[resource for resource in plans[0]['resource_changes']if resource.get('type')==task_type and resource['address'].endswith('_api[0]')]
        if len(tasks)!=1:raise ValueError('Expected the exact native API workload')
        def containers(task):
            after=task['change']['after']
            return json.loads(after['container_definitions'])if args.provider=='aws'else after['body']['properties']['template']['containers']
        apis=[container for container in containers(tasks[0])if container['name']=='api']
        if len(apis)!=1:raise ValueError('Expected one native API container')
        env_key='environment'if args.provider=='aws'else'env'
        runtime_environment={entry['name']:entry['value']for entry in apis[0][env_key]}
        worker_tasks=[resource for resource in plans[0]['resource_changes']if resource.get('type')==task_type and resource['address'].endswith('_worker[0]')]
        if len(worker_tasks)!=1:raise ValueError('Expected the exact native worker workload')
        workers=[container for container in containers(worker_tasks[0])if container['name']=='worker']
        if len(workers)!=1 or workers[0].get('command')!=['python','-I','/app/invoice_worker.py']:raise ValueError('Native worker command changed')
        worker=workers[0]
        secrets=[secret['name']for secret in worker.get('secrets',[])]if args.provider=='aws'else[entry['name']for entry in worker['env']if'secretRef'in entry]
        if secrets!=['DESTINATION_TOKEN']:raise ValueError('Native worker secret boundary changed')
        worker_environment={entry['name']:entry['value']for entry in worker[env_key]if'value'in entry}
        if any(not isinstance(value,str)for value in [*runtime_environment.values(),*worker_environment.values()]):raise ValueError('Native workload environment is unresolved')
        if args.provider=='azure':
            for task in [tasks[0],worker_tasks[0]]:
                configuration=task['change']['after']['body']['properties']['configuration'];registries=configuration['registries']
                if len(registries)!=1 or not all(container['image'].startswith(registries[0]['server']+'/invoice/')for container in containers(task)):raise ValueError('Registry/image wiring disagrees in the emitted plan')
        plan_evidence={'qualificationSha256':hashlib.sha256((plan_path.parent/'qualification.json').read_bytes()).hexdigest(),'planLogSha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'taskAddress':tasks[0]['address'],'boundary':'Actual emitted environment resolved by a native provider-mock Terraform plan; native cloud resources/values remain fixtures.'}
    with tempfile.TemporaryDirectory(prefix='atmem-invoice-image-check-')as scratch:
        config=Path(scratch)/'docker-config';config.mkdir();(config/'config.json').write_text('{}\n');env={'PATH':os.environ.get('PATH',''),'HOME':scratch,'DOCKER_CONFIG':str(config),'DOCKER_HOST':args.docker_host}
        inspect=subprocess.run(['docker','image','inspect',args.image],env=env,capture_output=True,timeout=15);metadata=json.loads(inspect.stdout)[0]
        if metadata['Os']!='linux'or metadata['Architecture']!='amd64'or metadata['Config']['User']!='10001:10001':raise ValueError('Unexpected delivery image platform/user')
        (out/'image.json').write_text(json.dumps(metadata,indent=2)+'\n')
        command=['docker','run','--rm','--platform','linux/amd64','--network','none','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--memory','512m','--cpus','1','--pids-limit','32','--cap-drop','ALL','--security-opt','no-new-privileges:true','-i',args.image,'python','-I','-c',PROBE]
        result=subprocess.run(command,env=env,input=json.dumps({'provider':args.provider,'files':files,'dependencies':dependencies,'environment':runtime_environment,'workerEnvironment':worker_environment}).encode(),capture_output=True,timeout=30)
        (out/'runtime.stdout').write_bytes(result.stdout);(out/'runtime.stderr').write_bytes(result.stderr);checks.append({'check':'exact-image-files-dependencies-native-imports-api-startup-and-denial','exitCode':result.returncode,'passed':result.returncode==0})
        if args.postgres_config:
            fixture_path=Path(args.postgres_config).resolve()
            if fixture_path.parent!=ROOT/'.local/durable-postgres'or fixture_path.name not in {'fixture.json','fixture-pg18.json'}:raise ValueError('Use the task-owned private local fixture config')
            fixture=json.loads(fixture_path.read_text())
            if fixture.get('name')not in {'atmem-durable-qualification','atmem-durable-qualification-pg18'}or not re.fullmatch(r'architect_qualification_[a-z0-9]{1,32}',fixture.get('database',''))or not re.fullmatch('[0-9a-f]{64}',fixture.get('marker','')):raise ValueError('Refusing an unrecognized local fixture')
            names=['durable_restricted_worker_acceptance.py','durable_worker_acceptance.py','durable_postgres_acceptance.py','durable_privileges_acceptance.py','durable_fixture_tasks.py']
            tests={'tests/runtime/'+name:(ROOT/'tests/runtime'/name).read_text()for name in names};test_hashes={name:hashlib.sha256(body.encode()).hexdigest()for name,body in tests.items()}
            # Only this qualification run uses the local VM host network to reach
            # the loopback-published synthetic database. No host files are mounted;
            # the private nonce is rechecked before creating any test SQL roles.
            queue_command=list(command);queue_command[queue_command.index('none')]='host';queue_command[-1]=QUEUE_PROBE
            result=subprocess.run(queue_command,env=env,input=json.dumps({'tests':tests,'fixture':fixture}).encode(),capture_output=True,timeout=45)
            (out/'queue.stdout').write_bytes(result.stdout);(out/'queue.stderr').write_bytes(result.stderr);checks.append({'check':'actual-delivery-image-restricted-native-postgres-queue-five-cases','exitCode':result.returncode,'passed':result.returncode==0})
    unchanged=all(hashlib.sha256((source/name).read_bytes()).hexdigest()==digest for name,digest in source_hashes.items());passed=unchanged and all(check['passed']for check in checks)
    receipt={'kind':'emitted-invoice-delivery-image','recordedAt':datetime.now(timezone.utc).isoformat(),'provider':args.provider,'imageId':args.image,'passed':passed,'checks':checks,'sourceHashes':source_hashes,'qualificationTestHashes':test_hashes,'nativeTerraformEnvironment':plan_evidence,'qualifierSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sourcesUnchanged':unchanged,'boundary':'Exact emitted delivery files, locked dependencies, actual native API startup/denial in network-disabled Linux. Optional five actual restricted native queue/PostgreSQL cases use the owned local loopback database through the VM host network with no host mounts; processors and destinations are synthetic. No native cloud token/IdP/model/storage/managed-database/hosting, complete generated Terraform project or deployment.','cloudOperations':False,'full28CaseAcceptanceComplete':False}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'provider':args.provider,'passed':passed,'receipt':str(out/'receipt.json')}));raise SystemExit(0 if passed else 1)
