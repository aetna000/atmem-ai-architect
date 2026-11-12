"""Run emitted local acceptance sources; never connect to a cloud database."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
TESTS=['invoice_extraction_acceptance.py','invoice_storage_acceptance.py','invoice_http_acceptance.py','invoice_web_acceptance.py','invoice_identity_acceptance.py','invoice_parser_rpc_acceptance.py','invoice_parser_identity_acceptance.py','invoice_worker_acceptance.py','invoice_operations_acceptance.py','invoice_operator_acceptance.py','invoice_operator_job_acceptance.py']

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    fixture=Path(args.fixture).resolve();out=Path(args.out).resolve()
    if out.exists()or not out.is_relative_to(ROOT/'.local'):raise ValueError('Use a fresh private .local output directory')
    out.mkdir(parents=True,mode=0o700);out.chmod(0o700)
    # Guarded fixture validation happens before any acceptance test writes SQL.
    os.environ['ATMEM_WORKFLOW_TEST_CONFIG']=str(fixture);sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
    from durable_postgres_acceptance import fixture_dsn
    fixture_dsn()
    files=[*ROOT.glob('*.py'),*ROOT.glob('*.sql'),*ROOT.glob('*.lock'),*ROOT.glob('invoice-web.*'),*(ROOT/'tests').glob('*.py'),*(ROOT/'test-fixtures').glob('*')]
    def hashes():return {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in sorted(files)}
    before=hashes();checks=[]
    with (fixture.parent/'invoice-export-tests.lock').open('a')as lock:
        os.chmod(lock.name,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for name in TESTS:
            log=out/(name+'.log')
            with log.open('wb')as stream:result=subprocess.run([sys.executable,'-I',str(ROOT/'tests'/name)],cwd=ROOT,env={**os.environ,'ATMEM_WORKFLOW_TEST_CONFIG':str(fixture),'PYTHONDONTWRITEBYTECODE':'1'},stdout=stream,stderr=subprocess.STDOUT,timeout=60)
            counts=re.findall(r'Ran (\d+) tests in',log.read_text());checks.append({'name':name,'passed':result.returncode==0,'tests':int(counts[0])if len(counts)==1 else None,'log':log.name})
    passed=all(check['passed']and check['tests']for check in checks)and before==hashes()
    receipt={'format':'invoice-package-local-tests-v1','passed':passed,'checks':checks,'sourceHashes':before,'sourcesUnchanged':before==hashes(),'cloudOperations':False,'boundary':'Actual emitted source and owned loopback SQL with synthetic identities/storage/model/accounting protocols. Not native cloud authentication, model quality, real parser image, managed restore, account plan or deployment.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':passed,'tests':sum(check['tests']or 0 for check in checks),'receipt':str(out/'receipt.json')}));sys.exit(0 if passed else 1)
