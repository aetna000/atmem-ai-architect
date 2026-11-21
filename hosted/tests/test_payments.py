import copy
import hashlib
import hmac
import json
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from hosted.configuration import BillingConfiguration
from hosted.credits import CreditLedger, CreditError, Conflict
from hosted.payments import CheckoutOrders, StripeCheckout, PaymentsUnavailable
from hosted.tests.test_credits import AtomicTestStore


class FakeStripe:
    """Explicit provider double. These tests make no Stripe acceptance claim."""
    live = False
    def __init__(self): self.sessions = {}; self.create_count = 0
    def create(self, order, return_url):
        self.create_count += 1
        sid = 'cs_test_' + order['id']
        self.sessions.setdefault(sid, dict(id=sid, livemode=False, mode='payment', currency='usd',
            amount_total=order['amountCents'], payment_status='unpaid',
            client_reference_id=order['id'], metadata={'architectOrder': order['id']},
            url='https://checkout.stripe.com/c/pay/' + sid,
            line_items={'has_more': False, 'data': [{'quantity': 1, 'amount_total': order['amountCents'],
                 'price': {'currency': 'usd', 'unit_amount': order['amountCents']}}]}))
        return copy.deepcopy(self.sessions[sid])
    def retrieve(self, sid): return copy.deepcopy(self.sessions[sid])
    def paid(self, sid, *, refunded=0):
        s = self.sessions[sid]
        s['payment_status'] = 'paid'
        s['payment_intent'] = dict(id='pi_' + sid, status='succeeded', amount_received=s['amount_total'],
            currency='usd', livemode=False, metadata=s['metadata'],
            latest_charge=dict(id='ch_' + sid, paid=True, payment_intent='pi_' + sid,
                amount=s['amount_total'], currency='usd', livemode=False, amount_refunded=refunded))


