"""Fixed job metadata, preview, credential and receipt boundaries; no cloud calls."""
import base64
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime')]
from invoice_operator_job import deployment_input,private_environment,native_connect,main

def deployment():
    return {'provider':'ibm','deploymentId':str(uuid.uuid4()),'accountId':str(uuid.uuid4()),'namespace':'invoice','tenantId':None,'bindings':{purpose:{'name':'owned_'+purpose,'principal':str(uuid.uuid4())}for purpose in ['api','worker']}}

class OperatorJobTests(unittest.TestCase):
    def test_metadata_rejects_duplicate_keys_wrong_provider_and_oversize_before_execution(self):
        data=deployment()
        for raw,provider in [(json.dumps(data),'aws'),('{"provider":"ibm","provider":"ibm"}','ibm'),('x'*20000,'ibm')]:
            with self.subTest(provider=provider),self.assertRaises((ValueError,KeyError)):
                deployment_input({'OPERATOR_DEPLOYMENT_BASE64':base64.b64encode(raw.encode()).decode()},provider)
        self.assertEqual(deployment_input({'OPERATOR_DEPLOYMENT_BASE64':base64.b64encode(json.dumps(data).encode()).decode()},'ibm'),data)

    def test_preview_makes_no_secret_sdk_or_database_call(self):
        environment={'OPERATOR_DEPLOYMENT_BASE64':base64.b64encode(json.dumps(deployment()).encode()).decode()};output=io.StringIO()
        with patch.dict(os.environ,environment,clear=True),patch('invoice_operator_job.owned_deployment',return_value={'provider':'ibm'}),patch('invoice_operator_job.private_environment')as private,patch('invoice_operator_job.native_connect')as connect,redirect_stdout(output):
            self.assertEqual(main(['initialize']),0)
        private.assert_not_called();connect.assert_not_called();self.assertFalse(json.loads(output.getvalue())['willWrite'])

    def test_private_platform_secret_files_are_owned_bounded_and_removed_even_on_failure(self):
        env={'DATABASE_PASSWORD':'synthetic-operator-value','API_DATABASE_PASSWORD':'a'*32,'WORKER_DATABASE_PASSWORD':'b'*32}
        pointers=[]
        with self.assertRaisesRegex(RuntimeError,'synthetic'):
            with private_environment('ibm',env)as settings:
                for key in env:
                    self.assertNotIn(key,settings);file=Path(settings[key+'_FILE']);pointers.append(file)
                    self.assertEqual(file.stat().st_mode&0o777,0o600);self.assertEqual(file.parent.stat().st_mode&0o777,0o700);self.assertEqual(file.read_text(),env[key])
                raise RuntimeError('synthetic')
        self.assertTrue(all(not file.exists()for file in pointers))

    def test_operator_cannot_receive_worker_or_model_authority_or_conflicting_secret_inputs(self):
        for provider,env in [('aws',{'PARSER_ENDPOINT':'https://not-allowed.test'}),('ibm',{'DESTINATION_TOKEN':'not-allowed'}),('azure',{'DATABASE_PASSWORD':'not-allowed'}),('gcp',{'API_DATABASE_PASSWORD':'not-allowed'}),('ibm',{'DATABASE_PASSWORD':'secret','DATABASE_PASSWORD_FILE':'/conflict'}),('ibm',{'DATABASE_PASSWORD':'a'*501})]:
            with self.subTest(provider=provider),self.assertRaises(ValueError):
                with private_environment(provider,env):self.fail('Invalid authority must be refused')

    def test_native_operator_factory_rejects_runtime_login_before_secret_read_or_connection(self):
        data=deployment();data['provider']='aws';data['bindings']={purpose:{'name':'owned_'+purpose,'principal':'arn:aws:iam::123456789012:role/'+purpose}for purpose in ['api','worker']}
        env={'REGION':'ap-southeast-2','DATABASE_HOST':'owned.abcdef.ap-southeast-2.rds.amazonaws.com','DATABASE_NAME':'invoice','DATABASE_USER':'owned_api','DATABASE_CA_FILE':str(ROOT/'src/runtime/rds-global-ca.pem'),'DATABASE_PASSWORD_FILE':'/must/not/read'}
        with patch('invoice_operator_job.psycopg.connect')as connect,self.assertRaises(PermissionError):native_connect('aws',env,data)(None)
        connect.assert_not_called()

    def test_native_aws_operator_uses_rotatable_password_and_full_tls_not_iam_runtime_login(self):
        from psycopg.conninfo import conninfo_to_dict
        data=deployment();data['provider']='aws'
        with tempfile.TemporaryDirectory()as folder:
            secret=Path(folder)/'password';secret.write_text('first-synthetic-password')
            env={'REGION':'ap-southeast-2','DATABASE_HOST':'owned.abcdef.ap-southeast-2.rds.amazonaws.com','DATABASE_NAME':'invoice','DATABASE_USER':'invoice_operator','DATABASE_CA_FILE':str(ROOT/'src/runtime/rds-global-ca.pem'),'DATABASE_PASSWORD_FILE':str(secret)}
            factory=native_connect('aws',env,data)
            with patch('invoice_operator_job.psycopg.connect')as connect:
                factory(None);first=conninfo_to_dict(connect.call_args.args[0]);secret.write_text('second-synthetic-password');factory(None);second=conninfo_to_dict(connect.call_args.args[0])
            self.assertEqual(first['password'],'first-synthetic-password');self.assertEqual(second['password'],'second-synthetic-password');self.assertEqual(second['sslmode'],'verify-full');self.assertEqual(second['ssl_min_protocol_version'],'TLSv1.2');self.assertEqual(second['user'],'invoice_operator')

    def test_monitor_attention_is_a_nonzero_job_result_and_does_not_claim_success(self):
        data=deployment();environment={'OPERATOR_DEPLOYMENT_BASE64':base64.b64encode(json.dumps(data).encode()).decode()};output=io.StringIO()
        with patch.dict(os.environ,environment,clear=True),patch('invoice_operator_job.owned_deployment',return_value={'provider':'ibm'}),patch('invoice_operator_job.native_connect'),patch('invoice_operator_job.run_action',return_value={'status':'attention','stalledWork':1}),redirect_stdout(output):self.assertEqual(main(['monitor','--execute']),2)
        self.assertEqual(json.loads(output.getvalue())['status'],'attention');self.assertNotIn(data['accountId'],output.getvalue())

if __name__=='__main__':unittest.main(verbosity=2)
