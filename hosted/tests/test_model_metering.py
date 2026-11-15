import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
import httpx
from hosted.credits import CreditLedger,Conflict,InsufficientCredits,digest
from hosted.sqlite_store import SQLiteTransactions
from hosted.openrouter_metering import MeteredOpenRouterTransport,quote_ceiling,ModelUnavailable

MODEL={'id':'vendor/model','contextLength':1000000,'pricing':{'prompt':'0.000001','completion':'0.00001','input_cache_write':'0.000002','overrides':[{'min_prompt_tokens':10,'prompt':'0.000003','completion':'0.00002'}]}}
POLICY={'maxOutputTokens':100,'dailyPlatformBudgetMicros':1000000,'platformSpendingEnabled':True}
PAYLOAD={'model':'vendor/model','messages':[{'role':'user','content':'Hello'}],'max_tokens':100}

class MeteringTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory();self.store=SQLiteTransactions(Path(self.temp.name)/'credits.sqlite')
  self.ledger=CreditLedger(self.store,welcome_units=1000000,policy_version='test');self.ledger.register('alice');self.ledger.register('bob')
 async def asyncTearDown(self):self.temp.cleanup()
 def test_daily_and_wallet_reservations_are_atomic_and_dispatch_is_exclusive(self):
  def reserve(i):
   try:self.ledger.reserve('alice',str(i),'a'*64,30,daily_budget={'day':'2026-11-15','limit':100});return True
   except InsufficientCredits:return False
  with ThreadPoolExecutor(max_workers=4) as pool:result=list(pool.map(reserve,range(8)))
  self.assertEqual(sum(result),3)
  def dispatch(_):
   try:self.ledger.claim_dispatch('alice','0');return True
   except Conflict:return False
  # Pick a known newly admitted request independently of the race above.
  self.ledger.reserve('bob','exclusive','b'*64,1)
  def exclusive(_):
   try:self.ledger.claim_dispatch('bob','exclusive');return True
   except Conflict:return False
  with ThreadPoolExecutor(max_workers=4) as pool:self.assertEqual(sum(pool.map(exclusive,range(8))),1)
 def test_settlement_updates_original_daily_budget_once(self):
  budget={'day':'2026-11-15','limit':100}
  self.ledger.reserve('alice','one','a'*64,80,daily_budget=budget);self.ledger.claim_dispatch('alice','one')
  self.ledger.settle('alice','one',20,'receipt-one');self.ledger.settle('alice','one',20,'receipt-one')
  row=self.store.transaction(lambda tx:tx.get('daily_budgets',digest(budget['day'])))
  self.assertEqual((row['reserved'],row['spent']),(0,20))
  self.ledger.reserve('bob','two','b'*64,80,daily_budget=budget)
  with self.assertRaises(InsufficientCredits):self.ledger.reserve('bob','three','c'*64,1,daily_budget=budget)
 async def test_real_response_usage_receipt_settles_exactly_and_key_is_not_stored(self):
  calls=[]
  async def respond(request):calls.append(request);return httpx.Response(200,json={'id':'verified-receipt','usage':{'cost':'0.000037'},'choices':[]})
  transport=MeteredOpenRouterTransport(store=self.store,ledger=self.ledger,uid='alice',operation_prefix='request',model=MODEL,policy=POLICY,transport=httpx.MockTransport(respond))
  async with httpx.AsyncClient(transport=transport) as client:await client.post('https://openrouter.ai/api/v1/chat/completions',json=PAYLOAD,headers={'Authorization':'Bearer synthetic-provider-key'})
  self.assertEqual(len(calls),1);self.assertEqual(self.ledger.account('alice')['spent'],37)
  self.assertEqual(self.ledger.account('alice')['reserved'],0);self.assertEqual(transport.receipts[0]['costMicros'],37)
 async def test_unknown_provider_outcome_keeps_reservation_and_cannot_dispatch_again(self):
  async def lost(request):raise httpx.ReadTimeout('Synthetic lost response')
  transport=MeteredOpenRouterTransport(store=self.store,ledger=self.ledger,uid='alice',operation_prefix='lost',model=MODEL,policy=POLICY,transport=httpx.MockTransport(lost))
  async with httpx.AsyncClient(transport=transport) as client:
   with self.assertRaises(httpx.ReadTimeout):await client.post('https://openrouter.ai/api/v1/chat/completions',json=PAYLOAD)
  self.assertGreater(self.ledger.account('alice')['reserved'],0)
  with self.assertRaises(Conflict):self.ledger.claim_dispatch('alice','lost-1')
  with self.assertRaises(Conflict):self.ledger.release_unsent('alice','lost-1')
 async def test_byok_usage_does_not_spend_or_reserve_managed_credit(self):
  transport=MeteredOpenRouterTransport(store=self.store,ledger=self.ledger,uid='alice',operation_prefix='byok',model=MODEL,policy=POLICY,connection='openrouter',transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'id':'byok-receipt','usage':{'cost':'0.0001'}})))
  async with httpx.AsyncClient(transport=transport) as client:await client.post('https://openrouter.ai/api/v1/chat/completions',json=PAYLOAD)
  account=self.ledger.account('alice');self.assertEqual((account['available'],account['reserved'],account['spent']),(1000000,0,0))
 async def test_compressed_provider_reply_is_not_decoded_twice_or_retried(self):
  import gzip
  raw=json.dumps({'id':'gzip-receipt','usage':{'cost':'0.000003'}}).encode()
  transport=MeteredOpenRouterTransport(store=self.store,ledger=self.ledger,uid='alice',operation_prefix='gzip',model=MODEL,policy=POLICY,transport=httpx.MockTransport(lambda request:httpx.Response(200,content=gzip.compress(raw),headers={'Content-Encoding':'gzip'})))
  async with httpx.AsyncClient(transport=transport) as client:
   response=await client.post('https://openrouter.ai/api/v1/chat/completions',json=PAYLOAD)
  self.assertEqual(response.json()['id'],'gzip-receipt');self.assertNotIn('Content-Encoding',response.headers)
  self.assertEqual(self.ledger.account('alice')['spent'],3)
 def test_quote_uses_highest_pricing_tier_and_rejects_unadmitted_features(self):
  self.assertGreater(quote_ceiling(PAYLOAD,MODEL,max_output_tokens=100),2000)
  for override in [{'model':'other'},{'stream':True},{'plugins':[{'id':'web'}]},{'max_tokens':101}]:
   with self.assertRaises(ModelUnavailable):quote_ceiling({**PAYLOAD,**override},MODEL,max_output_tokens=100)

 def test_vision_quotes_context_ceiling_without_counting_base64_as_text_or_changing_image(self):
  model={**MODEL,'inputModalities':['text','image']}
  payload={**PAYLOAD,'messages':[{'role':'user','content':[{'type':'text','text':'Read this diagram'},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+'a'*2000000}}]}]}
  original=json.dumps(payload);ceiling=quote_ceiling(payload,model,max_output_tokens=100)
  self.assertGreater(ceiling,2000000);self.assertEqual(json.dumps(payload),original)
  with self.assertRaises(ModelUnavailable):quote_ceiling(payload,MODEL,max_output_tokens=100)
