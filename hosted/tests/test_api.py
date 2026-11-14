import unittest
import httpx

from hosted.api import create_app, Services
from hosted.auth import Identity, Unauthorized
from hosted.credits import CreditLedger
from hosted.configuration import BillingConfiguration
from hosted.payments import CheckoutOrders
from hosted.credentials import CredentialVault
from hosted.tests.test_credits import AtomicTestStore
from hosted.tests.test_payments import FakeStripe


class VerifiedIdentityFixture:
    """Explicit API fixture; does not bypass or qualify real Firebase verification."""
    def verify(self, token):
        identities = {'Bearer alice':Identity('alice','alice@example.test','google.com',True),
                      'Bearer bob':Identity('bob','bob@example.test','google.com',True),
                      'Bearer owner':Identity('owner','taghia.javad@gmail.com','google.com',True)}
        if token not in identities: raise Unauthorized('Sign in with Google')
        return identities[token]


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store=AtomicTestStore(); self.provider=FakeStripe()
        self.ledger=CreditLedger(self.store,welcome_units=5_000_000,policy_version='fixture')
        self.orders=CheckoutOrders(self.store,self.ledger,BillingConfiguration(self.store),self.provider,
                                   return_url='https://atmem.ai/ai-architect/workspace/')
        self.vault=CredentialVault(self.store,self.ledger,keyring={'v1':b'a'*32},active_key='v1')
        self.app=create_app(Services(self.store,VerifiedIdentityFixture(),self.orders,vault=self.vault))
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='https://atmem.ai')
        self.prefix='/api/ai-architect'

    async def asyncTearDown(self): await self.client.aclose()

    async def request(self, method, path, user='alice', **kwargs):
        return await self.client.request(method,self.prefix+path,headers={'Authorization':'Bearer '+user},**kwargs)

    async def test_authentication_registration_and_no_other_user_balance(self):
        self.assertEqual((await self.client.post(self.prefix+'/account')).status_code,401)
        self.assertEqual(len(self.store.data),0)
        for user in ['alice','bob']:
            result=await self.request('POST','/account',user)
            self.assertEqual(result.status_code,200)
            self.assertEqual(result.json()['balanceMicros'],5_000_000)
            self.assertEqual(result.headers['cache-control'],'no-store')
        self.ledger.reserve('alice','one','a'*64,400)
        bob=await self.request('GET','/balance?uid=alice','bob')
        self.assertEqual(bob.json()['balanceMicros'],5_000_000)
        repeated=await self.request('POST','/account')
        self.assertEqual(repeated.json()['balanceMicros'],4_999_600)
        self.assertFalse(repeated.json()['admin'])

    async def test_admin_is_server_enforced_and_configuration_updates_are_versioned(self):
        for method,kwargs in [('GET',{}),('PATCH',{'json':{'revision':1,'changes':{'welcomeMicros':1}}})]:
            self.assertEqual((await self.request(method,'/admin/billing',**kwargs)).status_code,403)
        result=await self.request('PATCH','/admin/billing','owner',json={'revision':1,'changes':{'welcomeMicros':6_000_000}})
        self.assertEqual(result.status_code,200)
        self.assertEqual((await self.request('POST','/account')).json()['balanceMicros'],6_000_000)
        stale=await self.request('PATCH','/admin/billing','owner',json={'revision':1,'changes':{'welcomeMicros':1}})
        self.assertEqual(stale.status_code,409)

    async def test_checkout_amount_and_uid_cannot_be_forged_and_click_does_not_grant(self):
        await self.request('POST','/account')
        for body in [{'requestId':'one','amountCents':True},{'requestId':'one','amountCents':100,'uid':'bob'},
                     {'requestId':'one','amountCents':100,'creditMicros':99999999}]:
            self.assertEqual((await self.request('POST','/checkout',json=body)).status_code,422)
        result=await self.request('POST','/checkout',json={'requestId':'one','amountCents':137})
        self.assertEqual(result.status_code,200)
        self.assertEqual(self.ledger.account('alice')['available'],5_000_000)
        self.assertTrue(result.json()['url'].startswith('https://checkout.stripe.com/'))

    async def test_oversized_json_and_chunked_body_rejected_before_parsing(self):
        result=await self.request('POST','/checkout',content=b'X'*1_048_577)
        self.assertEqual(result.status_code,413)
        async def chunks():
            for _ in range(5): yield b'x'*300_000
        result=await self.request('POST','/checkout',content=chunks())
        self.assertEqual(result.status_code,413)
        self.assertEqual(self.provider.create_count,0)

    async def test_shared_per_uid_checkout_rate_limit_and_no_local_session_backdoor(self):
        await self.request('POST','/account')
        for n in range(5):
            self.assertEqual((await self.request('POST','/checkout',json={'requestId':str(n),'amountCents':100})).status_code,200)
        limited=await self.request('POST','/checkout',json={'requestId':'six','amountCents':100})
        self.assertEqual(limited.status_code,429)
        self.assertEqual(limited.headers['retry-after'],'60')
        self.assertEqual((await self.client.get('/api/session')).status_code,404)
        self.assertEqual((await self.request('POST','/credits/grant',json={'amount':999})).status_code,404)

    async def test_provider_key_responses_and_validation_never_echo_plaintext(self):
        for user in ['alice','bob']: await self.request('POST','/account',user)
        secret='sk-test-fixture-sensitive-key-value'
        for body in [{'apiKey':secret,'revision':'invalid'},{'apiKey':secret,'revision':0,'uid':'bob'}]:
            response=await self.request('PUT','/providers/openai',json=body)
            self.assertEqual(response.status_code,422)
            self.assertNotIn(secret,response.text)
        saved=await self.request('PUT','/providers/openai',json={'apiKey':secret,'revision':0})
        self.assertEqual(saved.status_code,200)
        self.assertNotIn(secret,saved.text)
        status=await self.request('GET','/providers','bob')
        self.assertFalse(status.json()['openai']['configured'])
        self.assertEqual(self.vault.for_broker('alice','openai'),secret)

    async def test_test_payments_cannot_be_configured_against_production_wallets(self):
        from unittest.mock import patch
        from hosted.api import configured_app
        with patch.dict('os.environ',{'ARCHITECT_GOOGLE_PROJECT':'demo-fixture',
                   'ARCHITECT_DATA_ENVIRONMENT':'production','ARCHITECT_STRIPE_MODE':'test'}):
            with self.assertRaisesRegex(ValueError,'isolated data environment'):configured_app()
