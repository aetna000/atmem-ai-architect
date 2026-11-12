"""Actual local TLS/RPC and composition; parser/model contents are explicit fixtures.

The separate Linux image qualification uses real PDF/OCR over this RPC handler.
Neither suite proves native cloud ingress, caller IAM or a deployed service.
"""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import hashlib
import http.client
import json
from pathlib import Path
import ssl
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent),str(ROOT/'.local/azure-runtime-sdk')]
import requests
from invoice_parser_service import ParserServer
from invoice_parser_transport import ParserClient,google_parser_authorization
from invoice_document import DocumentError
from invoice_processing import InvoiceProcessor
from workflow_errors import TemporaryWork,PermanentWork
from workflow_tls_destination_fixture import TlsDestinationFixture
from invoice_extraction_acceptance import evidence_fixture

RAW=b'%PDF-1.7\nExplicit parser transport fixture\n%%EOF'

class PrivateParserRpcTests(unittest.TestCase):
    def setUp(self):
        self.cert=TlsDestinationFixture();self.hold=threading.Event();self.hold.set();self.active=threading.Event();self.mode='normal';owner=self
        class ParserFixture:
            def extract(self,raw,digest):
                owner.active.set()
                if not owner.hold.wait(5):raise RuntimeError('Fixture hold expired')
                if owner.mode=='encrypted':raise DocumentError('encrypted_pdf')
                document,_=evidence_fixture();document['sha256']='0'*64 if owner.mode=='wrong-digest'else digest
                if owner.mode=='oversize':document['pages'][0]['text']='x'*121000
                return document
        self.server=ParserServer(('127.0.0.1',0),ParserFixture());context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.cert.ca_file,Path(self.cert.folder.name)/'fixture.key');self.server.socket=context.wrap_socket(self.server.socket,server_side=True)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.endpoint='https://localhost:'+str(self.server.server_port)+'/extract'
        self.session=requests.Session();self.session.verify=str(self.cert.ca_file);self.client=ParserClient(self.endpoint,session=self.session)
    def tearDown(self):self.hold.set();self.server.shutdown();self.server.server_close();self.thread.join(timeout=2);self.session.close();self.cert.close()
    def test_actual_https_pdf_round_trip_and_exact_original_digest(self):
        result=self.client(RAW);self.assertEqual(result['sha256'],hashlib.sha256(RAW).hexdigest());self.assertIn('42.50',result['pages'][0]['text']);self.assertFalse(self.session.trust_env)
        with self.assertRaises(TemporaryWork):ParserClient(self.endpoint)(RAW)
    def test_ambiguous_or_oversize_request_framing_is_rejected_before_parsing(self):
        for lengths,transfer,expected in [(['10000001'],None,413),(['4','5'],None,411),(['4'],'chunked',411),(['0'],None,413)]:
            with self.subTest(lengths=lengths,transfer=transfer):
                connection=http.client.HTTPSConnection('localhost',self.server.server_port,context=self.cert.context,timeout=2);connection.putrequest('POST','/extract')
                for length in lengths:connection.putheader('Content-Length',length)
                if transfer:connection.putheader('Transfer-Encoding',transfer)
                connection.putheader('Content-Type','application/pdf');connection.endheaders();response=connection.getresponse();self.assertEqual(response.status,expected);response.read();connection.close()
        self.assertFalse(self.active.is_set())
    def test_busy_parser_backpressure_does_not_start_a_second_extraction(self):
        self.hold.clear();result=[]
        thread=threading.Thread(target=lambda:result.append(self.client(RAW)));thread.start();self.assertTrue(self.active.wait(2))
        with self.assertRaises(TemporaryWork):self.client(RAW)
        self.hold.set();thread.join(timeout=3);self.assertEqual(len(result),1)
    def test_rejected_pdf_changed_digest_and_oversize_output_never_reach_a_model(self):
        objects=SimpleNamespace(load=lambda account,ref:RAW);model=Mock();row={'created_at':datetime.now(timezone.utc),'account_id':'fixture-account','source_ref':{'sha256':hashlib.sha256(RAW).hexdigest()}}
        for mode,failure in [('encrypted',PermanentWork),('wrong-digest',TemporaryWork),('oversize',TemporaryWork)]:
            self.mode=mode
            with self.subTest(mode=mode),self.assertRaises(failure):InvoiceProcessor(objects,self.client,model)(row)
        model.generate.assert_not_called()
    def test_actual_composition_validates_model_quotes_and_retains_human_approval(self):
        _,reply=evidence_fixture();model=Mock();model.generate.return_value=json.dumps(reply);objects=SimpleNamespace(load=lambda account,ref:RAW);row={'created_at':datetime.now(timezone.utc),'account_id':'fixture-account','source_ref':{'sha256':hashlib.sha256(RAW).hexdigest()}}
        result=InvoiceProcessor(objects,self.client,model)(row);self.assertTrue(result['requiresHumanReview']);self.assertEqual(result['total'],'42.50');self.assertEqual(result['documentSha256'],row['source_ref']['sha256'])
        reply['total']['quote']='Made up invoice total'
        model.generate.return_value=json.dumps(reply)
        with self.assertRaises(PermanentWork):InvoiceProcessor(objects,self.client,model)(row)
    def test_expired_or_undated_invoices_never_read_objects_parse_or_call_models(self):
        objects=Mock();model=Mock();parser=Mock()
        for created in [None,datetime.now(timezone.utc)-timedelta(days=91),'untrusted-date']:
            with self.subTest(created=created),self.assertRaises(PermanentWork):InvoiceProcessor(objects,parser,model)({'created_at':created})
        objects.load.assert_not_called();parser.assert_not_called();model.generate.assert_not_called()
    def test_arbitrary_parser_locations_and_caller_selected_auth_are_not_admitted(self):
        for endpoint in ['http://localhost/extract','https://user:secret@localhost/extract','https://localhost/extract?url=other','file:///etc/passwd','https://localhost/different']:
            with self.assertRaises(ValueError):ParserClient(endpoint)
        client=ParserClient(self.endpoint,lambda:'invalid header',session=self.session)
        with self.assertRaises(TemporaryWork):client(RAW)
        self.assertFalse(self.active.is_set())

class GoogleParserIdentityTests(unittest.TestCase):
    def response(self,headers=None):
        response=Mock();response.status_code=200;response.headers={'Metadata-Flavor':'Google'}if headers is None else headers;response.iter_content.return_value=[b'fixture.identity.token'];response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);return response
    def test_metadata_identity_is_requested_only_for_the_owned_service_audience(self):
        session=Mock();session.get.return_value=self.response();audience='https://parser-fixture.run.app'
        read=google_parser_authorization(audience,session);self.assertEqual(read(),'Bearer fixture.identity.token');args=session.get.call_args
        self.assertEqual(args.args[0],'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity');self.assertEqual(args.kwargs['params'],{'audience':audience,'format':'full'});self.assertFalse(args.kwargs['allow_redirects']);self.assertFalse(session.trust_env)
        session.get.return_value=self.response({})
        with self.assertRaises(TemporaryWork):read()

if __name__=='__main__':unittest.main(verbosity=2)
