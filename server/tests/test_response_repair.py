import asyncio
import copy
import json
import unittest
from unittest.mock import AsyncMock,patch
from server.architect import AtMemArchitect
from server.contracts import ChatRequest

class ResponseRepairTests(unittest.TestCase):
    def request(self):return ChatRequest(provider='codex',model='default',message='Build a private AI application on Google Cloud',project={'version':1,'revision':2,'name':'System','provider':'gcp','requirements':'Keep the existing site','nodes':[],'edges':[]})
    def invalid(self):return {'message':'Proposed','proposal':{'baseRevision':2,'title':'Change','body':'Proposal','next':{'version':1,'revision':2,'name':'System','provider':'gcp','nodes':[{'id':'source','position':{'x':0,'y':0},'data':{'label':'Source','kind':'resource','provider':'gcp','origin':'existing','deploymentMode':'create'}}],'edges':[]}}}
    def test_invalid_proposal_repaired_without_mutating_request_or_reprompting_user(self):
        async def check():
            request=self.request();before=request.model_dump();native=AsyncMock(side_effect=[self.invalid(),{'message':'I will prepare the new deployment from existing source.'}])
            with patch('server.local_providers.call_cli',native):
                result=await AtMemArchitect().call(request,AsyncMock(return_value=False),{'fact':'preserve'})
            self.assertEqual(native.await_count,2);self.assertEqual(request.model_dump(),before)
            context=json.loads(native.call_args_list[1].args[2]);repair=context['runtimeContext']['responseRepair']
            self.assertEqual(repair['attempt'],1);self.assertIn('container-service',repair['issues'][0]['message'])
            self.assertEqual(context['runtimeContext']['fact'],'preserve');self.assertEqual(context['request'],request.message)
            self.assertNotIn('repair',result.message);self.assertEqual(result._response_repair_attempts,1);self.assertNotIn('_response_repair_attempts',result.model_dump());self.assertNotIn('_response_repair_attempts',result.model_json_schema()['properties'])
        asyncio.run(check())
    def test_repair_is_bounded_and_cannot_approve_invalid_output(self):
        async def check():
            native=AsyncMock(return_value=self.invalid())
            with patch('server.local_providers.call_cli',native):
                with self.assertRaises(ValueError):await AtMemArchitect().call(self.request(),AsyncMock(return_value=False))
            self.assertEqual(native.await_count,2)
        asyncio.run(check())
    def test_cancellation_prevents_second_model_call(self):
        async def check():
            native=AsyncMock(return_value=self.invalid())
            with patch('server.local_providers.call_cli',native):
                with self.assertRaises(asyncio.CancelledError):await AtMemArchitect().call(self.request(),AsyncMock(side_effect=[False,True]))
            self.assertEqual(native.await_count,1)
        asyncio.run(check())
