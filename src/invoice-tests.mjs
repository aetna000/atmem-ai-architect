import sources from'./runtime/invoice-test-sources.json'with{type:'json'};
import runtime from'./runtime/invoice-sources.json'with{type:'json'};
import base from'./runtime/python-container-lock.json'with{type:'json'};

export function invoiceTestFiles(provider,address){
 const root='applications/'+address+'/',files={};
 for(const[name,original]of Object.entries(sources)){
  if(!name.endsWith('.py'))continue;
  let code=original;
  if(name==='start-durable-fixture.py'){
   code=code.replace("import argparse\n","import argparse\nimport hashlib\n").replace("name='atmem-durable-qualification'+('-pg18'if args.major=='18'else'')","name='atmem-invoice-'+hashlib.sha256(str(ROOT).encode()).hexdigest()[:12]+('-pg18'if args.major=='18'else'')");
  }else{
   if(!code.includes('ROOT=Path(__file__).resolve().parents[2]')&&!['workflow_tls_destination_fixture.py','durable_fixture_tasks.py'].includes(name))throw Error('Review portable invoice test root: '+name);
   code=code.replaceAll('ROOT=Path(__file__).resolve().parents[2]',"ROOT=Path(__file__).resolve().parents[1]\nsys.path.insert(0,str(ROOT/'parser'))");
  }
  code=code.replaceAll("ROOT/'src/runtime/rds-global-ca.pem'","ROOT/'test-fixtures/rds-global-ca.pem'").replaceAll("ROOT/'src/runtime/postgres-qualification-lock.json'","ROOT/'test-fixtures/postgres-qualification-lock.json'").replaceAll("ROOT/'src/runtime'","ROOT").replaceAll("ROOT/'tests/runtime'","ROOT/'tests'").replaceAll(",str(ROOT/'.local/azure-runtime-sdk')",'');
  if(name==='durable_postgres_acceptance.py')code=code.replace("c.get('name')not in {'atmem-durable-qualification','atmem-durable-qualification-pg18'}","(c.get('name')not in {'atmem-durable-qualification','atmem-durable-qualification-pg18'}and not re.fullmatch(r'atmem-invoice-[0-9a-f]{12}(?:-pg18)?',str(c.get('name',''))))");
  if(name==='invoice_http_acceptance.py'){
   const fixture="(ROOT/'benchmarks/convergence/fixtures/invoices/invoice-text.pdf').read_bytes()";
   if(!code.includes(fixture))throw Error('Review portable PDF transport fixture');
   code='import base64\n'+code.replace(fixture,"base64.b64decode((ROOT/'test-fixtures/invoice-text.pdf.base64').read_text())");
  }
  if(name==='invoice_storage_acceptance.py'&&provider!=='aws'){
   const start=code.indexOf('class NativeS3InvoiceObjectsTests('),end=code.indexOf("if __name__=='__main__':");
   if(start<0||end<=start)throw Error('Review isolated provider test boundary');
   code=code.slice(0,start)+code.slice(end);code=code.replace(/^import boto3\n/m,'').replace(/^from botocore\.[^\n]+\n/gm,'');
  }
  if(name==='invoice_parser_rpc_acceptance.py'&&provider!=='azure'){
   const start=code.indexOf('class AzureParserIdentityTests('),end=code.indexOf('class IbmParserIdentityTests(');
   if(start<0||end<=start)throw Error('Review Azure-only native SDK test boundary');
   code=code.slice(0,start)+code.slice(end);
  }
  files[root+(name==='start-durable-fixture.py'?'tests/start-local-fixture.py':'tests/'+name)]=code;
 }
 files[root+'test-fixtures/postgres-qualification-lock.json']=sources['postgres-qualification-lock.json'];
 files[root+'test-fixtures/invoice-text.pdf.base64']=sources['invoice-text.pdf.base64']+'\n';
 files[root+'test-fixtures/rds-global-ca.pem']=runtime['rds-global-ca.pem'];
 files[root+'test-scope.json']=JSON.stringify({provider,scope:'Owned local SQL and synthetic protocol checks; provider SDK requirements follow the selected delivery lock.',sdkCases:{awsS3:provider==='aws',azureManagedIdentity:provider==='azure'},excludedForeignSdkCases:provider==='aws'?['azure ManagedIdentityCredential']:provider==='azure'?['AWS S3 boto3']:['AWS S3 boto3','azure ManagedIdentityCredential'],boundary:'Exclusion of a foreign SDK case is explicit contract selection, not a skipped test or evidence for that foreign provider.'},null,2)+'\n';
 files[root+'tests/run.py']=INVOICE_TEST_RUNNER;
 files[root+'TESTING.md']=INVOICE_TESTING;
 const patch=base.securityPackages[0];
 files[root+'Dockerfile.tests']=`FROM ${base.image}\nENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1\nADD --checksum=sha256:${patch.sha256} ${patch.url} /tmp/runtime-security.deb\nRUN dpkg -i /tmp/runtime-security.deb && rm /tmp/runtime-security.deb\nWORKDIR /app\nCOPY test-requirements.lock ./\nRUN python -I -m pip --isolated install --no-cache-dir --only-binary=:all: --require-hashes -r test-requirements.lock\nCOPY *.py *.sql invoice-deployment.json invoice-web.* ./\nCOPY parser/*.py ./parser/\nCOPY tests/ ./tests/\nCOPY test-fixtures/ ./test-fixtures/\nENTRYPOINT ["python", "-I", "tests/run.py"]\n`;
 files[root+'Dockerfile.tests.dockerignore']='*\n!test-requirements.lock\n!*.py\n!*.sql\n!invoice-deployment.json\n!invoice-web.*\n!parser/\n!parser/*.py\n!tests/\n!tests/*.py\n!test-fixtures/\n!test-fixtures/*\n';
 return files;
}

