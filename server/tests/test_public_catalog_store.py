"""Native SDK shape checks and scripted HTTP contracts; not cloud IAM evidence."""
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import sys
import threading
import unittest
from email.utils import parsedate_to_datetime
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src/runtime'))
import boto3
from botocore.response import StreamingBody
from botocore.stub import Stubber
from botocore.exceptions import ClientError
from public_catalog_store import HttpCatalogStore,S3CatalogStore
from public_faq import CatalogChanged,CatalogUnavailable,PublicFaq

def catalog(revision='catalog-v1',text='Refunds are accepted within thirty days after purchase.'):
    return json.dumps({'format':'atmem-public-faq-v1','revision':revision,'articles':[{'id':'refund','revision':revision,'title':'Refund policy','text':text,'url':'https://help.example.test/refund','visibility':'public'}]}).encode()

class Response:
    def __init__(self,raw=b'',status=200,headers=None):self.raw=raw;self.status_code=status;self.headers=headers or {}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def iter_content(self,size):
        for i in range(0,len(self.raw),size):yield self.raw[i:i+size]

def store(provider,session,auth=None):
    return HttpCatalogStore(provider,'au-syd','reviewed-public-catalog',auth or (lambda:{'Authorization':'Bearer fixture-workload'}),session=session,account='reviewedstorage')

class HttpCatalogContractTests(unittest.TestCase):
    def test_azure_bearer_requests_include_the_required_http_date_and_version(self):
        session=Mock();session.request.side_effect=[Response(catalog(),headers={'ETag':'"one"'}),Response(status=201,headers={'ETag':'"two"'})]
        client=store('azure',session);client.load();client.save(catalog(),None)
        for call in session.request.call_args_list:
            headers=call.kwargs['headers'];self.assertEqual(headers['x-ms-version'],'2023-11-03');self.assertIsNotNone(parsedate_to_datetime(headers['x-ms-date']).tzinfo);self.assertTrue(headers['x-ms-date'].endswith(' GMT'))
    def test_azure_and_ibm_authoritative_etag_and_conditional_create_replace(self):
        for provider in ['azure','ibm']:
            session=Mock();session.request.side_effect=[Response(catalog(),headers={'ETag':'"one"'}),Response(status=201,headers={'etag':'"two"'}),Response(headers={'ETag':'"three"'})]
            client=store(provider,session);current=client.load();self.assertEqual(current.version,'"one"');self.assertEqual(client.save(catalog('catalog-v2'),current.version),'"two"');self.assertEqual(client.save(catalog('catalog-v3'),None),'"three"')
            calls=session.request.call_args_list;self.assertEqual([c.args[0] for c in calls],['GET','PUT','PUT']);self.assertEqual(calls[1].kwargs['headers']['If-Match'],'"one"');self.assertEqual(calls[2].kwargs['headers']['If-None-Match'],'*')
            self.assertTrue(all(c.kwargs['allow_redirects'] is False and c.kwargs['stream'] is True for c in calls));self.assertFalse(session.trust_env)
            if provider=='azure':self.assertEqual(calls[1].kwargs['headers']['x-ms-blob-type'],'BlockBlob');self.assertEqual(calls[0].args[1],'https://reviewedstorage.blob.core.windows.net/reviewed-public-catalog/catalog.json')
            else:self.assertEqual(calls[0].args[1],'https://s3.au-syd.cloud-object-storage.appdomain.cloud/reviewed-public-catalog/catalog.json')
    def test_google_read_binds_content_to_exact_generation_and_writes_use_native_precondition(self):
        session=Mock();session.request.side_effect=[Response(b'{"generation":"123"}'),Response(catalog()),Response(b'{"generation":"124"}'),Response(b'{"generation":"125"}')]
        client=store('gcp',session);current=client.load();self.assertEqual(current.version,'123');self.assertEqual(client.save(catalog('v2'),'123'),'124');self.assertEqual(client.save(catalog('v3'),'0'),'125')
        calls=session.request.call_args_list;self.assertEqual(calls[0].kwargs['params'],{'fields':'generation'});self.assertEqual(calls[1].kwargs['params'],{'alt':'media','generation':'123'})
        self.assertEqual(calls[2].args,('POST','https://storage.googleapis.com/upload/storage/v1/b/reviewed-public-catalog/o'));self.assertEqual(calls[2].kwargs['params'],{'uploadType':'media','name':'catalog.json','ifGenerationMatch':'123'});self.assertEqual(calls[3].kwargs['params']['ifGenerationMatch'],'0')
    def test_denied_missing_redirected_and_stale_operations_fail_without_retry_or_cached_data(self):
        for provider in ['azure','gcp','ibm']:
            for status,exception in [(401,PermissionError),(403,PermissionError),(404,CatalogUnavailable),(302,CatalogUnavailable),(500,CatalogUnavailable),(412,CatalogChanged),(409,CatalogChanged)]:
                session=Mock();session.request.return_value=Response(status=status);client=store(provider,session)
                with self.subTest(provider=provider,status=status),self.assertRaises(exception):client.load()
                session.request.assert_called_once()
                session.reset_mock()
                with self.assertRaises(exception):client.save(catalog(),'123' if provider=='gcp' else '"one"')
                session.request.assert_called_once()
    def test_invalid_catalog_or_precondition_is_never_written(self):
        for provider in ['azure','gcp','ibm']:
            session=Mock();client=store(provider,session)
            private=json.loads(catalog());private['articles'][0]['visibility']='private'
            with self.assertRaises(CatalogUnavailable):client.save(json.dumps(private).encode(),'123' if provider=='gcp' else '"one"')
            for version in ['*','anything','"\r\nAuthorization: stolen"']:
                with self.assertRaises(ValueError):client.save(catalog(),version)
            session.request.assert_not_called()
    def test_missing_or_malformed_provider_versions_are_not_replaced_by_local_guesses(self):
        for provider in ['azure','ibm']:
            for headers in [{},{'ETag':'weak'}, {'ETag':'W/"one"'}]:
                session=Mock();session.request.return_value=Response(catalog(),headers=headers)
                with self.assertRaises(CatalogUnavailable):store(provider,session).load()
        for metadata in [b'{}',b'{"generation":123}',b'{"generation":"0"}',b'{"generation":"1","generation":"2"}']:
            session=Mock();session.request.return_value=Response(metadata)
            with self.assertRaises(CatalogUnavailable):store('gcp',session).load()
            session.request.assert_called_once()
    def test_invalid_destination_or_missing_workload_token_never_calls_http(self):
        session=Mock()
        for provider in ['azure','gcp','ibm']:
            for bucket in ['../private','bucket/path','https://attacker.test','has space']:
                with self.assertRaises(ValueError):HttpCatalogStore(provider,'au-syd',bucket,lambda:{},session=session,account='reviewedstorage')
            with self.assertRaises(PermissionError):store(provider,session,lambda:{}).load()
        session.request.assert_not_called()

