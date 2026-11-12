"""Real RSA/JWT and encryption primitives; scripted JWKS resolver, no IdP call."""
from pathlib import Path
import sys
import time
import unittest
from types import SimpleNamespace
sys.path[:0]=[str(Path(__file__).resolve().parents[2]/'src/runtime'),str(Path(__file__).resolve().parents[2]/'.local/azure-runtime-sdk')]
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from enterprise_identity import CompanyIdentity
from enterprise_sources import SourceDenied

class CompanyIdentityPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.key=rsa.generate_private_key(public_exponent=65537,key_size=2048);cls.other=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    def verifier(self):
        key=self.key
        class Resolver:
            def get_signing_key_from_jwt(self,token):
                return SimpleNamespace(key=key.public_key())
        return CompanyIdentity('company1','https://company.example/issuer','knowledge-api','https://company.example/jwks',jwks=Resolver())
    def token(self,**changes):
        now=int(time.time());return jwt.encode({'iss':'https://company.example/issuer','sub':'alice','aud':'knowledge-api','iat':now,'exp':now+3600,'scp':'knowledge.read',**changes},self.key,algorithm='RS256',headers={'kid':'owned-key'})
    def test_existing_company_api_identity_is_stable_but_account_scoped(self):
        first=self.verifier().verify(self.token());second=self.verifier().verify(self.token());self.assertEqual(first.key,second.key);self.assertEqual(first.account_id,'company1');self.assertEqual(first.subject,'alice');self.assertNotIn(self.token(),repr(first))
    def test_wrong_issuer_audience_expiry_scope_and_id_tokens_deny(self):
        for changes in [{'iss':'https://other.example'},{'aud':'other-api'},{'exp':int(time.time())-1},{'scp':'openid profile'},{'scp':''},{'sub':''},{'exp':True},{'iat':True},{'exp':int(time.time())+7200}]:
            with self.assertRaises(SourceDenied):self.verifier().verify(self.token(**changes))
    def test_wrong_signature_algorithm_and_unknown_key_url_do_not_establish_identity(self):
        token=jwt.encode({'iss':'https://company.example/issuer','sub':'alice','aud':'knowledge-api','iat':int(time.time()),'exp':int(time.time())+3600,'scp':'knowledge.read'},self.other,algorithm='RS256',headers={'jku':'https://evil.example/keys'})
        with self.assertRaises(SourceDenied):self.verifier().verify(token)
        with self.assertRaises(SourceDenied):self.verifier().verify(jwt.encode({'scp':'knowledge.read'},'SYNTHETIC'*8,algorithm='HS256'))

if __name__=='__main__':unittest.main()
