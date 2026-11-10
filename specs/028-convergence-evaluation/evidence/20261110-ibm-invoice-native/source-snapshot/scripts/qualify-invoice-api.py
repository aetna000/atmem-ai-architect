"""Exact local API/identity/storage-contract evidence; no cloud authentication."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
TESTS=['invoice_extraction_acceptance.py','invoice_storage_acceptance.py','invoice_http_acceptance.py','invoice_web_acceptance.py','invoice_identity_acceptance.py','invoice_parser_rpc_acceptance.py','invoice_parser_identity_acceptance.py','invoice_worker_acceptance.py','invoice_operations_acceptance.py','invoice_operator_acceptance.py']
def source_hashes():
    files=[Path(__file__),*list((ROOT/'src/runtime').glob('invoice*')),*list((ROOT/'src/runtime').glob('workflow*')),ROOT/'src/runtime/durable_workflow.py',*[ROOT/'src/runtime'/name for name in ['approved_http_destination.py','structured_output.py','structured_http.py','azure_structured.py','gcp_structured.py','ibm_structured.py','policy_review.py']],*[ROOT/'tests/runtime'/name for name in [*TESTS,'durable_postgres_acceptance.py','durable_privileges_acceptance.py','durable_fixture_tasks.py','workflow_tls_destination_fixture.py']]]
    return{str(file.relative_to(ROOT)):hashlib.sha256(file.read_bytes()).hexdigest()for file in sorted(set(files))if file.is_file()}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);args=parser.parse_args();out=Path(args.out).resolve()
    if not out.is_relative_to(ROOT/'.local')or out.exists():raise ValueError('Use a fresh evidence directory below .local')
    out.mkdir(parents=True);before=source_hashes();checks=[]
    for name in TESTS:
        log=out/(name+'.log')
        # The queue environment deliberately excludes cloud SDKs. The storage
        # protocol test uses the separately hash-pinned AWS SDK fixture, rather
        # than changing a shared Python installation or inheriting PYTHONPATH.
        command=[sys.executable,'-I',str(ROOT/'tests/runtime'/name)]
        if name=='invoice_storage_acceptance.py':
            sdk=ROOT/'.local/aws-web-runtime-sdk'
            if not(sdk/'boto3').is_dir():raise ValueError('Install the pinned isolated AWS runtime SDK fixture')
            command=[sys.executable,'-I','-c','import sys,runpy;sys.path.insert(0,'+repr(str(sdk))+');test=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(test,run_name="__main__")',str(ROOT/'tests/runtime'/name)]
        with log.open('wb')as stream:result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=45)
        counts=re.findall(r'Ran (\d+) tests in',log.read_text());checks.append({'name':name,'exitCode':result.returncode,'tests':int(counts[0])if len(counts)==1 else None,'log':log.name})
    versions={}
    for directory in [Path(sys.prefix)/'lib'/('python'+str(sys.version_info.major)+'.'+str(sys.version_info.minor))/'site-packages',ROOT/'.local/azure-runtime-sdk',ROOT/'.local/aws-web-runtime-sdk']:
        versions[str(directory.relative_to(ROOT))]={d.metadata['Name']:d.version for d in importlib.metadata.distributions(path=[str(directory)])}
    unchanged=before==source_hashes();passed=unchanged and all(check['exitCode']==0 and check['tests']is not None for check in checks)
    receipt={'kind':'local-invoice-api-and-native-identity-contracts','recordedAt':datetime.now(timezone.utc).isoformat(),'passed':passed,'checks':checks,'sourceHashes':before,'sourcesUnchanged':unchanged,'python':sys.version,'isolatedDependencyVersions':versions,'boundary':'Actual local SQL/ASGI/JWT cryptography and native SDK/scripted object/identity protocols. Identity keys, private objects and destinations are synthetic. No native cloud authentication, parser/model, complete generated project, account plan or deployment qualification.','cloudOperations':False,'full28CaseAcceptanceComplete':False}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':passed,'tests':sum(check['tests']or 0 for check in checks),'receipt':str(out/'receipt.json')}));sys.exit(0 if passed else 1)
