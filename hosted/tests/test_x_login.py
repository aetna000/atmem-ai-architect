"""OAuth boundary tests: actual HTTP adapter, explicit upstream/identity fixtures."""
import asyncio
import os
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
import httpx
from hosted.auth import Unauthorized, Forbidden, AuthenticationUnavailable
from hosted.sqlite_store import SQLiteTransactions
from hosted.x_access import XIdentity, XWhitelist
from hosted.x_login import XLogin, FirebaseXTokenIssuer, SCOPES, CALLBACK, ORIGIN, challenge
from hosted.pilot_api import PilotServices, create_pilot_app


class XLoginTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=SQLiteTransactions(Path(self.temp.name)/'login.sqlite')
        self.access=XWhitelist(self.store,admin_ids=['1'],initial_ids=['2'])
        self.now=1000.;self.calls=[];self.issued=[];self.subject='2';self.status=200;self.scopes=' '.join(SCOPES)
        self.revoke_status=200
        def request(req):
            self.calls.append(req)
            if req.url.path.endswith('/token'):
                return httpx.Response(200,json={'access_token':'private-upstream-token','token_type':'bearer','scope':self.scopes})
            if req.url.path.endswith('/revoke'):return httpx.Response(self.revoke_status,json={'revoked':True})
            return httpx.Response(self.status,json={'data':{'id':self.subject,'name':'Alice'}})
        def issue(subject,name):self.issued.append((subject,name));return 'firebase-custom-token'
        self.login=XLogin(self.store,self.access,{'clientId':'client','clientSecret':'private-client-secret'},
            SimpleNamespace(issue=issue),clock=lambda:self.now,client=httpx.Client(transport=httpx.MockTransport(request)))
        self.verifier='a'*43

    def start(self):return self.login.start(challenge(self.verifier))
    def finish(self,state=None,verifier=None):return self.login.finish(state or self.start()['state'],'one-time-code',verifier or self.verifier)

    def test_only_documented_scopes_s256_fixed_callback_and_no_upstream_call_on_start(self):
        start=self.start();url=urlparse(start['authorizationUrl']);query=parse_qs(url.query)
        self.assertEqual(url.netloc,'x.com');self.assertEqual(query['scope'],['users.read tweet.read'])
        self.assertEqual(query['redirect_uri'],[CALLBACK]);self.assertEqual(query['code_challenge_method'],['S256'])
        self.assertEqual(query['code_challenge'],[challenge(self.verifier)]);self.assertEqual(self.calls,[])

    def test_exchange_fetches_only_me_revokes_before_mint_and_is_single_use(self):
        start=self.start();result=self.finish(start['state'])
        self.assertEqual(result,{'firebaseToken':'firebase-custom-token'})
        self.assertEqual([r.url.path for r in self.calls],['/2/oauth2/token','/2/users/me','/2/oauth2/revoke'])
        self.assertEqual(self.calls[1].url.query,b'');self.assertEqual(self.issued,[('2','Alice')])
        self.assertEqual(parse_qs(self.calls[-1].content.decode())['token_type_hint'],['access_token'])
        self.assertNotIn('private-upstream-token',str(result))
        with self.assertRaises(Unauthorized):self.finish(start['state'])
        self.assertEqual(len(self.calls),3)

    def test_mismatched_state_verifier_and_expiry_rejected_before_network(self):
        state=self.start()['state']
        for wrong,verifier in [(state,'b'*43),(state[:-1]+'!',self.verifier),('999.'+'a'*43,self.verifier)]:
            with self.assertRaises(Unauthorized):self.finish(wrong,verifier)
        self.now+=301
        with self.assertRaises(Unauthorized):self.finish(state)
        self.assertEqual(self.calls,[])

    def test_outsider_gets_no_session_and_upstream_permission_is_revoked(self):
        self.subject='3'
        with self.assertRaises(Forbidden):self.finish()
        self.assertEqual(self.issued,[]);self.assertTrue(self.calls[-1].url.path.endswith('/revoke'))

    def test_unexpected_scope_payment_failure_and_cleanup_failure_never_mint(self):
        self.scopes+=' follows.read'
        with self.assertRaises(AuthenticationUnavailable):self.finish()
        self.assertEqual([r.url.path for r in self.calls],['/2/oauth2/token','/2/oauth2/revoke'])
        self.scopes=' '.join(SCOPES);self.status=402
        with self.assertRaisesRegex(AuthenticationUnavailable,'operator API access'):self.finish()
        self.status=200;self.revoke_status=503
        with self.assertRaisesRegex(AuthenticationUnavailable,'cleanup'):self.finish()
        self.assertEqual(self.issued,[])

    def test_pending_records_bounded_and_reusable_after_expiry(self):
        for _ in range(300):self.start();self.now+=301
        count=self.store.transaction(lambda tx:tx.connection.execute("SELECT count(*) FROM records WHERE collection='x_login'").fetchone()[0])
        self.assertLessEqual(count,256)

    @unittest.skipUnless(os.environ.get('FIRESTORE_EMULATOR_HOST'),'Real local Firestore emulator required')
    def test_firestore_pending_state_is_single_use_across_concurrent_consumers(self):
        from hosted.firestore_store import FirestoreTransactions
        from google.cloud import firestore
        client=firestore.Client(project='demo-architect-hosted',database='(default)')
        self.login.store=FirestoreTransactions(client,namespace='x_login_test_'+uuid.uuid4().hex[:12])
        state=self.start()['state']
        def consume(_):
            try:self.finish(state);return 'accepted'
            except Unauthorized:return 'rejected'
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(consume,range(2))),['accepted','rejected'])
        self.assertEqual(len(self.issued),1)

    def test_custom_claims_preserve_subject_without_trusting_handles_or_other_providers(self):
        claims={'uid':'architect-x-2','architect_x_login':'oauth2-v1','architect_x_id':'2',
                'firebase':{'sign_in_provider':'custom','identities':{}},'admin':True,'handle':'AtMemAi'}
        actor=XIdentity.from_verified_claims(claims);self.assertEqual(actor.uid,'2');self.assertFalse(actor.admin)
        for patch_ in [{'uid':'unrelated'}, {'architect_x_id':'1'}, {'architect_x_login':'forged'},
                       {'firebase':{'sign_in_provider':'google.com','identities':{}}}]:
            with self.assertRaises(Unauthorized):XIdentity.from_verified_claims({**claims,**patch_})
        existing={**claims,'uid':'original-firebase-uid','firebase':{'sign_in_provider':'custom','identities':{'twitter.com':['2']}}}
        self.assertEqual(XIdentity.from_verified_claims(existing).firebase_uid,'original-firebase-uid')

    def test_token_issuer_reuses_existing_uid_and_rejects_disabled_account(self):
        from firebase_admin import auth
        issuer=object.__new__(FirebaseXTokenIssuer);issuer.app=object()
        existing=SimpleNamespace(uid='existing-firebase-id',disabled=False)
        with patch.object(auth,'get_users',return_value=SimpleNamespace(users=[existing])),patch.object(auth,'create_custom_token',return_value=b'session') as mint:
            self.assertEqual(issuer.issue('2','Alice'),'session')
            self.assertEqual(mint.call_args.args[0],'existing-firebase-id')
            existing.disabled=True
            with self.assertRaises(Unauthorized):issuer.issue('2','Alice')
            self.assertEqual(mint.call_count,1)
        with patch.object(auth,'get_users',return_value=SimpleNamespace(users=[])),patch.object(auth,'get_user',side_effect=auth.UserNotFoundError('missing')),patch.object(auth,'create_custom_token',return_value=b'session') as mint:
            issuer.issue('2','Alice');self.assertEqual(mint.call_args.args[0],'architect-x-2')

    def test_api_requires_exact_origin_and_never_caches_authentication_material(self):
        async def run():
            app=create_pilot_app(PilotServices(self.store,None,self.access,x_login=self.login))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://fixture') as client:
                for headers in [{},{'Origin':'https://evil.example'}]:
                    self.assertEqual((await client.post('/api/ai-architect/auth/x/start',json={'challenge':challenge(self.verifier)},headers=headers)).status_code,403)
                response=await client.post('/api/ai-architect/auth/x/start',json={'challenge':challenge(self.verifier)},headers={'Origin':ORIGIN})
                self.assertEqual(response.status_code,200);self.assertIn('no-store',response.headers['cache-control'])
                result=await client.post('/api/ai-architect/auth/x/finish',json={'state':response.json()['state'],'code':'code','verifier':self.verifier},headers={'Origin':ORIGIN})
                self.assertEqual(result.status_code,200);self.assertIn('no-store',result.headers['cache-control'])
        asyncio.run(run())
