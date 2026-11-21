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
