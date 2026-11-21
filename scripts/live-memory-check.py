"""Opt-in real account request over isolated synthetic AtMem data. Never runs in CI."""
import asyncio
import json
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, patch
from server.memory_service import MemoryService
from server.contracts import ChatRequest
from server.architect import AtMemArchitect
from server.agent_runtime import run

async def main():
    with tempfile.TemporaryDirectory(prefix='atforma-live-memory-') as home:
        memory=MemoryService(home)
        project='live-context-001'
        memory.profile(project,'explanation','Give concise explanations for a cloud beginner.')
        memory.sync(project,{'format':'atforma.project','meta':{'id':project,'revision':1},'design':{'provider':'tools'},'decisions':[{'id':'region-choice','subject':'data.residency','decision':'Customer data must stay in Australia','status':'Accepted','reason':'User confirmed residency'}]})
        req=ChatRequest(projectId=project,provider='claude-code',model='default',effort='low',message='Compare AWS, Azure, Google Cloud and IBM for our internal policy-document assistant. Populate optionAssessment for all four. Use my relevant context, keep the diagram unchanged, explain one key tradeoff and ask one useful next question. No cloud operation.',project={'version':1,'revision':1,'name':'Synthetic policy assistant','provider':'tools','requirements':'Internal document assistant for staff','nodes':[],'edges':[]})
        with patch('server.agent_runtime.service',return_value=memory):
            result=await run(AtMemArchitect(),req,AsyncMock(return_value=False))
        providers={r['provider'] for r in result.get('optionAssessment',[])}
        assert {'aws','azure','gcp','ibm'} <= providers, providers
        assert result['contextUsed']['recordsUsed'], 'Real account request received no memory'
        assert 'Australia' in json.dumps(result), 'Relevant residency context was lost'
        out=Path('/tmp/forma-qa/memory');out.mkdir(parents=True,exist_ok=True)
        (out/'live-account-result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps({'message':result['message'],'optionProviders':sorted(providers),'memoryRecords':len(result['contextUsed']['recordsUsed']),'skills':[s['id'] for s in result['contextUsed']['skills']],'boundary':result['contextUsed']['boundary']}))

if __name__=='__main__':asyncio.run(main())