class PaymentTests(unittest.TestCase):
    def setUp(self):
        self.store = AtomicTestStore(); self.configuration = BillingConfiguration(self.store)
        self.ledger = CreditLedger(self.store, welcome_units=5_000_000, policy_version='test')
        self.ledger.register('alice'); self.ledger.register('bob')
        self.provider = FakeStripe()
        self.orders = CheckoutOrders(self.store, self.ledger, self.configuration, self.provider,
                                     return_url='https://atmem.ai/ai-architect/workspace/')

    def checkout(self, request='one', amount=137):
        order = self.orders.create('alice', request, amount)
        sid = 'cs_test_' + order['id']
        return order, sid

    def test_checkout_does_not_grant_and_replays_use_original_order(self):
        order, sid = self.checkout()
        self.assertEqual(self.orders.create('alice', 'one', 137), order)
        self.assertEqual(self.provider.create_count, 1)
        self.assertEqual(self.orders.fulfill(sid), {'state': 'awaiting_payment'})
        self.assertEqual(self.ledger.account('alice')['available'], 5_000_000)
        with self.assertRaises(Conflict): self.orders.create('alice', 'one', 138)
        for bad in [True, 99, 100.1]:
            with self.assertRaises(CreditError): self.orders.create('alice', 'bad', bad)

    def test_concurrent_fulfillment_grants_once_and_cannot_change_tenant(self):
        order, sid = self.checkout(); self.provider.paid(sid)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: self.orders.fulfill(sid), range(24)))
        self.assertEqual(self.ledger.account('alice')['available'], 6_370_000)
        self.assertEqual(self.ledger.account('bob')['available'], 5_000_000)
        self.assertEqual(len([x for (c,k),x in self.store.data.items() if c == 'payments']), 1)

    def test_mismatched_currency_amount_line_item_or_mode_cannot_mint(self):
        order, sid = self.checkout(); self.provider.paid(sid)
        original = copy.deepcopy(self.provider.sessions[sid])
        variants = [{'currency':'aud'}, {'amount_total':138}, {'livemode':True}, {'mode':'subscription'},
                    {'client_reference_id':'forged'}, {'line_items':{'has_more':True, 'data':[]}}]
        for patch in variants:
            self.provider.sessions[sid] = {**original, **patch}
            with self.assertRaises(Conflict): self.orders.fulfill(sid)
            self.assertEqual(self.ledger.account('alice')['available'], 5_000_000)
        self.provider.sessions[sid] = copy.deepcopy(original)
        self.provider.sessions[sid]['payment_intent']['latest_charge']['amount_refunded'] = 999
        with self.assertRaises(Conflict): self.orders.fulfill(sid)
        self.assertEqual(self.ledger.account('alice')['available'], 5_000_000)

    def test_crash_after_grant_recovers_without_second_grant(self):
        order, sid = self.checkout(); self.provider.paid(sid)
        original = self.orders._refund
        self.orders._refund = lambda *args: (_ for _ in ()).throw(RuntimeError('synthetic process failure'))
        with self.assertRaises(RuntimeError): self.orders.fulfill(sid)
        self.orders._refund = original
        self.orders.fulfill(sid)
        self.assertEqual(self.ledger.account('alice')['available'], 6_370_000)

    def test_refund_before_fulfillment_and_later_duplicate_do_not_restore_credits(self):
        order, sid = self.checkout(); self.provider.paid(sid, refunded=137)
        self.orders.fulfill(sid); self.orders.fulfill(sid)
        self.assertEqual(self.ledger.account('alice')['available'], 5_000_000)
        # Stale reads cannot lower the retained cumulative refunded amount.
        self.provider.paid(sid, refunded=37); self.orders.fulfill(sid)
        self.assertEqual(self.ledger.account('alice')['available'], 5_000_000)

    def test_timeout_before_ack_uses_provider_idempotency_and_old_attempt_never_recreated(self):
        original = self.provider.create
        def timeout(order, url):
            original(order, url)
            raise TimeoutError('synthetic lost response')
        self.provider.create = timeout
        with self.assertRaises(TimeoutError): self.checkout()
        self.provider.create = original
        self.checkout()
        self.assertEqual(len(self.provider.sessions), 1)
        with self.assertRaises(TimeoutError):
            self.provider.create = timeout; self.checkout('expired')
        self.provider.create = original
        self.orders.clock = lambda: time.time() + 24 * 3600
        with self.assertRaises(PaymentsUnavailable): self.checkout('expired')
        self.assertEqual(len(self.provider.sessions), 2)

    def test_paid_notification_can_arrive_before_creation_acknowledgement(self):
        original = self.provider.create
        def race(order, url):
            s = original(order, url); self.provider.paid(s['id'])
            self.orders.fulfill(s['id'])
            return s
        self.provider.create = race
        order, sid = self.checkout()
        self.assertEqual(order['state'], 'credited')
        self.assertEqual(self.ledger.account('alice')['available'], 6_370_000)

    def test_lost_checkout_response_keeps_original_branding_parameters_after_deployment(self):
        self.provider.parameters=lambda order,url:{'brand':'AtMem original','return':url}
        original=self.provider.create
        def timeout(order,url):
            original(order,url)
            raise TimeoutError('synthetic lost checkout response')
        self.provider.create=timeout
        with self.assertRaises(TimeoutError):self.checkout()
        seen=[]
        def retry(order,url):
            seen.append(order['checkoutParameters'])
            return original(order,url)
        self.provider.parameters=lambda order,url:{'brand':'New deployment','return':url}
        self.provider.create=retry
        self.checkout()
        self.assertEqual(seen[0]['brand'],'AtMem original')


    def test_webhook_sdk_verifies_exact_raw_body_timestamp_and_environment(self):
        adapter = StripeCheckout('sk_test_not_real', 'whsec_synthetic')
        def signed(body, timestamp=None):
            t = int(time.time()) if timestamp is None else timestamp
            signature = hmac.new(b'whsec_synthetic', str(t).encode() + b'.' + body, hashlib.sha256).hexdigest()
            return f't={t},v1={signature}'
        raw = json.dumps({'id':'evt_fixture', 'type':'checkout.session.completed',
                          'livemode':False, 'data':{'object':{'id':'cs_test_fixture'}}}).encode()
        signature = signed(raw)
        self.assertEqual(adapter.verify_event(raw, signature)['id'], 'evt_fixture')
        for body, sig in [(raw + b' ', signature), (raw, signed(raw, int(time.time())-301)), (raw,'v1=forged')]:
            with self.assertRaises(CreditError): adapter.verify_event(body,sig)
        live = raw.replace(b'false', b'true')
        with self.assertRaises(CreditError): adapter.verify_event(live,signed(live))

    def test_unrelated_account_notifications_are_ignored_without_credit_mutations(self):
        self.provider.verify_event=lambda raw,sig:json.loads(raw)
        before=copy.deepcopy(self.store.data)
        result=self.orders.event(json.dumps({'type':'checkout.session.completed','data':{'object':{'id':'cs_other','metadata':{}}}}).encode(),'fixture')
        self.assertEqual(result,{'state':'ignored'})
        self.provider.charge=lambda cid:{'id':cid,'payment_intent':'pi_other'}
        self.provider.intent=lambda pid:{'id':pid,'metadata':{}}
        result=self.orders.event(json.dumps({'type':'charge.refunded','data':{'object':{'id':'ch_other'}}}).encode(),'fixture')
        self.assertEqual(result,{'state':'ignored'})
        self.assertEqual(self.store.data,before)

    def test_signed_own_checkout_notification_still_fulfills_once(self):
        order,sid=self.checkout();self.provider.paid(sid)
        adapter=StripeCheckout('sk_test_not_real','whsec_synthetic')
        adapter.retrieve=self.provider.retrieve
        self.orders.provider=adapter
        raw=json.dumps({'id':'evt_fixture','type':'checkout.session.completed','livemode':False,
                        'data':{'object':{'id':sid,'metadata':{'architectOrder':order['id']}}}}).encode()
        now=int(time.time())
        signature=hmac.new(b'whsec_synthetic',str(now).encode()+b'.'+raw,hashlib.sha256).hexdigest()
        for _ in range(2):self.assertEqual(self.orders.event(raw,f't={now},v1={signature}'),{'state':'credited'})
        self.assertEqual(self.ledger.account('alice')['available'],6_370_000)
