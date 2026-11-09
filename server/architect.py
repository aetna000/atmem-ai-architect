"""Local adaptation of the AWS sample's composed agent, with upstream retry/limiter reuse."""
import asyncio, base64, json, os, shutil, signal, tempfile
from .contracts import ArchitectResponse, ChatRequest
from .prompts import SYSTEM_PROMPT
from .abstraction import consultation_focus

class AtMemArchitect:
    def __init__(self):
        self._sdk_lock=asyncio.Lock()
        self._limiter=None
        self.keys={}

    @staticmethod
    def context(request:ChatRequest,runtime=None):
        return json.dumps({'consultationFocus':consultation_focus(request),'origin':request.origin,'currentProject':request.project.model_dump(exclude_none=True),'baseRevision':request.project.revision,'history':[m.model_dump() for m in request.history],'stage':request.stage,'readOnlyContext':[c.model_dump() for c in request.context],'request':request.message,'runtimeContext':runtime or {},'outputSchema':ArchitectResponse.model_json_schema()},ensure_ascii=False)

    async def call(self,request:ChatRequest,is_disconnected,runtime=None):
        from .attachments import prepare
        attachments=await asyncio.to_thread(prepare,[a.model_dump() for a in request.attachments])
        runtime={**(runtime or {}),'attachmentEvidence':[a for a in attachments if 'text' in a],'imageEvidence':[{'name':a['name'],'mime':a['mime']} for a in attachments if 'data' in a]}
        images=[a for a in attachments if 'data' in a]
        if images and request.provider=='gemini-cli':
            raise RuntimeError('This account connector cannot send images yet. Choose Codex, Claude Code, Copilot or an image-capable API connection. Documents with extractable text work here.')
        if request.provider in {'claude-code','codex','copilot','gemini-cli'}:
            from .local_providers import call_cli
            raw=await self._claude(request,is_disconnected,runtime,images) if request.provider=='claude-code' else await call_cli(request.provider,request.model,self.context(request,runtime),SYSTEM_PROMPT,ArchitectResponse.model_json_schema(),is_disconnected,request.effort,images)
        else:
            async with self._sdk_lock:
                # The upstream synchronous retry/limiter is confined to one worker.
                raw=await asyncio.wait_for(asyncio.to_thread(self._strands,request,runtime,images),timeout=90)
        result=ArchitectResponse.model_validate(raw)
        if result.proposal and result.proposal.baseRevision!=request.project.revision:
            raise ValueError('Architect returned a proposal for the wrong revision.')
        return result

    async def _claude(self,request,is_disconnected,runtime=None,images=None):
        from .local_providers import call_cli
        return await call_cli('claude-code',request.model,self.context(request,runtime),SYSTEM_PROMPT,ArchitectResponse.model_json_schema(),is_disconnected,request.effort,images)

    def _strands(self,request,runtime=None,images=None):
        from strands import Agent
        from .upstream.agent.aws_architect import AWSArchitectAgent
        from .upstream.agent.rate_limiter import RateLimiter
        if request.provider=='anthropic':
            if not (self.keys.get('anthropic') or os.getenv('ANTHROPIC_API_KEY')):raise RuntimeError('Set ANTHROPIC_API_KEY in the sidecar environment.')
            from strands.models.anthropic import AnthropicModel
            model=AnthropicModel(client_args={'api_key':self.keys.get('anthropic') or os.environ['ANTHROPIC_API_KEY']},model_id=request.model,max_tokens=6000)
        elif request.provider=='openai':
            if not (self.keys.get('openai') or os.getenv('OPENAI_API_KEY')):raise RuntimeError('Set OPENAI_API_KEY in the sidecar environment.')
            from strands.models.openai import OpenAIModel
            model=OpenAIModel(client_args={'api_key':self.keys.get('openai') or os.environ['OPENAI_API_KEY']},model_id=request.model,params={'max_tokens':6000})
        elif request.provider=='xai':
            key=self.keys.get('xai') or os.getenv('XAI_API_KEY')
            if not key:raise RuntimeError('Add an xAI API key in Connections.')
            from strands.models.openai import OpenAIModel
            # Grok's API is OpenAI-compatible.
            model=OpenAIModel(client_args={'api_key':key,'base_url':'https://api.x.ai/v1'},model_id=request.model,params={'max_tokens':6000})
        elif request.provider=='gemini-api':
            key=self.keys.get('gemini-api') or os.getenv('GEMINI_API_KEY')
            if not key:raise RuntimeError('Add a Gemini API key in Connections.')
            from strands.models.gemini import GeminiModel
            model=GeminiModel(client_args={'api_key':key},model_id=request.model)
        else:
            from strands.models import BedrockModel
            model=BedrockModel(model_id=request.model,region_name=os.getenv('AWS_REGION','us-east-1'),max_tokens=6000)
        # Preserve the sample's composition, retry/backoff and sliding-window limiter.
        # Do not call initialize(): it auto-starts MCP servers and uses an AWS-only prompt.
        composed=AWSArchitectAgent()
        if self._limiter is None:self._limiter=RateLimiter(max_requests=5,time_window=60)
        composed.rate_limiter=self._limiter
        composed.agent=Agent(name='atforma-architect',system_prompt=SYSTEM_PROMPT,model=model,tools=[],callback_handler=None)
        composed.initialized=True
        content=[{'text':self.context(request,runtime)}]+[{'image':{'format':i['mime'].split('/')[1],'source':{'bytes':base64.b64decode(i['data'])}}} for i in images or []]
        result=composed._call_agent_with_retry(content if images else self.context(request,runtime))
        text=''.join(c.get('text','') for c in result.message.get('content',[])).strip()
        if text.startswith('```'):text='\n'.join(text.splitlines()[1:-1])
        return json.loads(text)
