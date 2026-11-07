import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
root=Path(__file__).resolve().parents[2]/'src/runtime'
for name in ['bounded_rag','rag_aws_adapter']:
    spec=importlib.util.spec_from_file_location(name,root/(name+'.py'));module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
adapter=sys.modules['rag_aws_adapter']

class RagAwsAdapterTests(unittest.TestCase):
    def event(self):
        return {'version':'2.0','requestContext':{'accountId':'123456789012','apiId':'test-api','routeKey':'POST /ask','authorizer':{'iam':{'accountId':'123456789012','callerId':'AROA1234567890123456:session','userArn':'arn:aws:sts::123456789012:assumed-role/TestRole/session'}}},'body':'{"question":"holiday"}'}
    def test_identity_comes_from_gateway_and_authoritative_directory(self):
        directory=Mock();directory.get_identity.return_value={'enabled':True,'subject':'alice','employeeRegion':'AU'}
        event=self.event();event['subject']='bob';event['employeeRegion']='US'
        principal=adapter.authenticated_principal(event,directory,'123456789012','test-api')
        self.assertEqual((principal.subject,principal.region),('alice','AU'));directory.get_identity.assert_called_once_with('AROA1234567890123456')
    def test_unknown_gateway_identity_region_and_disabled_user_fail_closed(self):
        directory=Mock();directory.get_identity.return_value={'enabled':False}
        with self.assertRaises(adapter.RetrievalDenied):adapter.authenticated_principal(self.event(),directory,'123456789012','test-api')
        event=self.event();event['requestContext']['apiId']='forged'
        directory.reset_mock()
        with self.assertRaises(adapter.RetrievalDenied):adapter.authenticated_principal(event,directory,'123456789012','test-api')
        directory.get_identity.assert_not_called()
    def test_body_identity_claims_are_rejected(self):
        event=self.event();event['body']='{"question":"holiday","subject":"bob"}'
        with self.assertRaises(ValueError):adapter.question_body(event)
        self.assertEqual(adapter.question_body(self.event()),'holiday')
    def test_strongly_consistent_reads_and_no_silent_pagination_truncation(self):
        client=Mock();repo=adapter.DynamoRepository(client,'test-table',lambda item:item)
        client.get_item.return_value={'Item':{'id':'doc'}}
        self.assertEqual(repo.get_current('doc'),{'id':'doc'})
        self.assertTrue(client.get_item.call_args.kwargs['ConsistentRead'])
        client.scan.return_value={'Items':[],'ScannedCount':100,'LastEvaluatedKey':{'recordId':{'S':'next'}}}
        with self.assertRaises(ValueError):repo.list_bounded()
        self.assertEqual(client.scan.call_count,5)
        self.assertTrue(all(c.kwargs['ConsistentRead'] for c in client.scan.call_args_list))
    def test_document_cap_cannot_be_bypassed_by_pagination(self):
        client=Mock();repo=adapter.DynamoRepository(client,'test-table',lambda item:item)
        client.scan.side_effect=[{'Items':[{'kind':'DOCUMENT'}]*100,'LastEvaluatedKey':{'recordId':{'S':'next'}}},{'Items':[{'kind':'DOCUMENT'}]}]
        with self.assertRaises(ValueError):repo.list_bounded()
    def test_verified_gateway_access_token_uses_directory_region_not_claims(self):
        directory=Mock();directory.get_identity.return_value={'enabled':True,'subject':'alice','employeeRegion':'AU'}
        event=self.event();event['requestContext']['routeKey']='POST /api/ask'
        claims={'iss':'https://issuer.example/pool','client_id':'client','token_use':'access','sub':'12345678-1234-1234-1234-123456789012','scope':'openid atmem/ask','employeeRegion':'US'}
        event['requestContext']['authorizer']={'jwt':{'claims':claims}}
        principal=adapter.authenticated_principal(event,directory,'123456789012','test-api','https://issuer.example/pool','client')
        self.assertEqual(principal.region,'AU');directory.get_identity.assert_called_once_with('COGNITO#12345678-1234-1234-1234-123456789012')
        claims['token_use']='id'
        with self.assertRaises(adapter.RetrievalDenied):adapter.authenticated_principal(event,directory,'123456789012','test-api','https://issuer.example/pool','client')
