"""Hosted control plane. Local CLI/session endpoints are deliberately absent.

Run with ``uvicorn hosted.api:configured_app --factory`` after supplying explicit
project/database/payment configuration. No production in-memory fallback exists.
"""
import os
import time
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr
from starlette.concurrency import run_in_threadpool

from .auth import FirebaseIdentity, Unauthorized, Forbidden, AuthenticationUnavailable
from .configuration import BillingConfiguration
from .credits import CreditError, Conflict, InsufficientCredits, AccountUnavailable, CreditLedger, digest
from .firestore_store import FirestoreTransactions
from .payments import CheckoutOrders, StripeCheckout, PaymentsUnavailable
from .credentials import CredentialVault, CredentialsUnavailable, PROVIDERS

PREFIX = '/api/ai-architect'


class StrictBody(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class CheckoutBody(StrictBody):
    requestId: StrictStr = Field(min_length=1, max_length=128)
    amountCents: StrictInt = Field(ge=100, le=99_999_999)


class PolicyBody(StrictBody):
    revision: StrictInt = Field(ge=1)
    changes: dict[str, Any]


class CredentialBody(StrictBody):
    apiKey: StrictStr = Field(min_length=20, max_length=512, repr=False)
    revision: StrictInt = Field(ge=0)


class RemoveCredentialBody(StrictBody):
    revision: StrictInt = Field(ge=0)


class BodyLimit:
    def __init__(self, app, limit=1_048_576): self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http': return await self.app(scope, receive, send)
        # Buffer only up to the explicit bound, including chunked requests. This
        # precedes JSON parsing and raw Stripe signature verification.
        messages = []; total = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect': return
            total += len(message.get('body', b''))
            if total > self.limit:
                return await JSONResponse({'detail':'Request too large'}, status_code=413)(scope, receive, send)
            messages.append(message)
            if not message.get('more_body'): break
        position = 0
        async def replay():
            nonlocal position
            if position < len(messages):
                value = messages[position]; position += 1; return value
            return await receive()
        async def secure_send(message):
            if message['type'] == 'http.response.start':
                message['headers'] = list(message.get('headers', [])) + [
                    (b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff')]
            await send(message)
        await self.app(scope, replay, secure_send)


class RateExceeded(ValueError): pass


class AccountRateLimit:
    """Shared per-UID fixed-window admission; frontend/IP headers cannot choose UID."""
    def __init__(self, store, *, clock=time.time): self.store, self.clock = store, clock

    def admit(self, uid, action, maximum):
        window = int(self.clock()) // 60
        key = digest(uid) + '-' + action
        def apply(tx):
            record = tx.get('rate_limits', key) or {'window': window, 'count': 0}
            count = record['count'] if record['window'] == window else 0
            if count >= maximum: raise RateExceeded('Too many requests. Try again shortly')
            tx.set('rate_limits', key, {'window': window, 'count': count + 1})
        self.store.transaction(apply)


@dataclass
class Services:
    store: Any
    identity: Any
    payments: Any = None
    test_payments: bool = True
    vault: Any = None


def create_app(services):
    app = FastAPI(title='AtMem AI Architect', docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(BodyLimit)
    configuration = BillingConfiguration(services.store)
    rate = AccountRateLimit(services.store)

    def ledger():
        policy = configuration.current()
        return CreditLedger(services.store, welcome_units=policy['welcomeMicros'],
                            policy_version='billing-' + str(policy['revision']))

    async def signed_in(authorization, action='account', maximum=60):
        identity = await run_in_threadpool(services.identity.verify, authorization)
        await run_in_threadpool(rate.admit, identity.uid, action, maximum)
        return identity

    errors = [(Unauthorized,401),(Forbidden,403),(AuthenticationUnavailable,503),(RateExceeded,429),
              (Conflict,409),(InsufficientCredits,402),(AccountUnavailable,403),(CreditError,400),
              (PaymentsUnavailable,503),(CredentialsUnavailable,503)]
    for error, status in errors:
        async def handler(request, exc, status=status):
            return JSONResponse({'detail': str(exc)}, status_code=status,
                                headers={'Retry-After':'60'} if status == 429 else None)
        app.add_exception_handler(error, handler)

    @app.exception_handler(RequestValidationError)
    async def invalid_body(request, error):
        # Pydantic's default error includes submitted values, including API keys.
        return JSONResponse({'detail':'Check the submitted fields'}, status_code=422)

    @app.get(PREFIX + '/health')
    def health(): return {'service':'AtMem AI Architect', 'status':'ok'}

    @app.post(PREFIX + '/account')
    async def register(authorization: str | None = Header(default=None)):
        identity = await signed_in(authorization, 'register', 10)
        account = await run_in_threadpool(lambda: ledger().register(identity.uid))
        policy = await run_in_threadpool(configuration.current)
        return {'balanceMicros': account['available'], 'reservedMicros': account['reserved'],
                'currency':'usd', 'admin':identity.admin, 'email':identity.email,
                'minimumPurchaseCents':policy['minimumPurchaseCents'],
                'maximumPurchaseCents':policy['maximumPurchaseCents'],
                'paymentsAvailable':services.payments is not None,
                'testPayments':services.test_payments,
                'platformSpendingEnabled':policy['platformSpendingEnabled']}

    @app.get(PREFIX + '/balance')
    async def balance(authorization: str | None = Header(default=None)):
        identity = await signed_in(authorization)
        account = await run_in_threadpool(lambda: ledger().account(identity.uid))
        return {'balanceMicros':account['available'], 'reservedMicros':account['reserved'], 'currency':'usd'}

    @app.get(PREFIX + '/admin/billing')
    async def admin_billing(authorization: str | None = Header(default=None)):
        identity = await signed_in(authorization)
        identity.require_admin()
        return await run_in_threadpool(configuration.current)

    @app.patch(PREFIX + '/admin/billing')
    async def update_billing(body: PolicyBody, authorization: str | None = Header(default=None)):
        identity = await signed_in(authorization, 'admin', 10)
        return await run_in_threadpool(configuration.update, identity, body.revision, body.changes)

    @app.post(PREFIX + '/checkout')
    async def checkout(body: CheckoutBody, authorization: str | None = Header(default=None)):
        identity = await signed_in(authorization, 'checkout', 5)
        if services.payments is None: raise PaymentsUnavailable('Payments are not configured yet')
        return await run_in_threadpool(services.payments.create, identity.uid, body.requestId, body.amountCents)

    @app.post(PREFIX + '/stripe/webhook')
    async def webhook(request: Request, stripe_signature: str | None = Header(default=None)):
        if services.payments is None: raise PaymentsUnavailable('Payments are not configured yet')
        raw = await request.body()
        # No client-auth bypass for account/admin APIs: only this route uses the
        # provider's independently verified raw-body signature instead of Firebase.
        return await run_in_threadpool(services.payments.event, raw, stripe_signature)

    @app.get(PREFIX + '/providers')
    async def providers(authorization: str | None = Header(default=None)):
        identity = await signed_in(authorization)
        if services.vault is None: raise CredentialsUnavailable('Provider key storage is not configured yet')
        return await run_in_threadpool(lambda: {provider:services.vault.status(identity.uid, provider)
                                                for provider in sorted(PROVIDERS)})

    @app.put(PREFIX + '/providers/{provider}')
    async def save_provider(provider: str, body: CredentialBody, authorization: str | None = Header(default=None)):
        identity = await signed_in(authorization, 'credentials', 10)
        if services.vault is None: raise CredentialsUnavailable('Provider key storage is not configured yet')
        return await run_in_threadpool(services.vault.update, identity.uid, provider, body.apiKey, body.revision)

    @app.delete(PREFIX + '/providers/{provider}')
    async def remove_provider(provider: str, body: RemoveCredentialBody, authorization: str | None = Header(default=None)):
        identity = await signed_in(authorization, 'credentials', 10)
        if services.vault is None: raise CredentialsUnavailable('Provider key storage is not configured yet')
        return await run_in_threadpool(services.vault.remove, identity.uid, provider, body.revision)

    return app


def configured_app():
    project = os.environ['ARCHITECT_GOOGLE_PROJECT']
    environment = os.environ['ARCHITECT_DATA_ENVIRONMENT']
    if environment not in {'sandbox','production'}: raise ValueError('Choose an explicit data environment')
    mode = os.environ.get('ARCHITECT_STRIPE_MODE', 'disabled')
    if mode not in {'disabled','test','live'}: raise ValueError('Choose explicit Stripe mode')
    if mode == 'test' and environment != 'sandbox' or mode == 'live' and environment != 'production':
        raise ValueError('Stripe mode must match the isolated data environment')
    base_store = FirestoreTransactions.configured(project, os.environ['ARCHITECT_FIRESTORE_DATABASE'])
    store = FirestoreTransactions(base_store.client, namespace='architect_sandbox' if environment == 'sandbox' else 'architect')
    identity = FirebaseIdentity(project)
    config = BillingConfiguration(store)
    policy = config.current()
    ledger = CreditLedger(store, welcome_units=policy['welcomeMicros'], policy_version='billing-' + str(policy['revision']))
    payments = None
    if mode != 'disabled':
        icon = {'type':'file','file':os.environ['ARCHITECT_STRIPE_ICON_FILE']}
        provider = StripeCheckout(os.environ['STRIPE_SECRET_KEY'], os.environ['STRIPE_WEBHOOK_SECRET'], live=mode == 'live', icon=icon)
        payments = CheckoutOrders(store, ledger, config, provider, return_url=os.environ['ARCHITECT_CHECKOUT_RETURN_URL'])
    vault = CredentialVault.configured(store, ledger) if os.environ.get('ARCHITECT_BYOK_KEYRING') else None
    return create_app(Services(store, identity, payments, mode != 'live', vault))
