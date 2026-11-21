"""Native worker configuration boundaries and the concrete TLS dispatch adapter."""
import base64
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'parser'))
sys.path[:0]=[str(ROOT),str(Path(__file__).resolve().parent)]
from invoice_worker import create_native_worker
from invoice_stage import dispatch_operation,replay_review
from workflow_contract import normalized_contract
from workflow_errors import DestinationNotAttempted,InvalidDispatch
from durable_postgres_acceptance import DurableFixture
from workflow_tls_destination_fixture import TlsDestinationFixture
from invoice_runtime_secrets import prepare_runtime_environment
from structured_http import PolicyUnverified

def encoded(value):return base64.b64encode(json.dumps(value).encode()).decode()

class NativeWorkerConfigurationTests(unittest.TestCase):
    def environment(self):
        endpoint='https://accounting.example.test/actions';contract=normalized_contract(endpoint,'owned-team')
        return{'DESTINATION_ENDPOINT':endpoint,'DESTINATION_SCOPE':'owned-team','DESTINATION_CONTRACT_BASE64':encoded(contract),'DESTINATION_TOKEN_FILE':'/var/run/secrets/atmem/action','WORKFLOW_NAMESPACE':'invoice','UNRELATED_PRIVATE_MARKER':'must-not-enter-children','DATABASE_HOST':'must-not-enter-children','API_CLIENT_SECRET':'must-not-enter-children','MODEL_ID':'owned-model','MODEL_ENDPOINT':'https://model.example.test','DOCUMENT_BUCKET':'owned-documents','REGION':'ap-southeast-2','PARSER_ENDPOINT':'https://parser.example.test/extract'}
    def test_four_provider_factories_separate_model_and_action_secrets_from_sql_and_each_other(self):
        for provider in ['aws','azure','gcp','ibm']:
            with self.subTest(provider=provider):
                runtime=create_native_worker(provider,self.environment(),connection='explicit-unconnected-local-fixture')
                for stage in [runtime.processor,runtime.deliver]:
                    self.assertEqual(stage.command[0],sys.executable);self.assertNotIn('must-not-enter-children',stage.environment.values());self.assertNotIn('DATABASE_PASSWORD',stage.environment);self.assertNotIn('DATABASE_HOST',stage.environment);self.assertNotIn('API_CLIENT_SECRET',stage.environment)
                self.assertNotIn('DESTINATION_TOKEN_FILE',runtime.processor.environment);self.assertNotIn('MODEL_ID',runtime.deliver.environment);self.assertNotIn('DOCUMENT_BUCKET',runtime.deliver.environment)
                self.assertEqual(runtime.processor.timeout_seconds,180);self.assertEqual(runtime.deliver.timeout_seconds,45);self.assertFalse(runtime.idempotent_destination)
    def test_ibm_parser_token_is_private_to_extraction_and_cannot_enter_api_or_dispatch(self):
        env={**self.environment(),'PARSER_SHARED_TOKEN':'a'*64};runtime=create_native_worker('ibm',env,connection='explicit-unconnected-local-fixture');path=Path(runtime.processor.environment['PARSER_SHARED_TOKEN_FILE'])
        self.assertEqual(path.read_text(),'a'*64);self.assertEqual(path.stat().st_mode&0o777,0o600);self.assertNotIn('PARSER_SHARED_TOKEN',runtime.processor.environment);self.assertNotIn('PARSER_SHARED_TOKEN_FILE',runtime.deliver.environment)
        for provider,role in [('ibm','api'),('gcp','worker'),('azure','worker'),('aws','worker')]:
            with self.assertRaises(ValueError):prepare_runtime_environment(provider,env,role)
        for token in ['short','g'*64]:
            with self.assertRaises(ValueError):prepare_runtime_environment('ibm',{**env,'PARSER_SHARED_TOKEN':token},'worker')
    def test_changed_destination_cannot_reuse_an_approval_or_replay_receipt(self):
        env=self.environment();env['DESTINATION_ENDPOINT']='https://different.example.test/actions'
        with self.assertRaisesRegex(ValueError,'approved integration'):create_native_worker('aws',env,connection='explicit-unconnected-local-fixture')
        with self.assertRaises(ValueError):create_native_worker('different',env,connection='explicit-unconnected-local-fixture')
    def test_replay_requires_a_scoped_unexpired_operator_receipt_not_a_boolean(self):
        env=self.environment();contract=json.loads(base64.b64decode(env['DESTINATION_CONTRACT_BASE64']));self.assertFalse(replay_review(env,contract))
        receipt={'contract':contract,'idempotency':'same-key-same-payload-one-effect','approvedBy':'synthetic-operator','evidenceSha256':'a'*64,'expiresAt':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}
        env['DESTINATION_REPLAY_REVIEW_BASE64']=encoded(receipt);self.assertTrue(replay_review(env,contract))
        env['DESTINATION_REPLAY_REVIEW_BASE64']=encoded({**receipt,'expiresAt':(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()})
        with self.assertRaises(PolicyUnverified):replay_review(env,contract)
    def test_native_secret_injection_becomes_a_private_file_and_is_absent_from_child_environment_values(self):
        env=self.environment();env.pop('DESTINATION_TOKEN_FILE');env['DESTINATION_TOKEN']='synthetic-private-action-token'
        runtime=create_native_worker('aws',env,connection='explicit-unconnected-local-fixture');path=Path(runtime.deliver.environment['DESTINATION_TOKEN_FILE'])
        self.assertEqual(path.read_text(),env['DESTINATION_TOKEN']);self.assertEqual(path.stat().st_mode&0o777,0o600);self.assertEqual(path.parent.stat().st_mode&0o777,0o700)
        self.assertNotIn(env['DESTINATION_TOKEN'],runtime.processor.environment.values());self.assertNotIn(env['DESTINATION_TOKEN'],runtime.deliver.environment.values())
    def test_api_action_secret_and_plaintext_iam_database_credentials_are_rejected(self):
        for provider in ['aws','azure','gcp']:
            with self.subTest(provider=provider),self.assertRaises(ValueError):prepare_runtime_environment(provider,{'DATABASE_PASSWORD':'unexpected-password'},'worker')
        with self.assertRaises(ValueError):prepare_runtime_environment('ibm',{'DESTINATION_TOKEN':'unexpected-token'},'api')
        with self.assertRaises(ValueError):prepare_runtime_environment('ibm',{'DATABASE_PASSWORD':'one','DATABASE_PASSWORD_FILE':'/other'},'worker')

class NativeDispatchTests(DurableFixture,unittest.TestCase):
    def test_actual_dispatch_wrapper_uses_owned_endpoint_secret_and_immutable_contract(self):
        sink=TlsDestinationFixture()
        try:
            self.store.destination_contract=normalized_contract(sink.url,'synthetic-account');operation=self.approved();row=self.store.claim_dispatch(operation)
            with tempfile.TemporaryDirectory(prefix='atmem-dispatch-secret-')as folder:
                secret=Path(folder)/'token';secret.write_text(sink.token);secret.chmod(0o600)
                env={'DESTINATION_ENDPOINT':sink.url,'DESTINATION_SCOPE':'synthetic-account','DESTINATION_CONTRACT_BASE64':encoded(self.store.destination_contract),'DESTINATION_TOKEN_FILE':str(secret)}
                identity={'idempotency_key':operation,'payload_sha256':row['approved_hash']}
                with patch.dict(os.environ,{'SSL_CERT_FILE':str(sink.ca_file)}):receipt=dispatch_operation(row,identity,env)
                self.assertEqual(receipt['operationId'],operation);self.assertEqual(len(sink.effects),1)
                env['DESTINATION_ENDPOINT']='https://changed.example.test/actions'
                with self.assertRaises(InvalidDispatch):dispatch_operation(row,identity,env)
                env['DESTINATION_ENDPOINT']=sink.url;env['DESTINATION_REPLAY_REVIEW_BASE64']=encoded({'invalid':'not an operator receipt'})
                with self.assertRaises(DestinationNotAttempted):dispatch_operation(row,identity,env)
                self.assertEqual(len(sink.calls),1)
        finally:sink.close()

if __name__=='__main__':unittest.main(verbosity=2)
