"""Local composed upload -> sandbox OCR -> model -> approval -> TLS workflow.

Native PostgreSQL and queue workers use distinct restricted DB logins. Identity
and object storage are explicit local fixtures. Docker access belongs to this
probe, never to an exported application. No complete cloud project is claimed.
"""
import argparse
import asyncio
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import time
import threading
import uuid

ROOT=Path(__file__).resolve().parents[1]
admission=argparse.ArgumentParser(add_help=False);admission.add_argument('--application-source');admission.add_argument('--artifact-receipt');admitted,_=admission.parse_known_args()
RUNTIME=ROOT/'src/runtime';artifact_receipt_hash=None
if bool(admitted.application_source)!=bool(admitted.artifact_receipt):raise ValueError('Provide both exact application source and native artifact receipt')
if admitted.application_source:
    RUNTIME=Path(admitted.application_source).resolve();receipt_path=Path(admitted.artifact_receipt).resolve()
    if not RUNTIME.is_relative_to(ROOT/'.local')or not receipt_path.is_relative_to(ROOT/'.local'):raise ValueError('Use local qualification artifacts')
    qualified=json.loads(receipt_path.read_text());artifact_receipt_hash=hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    if qualified.get('kind')!='invoice-live-artifact-native-qualification'or not qualified.get('passed'):raise ValueError('Use a passing exact live artifact receipt')
    prefix='applications/'+RUNTIME.name+'/'
    expected={name[len(prefix):]:digest for name,digest in qualified['sourceHashes'].items()if name.startswith(prefix)}
    if not expected:raise ValueError('Application missing from qualified artifact')
    for name,digest in expected.items():
        target=(RUNTIME/name).resolve()
        if not target.is_relative_to(RUNTIME)or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('Application differs from original live artifact')
sys.path[:0]=[str(ROOT),str(RUNTIME),str(RUNTIME/'parser'),str(ROOT/'tests/runtime'),str(ROOT/'.local/azure-runtime-sdk')]
import httpx
import psycopg
from durable_privileges_acceptance import create_runtime_roles
from invoice_http_acceptance import OwnedObjectsFixture
from workflow_tls_destination_fixture import TlsDestinationFixture
from approved_http_destination import ApprovedHttpDestination
from workflow_worker import WorkflowRuntime,producer_store
from invoice_http import create_app
from invoice_processing import InvoiceProcessor
from invoice_parser_transport import ParserClient
from invoice_parser_service import ParserServer
from server.local_providers import call_cli

