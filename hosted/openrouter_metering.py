"""Receipt-bound OpenRouter dispatch; the native SDK owns the agent/model loop."""
import asyncio
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation,ROUND_CEILING
import hashlib
import json
import httpx
from .credits import CreditError,Conflict,identifier

class ModelUnavailable(RuntimeError):pass

def amount(value):
 try:result=Decimal(str(value))
 except (InvalidOperation,TypeError,ValueError) as error:raise ModelUnavailable('Model pricing is unavailable') from error
 if not result.is_finite() or result<0:raise ModelUnavailable('Model pricing is unavailable')
 return result

def micros(value):return int((amount(value)*1_000_000).to_integral_value(rounding=ROUND_CEILING))

def quote_ceiling(payload,model,*,max_output_tokens):
 if payload.get('model')!=model['id'] or payload.get('stream') or payload.get('plugins') or payload.get('web_search_options'):
  raise ModelUnavailable('The model request does not match the admitted connection')
 output=payload.get('max_completion_tokens',payload.get('max_tokens'))
 if type(output) is not int or not 1<=output<=max_output_tokens:raise ModelUnavailable('Model output exceeds its admitted limit')
 pricing=model.get('pricing',{});tiers=[pricing,*pricing.get('overrides',[])]
 if any('prompt' not in tier or 'completion' not in tier for tier in tiers):raise ModelUnavailable('Complete model pricing is required')
 prompt=max(amount(tier.get(field,0)) for tier in tiers for field in ['prompt','input_cache_write'])
 completion=max(amount(tier['completion']) for tier in tiers)
 # Conservative tokenizer-independent bound; includes messages, schemas and tool definitions.
 quoted=json.loads(json.dumps(payload));images=0
 for message in quoted.get('messages',[]):
  content=message.get('content')
  if not isinstance(content,list):continue
  for part in content:
   if part.get('type')=='image_url':
    value=part.get('image_url',{}).get('url','')
    if not value.startswith('data:image/'):raise ModelUnavailable('Use an attached image, not an external image URL')
    if 'image' not in model.get('inputModalities',[]):raise ModelUnavailable('The selected model does not advertise image input')
    images+=1;part['image_url']['url']='attached-image'
 encoded=json.dumps(quoted,ensure_ascii=False,separators=(',',':')).encode()
 input_bound=len(encoded)+2048+256*len(payload.get('messages',[]))
 if input_bound+output>model.get('contextLength',10**9):raise ModelUnavailable('This request exceeds the model context budget')
 # Bound unknown vision tokenization by the model's entire advertised input
 # context, not by base64 bytes. The submitted image bytes remain untouched.
 if images:input_bound=model['contextLength']-output
 image_fee=max(amount(tier.get('image',0)) for tier in tiers)*images
 return max(1,micros(prompt*input_bound+completion*output+amount(pricing.get('request',0))+image_fee))

class MeteredOpenRouterTransport(httpx.AsyncBaseTransport):
 def __init__(self,*,store,ledger,uid,operation_prefix,model,policy,connection='managed',transport=None,clock=None,admission=None):
  self.store,self.ledger,self.uid=store,ledger,uid;self.prefix=identifier(operation_prefix)
  self.model,self.policy,self.connection=model,policy,connection
  self.transport=transport or httpx.AsyncHTTPTransport(retries=0)
  self.admission=admission
  self.sequence=0;self.receipts=[];self.clock=clock or (lambda:datetime.now(timezone.utc).date().isoformat())
 async def aclose(self):await self.transport.aclose()
 async def handle_async_request(self,request):
  if str(request.url)!='https://openrouter.ai/api/v1/chat/completions' or request.method!='POST':
   raise ModelUnavailable('Only the fixed OpenRouter model endpoint is allowed')
  if self.admission:
   current=await asyncio.to_thread(self.admission)
   if current['model']!=self.model['id']:raise ModelUnavailable('Model policy changed. Start a new request.')
   self.policy=current
  raw=await request.aread();payload=json.loads(raw)
  ceiling=quote_ceiling(payload,self.model,max_output_tokens=self.policy['maxOutputTokens'])
  self.sequence+=1;operation=identifier(self.prefix+'-'+str(self.sequence));fingerprint=hashlib.sha256(raw).hexdigest()
  if self.connection=='managed':
   if not self.policy.get('platformSpendingEnabled') or not self.policy.get('dailyPlatformBudgetMicros'):
    raise ModelUnavailable('The administrator must enable a daily managed AI budget')
   await asyncio.to_thread(self.ledger.reserve,self.uid,operation,fingerprint,ceiling,
       daily_budget={'day':self.clock(),'limit':self.policy['dailyPlatformBudgetMicros']})
   await asyncio.to_thread(self.ledger.claim_dispatch,self.uid,operation)
  elif self.connection=='openrouter':
   key=hashlib.sha256((self.uid+'\0'+operation).encode()).hexdigest()
   def claim(tx):
    prior=tx.get('byok_operations',key)
    if prior:raise Conflict('This provider request was already dispatched')
    tx.create('byok_operations',key,{'uid':self.uid,'state':'sent','requestSha256':fingerprint,'model':self.model['id']})
   await asyncio.to_thread(self.store.transaction,claim)
  else:raise ModelUnavailable('Unsupported AI connection')
  try:
   response=await self.transport.handle_async_request(request);content=await response.aread()
   if response.status_code!=200:raise ModelUnavailable('OpenRouter did not confirm a usable response; billing requires reconciliation')
   result=json.loads(content);receipt=identifier(result['id']);used=micros(result['usage']['cost'])
   if self.connection=='managed':await asyncio.to_thread(self.ledger.settle,self.uid,operation,used,receipt)
   else:
    def settle(tx):
     previous=tx.get('byok_operations',key)
     if not previous or previous['uid']!=self.uid or previous['state']!='sent':raise Conflict('Provider receipt requires reconciliation')
     previous.update(state='settled',used=used,receipt=receipt);tx.set('byok_operations',key,previous)
    await asyncio.to_thread(self.store.transaction,settle)
   self.receipts.append({'operation':operation,'receipt':receipt,'costMicros':used,'connection':self.connection})
   # aread() already decoded compression. Do not ask the SDK to decode it again.
   headers={name:value for name,value in response.headers.items() if name.lower() not in {'content-encoding','content-length'}}
   return httpx.Response(response.status_code,headers=headers,content=content,request=request)
  except BaseException:
   if self.connection=='managed':
    try:await asyncio.to_thread(self.ledger.transition,self.uid,operation,'uncertain')
    except Conflict:pass
   else:
    def uncertain(tx):
     previous=tx.get('byok_operations',key)
     if previous and previous['state']=='sent':previous['state']='uncertain';tx.set('byok_operations',key,previous)
    await asyncio.to_thread(self.store.transaction,uncertain)
   raise
