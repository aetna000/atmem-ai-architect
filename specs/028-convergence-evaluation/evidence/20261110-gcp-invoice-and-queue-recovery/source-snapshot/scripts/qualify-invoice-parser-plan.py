"""Actual locked parser startup with native Terraform-resolved public settings.

Network-disabled Linux only. JWT signatures/caller denial and native PDF/OCR are
qualified separately. No cloud identity, ingress, account or deployment claim.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[1]
PROBE=r'''
import hashlib,http.client,json,os,subprocess,sys,time
from pathlib import Path
packet=json.load(sys.stdin)
for name,digest in packet['files'].items():assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest()==digest,name
env={'PATH':'/usr/local/bin:/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1',**packet['environment']}
assert env['PARSER_AUTH_MODE']=='entra-workload'
process=subprocess.Popen([sys.executable,'-I','/app/invoice_parser_service.py'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
try:
 deadline=time.monotonic()+8
 while True:
  if process.poll()is not None:raise AssertionError('Parser main exited: '+process.stderr.read().decode())
  try:
   client=http.client.HTTPConnection('127.0.0.1',int(env['PORT']),timeout=1);client.request('GET','/healthz');response=client.getresponse();assert response.status==200;response.read();client.close();break
  except OSError:
   if time.monotonic()>deadline:raise
   time.sleep(.05)
 for token in [None,'malformed']:
  headers={'Content-Type':'application/pdf'}
  if token:headers['Authorization']='Bearer '+token
  client=http.client.HTTPConnection('127.0.0.1',int(env['PORT']),timeout=2);client.request('POST','/extract',body=b'%PDF-deliberately-not-parsed',headers=headers);response=client.getresponse();assert response.status==403;value=json.loads(response.read());assert value=={'status':'rejected','reason':'access_denied'};client.close()
 print(json.dumps({'actualParserEntrypoint':'running','nativeTerraformEnvironment':'accepted','missingAndMalformedWorkerCredentials':403,'network':'disabled; no cloud requests'}))
finally:
 process.terminate()
 try:process.wait(timeout=3)
 except subprocess.TimeoutExpired:process.kill();process.wait(timeout=2)
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--parser-receipt',required=True);parser.add_argument('--terraform-plan-log',required=True);parser.add_argument('--docker-host',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    out=Path(args.out).resolve();plan_path=Path(args.terraform_plan_log).resolve();parser_path=Path(args.parser_receipt).resolve()
    if out.exists()or not out.is_relative_to(ROOT/'.local')or not plan_path.is_relative_to(ROOT/'.local')or not parser_path.is_relative_to(ROOT/'.local'):raise ValueError('Use local exact receipts and a fresh output')
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket():raise ValueError('Use the existing local Docker socket')
    source=json.loads(parser_path.read_text());qualification=json.loads((plan_path.parent/'qualification.json').read_text())
    if source.get('passed')is not True or qualification.get('passed')is not True or qualification.get('provider')!='azure'or not re.fullmatch(r'sha256:[0-9a-f]{64}',source.get('imageId','')):raise ValueError('Require passing exact parser and native Azure compiler receipts')
    if not any(check.get('name')=='provider-mocks'and check.get('logSha256')==hashlib.sha256(plan_path.read_bytes()).hexdigest()for check in qualification['checks']):raise ValueError('Native plan log changed')
    plans=[event['test_plan']for line in plan_path.read_text().splitlines()if line.strip()and(event:=json.loads(line)).get('type')=='test_plan'and event.get('@testrun')=='private_data_and_parser']
    if len(plans)!=1:raise ValueError('Use one admitted native application plan')
    tasks=[resource for resource in plans[0]['resource_changes']if resource['type']=='azapi_resource'and resource['address'].endswith('_parser[0]')]
    if len(tasks)!=1:raise ValueError('Expected one private parser workload')
    task=tasks[0]['change']['after'];settings=task['body']['properties']['configuration'];containers=task['body']['properties']['template']['containers']
    if len(containers)!=1 or settings['ingress']['external']is not False or len(settings['identitySettings'])!=1 or settings['identitySettings'][0]['lifecycle']!='None':raise ValueError('Native parser ingress/identity separation changed')
    env={entry['name']:entry['value']for entry in containers[0]['env']}
    if any(not isinstance(value,str)or(key!='PORT'and not key.startswith('PARSER_'))for key,value in env.items()):raise ValueError('Parser settings contain unrelated/unresolved authority')
    files={name:source['sourceHashes']['src/runtime/'+name]for name in ['invoice_parser_service.py','invoice_parser_identity.py','invoice_document.py','invoice_extraction.py','structured_output.py','parser-requirements.lock']}
    component=tasks[0]['name'].removesuffix('_parser')
    if not re.fullmatch(r'block_[0-9a-f]+',component):raise ValueError('Use the exact owned parser component')
    for name,digest in files.items():
        if qualification['sourceHashes'].get('applications/'+component+'/parser/'+name)!=digest:raise ValueError('Parser image source differs from the qualified native export')
    out.mkdir(parents=True)
    command=['docker','--config',str(ROOT/'.local/qualification-docker-config'),'--host',args.docker_host,'run','--rm','--platform','linux/amd64','--network','none','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--memory','512m','--pids-limit','32','--cap-drop','ALL','--security-opt','no-new-privileges:true','-i',source['imageId'],'python','-I','-c',PROBE]
    result=subprocess.run(command,input=json.dumps({'files':files,'environment':env}).encode(),capture_output=True,timeout=20)
    (out/'stdout.log').write_bytes(result.stdout);(out/'stderr.log').write_bytes(result.stderr)
    receipt={'kind':'native-plan-parser-entrypoint','recordedAt':datetime.now(timezone.utc).isoformat(),'passed':result.returncode==0,'exitCode':result.returncode,'imageId':source['imageId'],'parserReceiptSha256':hashlib.sha256(parser_path.read_bytes()).hexdigest(),'nativePlanQualificationSha256':hashlib.sha256((plan_path.parent/'qualification.json').read_bytes()).hexdigest(),'planLogSha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'sourceHashes':{'scripts/qualify-invoice-parser-plan.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},'imageFiles':files,'cloudOperations':False,'boundary':'Actual nonroot network-disabled Linux parser main accepts public settings resolved from the native Terraform mock plan; health succeeds and missing/malformed caller credentials are denied before parsing. No cloud IAM/ingress or full project qualification.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':receipt['passed'],'receipt':str(out/'receipt.json')}));raise SystemExit(result.returncode)