class S3CatalogContractTests(unittest.TestCase):
    def setUp(self):
        self.client=boto3.client('s3',region_name='ap-southeast-2',aws_access_key_id='fixture',aws_secret_access_key='fixture');self.stub=Stubber(self.client);self.stub.activate();self.addCleanup(self.stub.deactivate)
        self.store=S3CatalogStore('reviewed-public-catalog','ap-southeast-2','123456789012',client=self.client)
    def test_real_sdk_shape_checks_conditional_writes_and_owner_binding(self):
        raw=catalog();underlying=io.BytesIO(raw);stream=StreamingBody(underlying,len(raw));self.stub.add_response('get_object',{'Body':stream,'ETag':'"one"'},{'Bucket':'reviewed-public-catalog','Key':'catalog.json','ExpectedBucketOwner':'123456789012'})
        current=self.store.load();self.assertEqual(current.version,'"one"');self.assertTrue(underlying.closed)
        common={'Bucket':'reviewed-public-catalog','Key':'catalog.json','Body':raw,'ContentType':'application/json','ExpectedBucketOwner':'123456789012'}
        self.stub.add_response('put_object',{'ETag':'"two"'},{**common,'IfMatch':'"one"'});self.assertEqual(self.store.save(raw,current.version),'"two"')
        self.stub.add_response('put_object',{'ETag':'"three"'},{**common,'IfNoneMatch':'*'});self.assertEqual(self.store.save(raw,None),'"three"');self.stub.assert_no_pending_responses()
    def test_stale_s3_write_is_a_conflict_and_does_not_retry(self):
        raw=catalog();self.stub.add_client_error('put_object','PreconditionFailed',http_status_code=412,expected_params={'Bucket':'reviewed-public-catalog','Key':'catalog.json','Body':raw,'ContentType':'application/json','ExpectedBucketOwner':'123456789012','IfMatch':'"one"'})
        with self.assertRaises(CatalogChanged):self.store.save(raw,'"one"')
        self.stub.assert_no_pending_responses()
    def test_read_outage_is_not_an_empty_catalog(self):
        self.stub.add_client_error('get_object','AccessDenied',http_status_code=403)
        with self.assertRaises(ClientError) as failed:self.store.load()
        self.assertEqual(failed.exception.response['Error']['Code'],'AccessDenied')
        self.stub.assert_no_pending_responses()

class ConditionalConcurrencyTests(unittest.TestCase):
    def test_two_editors_from_same_snapshot_cannot_overwrite_each_other(self):
        # Stateful transport fixture tests client CAS behavior; real cloud IAM and
        # consistency must be separately qualified in the destination account.
        for provider in ['azure','gcp','ibm']:
            lock=threading.Lock();state={'version':1,'raw':catalog()}
            def request(method,url,**kwargs):
                with lock:
                    version=str(state['version']);etag='"'+version+'"'
                    if method=='GET':
                        if provider=='gcp' and kwargs['params'].get('fields')=='generation':return Response(json.dumps({'generation':version}).encode())
                        return Response(state['raw'],headers={'ETag':etag})
                    expected=kwargs['params']['ifGenerationMatch'] if provider=='gcp' else kwargs['headers'].get('If-Match')
                    if expected!=(version if provider=='gcp' else etag):return Response(status=412)
                    state['version']+=1;state['raw']=kwargs['data'];return Response(json.dumps({'generation':str(state['version'])}).encode() if provider=='gcp' else b'',headers={'ETag':'"'+str(state['version'])+'"'})
            session=Mock();session.request.side_effect=request;client=store(provider,session);before=client.load()
            def save(revision):
                try:client.save(catalog(revision),before.version);return 'written'
                except CatalogChanged:return 'conflict'
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(save,['editor-one','editor-two']))
            self.assertEqual(sorted(results),['conflict','written']);self.assertEqual(state['version'],2)

if __name__=='__main__':unittest.main()
