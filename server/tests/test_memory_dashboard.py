import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from server.memory_service import MemoryService
from server.app import app,TOKEN

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.memory=MemoryService(self.tmp.name);self.project='dashboard-project';self.headers={'Authorization':'Bearer '+TOKEN}
    def tearDown(self):self.tmp.cleanup()
    def test_profile_identity_persists_and_rename_never_remaps_subject(self):
        original=self.memory.subject('user',self.project);self.memory.rename_profile('Local owner')
        reopened=MemoryService(self.tmp.name)
        self.assertEqual(reopened.owner,self.memory.owner);self.assertEqual(reopened.subject('user',self.project),original);self.assertEqual(reopened.user_profile()['name'],'Local owner')
    def test_indexed_pages_governance_detail_and_scope(self):
        self.memory.profile(self.project,'preferences','Keep concise')
        page=self.memory.browse(self.project,'user',limit=1)
        self.assertEqual(page['total'],1);record=page['records'][0]
        self.assertEqual(record['governance']['userId'],self.memory.owner);self.assertEqual(record['governance']['actorType'],'user')
        detail=self.memory.record_detail(self.project,'user',record['id']);self.assertTrue(detail['audit'])
        with self.assertRaises(RuntimeError):self.memory.record_detail('other-project','project',record['id'])
    def test_dashboard_routes_reject_forged_owners_and_subjects(self):
        with patch('server.memory_routes.service',return_value=self.memory):
            client=TestClient(app)
            self.assertEqual(client.post('/api/memory/records',json={'projectId':self.project}).status_code,401)
            for key in ['subject','userId','owner','database']:
                self.assertEqual(client.post('/api/memory/records',json={'projectId':self.project,key:'forged'},headers=self.headers).status_code,422)
            self.assertEqual(client.post('/api/memory/user-profile',json={'name':'New name','id':'forged'},headers=self.headers).status_code,422)
            result=client.post('/api/memory/records',json={'projectId':self.project},headers=self.headers)
            self.assertEqual(result.status_code,200);self.assertEqual(result.json()['total'],0)
