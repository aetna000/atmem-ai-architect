import asyncio
import json
import tempfile
import sqlite3
import unittest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from server.architecture_activity import ArchitectureActivity
from server.architect import AtMemArchitect
from server.contracts import ChatRequest
from server.agent_runtime import run
from server.memory_service import MemoryService
from server.app import app, TOKEN

PROJECT='activity-project-001'
def request():
    return ChatRequest(projectId=PROJECT,provider='codex',model='exact-model',effort='high',message='Keep the existing catalogue and add a reading screen.',project={'version':1,'revision':2,'name':'Catalogue','provider':'tools','nodes':[],'edges':[]})

class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'activity.sqlite'
        connect=sqlite3.connect
        with patch('server.architecture_activity.sqlite3.connect',side_effect=lambda path:connect(path,check_same_thread=False)):
            self.store=ArchitectureActivity(self.path)
        self.addCleanup(lambda:self.store.close())
        self.id=str(uuid.uuid4());self.store.start(PROJECT,self.id,{'model':'exact-model','effort':'high'})

    def test_ownership_pagination_and_restart_never_replay(self):
        for i in range(205):self.store.append(PROJECT,self.id,{'kind':'model_message','text':str(i)})
        first=self.store.read(PROJECT,self.id);second=self.store.read(PROJECT,self.id,first['events'][-1]['sequence'])
        self.assertEqual(len(first['events']),200);self.assertEqual(len(second['events']),5)
        with self.assertRaises(LookupError):self.store.read('another-project',self.id)
        with self.assertRaises(ValueError):self.store.start(PROJECT,self.id,{})
        self.store.close();self.store=ArchitectureActivity(self.path)
        self.assertEqual(self.store.read(PROJECT,self.id)['state'],'recovery_required')
        self.assertEqual(len(self.store.read(PROJECT,self.id)['events']),200)
        with self.assertRaises(ValueError):self.store.append(PROJECT,self.id,{'kind':'model_message','text':'replay'})

    def test_private_fields_oversize_and_cursor_rejected_without_clipping(self):
        for event in [{'kind':'reasoning','text':'private'},{'kind':'model_message','text':'public','details':{'prompt':'secret'}},{'kind':'model_message','text':'x'*16001}]:
            with self.assertRaises(ValueError):self.store.append(PROJECT,self.id,event)
        with self.assertRaises(ValueError):self.store.read(PROJECT,self.id,True)
        self.assertEqual(self.store.read(PROJECT,self.id)['events'],[])

    def test_real_host_loop_format_repair_tools_and_public_messages(self):
        async def check():
            native=AsyncMock(side_effect=[{'message':'Rejected raw private sentinel','proposal':{'baseRevision':999}}, {'message':'I will inspect the current design.','toolRequests':[{'name':'project.read'}]}, {'message':'The existing catalogue stays. Here is the next design step.'}])
            memory=MemoryService(self.temp.name)
            with patch('server.agent_runtime.service',return_value=memory),patch('server.local_providers.call_cli',native):
                output=await run(AtMemArchitect(),request(),AsyncMock(return_value=False),activity=lambda e:self.store.append(PROJECT,self.id,e))
            events=self.store.read(PROJECT,self.id)['events'];kinds=[e['kind'] for e in events]
            self.assertEqual(native.await_count,3);self.assertEqual(kinds.count('model_started'),3)
            self.assertEqual(kinds.count('response_repair'),1);self.assertIn('tool_started',kinds);self.assertIn('tool_finished',kinds)
            self.assertEqual([e['text'] for e in events if e['kind']=='model_message'],['I will inspect the current design.','The existing catalogue stays. Here is the next design step.'])
            self.assertNotIn('Rejected raw private sentinel',json.dumps(events));self.assertNotIn('rejectedResponse',json.dumps(events))
            for event in events:
                if event['kind']=='model_started':self.assertEqual((event['details']['model'],event['details']['effort']),('exact-model','high'))
            self.assertEqual(output['message'],'The existing catalogue stays. Here is the next design step.')
            self.assertEqual(kinds[-1],'response_ready')
        asyncio.run(check())

    def test_api_duplicate_stops_inference_and_cross_project_read(self):
        payload=request().model_dump();payload['activityId']=self.id
        with patch('server.app.architecture_activity',return_value=self.store),patch('server.app.run_architect',new_callable=AsyncMock) as runner:
            with TestClient(app) as client:
                headers={'Authorization':'Bearer '+TOKEN}
                self.assertEqual(client.post('/api/architect',json=payload,headers=headers).status_code,409)
                runner.assert_not_awaited()
                self.assertEqual(client.post('/api/architect/activity',json={'projectId':'another-project','activityId':self.id},headers=headers).status_code,404)
                self.assertEqual(client.post('/api/architect/activity',json={'projectId':PROJECT,'activityId':self.id,'after':True},headers=headers).status_code,422)
                self.assertEqual(client.post('/api/architect/activity',json={'projectId':PROJECT,'activityId':self.id},headers=headers).status_code,200)

    def test_observer_failure_does_not_replay_or_lose_response(self):
        payload=request().model_dump();payload['activityId']=str(uuid.uuid4())
        async def runner(*args,activity):
            activity({'kind':'model_started','text':'Consulting the selected model.'})
            activity({'kind':'response_ready','text':'Ready'})
            return {'message':'Public response'}
        with patch('server.app.architecture_activity',return_value=self.store),patch.object(self.store,'append',side_effect=OSError('disk fixture')),patch('server.app.run_architect',side_effect=runner) as inference:
            with TestClient(app) as client:
                response=client.post('/api/architect',json=payload,headers={'Authorization':'Bearer '+TOKEN})
            self.assertEqual(response.status_code,200);self.assertEqual(inference.call_count,1)
            self.assertEqual(response.json()['message'],'Public response');self.assertFalse(response.json()['architectureActivity']['detailsAvailable'])
            self.assertEqual(self.store.read(PROJECT,payload['activityId'])['state'],'details_unavailable')
