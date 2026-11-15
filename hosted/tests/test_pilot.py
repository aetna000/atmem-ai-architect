import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
import httpx

from hosted.auth import Unauthorized,Forbidden
from hosted.credits import CreditLedger,Conflict,digest
from hosted.credentials import CredentialVault
from hosted.sqlite_store import SQLiteTransactions
from hosted.x_access import XIdentity,XWhitelist
from hosted.projects import Profiles,Projects,CHUNK_BYTES
from hosted.pilot_settings import OpenRouterCatalog
from hosted.pilot_api import PilotServices,create_pilot_app


class XIdentityFixture:
    """API test fixture; actual Firebase signature/revocation qualification remains separate."""
    def verify(self,token):
        identities={'Bearer owner':XIdentity('firebase-owner','1','AtMem'),
                    'Bearer alice':XIdentity('firebase-alice','2','Alice'),
                    'Bearer bob':XIdentity('firebase-bob','3','Bob'),
                    'Bearer outsider':XIdentity('firebase-other','4','AtMem')}
        if token not in identities:raise Unauthorized('Sign in with X')
        return identities[token]


def catalog_fixture():
    def model(id,params=('reasoning',),outputs=('text',)):
        return {'id':id,'name':id,'architecture':{'input_modalities':['text'],'output_modalities':list(outputs)},
                'supported_parameters':list(params),'pricing':{'prompt':'0.000002','completion':'0.00001'}}
    return {'data':[model('openai/gpt-6.1-sol'),model('openai/gpt-6.1-terra'),model('vendor/reasoner'),
                    model('vendor/plain',params=()),model('vendor/image',outputs=('image',))]}


class PilotDomainTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'pilot.sqlite'
        self.store=SQLiteTransactions(self.path);self.profiles=Profiles(self.store)
        for who in [XIdentity('a','1','Owner'),XIdentity('b','2','Alice')]:self.profiles.register(who)
        self.projects=Projects(self.store,self.profiles)
    def tearDown(self):self.temp.cleanup()

    def test_sqlite_transactions_rollback_and_independent_connections_prevent_double_grants(self):
        def register(_):return CreditLedger(SQLiteTransactions(self.path),welcome_units=20_000_000,policy_version='pilot').register('2')
        with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(register,range(24)))
        account=self.store.transaction(lambda tx:tx.get('accounts',digest('2')))
        self.assertEqual(account['available'],20_000_000)
        def failure(tx):
            tx.set('profiles','synthetic',{'partial':True});raise RuntimeError('synthetic interrupted transaction')
        with self.assertRaises(RuntimeError):self.store.transaction(failure)
        self.assertIsNone(self.store.transaction(lambda tx:tx.get('profiles','synthetic')))

    def test_only_verified_x_subject_is_identity_and_handles_or_roles_do_not_grant_access(self):
        claims={'uid':'signed-uid','name':'AtMem','firebase':{'sign_in_provider':'twitter.com','identities':{'twitter.com':['2']}},'admin':True}
        actor=XIdentity.from_verified_claims(claims)
        self.assertEqual(actor.x_id,'2');self.assertFalse(actor.admin)
        for patch in [{'firebase':{'sign_in_provider':'google.com','identities':{'twitter.com':['1']}}},
                      {'firebase':{'sign_in_provider':'twitter.com','identities':{'twitter.com':['@atmemai']}}},
                      {'firebase':{'sign_in_provider':'twitter.com','identities':{'twitter.com':['1','2']}}}]:
            with self.assertRaises(Unauthorized):XIdentity.from_verified_claims({**claims,**patch})

    def test_admin_access_and_revocation_are_durable_and_not_based_on_a_name(self):
        access=XWhitelist(self.store,admin_ids=['1'],initial_ids=['2'])
        alice=access.authorize(XIdentity('a','2','AtMem'))
        self.assertFalse(alice.admin)
        with self.assertRaises(Forbidden):access.update(alice,'3',allowed=True,role='admin',revision=0)
        access.update(XIdentity('o','1','Owner'),'2',allowed=False,role='user',revision=0)
        fresh=XWhitelist(SQLiteTransactions(self.path),admin_ids=['1'],initial_ids=['2'])
        with self.assertRaises(Forbidden):fresh.authorize(alice)
        with self.assertRaises(Conflict):access.update(XIdentity('o','1','Owner'),'1',allowed=False,role='user',revision=0)

    def test_versioned_chunks_roundtrip_losslessly_recover_and_cannot_overwrite_newer_work(self):
        raw=json.dumps({'domain':'warehouse','requirements':['preserve all text '*(CHUNK_BYTES//4)]},ensure_ascii=False).encode()
        first=self.projects.begin('2','request',title='Warehouse',size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        self.assertEqual(first['id'],self.projects.begin('2','request',title='Warehouse',size=len(raw),sha256=hashlib.sha256(raw).hexdigest())['id'])
        self.assertGreater(first['chunks'],1)
        for i in range(first['chunks']):
            part=raw[i*CHUNK_BYTES:(i+1)*CHUNK_BYTES]
            self.projects.put_chunk('2',first['id'],i,base64.b64encode(part).decode(),hashlib.sha256(part).hexdigest())
        saved=self.projects.complete('2',first['id'])
        restarted=Projects(SQLiteTransactions(self.path),Profiles(SQLiteTransactions(self.path)))
        self.assertEqual(restarted.download('2',saved['id'])[1],raw)
        replacement=b'{"domain":"legal","requirements":["Keep accepted obligations"]}'
        second=restarted.begin('2','replace',title='Legal',size=len(replacement),sha256=hashlib.sha256(replacement).hexdigest(),pid=saved['id'],revision=1)
        restarted.put_chunk('2',second['id'],0,base64.b64encode(replacement).decode(),hashlib.sha256(replacement).hexdigest())
        restarted.complete('2',second['id']);restarted.complete('2',first['id'])
        self.assertEqual(restarted.download('2',saved['id'])[1],replacement)
        self.assertEqual(restarted.list('2')['projects'][0]['revision'],2)
        with self.assertRaises(Conflict):restarted.remove('2',saved['id'],1)
        restarted.remove('2',saved['id'],2)
        self.assertEqual(restarted.list('2')['usedBytes'],0)


class PilotApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=SQLiteTransactions(Path(self.temp.name)/'pilot.sqlite')
        self.access=XWhitelist(self.store,admin_ids=['1'],initial_ids=['2','3'])
        self.profiles=Profiles(self.store)
        self.vault=CredentialVault(self.store,self.profiles,keyring={'v1':b'a'*32},active_key='v1')
        catalog=OpenRouterCatalog(fetch=catalog_fixture)
        self.app=create_pilot_app(PilotServices(self.store,XIdentityFixture(),self.access,self.vault,catalog))
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='https://architect.example.test')
        self.prefix='/api/ai-architect'
    async def asyncTearDown(self):await self.client.aclose();self.temp.cleanup()
    async def request(self,method,path,user='alice',**kwargs):
        return await self.client.request(method,self.prefix+path,headers={'Authorization':'Bearer '+user},**kwargs)

    async def test_denied_x_account_cannot_create_profile_or_receive_credit(self):
        response=await self.request('POST','/profile','outsider')
        self.assertEqual(response.status_code,403)
        self.assertIsNone(self.store.transaction(lambda tx:tx.get('profiles',digest('4'))))
        self.assertIsNone(self.store.transaction(lambda tx:tx.get('accounts',digest('4'))))

    async def test_whitelisted_account_gets_usd20_exactly_once_without_public_admin_rights(self):
        for _ in range(2):
            response=await self.request('POST','/profile');self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['balanceMicros'],20_000_000)
            self.assertFalse(response.json()['admin']);self.assertFalse(response.json()['paymentsAvailable'])
            self.assertEqual(response.json()['ai']['model'],'openai/gpt-6.1-sol')
        for path in ['/checkout','/stripe/webhook','/credits/grant','/admin/billing']:
            self.assertEqual((await self.request('POST',path,json={})).status_code,404)

    async def test_private_project_save_download_and_delete_enforce_ownership(self):
        for user in ['alice','bob']:await self.request('POST','/profile',user)
        raw=b'{"project":"supply chain","requirements":["Keep USA data placement"]}'
        response=await self.request('POST','/projects/uploads',json={'requestId':'one','title':'Supply chain','size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        self.assertEqual(response.status_code,200);upload=response.json()['id']
        self.assertEqual((await self.request('POST',f'/projects/uploads/{upload}/complete')).status_code,409)
        body={'data':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
        self.assertEqual((await self.request('PUT',f'/projects/uploads/{upload}/parts/0','bob',json=body)).status_code,404)
        self.assertEqual((await self.request('PUT',f'/projects/uploads/{upload}/parts/0',json=body)).status_code,200)
        saved=(await self.request('POST',f'/projects/uploads/{upload}/complete')).json()
        self.assertEqual((await self.request('GET',f'/projects/{saved["id"]}/download','bob')).status_code,404)
        download=await self.request('GET',f'/projects/{saved["id"]}/download')
        self.assertEqual(download.content,raw);self.assertIn('attachment;',download.headers['content-disposition'])
        self.assertEqual(download.headers['cache-control'],'no-store')
        self.assertEqual((await self.request('DELETE',f'/projects/{saved["id"]}',json={'revision':1})).status_code,200)

    async def test_bad_json_cannot_be_saved_and_cancel_releases_storage(self):
        await self.request('POST','/profile');raw=b'{"invalid":NaN}'
        upload=(await self.request('POST','/projects/uploads',json={'requestId':'bad','title':'Bad','size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})).json()['id']
        await self.request('PUT',f'/projects/uploads/{upload}/parts/0',json={'data':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()})
        self.assertEqual((await self.request('POST',f'/projects/uploads/{upload}/complete')).status_code,400)
        self.assertEqual((await self.request('GET','/projects')).json()['projects'],[])
        await self.request('DELETE',f'/projects/uploads/{upload}')
        self.assertEqual((await self.request('GET','/projects')).json()['reservedBytes'],0)

    async def test_only_admin_can_select_live_catalog_models_and_medium_cannot_be_overridden(self):
        self.assertEqual((await self.request('GET','/admin/models')).status_code,403)
        models=(await self.request('GET','/admin/models','owner')).json()['models']
        self.assertNotIn('vendor/image',[m['id'] for m in models])
        update={'revision':1,'changes':{'model':'openai/gpt-6.1-terra'}}
        self.assertEqual((await self.request('PATCH','/admin/settings',json=update)).status_code,403)
        self.assertEqual((await self.request('PATCH','/admin/settings','owner',json=update)).status_code,200)
        self.assertEqual((await self.request('POST','/profile')).json()['ai']['model'],'openai/gpt-6.1-terra')
        for model in ['unavailable/model','vendor/plain']:
            self.assertEqual((await self.request('PATCH','/admin/settings','owner',json={'revision':2,'changes':{'model':model}})).status_code,400)
        self.assertEqual((await self.request('PATCH','/admin/settings','owner',json={'revision':2,'changes':{'reasoning':'high'}})).status_code,400)
        self.assertEqual((await self.request('PATCH','/profile',json={'revision':1,'model':'forged'})).status_code,422)

    async def test_revoked_user_is_denied_with_previously_valid_token(self):
        await self.request('POST','/profile')
        self.assertEqual((await self.request('PUT','/admin/whitelist/2','owner',json={'revision':0,'allowed':False,'role':'user'})).status_code,200)
        for method,path in [('GET','/projects'),('POST','/profile'),('GET','/provider/openrouter')]:
            self.assertEqual((await self.request(method,path)).status_code,403)

    async def test_own_openrouter_key_is_encrypted_and_separate_from_other_profiles(self):
        for user in ['alice','bob']:await self.request('POST','/profile',user)
        secret='sk-or-synthetic-fixture-never-real'
        response=await self.request('PUT','/provider/openrouter',json={'revision':0,'apiKey':secret})
        self.assertEqual(response.status_code,200);self.assertNotIn(secret,response.text)
        self.assertFalse((await self.request('GET','/provider/openrouter','bob')).json()['configured'])
        self.assertEqual(self.vault.for_broker('2','openrouter'),secret)
        self.assertEqual((await self.request('POST','/profile')).json()['balanceMicros'],20_000_000)
