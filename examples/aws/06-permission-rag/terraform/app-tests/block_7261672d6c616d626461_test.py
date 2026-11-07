import sys
import importlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"build/block_7261672d6c616d626461"))
api=importlib.import_module("block_7261672d6c616d626461")
from unittest.mock import MagicMock
import unittest
import json
import os
from boto3.dynamodb.types import TypeSerializer

class RagRuntimeTests(unittest.TestCase):
    def setUp(self):
        os.environ.update(CATALOG_TABLE='catalog',EXPECTED_ACCOUNT_ID='123456789012',EXPECTED_API_ID='test-api',MODEL_ARN='arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.nova-micro-v1:0',MAX_OUTPUT_TOKENS='256')
        self.db=MagicMock();self.model=MagicMock();api._clients=(self.db,self.model)
        self.subject={'enabled':True,'subject':'alice','employeeRegion':'AU'}
        self.doc={'kind':'DOCUMENT','id':'holiday','revision':'1','title':'Holiday policy','text':'The synthetic holiday is 12 November.','allowedSubjects':['alice'],'allowedRegions':['AU']}
        self.secret={**self.doc,'id':'secret','title':'SECRET TITLE','text':'SECRET BODY','allowedSubjects':['bob']}
        self.db.scan.side_effect=lambda **kwargs:{'Items':[self.encode(self.doc),self.encode(self.secret)],'ScannedCount':2}
        self.db.get_item.side_effect=lambda **kwargs:{'Item':self.encode(self.subject if kwargs['Key']['recordId']['S'].startswith('IDENTITY#') else self.doc)}
        self.model.converse.return_value={'output':{'message':{'content':[{'text':json.dumps({'answer':'12 November','citations':['holiday']})}]}},'stopReason':'end_turn'}
    def encode(self,value):
        serializer=TypeSerializer();return {k:serializer.serialize(v) for k,v in value.items()}
    def event(self,question='holiday'):
        return {'version':'2.0','requestContext':{'accountId':'123456789012','apiId':'test-api','routeKey':'POST /ask','authorizer':{'iam':{'accountId':'123456789012','callerId':'AROA1234567890123456:session','userArn':'arn:aws:sts::123456789012:assumed-role/TestRole/session'}}},'body':json.dumps({'question':question})}
    def test_cited_answer_excludes_restricted_evidence(self):
        result=api.handler(self.event(),None);self.assertEqual(result['statusCode'],200)
        self.assertEqual(json.loads(result['body'])['citations'][0]['id'],'holiday')
        self.assertNotIn('SECRET',json.dumps(self.model.converse.call_args.kwargs))
        self.assertEqual(self.model.converse.call_args.kwargs['inferenceConfig']['maxTokens'],256)
    def test_unknown_identity_and_body_spoofing_fail(self):
        self.subject['enabled']=False
        self.assertEqual(api.handler(self.event(),None)['statusCode'],403)
        self.model.converse.assert_not_called()
        self.subject['enabled']=True;event=self.event();event['body']=json.dumps({'question':'holiday','subject':'bob'})
        self.assertEqual(api.handler(event,None)['statusCode'],400);self.model.converse.assert_not_called()
    def test_no_evidence_abstains_without_model(self):
        result=api.handler(self.event('quantum mechanics'),None)
        self.assertTrue(json.loads(result['body'])['abstained']);self.model.converse.assert_not_called()
    def test_fabricated_citation_is_rejected(self):
        self.model.converse.return_value['output']['message']['content'][0]['text']=json.dumps({'answer':'Leak','citations':['secret']})
        result=api.handler(self.event(),None)
        self.assertEqual(result['statusCode'],400);self.assertNotIn('secret',result['body'])
    def test_revocation_during_generation_suppresses_delivery(self):
        def generate(**kwargs):
            self.doc['allowedSubjects']=[]
            return {'output':{'message':{'content':[{'text':json.dumps({'answer':'12 November','citations':['holiday']})}]}},'stopReason':'end_turn'}
        self.model.converse.side_effect=generate
        result=api.handler(self.event(),None);self.assertEqual(result['statusCode'],403);self.assertNotIn('November',result['body'])
    def test_repository_failure_does_not_send_any_evidence(self):
        self.db.scan.side_effect=RuntimeError('SECRET BACKEND ERROR')
        with self.assertLogs(api.logger,level='WARNING') as logs:result=api.handler(self.event(),None)
        self.assertEqual(result['statusCode'],503);self.assertNotIn('SECRET',' '.join(logs.output));self.model.converse.assert_not_called()
    def test_model_can_abstain_when_matching_terms_are_not_sufficient_evidence(self):
        self.model.converse.return_value['output']['message']['content'][0]['text']=json.dumps({'answer':'Insufficient evidence.','citations':[]})
        result=api.handler(self.event('holiday travel reimbursement'),None)
        self.assertEqual(result['statusCode'],200);self.assertTrue(json.loads(result['body'])['abstained'])
    def test_expired_or_excessively_future_source_authorization_abstains(self):
        import time
        self.doc['sourceId']='sharepoint-contract'
        for expiry in [int(time.time())-1,int(time.time())+1000]:
            self.doc['authorizationExpiresAt']=expiry
            result=api.handler(self.event(),None)
            self.assertEqual(result['statusCode'],200);self.assertTrue(json.loads(result['body'])['abstained'])
        self.model.converse.assert_not_called()
