"""Server-owned Checkout orders and replay-safe fulfillment.

Provider calls never run inside a retryable database transaction. Durable intent
precedes Checkout creation. Payment grants and order acknowledgements can recover
independently after a crash because the ledger binds each provider receipt once.
"""
import hashlib
import json
import time
from urllib.parse import urlsplit

from .credits import CreditError, Conflict, digest, identifier


class PaymentsUnavailable(RuntimeError): pass


def _stripe_id(value, prefix):
    identifier(value)
    if not value.startswith(prefix) or not all(c.isascii() and (c.isalnum() or c == '_') for c in value):
        raise CreditError('Invalid payment reference')
    return value


class StripeCheckout:
    """Fixed Stripe endpoint, pinned SDK/API and explicit test/live separation."""
    def __init__(self, api_key, webhook_secret, *, live=False, icon=None):
        import stripe
        if not api_key or not api_key.startswith('sk_live_' if live else 'sk_test_') or not webhook_secret.startswith('whsec_'):
            raise ValueError('Configure matching Stripe credentials securely')
        self.live, self.webhook_secret = live, webhook_secret
        self.branding = {'display_name':'AtMem AI Architect', 'background_color':'#FCECF0',
                         'button_color':'#873B50', 'border_style':'rounded'}
        if icon is not None:
            if not isinstance(icon, dict) or set(icon) != {'type','file'} or icon.get('type') != 'file':
                raise ValueError('Use a server-configured Stripe branding file')
            identifier(icon['file'])
            self.branding['icon'] = icon.copy()
        self.client = stripe.StripeClient(api_key, stripe_version='2026-10-28.endive', max_network_retries=2,
                                          http_client=stripe.RequestsClient(timeout=20))

    @staticmethod
    def _call(method, *args, **kwargs):
        import stripe
        try: return method(*args, **kwargs).to_dict()
        except stripe.StripeError as error:
            raise PaymentsUnavailable('Stripe is temporarily unavailable. Retry the same purchase attempt') from error

    def parameters(self, order, return_url):
        # Persist the exact non-secret request before sending. A branding/policy
        # deployment must not change parameters under an existing idempotency key.
        return {
            'mode': 'payment', 'allowed_payment_method_types': ['card'],
            'branding_settings':self.branding,
            'custom_text':{'submit':{'message':'[Terms](https://atmem.ai/terms) · [Privacy](https://atmem.ai/ai-architect/privacy/)'}},
            'client_reference_id': order['id'], 'metadata': {'architectOrder': order['id']},
            'payment_intent_data': {'metadata': {'architectOrder': order['id']}},
            'line_items': [{'quantity': 1, 'price_data': {'currency': 'usd',
                'unit_amount': order['amountCents'], 'product_data': {'name': 'AtMem AI Architect credits'}}}],
            'success_url': return_url + '?checkout=complete', 'cancel_url': return_url + '?checkout=cancelled',
        }

    def create(self, order, return_url):
        return self._call(self.client.v1.checkout.sessions.create, order['checkoutParameters'],
                          options={'idempotency_key': 'architect-checkout-' + order['id']})

    def retrieve(self, session_id):
        return self._call(self.client.v1.checkout.sessions.retrieve, _stripe_id(session_id, 'cs_'),
                    {'expand': ['line_items', 'payment_intent.latest_charge']})

    def charge(self, charge_id):
        return self._call(self.client.v1.charges.retrieve, _stripe_id(charge_id, 'ch_'))

    def intent(self, payment_id):
        return self._call(self.client.v1.payment_intents.retrieve, _stripe_id(payment_id, 'pi_'))

    def verify_event(self, raw, signature):
        import stripe
        if not isinstance(raw, bytes) or len(raw) > 1_048_576:
            raise CreditError('Invalid payment notification')
        try:
            event = stripe.Webhook.construct_event(raw, signature, self.webhook_secret, tolerance=300).to_dict()
        except (ValueError, stripe.SignatureVerificationError) as error:
            raise CreditError('Invalid payment notification') from error
        if event.get('livemode') is not self.live or event.get('account'):
            raise CreditError('Payment notification belongs to another environment')
        return event


