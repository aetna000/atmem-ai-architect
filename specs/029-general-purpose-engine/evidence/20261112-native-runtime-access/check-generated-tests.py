"""Run unchanged generated tests in a nonce-owned fresh database on local fixture.

Never replaces the fixture schema or another database. Cleanup matches the exact
new database/comment; credentials remain process-private and outside receipts.
"""
import hashlib,json,os,subprocess,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path[:0]=[str(ROOT/'tests/runtime'),str(ROOT/'src/runtime')]
from durable_postgres_acceptance import fixture_dsn
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
package=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();admin=fixture_dsn();nonce=uuid.uuid4().hex;database='atmem_equipment_'+nonce;marker='atmem-equipment-local-tests:'+nonce
before={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest()for p in package.rglob('*')if p.is_file()and not any(x in p.parts for x in ['__pycache__','.terraform','.git'])}
with psycopg.connect(admin,autocommit=True)as conn:
    assert 170000<=int(conn.execute('SHOW server_version_num').fetchone()[0])<180000
    conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
    conn.execute(sql.SQL('COMMENT ON DATABASE {} IS {}').format(sql.Identifier(database),sql.Literal(marker)))
try:
    temporary=out/'tmp';temporary.mkdir(mode=0o700)
    env={**os.environ,'LAB_TEST_ADMIN_DSN':make_conninfo(admin,dbname=database),'LAB_ALLOW_LOCAL_SQL_TESTS':'1','LAB_ALLOW_LOCAL_NETWORK':'1','TMPDIR':str(temporary),'PYTHONDONTWRITEBYTECODE':'1'}
    with(out/'generated-tests.log').open('wb')as log:
        result=subprocess.run([sys.executable,'-I',str(package/'scripts/qualify.py')],cwd=package,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    after={name:hashlib.sha256((package/name).read_bytes()).hexdigest()for name in before};assert before==after
    receipt={'passed':result.returncode==0,'exitCode':result.returncode,'sourceHashes':before,'sourcesUnchanged':True,'freshDatabaseOwned':True,'localTlsOptIn':True,'canonicalOwnedTmpdir':True,'cloudOperations':False,'boundary':'Actual unchanged generated qualification runner with private disposable PostgreSQL17 database, real roles/queue and labelled synthetic identity/TLS. Generated tests are not independent full-system acceptance.'}
finally:
    with psycopg.connect(admin,autocommit=True)as conn:
        row=conn.execute("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=%s",(database,)).fetchone();assert row and row[0]==marker,'Refuse cleanup of foreign database'
        conn.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
receipt['freshDatabaseRemoved']=True;(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':receipt['passed'],'freshDatabaseRemoved':True}));raise SystemExit(result.returncode)