async def evaluate(args,out):
    owner,_,_,api_dsn,worker_dsn=create_runtime_roles();account=str(uuid.uuid4());namespace='q'+uuid.uuid4().hex[:12];objects=OwnedObjectsFixture();sink=TlsDestinationFixture();model_calls=[];checks={};task=None;parser_runs=[];started=time.monotonic()
    source_paths=[Path(__file__).resolve(),*[(RUNTIME/name if(RUNTIME/name).is_file()else RUNTIME/'parser'/name)for name in ['invoice_http.py','invoice_object_store.py','invoice_extraction.py','invoice_processing.py','invoice_retention.py','invoice_document.py','structured_output.py','workflow_errors.py','invoice_parser_transport.py','invoice_parser_service.py','durable_workflow.py','workflow_worker.py','workflow_schema.sql','workflow_database.py','approved_http_destination.py','workflow_contract.py']],ROOT/'tests/runtime/invoice_http_acceptance.py',ROOT/'tests/runtime/durable_privileges_acceptance.py',ROOT/'tests/runtime/workflow_tls_destination_fixture.py',ROOT/'server/local_providers.py']
    hashes={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in source_paths};native=json.loads(Path(args.parser_receipt).read_text())
    if not native.get('passed')or native.get('kind')!='credentialless-linux-invoice-parser':raise ValueError('Use a passing exact parser image receipt')
    if admitted.application_source:
        for name in ['invoice_document.py','invoice_parser_cli.py','invoice_parser_service.py','invoice_parser_identity.py','parser-requirements.lock']:
            actual=RUNTIME/'parser'/name
            if hashlib.sha256(actual.read_bytes()).hexdigest()!=native['sourceHashes'].get('src/runtime/'+name):raise ValueError('Parser image does not match emitted parser sources: '+name)
    image=native['imageId'];destination=ApprovedHttpDestination(sink.url,lambda:sink.token,destination_scope='synthetic-account',idempotency_verified=True,tls_context=sink.context)
    with psycopg.connect(owner)as conn:
        conn.execute('INSERT INTO workflow.accounts(id)VALUES(%s)',(account,))
        for subject,roles in [('pipeline-staff',['user']),('pipeline-reviewer',['reviewer'])]:conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles)VALUES(%s,%s,%s)',(account,subject,roles))
    with tempfile.TemporaryDirectory(prefix='atmem-invoice-workflow-')as scratch:
        config=Path(scratch)/'docker-config';config.mkdir();(config/'config.json').write_text('{}\n');environment={'PATH':os.environ.get('PATH',''),'HOME':scratch,'DOCKER_HOST':args.docker_host,'DOCKER_CONFIG':str(config)}
        class IsolatedParserFixture:
            # Only this separate loopback fixture owns Docker access. The actual
            # worker's processing composition calls the private HTTPS adapter.
            def extract(self,raw,digest):
                command=['docker','run','--rm','--platform','linux/amd64','--network','none','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--memory','512m','--cpus','1','--pids-limit','32','--cap-drop','ALL','--security-opt','no-new-privileges:true','-i',image]
                response=subprocess.run(command,cwd=ROOT,env=environment,input=raw,capture_output=True,timeout=120)
                if response.returncode:raise RuntimeError('Sandbox parser did not complete')
                parsed=json.loads(response.stdout)
                if parsed.get('status')!='ok'or parsed['document']['sha256']!=digest:raise ValueError('Sandbox original digest mismatch')
                parser_runs.append({'imageId':image,'originalSha256':digest,'pages':len(parsed['document']['pages'])});return parsed['document']
        parser_server=ParserServer(('127.0.0.1',0),IsolatedParserFixture());parser_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);parser_context.load_cert_chain(sink.ca_file,Path(sink.folder.name)/'fixture.key');parser_server.socket=parser_context.wrap_socket(parser_server.socket,server_side=True);parser_thread=threading.Thread(target=parser_server.serve_forever,daemon=True);parser_thread.start()
        import requests
        parser_session=requests.Session();parser_session.verify=str(sink.ca_file);private_parser=ParserClient('https://localhost:'+str(parser_server.server_port)+'/extract',session=parser_session)
        class LocalModel:
            def __init__(self,operation_id):self.operation_id=operation_id
            def generate(self,payload,schema,instruction):
                async def connected():return False
                call={'operationId':self.operation_id,'request':json.loads(payload),'schema':schema,'instruction':instruction}
                answer=asyncio.run(call_cli('codex',args.model,payload,instruction,schema,connected,effort='low',timeout=180));call['response']=answer;model_calls.append(call);return json.dumps(answer,ensure_ascii=False)
        def process(row):return InvoiceProcessor(objects,private_parser,LocalModel(str(row['id'])))(row)
        runtime=WorkflowRuntime(worker_dsn,process,destination,namespace=namespace,idempotent_destination=True)
        api=producer_store(api_dsn,destination_contract=destination.contract,namespace=namespace)
        def verify(token):
            if token not in {'staff','reviewer'}:raise PermissionError('Unknown fixture identity')
            return'pipeline-'+token
        app=create_app(verify,api,objects,account_id=account,public_origin='https://invoices.example.test')
        def headers(token='staff'):return{'Authorization':'Bearer '+token,'Origin':'https://invoices.example.test'}
        cases=['invoice-mixed.pdf','invoice-injected.pdf'];operations={}
        try:
            task=asyncio.create_task(runtime.run(install_signal_handlers=False,fetch_job_polling_interval=.1,shutdown_graceful_timeout=2))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://invoices.example.test')as client:
                for name in cases:
                    raw=(ROOT/'benchmarks/convergence/fixtures/invoices'/name).read_bytes()
                    replies=await asyncio.gather(*[client.post('/api/invoices',content=raw,headers={**headers(),'Content-Type':'application/pdf'})for _ in range(2)])
                    checks[name+'-uploads']=all(reply.status_code==202 for reply in replies)
                    ids={reply.json()['invoice']['id']for reply in replies};checks[name+'-dedup']=len(ids)==1;operations[name]=next(iter(ids))
                async def wait_for(state):
                    deadline=time.monotonic()+240
                    while time.monotonic()<deadline:
                        if task.done():task.result();raise RuntimeError('Worker exited before acceptance completed')
                        rows=[(await client.get('/api/invoices/'+operation,headers=headers())).json()['invoice']for operation in operations.values()]
                        if all(row['state']==state for row in rows):return rows
                        if any(row['state']=='dead'for row in rows):raise RuntimeError('Workflow requires recovery; inspect retained model/parser evidence')
                        await asyncio.sleep(.15)
                    raise RuntimeError('Composed workflow exceeded its qualification deadline')
                rows=await wait_for('review');checks['noExternalActionBeforeApproval']=not sink.calls
                for row in rows:
                    checks[row['id']+'-fields']=all(row['result'].get(name)==expected for name,expected in {'supplier':'Southern Horizon Test Supplies','invoice_date':'2026-11-10','total':'42.50','currency':'AUD'}.items())
                    response=await client.post('/api/invoices/'+row['id']+'/approve',json={'revision':row['revision']},headers=headers());checks[row['id']+'-ordinaryStaffDenied']=response.status_code==403
                    response=await client.post('/api/invoices/'+row['id']+'/approve',json={'revision':row['revision']},headers=headers('reviewer'));checks[row['id']+'-approved']=response.status_code==200
                sent=await wait_for('sent');checks['twoIndependentCompletedOperations']=len(sent)==2 and len(sink.effects)==2 and len(sink.calls)==2
                for row in sent:
                    await client.post('/api/invoices/'+row['id']+'/approve',json={'revision':row['revision']},headers=headers('reviewer'))
                await asyncio.sleep(.2);checks['repeatedApprovalDidNotResend']=len(sink.calls)==2;checks['twoActualModelAndParserOperations']=len(model_calls)==len(parser_runs)==2
        except Exception as error:checks['completed']=False;(out/'error.json').write_text(json.dumps({'kind':type(error).__name__,'message':str(error)[:500]})+'\n')
        finally:
            if task is not None:
                task.cancel()
                try:await task
                except asyncio.CancelledError:pass
            parser_server.shutdown();parser_server.server_close();parser_thread.join(timeout=2);parser_session.close();sink.close()
    (out/'model-operations.json').write_text(json.dumps(model_calls,indent=2)+'\n');(out/'parser-operations.json').write_text(json.dumps(parser_runs,indent=2)+'\n')
    unchanged=all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in hashes.items());receipt={'kind':'local-composed-invoice-workflow','recordedAt':datetime.now(timezone.utc).isoformat(),'passed':bool(checks)and all(checks.values())and unchanged,'seconds':round(time.monotonic()-started,3),'checks':checks,'applicationSource':str(RUNTIME.relative_to(ROOT)),'artifactReceiptSha256':artifact_receipt_hash,'sourceHashes':hashes,'sourceUnchanged':unchanged,'parserImageId':image,'parserReceiptSha256':hashlib.sha256(Path(args.parser_receipt).read_bytes()).hexdigest(),'model':'signed-in-local-codex','requestedModel':args.model,'cloudOperations':False,'fullProjectQualification':False,'boundary':'Actual ASGI upload, restricted PostgreSQL producer/worker roles, Procrastinate jobs, network-disabled locked Linux PDF/OCR, local model, independent field/evidence decoder, server approval and real loopback TLS destination. Identity and object persistence are explicit fixtures. No native cloud model/IdP/storage/database/hosting, production Docker socket design, vendor guarantees, broad corpus or full project qualification.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':receipt['passed'],'checks':checks,'receipt':str(out/'receipt.json')}));return receipt['passed']

if __name__=='__main__':
    parser=argparse.ArgumentParser(parents=[admission]);parser.add_argument('--live',action='store_true',required=True);parser.add_argument('--out',required=True);parser.add_argument('--parser-receipt',required=True);parser.add_argument('--docker-host',required=True);parser.add_argument('--model',default='default');args=parser.parse_args();out=Path(args.out).resolve()
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket()or not out.is_relative_to(ROOT/'.local')or out.exists():raise ValueError('Use an existing local Docker socket and fresh local evidence directory')
    out.mkdir(parents=True);raise SystemExit(0 if asyncio.run(evaluate(args,out))else 1)
