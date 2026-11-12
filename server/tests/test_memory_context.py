import json
import unittest
from unittest.mock import patch
from server.memory_context import retrieve,providers

class Reply:
    def __init__(self,records):self.records=records
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,limit):return json.dumps({'records':self.records}).encode()

class ProviderTests(unittest.TestCase):
    config=json.dumps([{'id':'team-rag','url':'https://rag.example/context','label':'Team RAG'}])
    def test_scoped_context_is_returned_with_provenance_without_storage(self):
        row={'id':'record-1','userId':'owner','projectId':'project','scope':'project','text':'Reviewed fact','source':{'url':'https://source.example/doc'}}
        with patch('server.memory_context.setting',return_value=self.config),patch('server.memory_context.urllib.request.build_opener')as opener:
            opener.return_value.open.return_value=Reply([row]);records,status=retrieve('project','owner','question',lambda value:True)
            self.assertEqual(records[0]['provider'],'team-rag');self.assertTrue(records[0]['external']);self.assertEqual(records[0]['source'],row['source']);self.assertEqual(status[0]['status'],'ready')
            payload=json.loads(opener.return_value.open.call_args.args[0].data);self.assertEqual(payload['userId'],'owner');self.assertEqual(payload['limit'],6)
    def test_cross_user_or_project_context_is_rejected(self):
        for user,project in [('other','project'),('owner','other')]:
            row={'id':'record-1','userId':user,'projectId':project,'text':'Private fact','source':{}}
            with patch('server.memory_context.setting',return_value=self.config),patch('server.memory_context.urllib.request.build_opener')as opener:
                opener.return_value.open.return_value=Reply([row]);records,status=retrieve('project','owner','question',lambda value:True)
                self.assertEqual(records,[]);self.assertEqual(status[0]['status'],'unavailable')
    def test_credentials_cannot_be_embedded_in_urls(self):
        with patch('server.memory_context.setting',return_value=json.dumps([{'id':'rag','url':'https://secret@example.com/context'}])),self.assertRaises(ValueError):providers()
