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
from invoice_operator_job import deployment_input,private_environment,native_connect,private_proxy_job,main

def deployment():
    return {'provider':'ibm','deploymentId':str(uuid.uuid4()),'accountId':str(uuid.uuid4()),'namespace':'invoice','tenantId':None,'bindings':{purpose:{'name':'owned_'+purpose,'principal':str(uuid.uuid4())}for purpose in ['api','worker']}}

class OperatorJobTests(unittest.TestCase):
    def proxy_environment(self):
        data=deployment();data['provider']='gcp';data['bindings']={purpose:{'name':'invoice-'+purpose+'@reviewed-project.iam','principal':'invoice-'+purpose+'@reviewed-project.iam.gserviceaccount.com','created_by_package':True}for purpose in ['api','worker']}
        return {'OPERATOR_DEPLOYMENT_BASE64':base64.b64encode(json.dumps(data).encode()).decode(),'DATABASE_TRANSPORT':'cloudsql-private-proxy','OPERATOR_PROXY_SHUTDOWN':'cloudsql-private-proxy'}

    def test_proxy_cleanup_uses_fixed_loopback_and_preserves_failed_work_outcome(self):
        import http.client
        from contextlib import contextmanager
        original=http.client.HTTPConnection
        calls=[]
        @contextmanager
        def endpoint(status=200):
            import http.server,threading
            class Handler(http.server.BaseHTTPRequestHandler):
                def log_message(self,*_):pass
                def do_GET(self):
                    self.send_response(200 if self.path=='/startup'else 404);self.end_headers();self.wfile.write(b'ok')
                def do_POST(self):
                    calls.append((self.path,self.headers.get('Authorization')));self.send_response(status);self.end_headers();self.wfile.write(b'ok')
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def connect(host,port,timeout):
                self.assertEqual((host,port,timeout),('127.0.0.1',9090,1)if port==9090 else('127.0.0.1',9091,2));return original('127.0.0.1',server.server_port,timeout=timeout)
            try:
                with patch('invoice_operator_job.http.client.HTTPConnection',side_effect=connect):yield
            finally:server.shutdown();server.server_close();thread.join(2)
        with endpoint(),self.assertRaisesRegex(RuntimeError,'work failed'):
            with private_proxy_job('gcp',self.proxy_environment()):raise RuntimeError('work failed')
        self.assertEqual(calls,[('/quitquitquit',None)])
        output=io.StringIO()
        with endpoint(500),patch.dict(os.environ,self.proxy_environment(),clear=True),patch('invoice_operator_job.owned_deployment',return_value={'provider':'gcp'}),patch('invoice_operator_job.native_connect'),patch('invoice_operator_job.run_action',return_value={'status':'ok'}),redirect_stdout(output),self.assertRaises(ValueError):main(['monitor','--execute'])
        self.assertEqual(output.getvalue(),'','Failed sidecar shutdown must not emit a successful heartbeat')

    def test_preview_does_not_quit_proxy_and_invalid_deployment_is_cleaned_up_before_sql(self):
        environment=self.proxy_environment();output=io.StringIO()
        with patch.dict(os.environ,environment,clear=True),patch('invoice_operator_job.owned_deployment',return_value={'provider':'gcp'}),patch('invoice_operator_job.http.client.HTTPConnection')as connection,redirect_stdout(output):self.assertEqual(main(['initialize']),0)
        connection.assert_not_called()
        environment['OPERATOR_DEPLOYMENT_BASE64']='invalid'
        with patch.dict(os.environ,environment,clear=True),patch('invoice_operator_job.owned_deployment',return_value={'provider':'gcp'}),patch('invoice_operator_job.http.client.HTTPConnection')as connection,patch('invoice_operator_job.native_connect')as connect,self.assertRaises(ValueError):
            connection.return_value.getresponse.return_value.status=200;connection.return_value.getresponse.return_value.read.return_value=b'ok';main(['initialize','--execute'])
        from unittest.mock import call
        self.assertEqual(connection.call_args_list,[call('127.0.0.1',9090,timeout=1),call('127.0.0.1',9091,timeout=2)]);connect.assert_not_called()

    def test_startup_deadline_still_shuts_down_proxy_and_never_enters_work(self):
        with patch('invoice_operator_job.time.monotonic',side_effect=[0,0,31]),patch('invoice_operator_job.time.sleep'),patch('invoice_operator_job.http.client.HTTPConnection')as connection,self.assertRaises(TimeoutError):
            response=connection.return_value.getresponse.return_value;response.status=503;response.read.return_value=b'not ready'
            # The shutdown response is separate from the failed startup probe.
            shutdown=type('Shutdown',(),{'status':200,'read':lambda *_:b'ok'})()
            connection.return_value.getresponse.side_effect=[response,shutdown]
            with private_proxy_job('gcp',self.proxy_environment()):self.fail('Work must not run before the private proxy is ready')
        self.assertEqual(connection.call_args_list[-1].kwargs,{'timeout':2})

    def test_other_providers_or_transport_cannot_select_proxy_shutdown(self):
        for provider,env in [('aws',self.proxy_environment()),('gcp',{'OPERATOR_PROXY_SHUTDOWN':'https://external.test'}),('gcp',{'OPERATOR_PROXY_SHUTDOWN':'cloudsql-private-proxy','DATABASE_TRANSPORT':'remote-host'})]:
            with self.subTest(provider=provider),patch('invoice_operator_job.http.client.HTTPConnection')as connection,self.assertRaises(ValueError):
                with private_proxy_job(provider,env):self.fail('Invalid lifecycle must be refused')
            connection.assert_not_called()

    def test_google_cold_proxy_connect_retries_fresh_credentials_but_never_retries_bad_authentication(self):
        import psycopg
        from workflow_connection import DatabaseConnection
        from psycopg.conninfo import conninfo_to_dict
        data=deployment();data['provider']='gcp';tokens=[]
        def credential():tokens.append('synthetic-token-'+str(len(tokens)));return tokens[-1]
        factory=DatabaseConnection('gcp','127.0.0.1',5432,'invoice','invoice-ops@reviewed-project.iam',credential,managed_proxy_tcp=True,role='migration')
        with patch('invoice_operator_job.native_database',return_value=factory),patch('invoice_operator_job.time.sleep')as sleep,patch('invoice_operator_job.psycopg.connect',side_effect=[psycopg.OperationalError('proxy warming'),psycopg.OperationalError('proxy warming'),object()])as connect:
            native_connect('gcp',{},data)(None)
        self.assertEqual(len(tokens),3);self.assertEqual([conninfo_to_dict(call.args[0])['password']for call in connect.call_args_list],tokens);self.assertEqual(sleep.call_count,2)
        with patch('invoice_operator_job.native_database',return_value=factory),patch('invoice_operator_job.time.sleep')as sleep,patch('invoice_operator_job.psycopg.connect',side_effect=psycopg.errors.InvalidPassword('bad authentication'))as connect,self.assertRaises(psycopg.errors.InvalidPassword):native_connect('gcp',{},data)(None)
        self.assertEqual(connect.call_count,1);sleep.assert_not_called()
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
