"""Operator CLI boundaries; actual mutations are tested against owned PostgreSQL."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime')]
from invoice_operator import main,private_json,connection_settings

class OperatorCliTests(unittest.TestCase):
    def test_default_is_a_review_preview_and_never_opens_a_database_connection(self):
        with tempfile.TemporaryDirectory()as folder:
            deployment=Path(folder)/'deployment.json';deployment.write_text(json.dumps({'provider':'aws','deploymentId':'11111111-1111-4111-8111-111111111111','accountId':'11111111-1111-4111-8111-111111111111','namespace':'invoice','bindings':{},'tenantId':None}));deployment.chmod(0o600)
            output=io.StringIO()
            with patch('invoice_operator.psycopg.connect')as connect,redirect_stdout(output):main(['initialize','--connection-file','/not/read/in/preview','--deployment-file',str(deployment)])
            connect.assert_not_called();self.assertFalse(json.loads(output.getvalue())['willWrite'])
    def test_ibm_initialize_binds_both_private_password_files_to_their_owned_native_roles(self):
        import secrets
        import uuid
        import psycopg
        from psycopg.conninfo import conninfo_to_dict
        sys.path.insert(0,str(ROOT/'tests/runtime'))
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

if __name__=='__main__':unittest.main(verbosity=2)
