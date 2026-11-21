"""Owned metadata/native SQL dispatch and parser protocol, without cloud calls."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/azure-runtime-sdk'),str(ROOT/'tests/runtime')]
from enterprise_configuration import deployment,read_deployment,native_database
from enterprise_native import DocumentExecutor
from enterprise_secrets import SecretFiles
from enterprise_sources import SourceUnavailable
from enterprise_secrets_acceptance import environment


def metadata(provider='gcp'):
    identifier='11111111-1111-4111-8111-111111111111'
    return {'format':'enterprise-knowledge-v1','provider':provider,'accountId':'owned-company','publicOrigin':'https://workspace.example',
        'company':{'issuer':'https://company.example/issuer','audience':'knowledge-api','jwksUri':'https://company.example/jwks','scope':'knowledge.read',
            'web':{'clientId':'existing-company-client','authorizationEndpoint':'https://company.example/authorize','tokenEndpoint':'https://company.example/token','scopes':['openid','profile','knowledge.read']}},
        'sources':{'sharepoint':{'tenantId':identifier,'clientId':identifier,'driveId':'owned-drive','host':'tenant.sharepoint.com'},
            'confluence':{'clientId':'owned-client','cloudId':identifier,'host':'tenant.atlassian.net','spaces':{'ENG':'42'}}},'parserRevision':'a'*64}


class OwnedPrivateConfiguration(unittest.TestCase):
    def test_each_owned_provider_metadata_round_trips_and_is_detached_from_input(self):
        for provider in ['aws','azure','gcp','ibm']:
            value=metadata(provider);owned=deployment(value);self.assertEqual(value,owned)
            value['sources']['confluence']['spaces']['ENG']='different'
            self.assertEqual(owned['sources']['confluence']['spaces']['ENG'],'42')

    def test_untrusted_extra_fields_and_invalid_identity_source_endpoints_are_rejected(self):
        values=[{**metadata(),'provider':'unknown'},{**metadata(),'modelInstruction':'override'},
                {**metadata(),'publicOrigin':'https://workspace.example/unexpected-path'},{**metadata(),'parserRevision':'latest'}]
        for path,value in [('company.web.tokenEndpoint','http://insecure.example/token'),('sources.sharepoint.host','other.example'),
                           ('sources.confluence.host','evil.example'),('sources.sharepoint.tenantId','not-an-owned-id'),('company.web.scopes',['openid','profile','offline_access'])]:
            item=metadata();target=item;parts=path.split('.')
            for part in parts[:-1]:target=target[part]
            target[parts[-1]]=value;values.append(item)
        for value in values:
            with self.assertRaises((ValueError,SourceUnavailable)):deployment(value)

    def test_duplicate_or_oversized_deployment_files_never_fall_back(self):
        with tempfile.TemporaryDirectory()as directory:
            path=Path(directory)/'deployment.json'
            for raw in ['{"format":"one","format":"two"}','x'*32769]:
                path.write_text(raw)
                with self.assertRaises(ValueError):read_deployment(path)
            path.write_text(json.dumps(metadata()));self.assertEqual(read_deployment(path),metadata())

    def test_native_database_dispatch_preserves_tls_or_explicit_managed_proxy_identity(self):
        for provider in ['aws','azure','gcp','ibm']:
            with SecretFiles(provider,environment(provider),'worker')as secrets:
                env={'DATABASE_NAME':'owned_knowledge','DATABASE_USER':'owned_worker','REGION':'ap-southeast-2',
                     'DATABASE_HOST':'owned.example.ap-southeast-2.rds.amazonaws.com','DATABASE_PORT':'30934',
                     'WORKLOAD_IDENTITY_CLIENT_ID':'11111111-1111-4111-8111-111111111111',
                     'DATABASE_CONNECTION_NAME':'owned-project:australia-southeast1:owned-postgres',
                     'DATABASE_SERVICE_ACCOUNT':'owned-worker@owned-project.iam.gserviceaccount.com'}
                if provider=='azure':env['DATABASE_HOST']='owned-postgres.postgres.database.azure.com'
                if provider=='ibm':env['DATABASE_HOST']='owned.databases.appdomain.cloud'
                database=native_database(provider,env,'worker',secrets)
                self.assertEqual(database.provider,provider);self.assertNotIn('password',database.parameters)
                if provider=='gcp':
                    self.assertTrue(database.parameters['host'].startswith('/cloudsql/'));self.assertEqual(database.parameters['sslmode'],'disable')
                    with self.assertRaises(ValueError):native_database(provider,{**env,'DATABASE_TRANSPORT':'plaintext'},'worker',secrets)
                else:self.assertEqual(database.parameters['sslmode'],'verify-full')
                self.assertNotIn('SYNTHETIC',repr(database))

    def test_owned_executor_requires_exact_byte_bound_response_and_immutable_revision(self):
        raw=b'Approved source text.';calls=[]
        def run(data,mime):
            calls.append((data,mime));return{'format':'enterprise-document-v1','sha256':hashlib.sha256(data).hexdigest(),'mediaType':mime,'text':data.decode()}
        executor=DocumentExecutor('a'*64,run);self.assertEqual(executor(raw,'text/plain'),raw.decode());self.assertEqual(calls,[(raw,'text/plain')])
        with self.assertRaises(AttributeError):executor.artifact_revision='b'*64
        for value in [{'format':'enterprise-document-v1','sha256':'0'*64,'mediaType':'text/plain','text':'forged'},
                      {'format':'enterprise-document-v1','sha256':hashlib.sha256(raw).hexdigest(),'mediaType':'text/plain','text':'','partial':True}]:
            with self.assertRaises(SourceUnavailable):DocumentExecutor('a'*64,lambda data,mime:value)(raw,'text/plain')


if __name__=='__main__':unittest.main()
