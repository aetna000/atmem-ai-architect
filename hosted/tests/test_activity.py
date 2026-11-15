import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
import httpx
from hosted.activity import Activity
from hosted.auth import Forbidden
from hosted.credits import CreditError
from hosted.sqlite_store import SQLiteTransactions
from hosted.x_access import XWhitelist,XIdentity
from hosted.x_lookup import XLookup,XLookupUnavailable

class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=SQLiteTransactions(Path(self.temp.name)/'state.sqlite')
        self.access=XWhitelist(self.store,admin_ids=['1'],initial_ids=['2'])
        self.admin=self.access.authorize(XIdentity('a','1','Admin'))
        self.user=self.access.authorize(XIdentity('b','2','Person'))
        self.now=datetime(2026,11,15,tzinfo=timezone.utc)
        self.activity=Activity(self.store,self.access,clock=lambda:self.now)

    def test_admin_only_summaries_deduplicate_requests_and_preserve_counts_beyond_recent_window(self):
        for i in range(205):self.activity.record(self.user,'chat_requested',event_id=str(i))
        self.activity.record(self.user,'chat_requested',event_id='204')
        report=self.activity.report(self.admin)
        self.assertEqual(report['activeUsers'],1);self.assertEqual(report['counts']['chat_requested'],205)
        self.assertEqual(len(report['events']),200)
        self.assertEqual(report['users'][0]['xId'],'2')
        with self.assertRaises(Forbidden):self.activity.report(self.user)
        self.access.update(self.admin,'2',allowed=True,role='admin',revision=0)
        promoted=self.access.authorize(self.user)
        self.access.update(self.admin,'2',allowed=False,role='user',revision=1)
        with self.assertRaises(Forbidden):self.activity.report(promoted)

    def test_old_days_are_cleaned_and_unknown_events_are_rejected(self):
        self.activity.record(self.user,'project_opened',project='a'*32)
        self.now+=timedelta(days=31);self.activity.record(self.user,'account_opened')
        report=self.activity.report(self.admin,30)
        self.assertEqual(report['counts'],{'account_opened':1})
        self.assertIsNone(self.store.transaction(lambda tx:tx.get('activity_days','2026-11-15')))
        with self.assertRaises(CreditError):self.activity.record(self.user,'private prompt text')
        with self.assertRaises(CreditError):self.activity.report(self.admin,31)

    def test_handles_and_nicknames_are_labels_while_ids_control_access(self):
        row=self.access.update(self.admin,'3',allowed=True,role='user',revision=0,handle='Example_User',nickname='Team lead')
        self.assertEqual(row['handle'],'Example_User');self.assertEqual(row['nickname'],'Team lead')
        with self.assertRaises(Forbidden):self.access.authorize(XIdentity('x','4','Example_User'))
        row=self.access.update(self.admin,'3',allowed=False,role='user',revision=1)
        self.assertEqual(row['nickname'],'Team lead')
        self.access.update(self.admin,'1',allowed=True,role='admin',revision=0,handle='AtMemAi',nickname='Owner')
        self.assertEqual(self.access.list(self.admin)[0]['nickname'],'Owner')

    def test_lookup_never_runs_during_whitelist_edits_and_runs_only_on_resolve(self):
        calls=[]
        lookup=XLookup(fetch=lambda username:(calls.append(username) or httpx.Response(200,json={'data':{'id':'3','username':'Example_User'}})))
        self.access.update(self.admin,'3',allowed=True,role='user',revision=0,handle='Example_User',nickname='Lead')
        self.assertEqual(calls,[])
        self.assertEqual(lookup.resolve('@Example_User'),{'xId':'3','handle':'Example_User'})
        self.assertEqual(calls,['Example_User'])
        with self.assertRaises(CreditError):lookup.resolve('https://x.com/user')
        self.assertEqual(len(calls),1)

    def test_x_payment_and_mismatched_identity_fail_without_changing_access(self):
        for response in [httpx.Response(402,json={}),httpx.Response(200,json={'data':{'id':'3','username':'SomeoneElse'}})]:
            with self.assertRaises(XLookupUnavailable):XLookup(fetch=lambda _:response).resolve('@Example_User')
        self.assertEqual([row['xId'] for row in self.access.list(self.admin)],['1','2'])

class ActivityAPITests(unittest.IsolatedAsyncioTestCase):
    async def test_authenticated_admin_reporting_and_manual_lookup_keep_roles_and_tenants_separate(self):
        from hosted.pilot_api import PilotServices,create_pilot_app
        from hosted.tests.test_pilot import XIdentityFixture,catalog_fixture
        from hosted.pilot_settings import OpenRouterCatalog
        with tempfile.TemporaryDirectory() as folder:
            store=SQLiteTransactions(Path(folder)/'data.sqlite');access=XWhitelist(store,admin_ids=['1'],initial_ids=['2','3'])
            lookups=[]
            def resolve(name):
                lookups.append(name)
                return httpx.Response(200,json={'data':{'id':'3','username':'Example_User'}})
            app=create_pilot_app(PilotServices(store,XIdentityFixture(),access,catalog=OpenRouterCatalog(fetch=catalog_fixture),x_lookup=XLookup(fetch=resolve)))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://fixture') as client:
                prefix='/api/ai-architect'
                owner={'Authorization':'Bearer owner'};alice={'Authorization':'Bearer alice'};bob={'Authorization':'Bearer bob'}
                for headers in [owner,alice,bob]:self.assertEqual((await client.post(prefix+'/profile',headers=headers)).status_code,200)
                self.assertEqual(lookups,[])
                self.assertEqual((await client.get(prefix+'/admin/activity',headers=alice)).status_code,403)
                response=await client.post(prefix+'/admin/x/lookup',headers=alice,json={'handle':'Example_User'})
                self.assertEqual(response.status_code,403);self.assertEqual(lookups,[])
                response=await client.post(prefix+'/admin/x/lookup',headers=owner,json={'handle':'Example_User'})
                self.assertEqual(response.json()['xId'],'3');self.assertEqual(lookups,['Example_User'])
                response=await client.put(prefix+'/admin/whitelist/3',headers=owner,json={'revision':0,'allowed':True,'role':'user','handle':'Example_User','nickname':'Design partner'})
                self.assertEqual(response.status_code,200);self.assertEqual(lookups,['Example_User'])
                project=(await client.post(prefix+'/workspace/projects/new',headers=alice,json={'requestId':'create-one','title':'Private title never collected'})).json()
                forged=await client.post(prefix+'/activity',headers=bob,json={'kind':'project_opened','projectId':project['id']})
                self.assertEqual(forged.status_code,404)
                self.assertEqual((await client.post(prefix+'/activity',headers=alice,json={'kind':'project_opened','projectId':project['id']})).status_code,200)
                self.assertEqual((await client.post(prefix+'/activity',headers=bob,json={'kind':'signed_out','projectId':project['id']})).status_code,400)
                report=(await client.get(prefix+'/admin/activity',headers=owner)).json()
                self.assertEqual(report['activeUsers'],3);self.assertEqual(report['counts']['project_opened'],1)
                self.assertNotIn('Private title',json.dumps(report))
                person=next(row for row in report['users'] if row['xId']=='3');self.assertEqual(person['nickname'],'Design partner')
                self.assertEqual((await client.post(prefix+'/activity',headers=alice,json={'kind':'project_opened','projectId':project['id'],'xId':'3'})).status_code,422)
