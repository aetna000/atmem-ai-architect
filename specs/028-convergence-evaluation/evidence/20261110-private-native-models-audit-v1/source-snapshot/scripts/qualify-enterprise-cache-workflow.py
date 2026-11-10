"""Actual restricted Linux parser + encrypted SQL + native question queue.

Only owned synthetic fixtures are read. Microsoft/Atlassian HTTP and model output
remain explicit fixtures. This is a composed local receipt, not cloud acceptance.
"""
import argparse
import asyncio
from contextlib import suppress
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'tests/runtime'),str(ROOT/'.local/azure-runtime-sdk')]
import psycopg
from enterprise_document_contract import document_result
from enterprise_query_service import EnterpriseQueryWorker
import enterprise_queries_http_postgres as fixture


async def qualify(args):
    out=Path(args.out).resolve();receipt_path=Path(args.parser_receipt).resolve()
    if out.exists()or not out.is_relative_to(ROOT/'.local')or not receipt_path.is_relative_to(ROOT/'.local'):raise ValueError('Use a fresh local output and an owned prior parser receipt')
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket():raise ValueError('Use the owned local Docker Unix socket')
    prior=json.loads(receipt_path.read_text())
    if not prior['allChecksPassed']or not re.fullmatch('sha256:[0-9a-f]{64}',prior['imageId']):raise ValueError('Supply the qualified exact parser image')
    payload=['enterprise_document_contract.py','EnterpriseDocument.java','enterprise_document.py','enterprise_document_cli.py','enterprise_parser_service.py','enterprise-document.Dockerfile','enterprise-document-lock.json']
    for name in payload:
        source='src/runtime/'+name
        if hashlib.sha256((ROOT/source).read_bytes()).hexdigest()!=prior['sourceHashes'][source]:raise ValueError('Parser payload source changed; rebuild and qualify it first')
    out.mkdir(parents=True)
    env={'PATH':os.environ.get('PATH',''),'HOME':str(out),'DOCKER_HOST':args.docker_host,
        'DOCKER_CONFIG':str(ROOT/'.local/qualification-docker-config')}
    inspected=subprocess.run(['docker','image','inspect',prior['imageId']],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    image=json.loads(inspected.stdout)[0]
    if image['Os']!='linux'or image['Architecture']!='amd64'or image['Config']['User']!='10001:10001':raise ValueError('Use the qualified non-root Linux parser')
    revision=hashlib.sha256(json.dumps({key:image[key]for key in ['RootFS','Config','Os','Architecture']},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    (out/'parser-image.json').write_bytes(inspected.stdout)
    source_paths=[*list((ROOT/'src/runtime').glob('enterprise*.py')),
        *list((ROOT/'src/runtime').glob('enterprise*schema.sql')),
        ROOT/'src/runtime/public_faq.py',ROOT/'src/runtime/faq-output-contract.json',Path(__file__).resolve()]
    source_paths += [ROOT/'tests/runtime'/name for name in ['enterprise_queries_http_postgres.py','enterprise_http_postgres.py','enterprise_auth_postgres.py','enterprise_oauth_acceptance.py','durable_postgres_acceptance.py','durable_fixture_tasks.py']]
    inputs=[('policy.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document','Staff receive twenty days of paid leave.'),
            ('invoice-scan.pdf','application/pdf','Invoice total: AUD 42.50')]
    files={name:ROOT/'benchmarks/convergence/fixtures'/('invoices'if name.endswith('.pdf')else'enterprise-documents')/name for name,_,_ in inputs}
    source_paths += list(files.values())
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in source_paths}
    checks=[];parses=[];attempts=[];diagnostics=[];success=False;case=None;server_version=None
    def trace(frame,event,value):
        if event=='exception'and '/src/runtime/enterprise_'in frame.f_code.co_filename:
            diagnostics.append({'module':Path(frame.f_code.co_filename).name,'function':frame.f_code.co_name,'line':frame.f_lineno,'exception':value[0].__name__})
        return trace
    threading.settrace(trace)
    def check(label,value):
        checks.append({'check':label,'passed':bool(value)})
        if not value:raise AssertionError(label)
    def extract(raw,mime):
        started=time.monotonic()
        command=['docker','run','--rm','--platform','linux/amd64','--network','none','--read-only',
            '--tmpfs','/tmp:rw,noexec,nosuid,size=128m','--memory','1g','--cpus','2','--pids-limit','128',
            '--cap-drop','ALL','--security-opt','no-new-privileges:true','-i',prior['imageId'],
            'python','-I','/app/enterprise_document_cli.py',mime]
        result=subprocess.run(command,env=env,input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=150)
        attempts.append({'exitCode':result.returncode,'mediaType':mime,'stdoutBytes':len(result.stdout),'stderrBytes':len(result.stderr)})
        (out/('parser-attempt-'+str(len(attempts))+'.stderr')).write_bytes(result.stderr)
        if result.returncode!=0:raise RuntimeError('Actual isolated document extraction failed')
        value=json.loads(result.stdout)
        if set(value)!={'status','document'}or value['status']!='ok':raise ValueError('Invalid parser result')
        document=document_result(value['document'],raw,mime)
        parses.append({'sha256':hashlib.sha256(raw).hexdigest(),'mediaType':mime,'seconds':time.monotonic()-started,
            'outputSha256':hashlib.sha256(result.stdout).hexdigest()})
        return document['text']
    try:
        fixture.QueuedHttp.setUpClass();case=fixture.QueuedHttp();await case.asyncSetUp()
        with psycopg.connect(case.f.owner_dsn)as conn:server_version=int(conn.execute('SHOW server_version_num').fetchone()[0])
        case.answers.extraction_cache.parser_revision=revision
        original=case.answers.make_engine
        def factory(*values):
            engine=original(*values);engine.decode=extract;return engine
        case.answers.make_engine=factory
        worker=EnterpriseQueryWorker(case.f.app_dsn,case.answers)
        for number,(name,mime,quote)in enumerate(inputs):
            case.f.document_bytes=files[name].read_bytes();case.f.document_mime=mime
            case.f.source_version='v'+str(number+1);case.f.answer_quote=quote
            for iteration in range(2):
                identity=await case.submit()
                await worker.run(wait=False,concurrency=1,install_signal_handlers=False,listen_notify=False,fetch_job_polling_interval=.01)
                response=await case.status(identity);value=response.json()
                row=await asyncio.to_thread(case.store.get,case.browser(),identity)
                (out/(name+'-'+str(iteration)+'-status.json')).write_text(json.dumps({'httpStatus':response.status_code,'state':value.get('status'),'attempt':row['attempt'],'errorCode':value.get('errorCode'),'hasResult':'result'in value,'nativeAttempts':len(attempts),'modelCalls':len(case.f.model_calls)},indent=2)+'\n')
                check(name+'-'+str(iteration)+'-verified-answer',response.status_code==200 and value.get('status')=='ready'and value['result']['citations'][0]['quote']==quote)
                check(name+'-'+str(iteration)+'-expected-native-parse-count',len(parses)==number+1)
        check('every-question-reads-current-source-bytes',case.f.document_downloads==4)
        case.f.source_offline=True;identity=await case.submit()
        await worker.run(wait=False,concurrency=1,install_signal_handlers=False,listen_notify=False,fetch_job_polling_interval=.01)
        status=await case.status(identity)
        check('warm-cache-is-not-an-outage-answer',status.json()['status']=='queued'and'result'not in status.json()and len(case.f.model_calls)==4)
        case.f.source_offline=False
        pending=asyncio.create_task(worker.run(concurrency=1,install_signal_handlers=False,listen_notify=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=1))
        try:
            deadline=time.monotonic()+15
            while True:
                row=await asyncio.to_thread(case.store.get,case.browser(),identity)
                if row['state']=='ready':break
                if time.monotonic()>deadline:raise TimeoutError('Native queue recovery did not complete')
                await asyncio.sleep(.1)
        finally:
            pending.cancel()
            with suppress(asyncio.CancelledError):await pending
        check('recovery-revalidates-and-reuses-immutable-extraction',(await case.status(identity)).json()['status']=='ready'and len(parses)==2 and case.f.document_downloads==5)
        await case.f.client.delete('/api/sources/sharepoint',headers=case.f.headers())
        identity=await case.submit();await asyncio.to_thread(case.answers.execute,identity)
        status=(await case.status(identity)).json()
        check('withdrawn-consent-cannot-use-warm-derivative',status['status']=='failed'and status['errorCode']=='source'and len(case.f.model_calls)==5 and len(parses)==2)
        with psycopg.connect(case.f.owner_dsn)as conn:
            values=conn.execute('SELECT value_ciphertext FROM enterprise_extractions.documents WHERE account_id=%s',(case.f.account,)).fetchall()
            audit=conn.execute("SELECT count(*)FILTER(WHERE event='knowledge.answer'AND outcome='answered'),count(*)FILTER(WHERE event='knowledge.release'AND outcome='released'),count(*)FILTER(WHERE query_id IS NULL OR attempt IS NULL)FROM enterprise_audit.events WHERE account_id=%s",(case.f.account,)).fetchone()
        check('derived-text-persists-only-encrypted',len(values)==2 and all('twenty days'not in value[0]and'42.50'not in value[0]for value in values))
        check('native-office-pdf-answers-and-releases-have-durable-attempt-audit',audit==(5,5,0))
        check('source-bytes-unchanged',all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items()))
        success=True
    finally:
        threading.settrace(None)
        if case is not None:await case.asyncTearDown()
        (out/'exception-types.json').write_text(json.dumps(diagnostics[-100:],indent=2)+'\n')
        (out/'receipt.json').write_text(json.dumps({'recordedAt':datetime.now(timezone.utc).isoformat(),'passed':success,'checks':checks,
            'parserImageId':prior['imageId'],'parserRevision':revision,'parses':parses,'parserAttempts':attempts,'sourceHashes':hashes,
            'postgresVersionNum':server_version,'scope':'Actual restricted Linux Office/OCR bytes, encrypted local PostgreSQL, API/JWT/MSAL/native queue/source adapter/coordinator; vendor/source HTTP and model outputs are fixtures. No cloud/deployment/full-project claim.'},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--docker-host',required=True);parser.add_argument('--parser-receipt',required=True)
    asyncio.run(qualify(parser.parse_args()))
