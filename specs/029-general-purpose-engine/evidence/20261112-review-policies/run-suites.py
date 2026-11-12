"""Run existing suites in the controller's disposable, network-none SQL fixture.

Enable container loopback TCP solely for their existing nonce-guarded fixture API
and subprocesses. No host port, existing fixture, SQL schema or test is rewritten.
"""
import importlib, json, os, secrets, shlex, socket, subprocess, sys, tempfile, unittest
from pathlib import Path
sys.path[:0] = ['/work/source/src/runtime', '/work/source/tests/runtime']
import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from workflow_database import initialize_database

data = Path(os.environ['ATMEM_TEST_POSTGRES_DATA'])
binary = Path(os.environ['ATMEM_TEST_POSTGRES_BIN'])
assert str(data).startswith('/tmp/atmem-sql-') and os.getuid() == 65532
with socket.socket() as reserved:
    reserved.bind(('127.0.0.1', 0)); port = reserved.getsockname()[1]
options = shlex.split((data/'postmaster.opts').read_text())[1:]
options += ['-c', 'listen_addresses=127.0.0.1', '-p', str(port)]
environment = {**os.environ, 'LD_LIBRARY_PATH': '/opt/atmem/postgres-libs'}
hba = data/'pg_hba.conf'
hba.write_text('host all all 127.0.0.1/32 scram-sha-256\n'+hba.read_text())
subprocess.run([str(binary/'pg_ctl'), '-D', str(data), '-w', '-t', '10', '-m', 'fast', '-o', shlex.join(options), 'restart'],
    env=environment, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
connection = conninfo_to_dict(os.environ['ATMEM_TEST_POSTGRES_DSN'])
connection.update(host='127.0.0.1', port=str(port), dbname='architect_qualification_review')
with psycopg.connect(make_conninfo(os.environ['ATMEM_TEST_POSTGRES_DSN'], port=port), autocommit=True) as c:
    c.execute('CREATE DATABASE architect_qualification_review')
dsn = make_conninfo(**connection); marker = secrets.token_hex(32)
with psycopg.connect(dsn) as c:
    initialize_database(c)
    c.execute('CREATE ROLE qualification_admin NOLOGIN')
    c.execute('CREATE TABLE workflow.qualification_guard(marker text NOT NULL)')
    c.execute('INSERT INTO workflow.qualification_guard VALUES(%s)', (marker,))
temporary = tempfile.TemporaryDirectory(prefix='review-regressions-')
folder = temporary.name
config = Path(folder)/'fixture.json'
config.write_text(json.dumps({'name': 'atmem-durable-qualification', 'database': connection['dbname'],
    'marker': marker, 'port': port, 'user': connection['user'], 'password': connection['password']}))
config.chmod(0o600); os.environ['ATMEM_WORKFLOW_TEST_CONFIG'] = str(config)
modules = json.loads(os.environ['ATMEM_REVIEW_MODULES'])
def load_tests(loader, tests, pattern):
    return unittest.TestSuite(loader.loadTestsFromModule(importlib.import_module(name)) for name in modules)
