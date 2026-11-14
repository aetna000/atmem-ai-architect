import copy
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from hosted.credits import CreditLedger, Conflict, InsufficientCredits, CreditError, MAX_UNITS, digest


class AtomicTestStore:
    """Rollback-capable test double. Not a distributed or production adapter."""
    def __init__(self):
        self.data = {}; self.lock = threading.Lock()
    def transaction(self, callback):
        with self.lock:
            before = copy.deepcopy(self.data)
            try: return copy.deepcopy(callback(self))
            except BaseException:
                self.data = before; raise
    def get(self, collection, key): return copy.deepcopy(self.data.get((collection, key)))
    def set(self, collection, key, value): self.data[collection, key] = copy.deepcopy(value)
    def create(self, collection, key, value):
        if (collection,key) in self.data: raise Conflict('Immutable record already exists')
        self.set(collection,key,value)


class CreditTests(unittest.TestCase):
    def setUp(self):
        self.store = AtomicTestStore()
        # Explicit synthetic test policy, not a proposed live welcome grant or price.
        self.ledger = CreditLedger(self.store, welcome_units=100, policy_version='fixture-v1')
        self.ledger.register('alice'); self.ledger.register('bob')

    def test_welcome_grant_is_once_even_after_policy_change_and_concurrent_signup(self):
        with ThreadPoolExecutor(max_workers=12) as pool:
            list(pool.map(lambda _: self.ledger.register('new-user'), range(30)))
        changed = CreditLedger(self.store, welcome_units=900, policy_version='fixture-v2')
        self.assertEqual(changed.register('new-user')['available'],100)
        self.assertEqual(len([v for (c,k),v in self.store.data.items() if c=='ledger' and v['uid']=='new-user']),1)

    def test_parallel_reservations_cannot_overspend(self):
        def reserve(i):
            try:self.ledger.reserve('alice',str(i),'a'*64,30);return True
            except InsufficientCredits:return False
        with ThreadPoolExecutor(max_workers=12) as pool:results=list(pool.map(reserve,range(20)))
        self.assertEqual(sum(results),3)
        self.assertEqual(self.ledger.account('alice')['available'],10)
        self.assertEqual(self.ledger.account('alice')['reserved'],90)
        self.assertEqual(self.ledger.account('bob')['available'],100)

    def test_idempotent_request_and_settlement_match_exact_receipts(self):
        self.ledger.reserve('alice','one','a'*64,40)
        self.ledger.reserve('alice','one','a'*64,40)
        with self.assertRaises(Conflict):self.ledger.reserve('alice','one','b'*64,40)
        with self.assertRaises(Conflict):self.ledger.reserve('alice','one','a'*64,41)
        self.ledger.transition('alice','one','sent')
        self.ledger.settle('alice','one',17,'provider-receipt')
        self.ledger.settle('alice','one',17,'provider-receipt')
        with self.assertRaises(Conflict):self.ledger.settle('alice','one',18,'provider-receipt')
        account=self.ledger.account('alice')
        self.assertEqual((account['available'],account['reserved'],account['spent']),(83,0,17))

    def test_uncertain_work_never_refunds_or_replays_automatically(self):
        self.ledger.reserve('alice','one','a'*64,40);self.ledger.transition('alice','one','sent')
        self.ledger.transition('alice','one','uncertain')
        with self.assertRaises(Conflict):self.ledger.release_unsent('alice','one')
        self.assertEqual(self.ledger.reserve('alice','one','a'*64,40)['state'],'uncertain')
        restarted=CreditLedger(self.store,welcome_units=100,policy_version='fixture-v1')
        restarted.settle('alice','one',8,'verified-after-recovery')
        self.assertEqual(restarted.account('alice')['available'],92)

    def test_unsent_release_is_idempotent_and_cannot_settle(self):
        self.ledger.reserve('alice','one','a'*64,40)
        with self.assertRaises(Conflict):self.ledger.settle('alice','one',4,'unadmitted')
        self.ledger.release_unsent('alice','one');self.ledger.release_unsent('alice','one')
        with self.assertRaises(Conflict):self.ledger.transition('alice','one','sent')
        self.assertEqual(self.ledger.account('alice')['available'],100)

    def test_verified_usage_receipt_cannot_charge_another_operation_or_account(self):
        for uid,op in [('alice','one'),('alice','two'),('bob','one')]:
            self.ledger.reserve(uid,op,'a'*64,20);self.ledger.transition(uid,op,'sent')
        self.ledger.settle('alice','one',10,'receipt-once')
        for uid,op in [('alice','two'),('bob','one')]:
            with self.assertRaises(Conflict):self.ledger.settle(uid,op,10,'receipt-once')
        self.assertEqual(self.ledger.account('bob')['spent'],0)
        self.assertEqual(self.ledger.account('alice')['spent'],10)

    def test_verified_payment_global_receipt_cannot_mint_for_another_account(self):
        self.ledger.grant_purchase('alice','checkout-1',200,'c'*64)
        self.ledger.grant_purchase('alice','checkout-1',200,'c'*64)
        for uid,amount,fp in [('bob',200,'c'*64),('alice',201,'c'*64),('alice',200,'d'*64)]:
            with self.assertRaises(Conflict):self.ledger.grant_purchase(uid,'checkout-1',amount,fp)
        self.assertEqual(self.ledger.account('alice')['available'],300)
        self.assertEqual(self.ledger.account('bob')['available'],100)

    def test_refunds_are_cumulative_and_out_of_order_events_cannot_reverse_twice(self):
        self.ledger.grant_purchase('alice','checkout-1',200,'c'*64)
        self.ledger.refund_purchase('checkout-1',50,'refund-a')
        self.ledger.refund_purchase('checkout-1',50,'refund-a')
        self.ledger.refund_purchase('checkout-1',10,'older-refund')
        self.ledger.refund_purchase('checkout-1',200,'refund-b')
        self.assertEqual(self.ledger.account('alice')['available'],100)
        with self.assertRaises(Conflict):self.ledger.refund_purchase('checkout-1',201,'invalid')

    def test_spent_refunds_retain_debt_and_partial_topups_do_not_disappear(self):
        self.ledger.grant_purchase('alice','checkout-1',200,'c'*64)
        self.ledger.reserve('alice','one','a'*64,300);self.ledger.transition('alice','one','sent');self.ledger.settle('alice','one',300,'usage-1')
        self.ledger.refund_purchase('checkout-1',200,'refund-after-spend')
        self.assertEqual(self.ledger.account('alice')['available'],-200)
        self.ledger.grant_purchase('alice','checkout-2',50,'d'*64)
        self.assertEqual(self.ledger.account('alice')['available'],-150)
        with self.assertRaises(InsufficientCredits):self.ledger.reserve('alice','two','b'*64,1)

    def test_opaque_identifiers_cannot_collide_across_account_operation_pairs(self):
        self.ledger.register('x:y');self.ledger.register('x')
        self.ledger.reserve('x:y','z','a'*64,1);self.ledger.reserve('x','y:z','a'*64,1)
        self.assertNotEqual(self.ledger._operation_key('x:y','z'),self.ledger._operation_key('x','y:z'))

    def test_invalid_units_and_overflow_have_no_partial_writes(self):
        for bad in [True,1.5,-1,'1',MAX_UNITS+1]:
            with self.assertRaises(CreditError):self.ledger.reserve('alice','invalid','a'*64,bad)
        before=copy.deepcopy(self.store.data)
        with self.assertRaises(CreditError):self.ledger.grant_purchase('alice','too-much',MAX_UNITS,'c'*64)
        self.assertEqual(self.store.data,before)
        self.ledger.reserve('alice','one','a'*64,40);self.ledger.transition('alice','one','sent')
        before=copy.deepcopy(self.store.data)
        with self.assertRaises(Conflict):self.ledger.settle('alice','one',41,'excess')
        self.assertEqual(self.store.data,before)
