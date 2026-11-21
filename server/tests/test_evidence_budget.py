import asyncio,unittest
from unittest.mock import AsyncMock,patch
from server.agent_runtime import run
from server.contracts import ArchitectResponse,ChatRequest,ToolRequest
class Memory:
    def __init__(self,new=False):self.calls=0;self.new=new;self.status_value={'status':'ready','enabled':True,'engine':'fixture'}
    def enabled(self,p):return True
    def status(self,p):return self.status_value
    def recall(self,*args):return [],self.status_value
    def subject(self,*args):return 'scoped-knowledge'
    def call(self,ops):
        self.calls+=1;records=[{'id':'base','practice':'Already provided'}]
        if self.new and self.calls>1:records.append({'id':'new','practice':'New reviewed evidence'})
        return [records]
    def record_turn(self,*args):pass
class EvidenceBudgetTests(unittest.TestCase):
    def request(self):return ChatRequest(projectId='evaluation-fixture',provider='codex',model='default',message='Use EU regions for this system',project={'version':1,'revision':2,'name':'System','provider':'aws','nodes':[],'edges':[]})
    def execute(self,memory,architect):
        with patch('server.agent_runtime.service',return_value=memory),patch('server.agent_runtime.skills.publish'),patch('server.agent_runtime.skills.select',return_value=[]),patch('server.agent_runtime.skills.public',return_value=[]),patch('server.engineering_knowledge.context',side_effect=lambda raw,providers:raw):
            return asyncio.run(run(architect,self.request(),AsyncMock(return_value=False)))
    def test_no_information_gain_finishes_next_round_with_no_new_user_request(self):
        class Architect:
            calls=0
            async def call(self,request,disconnected,runtime):
                self.calls+=1
                if self.calls==1:return ArchitectResponse(message='Checking',toolRequests=[ToolRequest(name='knowledge.lookup',query='retention')])
                assert runtime['availableTools']==[] and runtime['toolBudget']['canRequestTools'] is False
                assert 'records' not in runtime['toolResults'][0]['result']
                assert runtime['toolResults'][0]['result']['contentsAt']=='runtimeContext.engineeringKnowledge'
                return ArchitectResponse(message='I recommend EU placement; account verification remains pending.')
        model=Architect();result=self.execute(Memory(),model);self.assertEqual(model.calls,2);self.assertNotIn('narrow',result['message']);self.assertFalse(result['contextUsed']['tools'][0]['evidenceAdded'])
    def test_new_evidence_is_supplied_once_and_repeated_query_uses_cache(self):
        class Architect:
            calls=0
            async def call(self,request,disconnected,runtime):
                self.calls+=1
                if self.calls<3:return ArchitectResponse(message='Checking',toolRequests=[ToolRequest(name='knowledge.lookup',query='retention')])
                assert runtime['toolBudget']['canRequestTools'] is False
                assert len(runtime['engineeringKnowledge'])==2 and len(runtime['toolResults'])==1
                return ArchitectResponse(message='A supported recommendation with explicit remaining tests.')
        memory=Memory(new=True);model=Architect();result=self.execute(memory,model);self.assertEqual(memory.calls,2);self.assertEqual(model.calls,3);self.assertTrue(result['contextUsed']['tools'][-1]['cached']);self.assertIn('new',result['contextUsed']['knowledgeRecordIds'])
