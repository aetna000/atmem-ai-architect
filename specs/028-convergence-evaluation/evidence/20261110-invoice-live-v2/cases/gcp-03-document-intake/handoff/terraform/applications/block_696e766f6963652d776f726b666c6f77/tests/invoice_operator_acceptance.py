"""Operator CLI boundaries; actual mutations are tested against owned PostgreSQL."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import copy
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'parser'))
sys.path[:0]=[str(ROOT)]
from invoice_operator import main,private_json,connection_settings
from invoice_operator_core import initialize_runtime,validate_deployment

def deployment_fixture():
    import uuid
    suffix=uuid.uuid4().hex[:12]
    return {'provider':'ibm','deploymentId':str(uuid.uuid4()),'accountId':str(uuid.uuid4()),'namespace':'invoice','bindings':{purpose:{'name':'boot_'+purpose+'_'+suffix,'principal':str(uuid.uuid4())}for purpose in ['api','worker']},'tenantId':None}

class OperatorCliTests(unittest.TestCase):
    def test_default_is_a_review_preview_and_never_opens_a_database_connection(self):
        with tempfile.TemporaryDirectory()as folder:
            deployment=Path(folder)/'deployment.json';deployment.write_text(json.dumps(deployment_fixture()));deployment.chmod(0o600)
            output=io.StringIO()
            with patch('invoice_operator.psycopg.connect')as connect,redirect_stdout(output):main(['initialize','--connection-file','/not/read/in/preview','--deployment-file',str(deployment)])
            connect.assert_not_called();self.assertFalse(json.loads(output.getvalue())['willWrite'])
    def test_ibm_initialize_binds_both_private_password_files_to_their_owned_native_roles(self):
        import secrets
        import uuid
        import psycopg
        from psycopg.conninfo import conninfo_to_dict
        sys.path.insert(0,str(ROOT/'tests'))
        from durable_postgres_acceptance import fixture_dsn
        settings=conninfo_to_dict(fixture_dsn());identity=str(uuid.uuid4());suffix=uuid.uuid4().hex[:12]
        bindings={purpose:{'name':'cli_'+purpose+'_'+suffix,'principal':str(uuid.uuid4())}for purpose in ['api','worker']};passwords={purpose:secrets.token_urlsafe(32)for purpose in bindings}
        with tempfile.TemporaryDirectory()as folder:
            folder=Path(folder);deployment=folder/'deployment.json';payload=folder/'passwords.json';inputs={}
            deployment.write_text(json.dumps({'provider':'ibm','deploymentId':identity,'accountId':identity,'namespace':'invoice','bindings':bindings,'tenantId':None}));deployment.chmod(0o600)
            for purpose,password in passwords.items():
                secret=folder/(purpose+'.password');secret.write_text(password);secret.chmod(0o600);inputs[purpose+'PasswordFile']=str(secret)
            payload.write_text(json.dumps(inputs));payload.chmod(0o600);output=io.StringIO()
            # Only transport is replaced by the owned loopback fixture. Native
            # SQL role creation, SCRAM verifiers, schema admission and grants run.
            with patch('invoice_operator.connection_settings',return_value=settings),redirect_stdout(output):main(['initialize','--connection-file','/owned-local-fixture','--deployment-file',str(deployment),'--input-file',str(payload),'--execute'])
            self.assertTrue(json.loads(output.getvalue())['receipt']['initialized'])
            for purpose,binding in bindings.items():
                with psycopg.connect(**{**settings,'user':binding['name'],'password':passwords[purpose]})as conn:
                    flags=conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone();self.assertEqual(flags,(False,False,False,False,False))
                    self.assertEqual(conn.execute('SELECT count(*)FROM workflow.accounts WHERE id=%s',(identity,)).fetchone()[0],1)
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):conn.execute('DELETE FROM workflow.events')
            for password in passwords.values():self.assertNotIn(password,output.getvalue())
    def test_private_files_reject_world_readable_data_duplicate_json_and_nonobjects(self):
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'input.json';path.write_text('{}');path.chmod(0o644)
            with self.assertRaises(ValueError):private_json(path)
            path.chmod(0o600)
            for body in ['{"same":1,"same":2}','[]']:
                path.write_text(body)
                with self.assertRaises(ValueError):private_json(path)
    def test_connection_input_cannot_downgrade_tls_or_put_password_inline(self):
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'input.json';path.write_text(json.dumps({'host':'native.example.test','password':'must-not-be-inline','sslmode':'disable'}));path.chmod(0o600)
            with self.assertRaises(ValueError):connection_settings(path)

    def test_invalid_deployment_never_opens_a_connection_or_creates_native_roles(self):
        from unittest.mock import Mock
        base=deployment_fixture()
        candidates=[{**base,'accountId':'not-a-uuid'},{**base,'namespace':'outside/scope'},{**base,'tenantId':'unexpected'},
                    {**base,'bindings':{}},{**base,'provider':'unknown'},{**base,'deploymentId':'invalid'}]
        duplicate=copy.deepcopy(base);duplicate['bindings']['worker']['name']=duplicate['bindings']['api']['name'];candidates.append(duplicate)
        for candidate in candidates:
            connect=Mock()
            with self.subTest(candidate=candidate),self.assertRaises(ValueError):initialize_runtime(connect,candidate,passwords=lambda *_:'not-read')
            connect.assert_not_called()

    def test_concurrent_empty_database_bootstrap_and_retry_preserve_owned_passwords(self):
        from concurrent.futures import ThreadPoolExecutor
        from contextlib import contextmanager
        import secrets
        import threading
        import uuid
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict
        sys.path.insert(0,str(ROOT/'tests'))
        from durable_postgres_acceptance import fixture_dsn
        settings=conninfo_to_dict(fixture_dsn()) # Requires the owned fixture nonce.
        database='architect_qualification_'+uuid.uuid4().hex[:16]
        deployment=deployment_fixture();passwords={purpose:secrets.token_urlsafe(32)for purpose in ['api','worker']}
        with psycopg.connect(**settings,autocommit=True)as owner:
            owner.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
        barrier=threading.Barrier(2);local=threading.local()
        @contextmanager
        def connect(override=None):
            if override is not None:raise AssertionError('IBM must use its own application database')
            local.count=getattr(local,'count',0)+1
            if local.count==2:barrier.wait(timeout=10)
            with psycopg.connect(**{**settings,'dbname':database})as conn:yield conn
        def password(purpose,principal):
            self.assertEqual(principal,deployment['bindings'][purpose]['principal']);return passwords[purpose]
        try:
            with ThreadPoolExecutor(max_workers=2)as pool:
                results=list(pool.map(lambda _:initialize_runtime(connect,deployment,passwords=password),range(2)))
            self.assertTrue(all(row['initialized']for row in results))
            def direct(_=None):return psycopg.connect(**{**settings,'dbname':database})
            # Repeat initialization must never silently rotate either native SQL
            # password; even the password supplier must not be called on retry.
            def unexpected(*_):raise AssertionError('Existing password must be preserved')
            self.assertTrue(initialize_runtime(direct,deployment,passwords=unexpected)['initialized'])
            with direct()as conn:
                self.assertEqual(conn.execute('SELECT count(*)FROM workflow.schema_version').fetchone()[0],1)
                self.assertEqual(conn.execute('SELECT count(*)FROM workflow.accounts').fetchone()[0],1)
            for purpose,binding in deployment['bindings'].items():
                with psycopg.connect(**{**settings,'dbname':database,'user':binding['name'],'password':passwords[purpose]})as conn:
                    self.assertEqual(conn.execute('SELECT count(*)FROM workflow.accounts').fetchone()[0],1)
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):conn.execute('DELETE FROM workflow.events')
        finally:
            # Only this newly created, unconnected synthetic database and its two
            # owned roles are removed. No user/cloud database is a test target.
            with psycopg.connect(**settings,autocommit=True)as owner:
                owner.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
                for binding in deployment['bindings'].values():owner.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(binding['name'])))

    def test_autocommit_is_rejected_before_any_native_role_is_created(self):
        import psycopg
        sys.path.insert(0,str(ROOT/'tests'))
        from durable_postgres_acceptance import fixture_dsn
        dsn=fixture_dsn();deployment=deployment_fixture()
        def password(*_):raise AssertionError('No role creation is authorized under autocommit')
        with self.assertRaisesRegex(ValueError,'transaction'):
            initialize_runtime(lambda _:psycopg.connect(dsn,autocommit=True),deployment,passwords=password)
        with psycopg.connect(dsn)as conn:
            self.assertEqual(conn.execute('SELECT count(*)FROM pg_roles WHERE rolname=ANY(%s)',([row['name']for row in deployment['bindings'].values()],)).fetchone()[0],0)

if __name__=='__main__':unittest.main(verbosity=2)