const INVOICE_TEST_RUNNER=`"""Run emitted local acceptance sources; never connect to a cloud database."""
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
TESTS=['invoice_extraction_acceptance.py','invoice_storage_acceptance.py','invoice_http_acceptance.py','invoice_web_acceptance.py','invoice_identity_acceptance.py','invoice_parser_rpc_acceptance.py','invoice_parser_identity_acceptance.py','invoice_worker_acceptance.py','invoice_operations_acceptance.py','invoice_operator_acceptance.py','invoice_operator_job_acceptance.py','workflow_payload_acceptance.py','workflow_http_acceptance.py']

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
            counts=re.findall(r'Ran (\\d+) tests in',log.read_text());checks.append({'name':name,'passed':result.returncode==0,'tests':int(counts[0])if len(counts)==1 else None,'log':log.name})
    passed=all(check['passed']and check['tests']for check in checks)and before==hashes()
    receipt={'format':'invoice-package-local-tests-v1','passed':passed,'checks':checks,'sourceHashes':before,'sourcesUnchanged':before==hashes(),'cloudOperations':False,'boundary':'Actual emitted source and owned loopback SQL with synthetic identities/storage/model/accounting protocols. Not native cloud authentication, model quality, real parser image, managed restore, account plan or deployment.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\\n');print(json.dumps({'passed':passed,'tests':sum(check['tests']or 0 for check in checks),'receipt':str(out/'receipt.json')}));sys.exit(0 if passed else 1)
`;

const INVOICE_TESTING=`# Portable local invoice acceptance

On Linux/amd64, create a separate Python 3.13 virtual environment from this application
directory for this provider. Install test-requirements.lock using pip --require-hashes
--only-binary=:all:. Do not mix IBM/AWS SDK environments or substitute another
provider's dependency resolution. Install OpenSSL with req -addext support for the
synthetic loopback TLS tests. No cloud credential is needed.

The wheel hashes target Linux/amd64. On another host, use the emitted Linux test
image: docker build --platform linux/amd64 -f Dockerfile.tests -t invoice-local-tests .
It is a separate developer test image, not the delivered API/worker image. Pass a
private owned loopback fixture configuration and a writable private output directory
to tests/run.py; do not copy credentials into its build context. Host networking
must be explicitly enabled/supported by the local Docker engine for loopback SQL.
No cloud/database/identity credential from the host is implicitly forwarded.

With an existing local Unix Docker socket, explicitly create the synthetic fixture:

    python tests/start-local-fixture.py --docker-host unix:///ABSOLUTE_LOCAL_DOCKER_SOCKET --major 18
    python tests/run.py --fixture .local/durable-postgres/fixture-pg18.json --out .local/test-run-1

Use the pinned native PostgreSQL image and retain its digest. The fixture binds only
127.0.0.1, gets a directory-derived owned name, uses private generated credentials
and validates its schema marker. Never point these tests at a client/cloud database.
The tests create synthetic accounts/roles/records; keep the fixture disposable and
run suites serially. No container/database adoption, dump, migration or cloud access
is implicit. Missing Docker/socket/image/prerequisite is a failed prerequisite,
not a skipped pass. Review any authorized image download and local resource costs.

The suite covers extraction validation, version-bound storage protocols, signed
staff/API admission and SQL memberships, upload/review/approval/history, local TLS
parser/action protocols, worker behavior, guarded operator initialization,
retention/monitoring and browser safety. AWS includes native SDK shape tests; other
providers include scripted HTTP contracts without pulling in AWS's SDK. Protocol
fixtures are not cloud IAM or actual model quality. Real PDF/OCR image acceptance,
native model examples, destination accounting compatibility, restore and actual
private-network/scheduled-alert behavior require their separate acceptance tasks.
Receipts distinguish these boundaries. Keep private .local credentials/logs/state
out of source control; do not send diagnostic logs containing secrets to a model.
`;
