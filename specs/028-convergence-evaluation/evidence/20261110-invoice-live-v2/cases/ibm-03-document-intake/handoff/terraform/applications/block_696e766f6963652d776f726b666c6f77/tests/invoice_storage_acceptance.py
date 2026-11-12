"""Native SDK shapes and scripted HTTP versions/conditions; not live cloud IAM."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import Mock,patch
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'parser'))
sys.path.insert(0,str(ROOT))
from invoice_object_store import HttpInvoiceObjects,S3InvoiceObjects,ObjectUnavailable,object_key

RAW=b'%PDF-1.7\nsynthetic transport fixture'
DIGEST=hashlib.sha256(RAW).hexdigest()
class Response:
    def __init__(self,raw=b'',code=200,headers=None):self.raw=raw;self.status_code=code;self.headers=headers or{}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def iter_content(self,size):
        for index in range(0,len(self.raw),size):yield self.raw[index:index+size]

class NativePrivateHttpObjectsTests(unittest.TestCase):
    def setUp(self):self.account=str(uuid.uuid4());self.other=str(uuid.uuid4())
    def client(self,provider,session):return HttpInvoiceObjects(provider,'au-syd'if provider=='ibm'else'australiaeast'if provider=='azure'else'australia-southeast1','private-invoices',lambda:{'Authorization':'Bearer synthetic-workload'},account='reviewedstorage',session=session)
    def metadata(self,provider):return b'{"generation":"123"}'if provider=='gcp'else b''
    def headers(self,provider,version='123'):return{'x-goog-generation'if provider=='gcp'else'x-ms-version-id'if provider=='azure'else'x-amz-version-id':version}
    def test_each_native_put_is_create_only_and_rechecks_the_exact_immutable_version(self):
        for provider in ['azure','gcp','ibm']:
            with self.subTest(provider=provider):
                session=Mock();session.request.side_effect=[Response(self.metadata(provider),201,self.headers(provider)),Response(RAW,headers=self.headers(provider))];client=self.client(provider,session);reference=client.put(self.account,RAW)
                self.assertEqual(reference['sha256'],DIGEST);self.assertEqual(reference['key'],object_key(self.account,DIGEST));calls=session.request.call_args_list
                if provider=='gcp':self.assertEqual(calls[0].kwargs['params']['ifGenerationMatch'],'0');self.assertEqual(calls[1].kwargs['params'],{'alt':'media','generation':'123'})
                else:
                    self.assertEqual(calls[0].kwargs['headers']['If-None-Match'],'*');self.assertEqual(calls[1].kwargs['params'],{'versionid'if provider=='azure'else'versionId':'123'})
                    if provider=='azure':self.assertIn('x-ms-date',calls[0].kwargs['headers']);self.assertEqual(calls[0].kwargs['headers']['x-ms-blob-type'],'BlockBlob')
                self.assertFalse(session.trust_env);self.assertTrue(all(not call.kwargs['allow_redirects']for call in calls))
    def test_repeated_delivery_resolves_existing_version_without_overwrite_or_guessing(self):
        for provider in ['azure','gcp','ibm']:
            session=Mock();session.request.side_effect=[Response(code=412),Response(self.metadata(provider)if provider=='gcp'else RAW,headers=self.headers(provider)),Response(RAW,headers=self.headers(provider))]
            ref=self.client(provider,session).put(self.account,RAW);self.assertEqual(ref['version'],'123');self.assertEqual([call.args[0]for call in session.request.call_args_list],['POST'if provider=='gcp'else'PUT','GET','GET'])
    def test_no_version_wrong_version_digest_changes_and_denied_or_redirected_reads_fail_closed(self):
        for provider in ['azure','gcp','ibm']:
            for responses in [[Response(b'{}',201)], [Response(self.metadata(provider),201,self.headers(provider)),Response(RAW,headers=self.headers(provider,'different'))], [Response(self.metadata(provider),201,self.headers(provider)),Response(b'%PDF-changed',headers=self.headers(provider))], [Response(code=403)],[Response(code=302)]]:
                session=Mock();session.request.side_effect=responses
                with self.subTest(provider=provider,responses=responses),self.assertRaises((ObjectUnavailable,PermissionError)):self.client(provider,session).put(self.account,RAW)
    def test_cross_account_destination_and_arbitrary_reference_fields_never_make_network_requests(self):
        for provider in ['azure','gcp','ibm']:
            session=Mock();client=self.client(provider,session);ref=client._reference(self.account,DIGEST,'123')
            for changed in [{**ref,'key':object_key(self.other,DIGEST)},{**ref,'bucket':'other-private-bucket'},{**ref,'region':'somewhere-else'},{**ref,'url':'https://attacker.test'}]:
                with self.assertRaises((ValueError,PermissionError)):client.load(self.account,changed)
            with self.assertRaises(PermissionError):client.load(self.other,ref)
            session.request.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
