"""Native credential/transport contracts; no live cloud database authentication."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import ssl
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from urllib.parse import urlsplit,parse_qs
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/aws-web-runtime-sdk'),str(ROOT/'.local/azure-runtime-sdk')]
import boto3
from psycopg.conninfo import conninfo_to_dict
from workflow_connection import DatabaseConnection,DatabaseCredentialUnavailable,aws_database,azure_database,gcp_database,ibm_database,google_metadata_token

class NativeDatabaseConnectionTests(unittest.TestCase):
    def test_twenty_cold_database_signers_share_an_owned_native_session_and_client(self):
        session=boto3.Session(aws_access_key_id='synthetic-access',aws_secret_access_key='synthetic-secret');created=[]
        def create(*args,**kwargs):created.append(True);time.sleep(.02);return session
        factory=aws_database(host='architect.abcdef.ap-southeast-2.rds.amazonaws.com',region='ap-southeast-2',database='architect',user='architect_worker',ca_file=self.ca)
        with patch.object(boto3,'DEFAULT_SESSION',None),patch.object(boto3,'Session',side_effect=create):
            with ThreadPoolExecutor(max_workers=20)as executor:values=list(executor.map(lambda _:conninfo_to_dict(factory()),range(20)))
        self.assertEqual(len(created),1);self.assertEqual(len(values),20)
        for value in values:
            self.assertEqual(value['user'],'architect_worker');self.assertEqual(parse_qs(urlsplit('https://'+value['password']).query)['DBUser'],['architect_worker'])
    @classmethod
    def setUpClass(cls):
        cls.ca=ssl.get_default_verify_paths().cafile
        if not cls.ca or not Path(cls.ca).is_file():raise RuntimeError('Install a valid local CA trust bundle for transport contract tests')
    def test_actual_boto_signer_binds_the_regional_endpoint_user_and_expiring_rds_auth_token(self):
        client=boto3.client('rds',region_name='ap-southeast-2',aws_access_key_id='synthetic-access',aws_secret_access_key='synthetic-secret')
        factory=aws_database(host='architect.abcdef.ap-southeast-2.rds.amazonaws.com',region='ap-southeast-2',database='architect',user='architect_worker',ca_file=self.ca,client=client)
        values=conninfo_to_dict(factory());token=urlsplit('https://'+values['password']);query=parse_qs(token.query)
        self.assertEqual(token.hostname,values['host']);self.assertEqual(token.port,5432);self.assertEqual(query['Action'],['connect']);self.assertEqual(query['DBUser'],['architect_worker']);self.assertEqual(query['X-Amz-Expires'],['900']);self.assertIn('/ap-southeast-2/rds-db/aws4_request',query['X-Amz-Credential'][0]);self.assertEqual(values['sslmode'],'verify-full');self.assertEqual(values['sslrootcert'],self.ca)
    def test_azure_uses_the_database_audience_and_retrieves_credential_each_connection(self):
        credential=Mock();credential.get_token.side_effect=[SimpleNamespace(token='first-private-token',expires_on=int(time.time())+3600),SimpleNamespace(token='second-private-token',expires_on=int(time.time())+3600)]
        factory=azure_database(host='architect-db.postgres.database.azure.com',database='architect',user='architect-worker',ca_file=self.ca,managed_identity_client_id=str(uuid.uuid4()),credential=credential)
        first=conninfo_to_dict(factory());second=conninfo_to_dict(factory());self.assertNotEqual(first['password'],second['password']);self.assertEqual(first['sslmode'],'verify-full');self.assertTrue(all(call.args==('https://ossrdbms-aad.database.windows.net/.default',)for call in credential.get_token.call_args_list));self.assertNotIn('private-token',repr(factory))
    def test_expiring_azure_token_or_secret_store_error_fails_without_raw_secret_details(self):
        credential=Mock();credential.get_token.return_value=SimpleNamespace(token='PRIVATE_TOKEN_CONTENT',expires_on=int(time.time()))
        factory=azure_database(host='architect-db.postgres.database.azure.com',database='architect',user='architect-worker',ca_file=self.ca,managed_identity_client_id=str(uuid.uuid4()),credential=credential)
        with self.assertRaises(DatabaseCredentialUnavailable)as caught:factory()
        self.assertNotIn('PRIVATE_TOKEN_CONTENT',str(caught.exception))
        def broken():raise RuntimeError('PRIVATE_SECRET_RESPONSE')
        ibm=ibm_database(host='owned.private.databases.appdomain.cloud',port=30324,database='architect',user='architect_worker',ca_file=self.ca,password=broken)
        with self.assertRaises(DatabaseCredentialUnavailable)as caught:ibm()
        self.assertNotIn('PRIVATE_SECRET_RESPONSE',str(caught.exception))
    def test_google_iam_user_is_bound_to_managed_unix_transport_without_tcp_fallback(self):
        factory=gcp_database(connection_name='sample-project:australia-southeast1:architect-db',service_account_email='architect-worker@sample-project.iam.gserviceaccount.com',database='architect',credential=lambda:'synthetic-google-access')
        values=conninfo_to_dict(factory());self.assertEqual(values['host'],'/cloudsql/sample-project:australia-southeast1:architect-db');self.assertEqual(values['user'],'architect-worker@sample-project.iam');self.assertEqual(values['password'],'synthetic-google-access');self.assertEqual(values['sslmode'],'disable')
        with self.assertRaises(ValueError):DatabaseConnection('gcp','127.0.0.1',5432,'architect','worker',lambda:'token',managed_cloudsql=True)
        with self.assertRaises(ValueError):DatabaseConnection('aws',values['host'],5432,'architect','worker',lambda:'token',managed_cloudsql=True)
    def test_ibm_uses_a_distinct_dedicated_database_password_and_native_instance_ca(self):
        passwords=iter(['first-secret-value','second-secret-value']);factory=ibm_database(host='owned.private.databases.appdomain.cloud',port=30324,database='architect',user='architect_worker',ca_file=self.ca,password=lambda:next(passwords))
        first=conninfo_to_dict(factory());second=conninfo_to_dict(factory());self.assertEqual(first['port'],'30324');self.assertEqual(first['sslmode'],'verify-full');self.assertNotEqual(first['password'],second['password']);self.assertEqual(first['ssl_min_protocol_version'],'TLSv1.2');self.assertEqual(first['passfile'],'/dev/null')
    def test_connection_credentials_are_escaped_without_replacing_endpoint_or_tls_options(self):
        value="opaque password ' host=attacker.test sslmode=disable"
        factory=ibm_database(host='owned.private.databases.appdomain.cloud',port=30324,database='architect',user='architect_worker',ca_file=self.ca,password=lambda:value)
        parsed=conninfo_to_dict(factory());self.assertEqual(parsed['password'],value);self.assertEqual(parsed['host'],'owned.private.databases.appdomain.cloud');self.assertEqual(parsed['sslmode'],'verify-full')
    def test_foreign_hosts_custom_rds_aliases_and_oversize_unix_paths_are_rejected(self):
        with self.assertRaises(ValueError):aws_database(host='database.customer.example',region='ap-southeast-2',database='architect',user='worker',ca_file=self.ca)
        with self.assertRaises(ValueError):azure_database(host='db.attacker.test',database='architect',user='worker',ca_file=self.ca,managed_identity_client_id=str(uuid.uuid4()))
        with self.assertRaises(ValueError):ibm_database(host='db.attacker.test',port=5432,database='architect',user='worker',ca_file=self.ca,password=lambda:'secret')
        with self.assertRaises(ValueError):gcp_database(connection_name='sample-project:australia-southeast1:'+'x'*63,service_account_email='architect-worker@sample-project.iam.gserviceaccount.com',database='architect')

class GoogleDatabaseMetadataTests(unittest.TestCase):
    class Response:
        def __init__(self,body,*,status=200,headers=None):self.body=body;self.status_code=status;self.headers=headers or{'Metadata-Flavor':'Google'}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def iter_content(self,size):
            for index in range(0,len(self.body),size):yield self.body[index:index+size]
    def test_google_workload_metadata_has_fixed_origin_flavor_expiry_and_no_redirect_or_proxy(self):
        session=Mock();session.get.return_value=self.Response(b'{"access_token":"synthetic","token_type":"Bearer","expires_in":3600}')
        self.assertEqual(google_metadata_token(session),'synthetic');self.assertFalse(session.trust_env);call=session.get.call_args;self.assertEqual(call.args[0],'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token');self.assertEqual(call.kwargs['headers'],{'Metadata-Flavor':'Google'});self.assertFalse(call.kwargs['allow_redirects'])
    def test_unknown_metadata_origin_redirect_expiry_duplicate_or_oversize_response_fails_closed(self):
        for response in [self.Response(b'{}',status=302),self.Response(b'{}',headers={'Metadata-Flavor':'Other'}),self.Response(b'{"access_token":"private","token_type":"Bearer","expires_in":1}'),self.Response(b'{"access_token":"private","access_token":"other"}'),self.Response(b'x'*8193)]:
            session=Mock();session.get.return_value=response
            with self.assertRaises(DatabaseCredentialUnavailable)as error:google_metadata_token(session)
            self.assertNotIn('private',str(error.exception))

if __name__=='__main__':unittest.main(verbosity=2)
