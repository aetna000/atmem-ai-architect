import copy
import json
import unittest
from hosted.credits import CreditLedger, Conflict, CreditError
from hosted.credentials import CredentialVault, CredentialsUnavailable
from hosted.tests.test_credits import AtomicTestStore


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.store=AtomicTestStore();self.ledger=CreditLedger(self.store,welcome_units=1,policy_version='fixture')
        self.ledger.register('alice');self.ledger.register('bob')
        self.vault=CredentialVault(self.store,self.ledger,keyring={'v1':b'a'*32},active_key='v1')
        self.secret='sk-synthetic-private-key-never-real'

    def test_encrypted_tenant_bound_store_never_returns_key_to_caller(self):
        result=self.vault.update('alice','openai',self.secret,0)
        self.assertEqual(result,{'configured':True,'revision':1,'verified':False})
        self.assertNotIn(self.secret,json.dumps(list(self.store.data.values())))
        self.assertEqual(self.vault.for_broker('alice','openai'),self.secret)
        self.assertFalse(self.vault.status('bob','openai')['configured'])
        alice=self.vault._path('alice','openai');bob=self.vault._path('bob','openai')
        self.store.data['credentials',bob]=copy.deepcopy(self.store.data['credentials',alice])
        self.store.data['credentials',bob]['uid']='bob'
        with self.assertRaises(CredentialsUnavailable):self.vault.for_broker('bob','openai')

    def test_revision_protects_concurrent_edits_and_remove_erases_ciphertext(self):
        self.vault.update('alice','anthropic',self.secret,0)
        with self.assertRaises(Conflict):self.vault.update('alice','anthropic','a'*30,0)
        with self.assertRaises(Conflict):self.vault.remove('alice','anthropic',0)
        self.vault.remove('alice','anthropic',1)
        record=self.store.data['credentials',self.vault._path('alice','anthropic')]
        self.assertNotIn('ciphertext',record)
        with self.assertRaises(CredentialsUnavailable):self.vault.for_broker('alice','anthropic')
        self.assertFalse(self.vault.status('alice','anthropic')['configured'])

    def test_versioned_key_rotation_can_read_old_values_and_new_ciphertext(self):
        self.vault.update('alice','openai',self.secret,0)
        rotated=CredentialVault(self.store,self.ledger,keyring={'v1':b'a'*32,'v2':b'b'*32},active_key='v2')
        self.assertEqual(rotated.for_broker('alice','openai'),self.secret)
        rotated.update('alice','openai','new-synthetic-key-value-12345',1)
        self.assertEqual(rotated.for_broker('alice','openai'),'new-synthetic-key-value-12345')
        with self.assertRaises(CredentialsUnavailable):self.vault.for_broker('alice','openai')

    def test_no_insecure_key_or_provider_fallback(self):
        with self.assertRaises(ValueError):CredentialVault(self.store,self.ledger,keyring={},active_key='v1')
        for secret in ['short','x'*513,'sk-a-key-with-newline\n','a'*20+'é']:
            with self.assertRaises(CreditError):self.vault.update('alice','openai',secret,0)
        with self.assertRaises(CreditError):self.vault.update('alice','http://untrusted.test',self.secret,0)
