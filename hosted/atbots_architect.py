"""AtBots native model adapter for the existing Architect contracts and tool runtime.

No replacement agent loop. AtBots/Pydantic AI owns model execution; Architect's
existing bounded design validation and evidence loop is reused unchanged.
"""
import asyncio
import json
from .openrouter_metering import MeteredOpenRouterTransport
from server.architect import AtMemArchitect
from server.prompts import SYSTEM_PROMPT

class AtBotsArchitect(AtMemArchitect):
 def __init__(self,*,store,ledger,uid,operation,model,policy,api_key,connection='managed',native_model=None,transport_factory=None,base_url='https://openrouter.ai/api/v1',request_headers=None):
  super().__init__();self.store,self.ledger,self.uid=store,ledger,uid
  self.operation,self.model,self.policy,self.api_key=operation,model,policy,api_key
  self.transport_factory,self.base_url,self.request_headers=transport_factory,base_url,request_headers or {}
  self.connection,self.native_model=connection,native_model;self.pass_number=0;self.usage_receipts=[]
 def _strands(self,request,runtime=None,images=None):
  self.pass_number+=1
  async def execute():
   import httpx
   from pydantic_ai import StructuredDict
   from atbots.providers.pydantic_ai import PydanticAIProvider
   from pydantic_ai.models.openai import OpenAIChatModel
   from pydantic_ai.providers.openai import OpenAIProvider
   from openai import AsyncOpenAI
   metering=self.transport_factory() if self.transport_factory else MeteredOpenRouterTransport(store=self.store,ledger=self.ledger,uid=self.uid,
      operation_prefix=self.operation+'-'+str(self.pass_number),model=self.model,policy=self.policy,connection=self.connection)
   async with httpx.AsyncClient(transport=metering,timeout=180,follow_redirects=False,trust_env=False) as client:
    native=self.native_model or OpenAIChatModel(self.model['id'],provider=OpenAIProvider(openai_client=AsyncOpenAI(
       api_key=self.api_key,base_url=self.base_url,http_client=client,max_retries=0,default_headers=self.request_headers)))
    provider=PydanticAIProvider(name='AtMem AI Architect',model=self.model['id'],endpoint='https://openrouter.ai/api/v1',kind='openai-compatible',egress_class='remote',retries=0)
    output=StructuredDict(self.output_schema(runtime),name='ArchitectResponse')
    agent=provider._build_agent(native,SYSTEM_PROMPT,output)
    agent.model_settings={'max_tokens':self.policy['maxOutputTokens'],'openai_reasoning_effort':'medium',
                         'extra_body':{'reasoning':{'effort':'medium'}},'max_retries':0}
    # Image input must use the native SDK's multimodal input, never textified base64.
    prompt=self.context(request,runtime)
    if images:
     import base64
     from pydantic_ai import BinaryContent
     prompt=[prompt,*[BinaryContent(data=base64.b64decode(image['data']),media_type=image['mime']) for image in images]]
    result=await agent.run(prompt)
    self.usage_receipts.extend(getattr(metering,'receipts',[]))
    return dict(result.output)
  return asyncio.run(execute())
