"""Actual RSA signatures and RPC admission; signing keys are local fixtures."""
import http.client
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/azure-runtime-sdk')]
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from invoice_parser_identity import EntraParserVerifier
from invoice_parser_service import ParserServer

TENANT='11111111-1111-1111-1111-111111111111';API='22222222-2222-2222-2222-222222222222';CLIENT='33333333-3333-3333-3333-333333333333';OID='44444444-4444-4444-4444-444444444444'

class EntraParserAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.key=rsa.generate_private_key(public_exponent=65537,key_size=2048);self.keys=Mock();self.keys.get_signing_key_from_jwt.return_value=SimpleNamespace(key=self.key.public_key())
        self.verify=EntraParserVerifier(TENANT,API,CLIENT,OID,jwks=self.keys);now=int(time.time());self.claims={'iss':'https://login.microsoftonline.com/'+TENANT+'/v2.0','aud':API,'tid':TENANT,'oid':OID,'azp':CLIENT,'ver':'2.0','iat':now-1,'nbf':now-1,'exp':now+600,'roles':['Parser.Invoke'],'idtyp':'app'}
    def token(self,changes=None,key=None):return jwt.encode({**self.claims,**(changes or{})},key or self.key,algorithm='RS256',headers={'kid':'owned-local-key'})
    def test_exact_signed_worker_and_parser_role_are_required(self):self.assertEqual(self.verify(self.token()),OID)
    def test_other_tenant_audience_worker_principal_client_role_and_delegated_tokens_are_denied(self):
        for changes in [{'tid':OID},{'aud':CLIENT},{'aud':[API,CLIENT]},{'oid':CLIENT},{'azp':OID},{'roles':['WorkspaceUser']},{'roles':['Parser.Invoke',{}]},{'scp':'access_as_user'},{'idtyp':'user'},{'ver':'1.0'},{'iss':'https://attacker.invalid'}]:
            with self.subTest(changes=changes),self.assertRaises(PermissionError):self.verify(self.token(changes))
    def test_expired_future_malformed_oversize_and_forged_credentials_fail_closed(self):
        for changes in [{'exp':int(time.time())-60},{'nbf':int(time.time())+120},{'iat':str(self.claims['iat'])},{'exp':self.claims['iat']+90000}]:
            with self.subTest(changes=changes),self.assertRaises(PermissionError):self.verify(self.token(changes))
        for token in ['malformed','x'*16385,jwt.encode(self.claims,'',algorithm='none'),self.token(key=rsa.generate_private_key(public_exponent=65537,key_size=2048))]:
            with self.assertRaises(PermissionError):self.verify(token)
        self.keys.get_signing_key_from_jwt.side_effect=TimeoutError()
        with self.assertRaises(PermissionError):self.verify(self.token())
    def test_signing_keys_are_requested_only_from_fixed_tenant_endpoint(self):
        with unittest.mock.patch('invoice_parser_identity.jwt.PyJWKClient')as client:
            EntraParserVerifier(TENANT,API,CLIENT,OID)
        self.assertEqual(client.call_args.args,('https://login.microsoftonline.com/'+TENANT+'/discovery/v2.0/keys',));self.assertEqual(client.call_args.kwargs['timeout'],2)
        for value in ['not-a-guid','https://attacker.invalid',TENANT.upper().replace('1','A',1)]:
            with self.assertRaises(ValueError):EntraParserVerifier(value,API,CLIENT,OID)
    def test_rpc_rejects_missing_duplicate_and_wrong_worker_before_reading_or_parsing_pdf(self):
        parser=Mock();parser.extract.return_value={'explicit':'synthetic parser result'};server=ParserServer(('127.0.0.1',0),parser,self.verify);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            for headers in [[],['Bearer malformed'],['Bearer '+self.token({'oid':CLIENT})],['Bearer '+self.token(),'Bearer '+self.token()]]:
                client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3);client.putrequest('POST','/extract')
                client.putheader('Content-Length','100');client.putheader('Content-Type','application/pdf')
                for value in headers:client.putheader('Authorization',value)
                client.endheaders();response=client.getresponse();self.assertEqual(response.status,403);response.read();client.close()
            parser.extract.assert_not_called()
            client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3);client.request('POST','/extract',body=b'%PDF-fixture',headers={'Content-Type':'application/pdf','Authorization':'Bearer '+self.token()});response=client.getresponse();self.assertEqual(response.status,200);response.read();client.close();parser.extract.assert_called_once()
        finally:server.shutdown();server.server_close();thread.join(timeout=2)

if __name__=='__main__':unittest.main(verbosity=2)
