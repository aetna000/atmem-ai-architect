"""Exact-source native SQL qualification on the two owned loopback fixtures.

Each test verifies the fixture ownership guard before creating fresh synthetic
databases/roles. No caller DSN, vendor login or cloud access is accepted here.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import argparse

ROOT=Path(__file__).resolve().parents[1]
SUITES={'enterprise_auth_postgres':21,'enterprise_sessions_postgres':4,'enterprise_http_postgres':14,
        'enterprise_queries_postgres':19,'enterprise_queries_http_postgres':21,'enterprise_extraction_cache_postgres':14,
        'enterprise_audit_postgres':9,'enterprise_native_postgres':11,'enterprise_operator_postgres':11,'enterprise_document_jobs_postgres':10}


def qualify(output):
    output=output.resolve()
    if output.exists()or not output.is_relative_to(ROOT/'.local'):raise ValueError('Use a fresh local qualification directory')
    output.mkdir(parents=True)
    sources=[*list((ROOT/'src/runtime').glob('enterprise*')),
        *list((ROOT/'tests/runtime').glob('enterprise*py')),
        ROOT/'src/runtime/public_faq.py',ROOT/'src/runtime/faq-output-contract.json',
        ROOT/'tests/runtime/durable_postgres_acceptance.py',ROOT/'tests/runtime/durable_fixture_tasks.py',
        ROOT/'scripts/enterprise-browser-fixture.py',ROOT/'scripts/enterprise-browser-check.mjs',Path(__file__).resolve()]
    sources=[p for p in sources if p.is_file()]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources}
    checks=[];success=False
    def run_version(version):
        env={**os.environ,'ATMEM_WORKFLOW_TEST_CONFIG':str(ROOT/'.local/durable-postgres'/('fixture.json'if version==17 else'fixture-pg18.json'))}
        results=[]
        probe="""import json,sys,platform,importlib.metadata
from pathlib import Path
root=Path.cwd();sys.path[:0]=[str(root/'tests/runtime'),str(root/'.local/azure-runtime-sdk')]
from durable_postgres_acceptance import fixture_dsn
import psycopg
with psycopg.connect(fixture_dsn())as conn:version=int(conn.execute('SHOW server_version_num').fetchone()[0])
print(json.dumps({'postgresVersionNum':version,'python':platform.python_version(),'dependencies':{name:importlib.metadata.version(name)for name in ['psycopg','procrastinate','msal','PyJWT','cryptography','requests','fastapi']}}))
"""
        preflight=subprocess.run([str(ROOT/'.local/durable-runtime/bin/python'),'-I','-c',probe],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
        if preflight.returncode!=0:raise RuntimeError('Owned PostgreSQL preflight failed')
        observed=json.loads(preflight.stdout)
        if observed['postgresVersionNum']//10000!=version:raise ValueError('Owned fixture server version differs from the qualification label')
        (output/f'pg{version}-preflight.json').write_text(json.dumps(observed,indent=2)+'\n')
        for suite,count in SUITES.items():
            result=subprocess.run([str(ROOT/'.local/durable-runtime/bin/python'),'-I',str(ROOT/'tests/runtime'/(suite+'.py')),'-v'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
            name=f'pg{version}-{suite}.log';(output/name).write_bytes(result.stdout)
            summary=re.search(rb'Ran (\d+) tests? in [^\n]+\n\nOK\s*$',result.stdout)
            results.append({'suite':suite,'postgres':version,'exitCode':result.returncode,'tests':int(summary[1])if summary else None,
                'expectedTests':count,'passed':result.returncode==0 and summary is not None and int(summary[1])==count,'log':name})
        return results
    try:
        with ThreadPoolExecutor(max_workers=2)as pool:
            for results in pool.map(run_version,[17,18]):checks.extend(results)
        if any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest for name,digest in hashes.items()):raise ValueError('Qualification sources changed during the run')
        success=len(checks)==2*len(SUITES) and all(check['passed']for check in checks)
        if not success:raise RuntimeError('Native question qualification failed; inspect the preserved logs')
    finally:
        (output/'receipt.json').write_text(json.dumps({'recordedAt':datetime.now(timezone.utc).isoformat(),'passed':success,
            'scope':'Actual owned loopback PostgreSQL/crypto/MSAL/ASGI/Procrastinate; source/profile/model HTTP is scripted. Not Linux/cloud/native-account/whole-project acceptance.',
            'checks':checks,'sourceHashes':hashes,'testsPerPostgresVersion':sum(SUITES.values()),'cloudOperations':False},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    qualify(parser.parse_args().out)