class CheckoutOrders:
    def __init__(self, store, ledger, configuration, provider, *, return_url, clock=time.time):
        parts = urlsplit(return_url)
        if parts.scheme != 'https' or not parts.netloc or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError('Use a fixed HTTPS checkout return URL')
        self.store, self.ledger, self.configuration, self.provider = store, ledger, configuration, provider
        self.return_url, self.clock = return_url, clock

    def create(self, uid, request_id, amount_cents):
        identifier(uid); identifier(request_id)
        if type(amount_cents) is not int:
            raise CreditError('Use an integer number of USD cents')
        key = hashlib.sha256((uid + '\0' + request_id).encode()).hexdigest()
        # Existing attempts keep their original policy snapshot even after an admin edit.
        existing = self.store.transaction(lambda tx: tx.get('orders', key))
        quote = None if existing else self.configuration.purchase_quote(amount_cents)
        def prepare(tx):
            _, account = self.ledger._account(tx, uid)
            previous = tx.get('orders', key)
            if previous:
                if previous['uid'] != uid or previous['amountCents'] != amount_cents:
                    raise Conflict('Checkout request already has a different amount')
                return previous
            if account['disabled']:
                raise CreditError('Account is unavailable')
            order = dict(id=key, uid=uid, requestId=request_id, state='prepared', createdAt=self.clock(),
                         live=self.provider.live, **quote)
            if hasattr(self.provider, 'parameters'):
                order['checkoutParameters'] = self.provider.parameters(order, self.return_url)
            tx.create('orders', key, order)
            return order
        order = self.store.transaction(prepare)
        if order.get('sessionId'):
            return self.public(order)
        # Stripe may prune idempotency records after 24h. Never blindly recreate
        # an ambiguous old payment attempt after that window.
        if self.clock() - order['createdAt'] >= 23 * 3600:
            raise PaymentsUnavailable('Checkout needs reconciliation. Start a new purchase attempt')
        session = self.provider.create(order, self.return_url)
        session_id = _stripe_id(session.get('id'), 'cs_')
        url = session.get('url', '')
        parts = urlsplit(url)
        if parts.scheme != 'https' or parts.netloc != 'checkout.stripe.com' or session.get('livemode') is not order['live']:
            raise PaymentsUnavailable('Payment provider returned an invalid checkout')
        def acknowledge(tx):
            record = tx.get('orders', key)
            if record.get('sessionId') and record['sessionId'] != session_id:
                raise Conflict('Checkout session changed unexpectedly')
            record.update(sessionId=session_id, url=url)
            if record['state'] == 'prepared': record['state'] = 'checkout'
            tx.set('orders', key, record)
            return record
        return self.public(self.store.transaction(acknowledge))

    @staticmethod
    def public(order):
        return {k: order[k] for k in ['id', 'state', 'amountCents', 'currency', 'creditMicros', 'url'] if k in order}

    def fulfill(self, session_id):
        # Always retrieve authoritative provider state; event/redirect metadata
        # alone can never mint a credit.
        session = self.provider.retrieve(session_id)
        key = session.get('metadata', {}).get('architectOrder')
        if type(key) is not str or len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
            raise Conflict('Payment has no matching order')
        order = self.store.transaction(lambda tx: tx.get('orders', key))
        if not order: raise Conflict('Payment has no matching order')
        if (session.get('id') != session_id or session.get('client_reference_id') != key
                or session.get('livemode') is not order['live'] or order['live'] is not self.provider.live
                or session.get('mode') != 'payment' or session.get('currency') != 'usd'
                or type(session.get('amount_total')) is not int or session['amount_total'] != order['amountCents']
                or order.get('sessionId', session_id) != session_id):
            raise Conflict('Payment does not match its retained order')
        if session.get('payment_status') != 'paid': return {'state': 'awaiting_payment'}
        items = session.get('line_items', {})
        rows = items.get('data', [])
        if (items.get('has_more') is not False or len(rows) != 1 or rows[0].get('quantity') != 1
                or rows[0].get('amount_total') != order['amountCents']
                or rows[0].get('price', {}).get('unit_amount') != order['amountCents']
                or rows[0].get('price', {}).get('currency') != 'usd'):
            raise Conflict('Payment items do not match the credit purchase')
        intent = session.get('payment_intent')
        if not isinstance(intent, dict) or intent.get('status') != 'succeeded':
            raise Conflict('Payment has no successful payment intent')
        payment = _stripe_id(intent.get('id'), 'pi_')
        if (intent.get('metadata', {}).get('architectOrder') != key or intent.get('currency') != 'usd'
                or intent.get('amount_received') != order['amountCents'] or intent.get('livemode') is not order['live']):
            raise Conflict('Payment receipt does not match the credit purchase')
        charge = intent.get('latest_charge')
        if not isinstance(charge, dict) or charge.get('paid') is not True or charge.get('payment_intent') != payment:
            raise Conflict('Payment has no verified paid charge')
        self._validate_charge(charge, order)
        receipt = 'stripe-' + payment
        def bind(tx):
            record = tx.get('orders', key)
            index = tx.get('payment_orders', digest(receipt))
            if index and index['orderId'] != key: raise Conflict('Payment belongs to another order')
            if record.get('sessionId', session_id) != session_id: raise Conflict('Checkout session changed unexpectedly')
            if index and record.get('sessionId') == session_id and record.get('paymentId') == payment:
                return  # Replayed notifications do not rewrite shared order records.
            record.update(sessionId=session_id, paymentId=payment)
            tx.set('orders', key, record)
            if not index: tx.create('payment_orders', digest(receipt), dict(orderId=key, sessionId=session_id))
        self.store.transaction(bind)
        fp = hashlib.sha256(json.dumps([key, payment, session_id, order['uid'], order['amountCents'],
                                       order['creditMicros'], order['live']], separators=(',', ':')).encode()).hexdigest()
        self.ledger.grant_purchase(order['uid'], receipt, order['creditMicros'], fp)
        # Handle refunds that preceded fulfillment using the latest paid charge.
        self._refund(charge, order, receipt)
        def complete(tx):
            record = tx.get('orders', key)
            if record['state'] == 'credited': return
            record.update(state='credited', creditedAt=self.clock())
            tx.set('orders', key, record)
        self.store.transaction(complete)
        return {'state': 'credited'}

    def _refund(self, charge, order, receipt):
        refunded = self._validate_charge(charge, order)
        if refunded:
            self.ledger.refund_purchase(receipt, refunded * 10_000, _stripe_id(charge.get('id'), 'ch_'))

    @staticmethod
    def _validate_charge(charge, order):
        _stripe_id(charge.get('id'), 'ch_')
        if (charge.get('currency') != 'usd' or charge.get('amount') != order['amountCents']
                or charge.get('livemode') is not order['live']):
            raise Conflict('Refund receipt does not match its payment')
        refunded = charge.get('amount_refunded')
        if type(refunded) is not int or not 0 <= refunded <= order['amountCents']:
            raise Conflict('Invalid cumulative refund amount')
        return refunded

    def event(self, raw, signature):
        event = self.provider.verify_event(raw, signature)
        kind = event.get('type')
        obj = event.get('data', {}).get('object', {})
        if kind in {'checkout.session.completed', 'checkout.session.async_payment_succeeded'}:
            if not obj.get('metadata', {}).get('architectOrder'):
                return {'state':'ignored'}
            return self.fulfill(_stripe_id(obj.get('id'), 'cs_'))
        if kind == 'charge.refunded':
            charge = self.provider.charge(_stripe_id(obj.get('id'), 'ch_'))
            payment = _stripe_id(charge.get('payment_intent'), 'pi_')
            index = self.store.transaction(lambda tx: tx.get('payment_orders', digest('stripe-' + payment)))
            if not index:
                intent = self.provider.intent(payment)
                if not intent.get('metadata', {}).get('architectOrder'):
                    return {'state':'ignored'}
                raise PaymentsUnavailable('Payment fulfillment is pending; retry the refund notification')
            self.fulfill(index['sessionId'])
            order = self.store.transaction(lambda tx: tx.get('orders', index['orderId']))
            self._refund(charge, order, 'stripe-' + payment)
            return {'state': 'reconciled'}
        return {'state': 'ignored'}
