"""Private OpenAI-compatible broker for native AtBots workers.

Worker capabilities bind a server-selected account. Only this trusted process
reads provider credentials or accesses wallets; none enter generated artifacts.
"""
from dataclasses import dataclass
import asyncio,json,secrets,uuid
from fastapi import FastAPI,Header,Request
from fastapi.responses import JSONResponse,Response
from .api import BodyLimit
from .credits import CreditLedger,CreditError
from .openrouter_metering import MeteredOpenRouterTransport,ModelUnavailable
from .x_access import XIdentity

@dataclass
class Binding:
 uid:str
 operation:str
 sequence:int=0

class NativeModelBroker:
 def __init__(self,*,store,profiles,access,settings,vault,platform_key,transport_factory=None,projects=None):
  self.store,self.profiles,self.access,self.settings,self.vault=store,profiles,access,settings,vault
  self.platform_key,self.transport_factory=platform_key,transport_factory
  self.projects=projects
  self.bindings={};self.app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
  self.app.add_middleware(BodyLimit,limit=64*1024*1024)
  @self.app.post('/v1/chat/completions')
  async def complete(request:Request,authorization:str|None=Header(default=None)):
   token=authorization[7:] if authorization and authorization.startswith('Bearer ') else ''
   binding=self.bindings.get(token)
   if not binding:return JSONResponse({'error':{'message':'Worker capability is unavailable'}},status_code=401)
   try:
    body=await request.body()
    response=await self.dispatch(binding,body,request.headers.get('X-Architect-Project'))
    return Response(response.content,status_code=response.status_code,media_type='application/json')
   except Exception:
    # No provider error dumps, prompts, credentials or private project text.
    return JSONResponse({'error':{'message':'AI request stopped. Check access, credits and model policy.'}},status_code=409)
 def bind(self,uid):
  self.admission(uid)
  token=secrets.token_urlsafe(48);self.bindings[token]=Binding(uid,uuid.uuid4().hex);return token
 def revoke(self,token):self.bindings.pop(token,None)
 def admission(self,uid):
  profile=self.profiles.get(uid)
  if profile.get('disabled'):raise ModelUnavailable('Account is unavailable')
  self.access.authorize(XIdentity('worker-authorized',uid,profile['displayName']))
  policy=self.settings.current()
  return profile,policy
 def owned_project(self,uid,pid):
  if self.projects is None:return
  def read(tx):
   self.profiles._account(tx,uid)
   row=tx.get('projects',self.projects._project_key(uid,pid))
   if not row or row.get('trashed'):raise ModelUnavailable('Project is unavailable')
  self.store.transaction(read)
 async def dispatch(self,binding,raw,pid=None):
  import httpx
  await asyncio.to_thread(self.owned_project,binding.uid,pid)
  profile,policy=await asyncio.to_thread(self.admission,binding.uid)
  model=await asyncio.to_thread(self.settings.catalog.selected,policy['model'])
  connection=profile['aiConnection']
  key=await asyncio.to_thread(self.vault.for_broker,binding.uid,'openrouter') if connection=='openrouter' else await asyncio.to_thread(self.platform_key)
  ledger=CreditLedger(self.store,welcome_units=policy['welcomeMicros'],policy_version='pilot-'+str(policy['revision']))
  # Every native tool-loop request rechecks current whitelist, account and policy.
  def guard():
   self.owned_project(binding.uid,pid)
   current,updated=self.admission(binding.uid)
   if current['aiConnection']!=connection:raise ModelUnavailable('AI connection changed; start a new request')
   return updated
  binding.sequence+=1
  transport=MeteredOpenRouterTransport(store=self.store,ledger=ledger,uid=binding.uid,
    operation_prefix=binding.operation+'-'+str(binding.sequence),model=model,policy=policy,connection=connection,
    admission=guard,transport=self.transport_factory() if self.transport_factory else None)
  async with httpx.AsyncClient(transport=transport,timeout=180,trust_env=False,follow_redirects=False) as client:
   return await client.post('https://openrouter.ai/api/v1/chat/completions',content=raw,
       headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
