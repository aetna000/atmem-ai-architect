"""Actual Firestore emulator evidence; never targets a cloud project."""
import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from hosted.credits import CreditLedger, InsufficientCredits, Conflict
from hosted.firestore_store import FirestoreTransactions


@unittest.skipUnless(os.environ.get('FIRESTORE_EMULATOR_HOST'), 'Explicit local Firestore emulator required')
class FirestoreCreditTests(unittest.TestCase):
    def setUp(self):
        from google.cloud import firestore
        self.client=firestore.Client(project='demo-architect-hosted')
        self.store=FirestoreTransactions(self.client,namespace='test_'+uuid.uuid4().hex[:16])
        self.ledger=CreditLedger(self.store,welcome_units=100,policy_version='synthetic-test-policy')
        self.ledger.register('alice');self.ledger.register('bob')

    def tearDown(self):
        for collection in self.client.collections():
            if collection.id.startswith(self.store.namespace+'_'):
                for snapshot in collection.stream():snapshot.reference.delete()
        self.client.close()

    def test_atomic_concurrent_welcome_and_reservations(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _:self.ledger.register('same-person'),range(8)))
        def reserve(i):
            try:self.ledger.reserve('alice',str(i),'a'*64,30);return True
            except InsufficientCredits:return False
        with ThreadPoolExecutor(max_workers=4) as pool:outcomes=list(pool.map(reserve,range(10)))
        self.assertEqual(sum(outcomes),3)
        self.assertEqual(self.ledger.account('alice')['available'],10)
        self.assertEqual(self.ledger.account('alice')['reserved'],90)
        self.assertEqual(self.ledger.account('same-person')['available'],100)
        self.assertEqual(self.ledger.account('bob')['available'],100)

    def test_durable_recovery_and_duplicate_payment_refund(self):
        self.ledger.grant_purchase('alice','payment-1',200,'c'*64)
        self.ledger.reserve('alice','request-1','a'*64,50)
        self.ledger.transition('alice','request-1','sent')
        self.ledger.transition('alice','request-1','uncertain')
        recovered=CreditLedger(FirestoreTransactions(self.client,namespace=self.store.namespace),welcome_units=999,policy_version='new-policy')
        self.assertEqual(recovered.register('alice')['available'],250)
        recovered.grant_purchase('alice','payment-1',200,'c'*64)
        with self.assertRaises(Conflict):recovered.grant_purchase('bob','payment-1',200,'c'*64)
        with self.assertRaises(Conflict):recovered.release_unsent('alice','request-1')
        recovered.settle('alice','request-1',20,'verified-usage')
        recovered.settle('alice','request-1',20,'verified-usage')
        recovered.refund_purchase('payment-1',200,'verified-refund')
        recovered.refund_purchase('payment-1',200,'verified-refund')
        account=recovered.account('alice')
        self.assertEqual((account['available'],account['reserved'],account['spent']),(80,0,20))

    def test_checkout_and_encrypted_key_transactions_survive_adapter_reconstruction(self):
        from hosted.configuration import BillingConfiguration
        from hosted.credentials import CredentialVault
        from hosted.payments import CheckoutOrders
        from hosted.tests.test_payments import FakeStripe
        provider=FakeStripe()
        orders=CheckoutOrders(self.store,self.ledger,BillingConfiguration(self.store),provider,
                              return_url='https://atmem.ai/ai-architect/workspace/')
        order=orders.create('alice','firestore-payment',137)
        sid='cs_test_'+order['id'];provider.paid(sid)
        with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda _:orders.fulfill(sid),range(4)))
        self.assertEqual(self.ledger.account('alice')['available'],1_370_100)
        vault=CredentialVault(self.store,self.ledger,keyring={'v1':b'a'*32},active_key='v1')
        vault.update('alice','anthropic','synthetic-provider-secret-value',0)
        fresh=CredentialVault(FirestoreTransactions(self.client,namespace=self.store.namespace),self.ledger,
                              keyring={'v1':b'a'*32},active_key='v1')
        self.assertEqual(fresh.for_broker('alice','anthropic'),'synthetic-provider-secret-value')
