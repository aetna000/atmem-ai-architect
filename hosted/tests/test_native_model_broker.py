import json,tempfile,unittest
from pathlib import Path
import httpx
from hosted.sqlite_store import SQLiteTransactions
from hosted.projects import Profiles,Projects
from hosted.workspace_projects import WorkspaceProjects
from hosted.credits import CreditLedger
from hosted.credentials import CredentialVault
from hosted.pilot_settings import OpenRouterCatalog,PilotSettings
from hosted.x_access import XWhitelist,XIdentity
from hosted.model_broker import NativeModelBroker
from hosted.tests.test_pilot import catalog_fixture

class NativeBrokerTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory();self.store=SQLiteTransactions(Path(self.temp.name)/'broker.sqlite')
  self.profiles=Profiles(self.store);self.access=XWhitelist(self.store,admin_ids=['1'],initial_ids=['2','3']);self.ledger=CreditLedger(self.store,welcome_units=20000000,policy_version='test')
  for uid in ['1','2','3']:self.profiles.register(XIdentity('signed-'+uid,uid,'User'));self.ledger.register(uid)
  self.vault=CredentialVault(self.store,self.ledger,keyring={'v1':b'x'*32},active_key='v1')
  self.settings=PilotSettings(self.store,self.access,OpenRouterCatalog(fetch=lambda:{'data':[{**row,'context_length':1000000} for row in catalog_fixture()['data']]}));self.settings.update(XIdentity('signed-1','1','Owner'),1,{'platformSpendingEnabled':True,'dailyPlatformBudgetMicros':2000000})
  self.projects=Projects(self.store,self.profiles)
  creation=WorkspaceProjects(self.store,self.profiles,self.projects)
  self.pids={uid:creation.create(uid,'owned-project','Owned')['id'] for uid in ['2','3']}
  self.calls=[]
  def respond(request):
   self.calls.append(request);return httpx.Response(200,json={'id':'receipt-'+str(len(self.calls)),'usage':{'cost':'0.000012'},'choices':[]})
  self.broker=NativeModelBroker(store=self.store,profiles=self.profiles,access=self.access,settings=self.settings,vault=self.vault,platform_key=lambda:'synthetic-managed-key',transport_factory=lambda:httpx.MockTransport(respond),projects=self.projects)
  self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.broker.app),base_url='http://private-broker')
 async def asyncTearDown(self):await self.client.aclose();self.temp.cleanup()
 async def call(self,token,pid=None,**overrides):
  binding=self.broker.bindings.get(token);uid=binding.uid if binding else '2'
  return await self.client.post('/v1/chat/completions',headers={'Authorization':'Bearer '+token,'X-Architect-Project':pid or self.pids[uid]},json={'model':'openai/gpt-6.1-sol','max_tokens':100,'messages':[{'role':'user','content':'Keep complete requirements'}],**overrides})
 async def test_private_capability_charges_only_its_owner_and_revocation_blocks_next_native_call(self):
  token=self.broker.bind('2');self.assertEqual((await self.call(token)).status_code,200)
  self.assertEqual(self.ledger.account('2')['spent'],12);self.assertEqual(self.ledger.account('3')['spent'],0)
  self.access.update(XIdentity('signed-1','1','Owner'),'2',allowed=False,role='user',revision=0)
  self.assertEqual((await self.call(token)).status_code,409);self.assertEqual(len(self.calls),1)
  self.assertEqual((await self.call('forged')).status_code,401)
 async def test_byok_uses_encrypted_owned_key_and_does_not_debit_managed_credits(self):
  self.vault.update('3','openrouter','synthetic-own-openrouter-key',0);self.profiles.update('3',revision=1,ai_connection='openrouter')
  token=self.broker.bind('3');self.assertEqual((await self.call(token)).status_code,200)
  self.assertEqual(self.calls[0].headers['authorization'],'Bearer synthetic-own-openrouter-key');self.assertEqual(self.ledger.account('3')['spent'],0)
 async def test_browser_model_override_is_rejected_before_provider_dispatch(self):
  token=self.broker.bind('2');self.assertEqual((await self.call(token,model='other/model')).status_code,409);self.assertEqual(self.calls,[])

 async def test_foreign_or_deleted_projects_cannot_spend_through_a_valid_tenant_capability(self):
  token=self.broker.bind('2');self.assertEqual((await self.call(token,pid=self.pids['3'])).status_code,409)
  self.projects.remove('2',self.pids['2'],1)
  self.assertEqual((await self.call(token)).status_code,409);self.assertEqual(self.calls,[])
