"""Receipt for exact workflow sources against owned local PostgreSQL and TLS.

Does not establish a generated project, cloud identity/model quality, production
deployment, backup/restore or a vendor's actual idempotency guarantees.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'tests/runtime')]
from durable_postgres_acceptance import fixture_dsn
import psycopg

def hashes():
    files=[*list((ROOT/'tests/runtime').glob('*.py')),*list((ROOT/'src/runtime').glob('*workflow*')),*[ROOT/'src/runtime'/name for name in ['approved_http_destination.py','postgres-qualification-lock.json','durable-python-lock.json']],*[ROOT/'scripts'/name for name in ['setup-durable-runtime.py','start-durable-fixture.py','initialize-durable-fixture.py','qualify-durable-runtime.py']]]
    return {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in sorted(set(files))if path.is_file()}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);args=parser.parse_args();out=Path(args.out).resolve()
    if not out.is_relative_to(ROOT/'.local')or out.exists():raise ValueError('Use a fresh evidence directory below .local')
    out.mkdir(parents=True);before=hashes()
    with psycopg.connect(fixture_dsn())as conn:
        version=conn.execute('SHOW server_version').fetchone()[0];schema=conn.execute('SELECT version,source_sha256,queue_version FROM workflow.schema_version').fetchone()
    start=time.monotonic();checks=[]
    for label,command in [('dependency-check',[sys.executable,'-I','-m','pip','check']),('workflow-acceptance',[sys.executable,'-I','-m','unittest','discover','-s','tests/runtime','-p','durable_*acceptance.py','-v'])]:
        with(out/(label+'.log')).open('wb')as stream:
            try:result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=90);code=result.returncode
            except subprocess.TimeoutExpired:code=124
        checks.append({'check':label,'exitCode':code,'log':label+'.log'})
    log=(out/'workflow-acceptance.log').read_text();counts=re.findall(r'Ran (\d+) tests in',log);after=hashes()
    passed=all(check['exitCode']==0 for check in checks)and before==after and len(counts)==1
    receipt={'kind':'local-durable-workflow-core','recordedAt':datetime.now(timezone.utc).isoformat(),'passed':passed,'tests':int(counts[0])if len(counts)==1 else None,'seconds':round(time.monotonic()-start,3),'python':sys.version,'postgresVersion':version,'schemaVersion':schema[0],'schemaSha256':schema[1],'queueVersion':schema[2],'sourceHashes':before,'sourcesUnchangedDuringChecks':before==after,'checks':checks,'evidenceBoundary':'Real local PostgreSQL, native queue workers, restricted local DB logins, SIGKILL replacements, loopback TLS and child process deadlines; synthetic processors and destinations. No native cloud/IdP/PDF/model/vendor, complete project, backup/restore, full matrix or deployment claim.','cloudOperations':False,'full28CaseAcceptanceComplete':False}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':passed,'tests':receipt['tests'],'receipt':str(out/'receipt.json')}));sys.exit(0 if passed else 1)
