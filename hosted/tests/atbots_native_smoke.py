"""Operator-only real native request, with a strict local shadow spending budget.

Run in the separate worker environment. Secret is read into memory only. This is
not a deployed-user acceptance test and never mutates a production wallet.
"""
import os
os.environ['PYDANTIC_AI_NO_BANNER']='1'
import asyncio,json,subprocess,uuid
from pathlib import Path
from hosted.sqlite_store import SQLiteTransactions
from hosted.credits import CreditLedger
from hosted.pilot_settings import OpenRouterCatalog
from hosted.atbots_architect import AtBotsArchitect
from server.contracts import ChatRequest

async def main():
 root=Path('.local/atbots-native-smoke');root.mkdir(parents=True,exist_ok=True,mode=0o700)
 store=SQLiteTransactions(root/'usage.sqlite');uid='operator-native-test-'+uuid.uuid4().hex
 ledger=CreditLedger(store,welcome_units=2000000,policy_version='operator-smoke-usd200-max');ledger.register(uid)
 model=OpenRouterCatalog().selected('openai/gpt-6.1-sol')
 key=subprocess.check_output(['gcloud','secrets','versions','access','1','--secret','architect-openrouter-api-key','--project','atmemai'],text=True).strip()
 engine=AtBotsArchitect(store=store,ledger=ledger,uid=uid,operation=uuid.uuid4().hex,model=model,
   policy={'maxOutputTokens':4096,'platformSpendingEnabled':True,'dailyPlatformBudgetMicros':2000000},api_key=key)
 request=ChatRequest(provider='openai',model=model['id'],effort='medium',message='We need a small appointment booking application for a local dentist. Ask the single most important business question first. Do not invent requirements or draw a complete system yet.',project={'version':1,'revision':1,'name':'Dental appointments','provider':'tools','requirements':'','nodes':[],'edges':[]})
 async def connected():return False
 result=await engine.call(request,connected)
 receipt={'kind':'real OpenRouter + native AtBots + existing Architect response validation','model':model['id'],'reasoning':'medium',
          'validResponse':True,'phase':result.phase,'hasMessage':bool(result.message),'receiptCount':len(engine.usage_receipts),
          'usage':engine.usage_receipts,'shadowAccount':ledger.account(uid),'productionWalletChanged':False,'providerSpendingLimitMicros':2000000}
 (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({key:receipt[key] for key in ['kind','model','validResponse','phase','receiptCount','usage','productionWalletChanged']}))
if __name__=='__main__':asyncio.run(main())
