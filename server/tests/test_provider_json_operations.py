"""Shared operations exercise real provider adapters with scripted wire fixtures."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src/runtime'))
import azure_acceptance as azure
import gcp_acceptance as gcp
from public_faq import PublicFaq,parse_catalog
from aws_json_model import BedrockJsonModel,read_model_config as aws_model_config

def current_catalog():
    return parse_catalog(json.dumps({'format':'atmem-public-faq-v1','revision':'catalog-v1','articles':[{
        'id':'refund','revision':'refund-v1','title':'Refund policy','text':'Refunds are available within thirty days after purchase.','url':'https://help.example.test/refund','visibility':'public'}]}).encode(),'generation-1')

RAW=json.dumps({'answer':'Refunds are available within thirty days.','citations':[{'id':'refund','quote':'Refunds are available within thirty days after purchase.'}],'abstained':False})

class ProviderJsonOperationTests(unittest.TestCase):
    def test_aws_converse_uses_real_sdk_shapes_regional_model_and_independent_citation_validation(self):
        import boto3
        from botocore.stub import Stubber,ANY
        policy=boto3.client('bedrock',region_name='ap-southeast-2',aws_access_key_id='fixture',aws_secret_access_key='fixture')
        runtime=boto3.client('bedrock-runtime',region_name='ap-southeast-2',aws_access_key_id='fixture',aws_secret_access_key='fixture')
        with Stubber(policy) as ps,Stubber(runtime) as rs:
            ps.add_response('get_account_data_retention',{'mode':'none'},{});ps.add_response('get_model_invocation_logging_configuration',{},{});
            rs.add_response('converse',{'output':{'message':{'role':'assistant','content':[{'text':RAW}]}},'stopReason':'end_turn','usage':{'inputTokens':10,'outputTokens':10,'totalTokens':20},'metrics':{'latencyMs':10}},
                {'modelId':'arn:aws:bedrock:ap-southeast-2::foundation-model/anthropic.reviewed-v1:0','system':ANY,'messages':ANY,'inferenceConfig':{'maxTokens':1024}})
            model=BedrockJsonModel(aws_model_config({'REGION':'ap-southeast-2','MODEL_ID':'anthropic.reviewed-v1:0'}),policy=policy,runtime=runtime)
            reply=PublicFaq(Mock(return_value=current_catalog()),model.generate)('refund');self.assertEqual(reply['citations'][0]['id'],'refund');ps.assert_no_pending_responses();rs.assert_no_pending_responses()
    def test_aws_unknown_retention_never_calls_inference(self):
        from structured_http import PolicyUnverified
        policy=Mock();policy.get_account_data_retention.return_value={'mode':'default'};runtime=Mock()
        model=BedrockJsonModel(aws_model_config({'REGION':'ap-southeast-2','MODEL_ID':'anthropic.reviewed-v1:0'}),policy=policy,runtime=runtime)
        with self.assertRaises(PolicyUnverified):PublicFaq(Mock(return_value=current_catalog()),model.generate)('refund')
        runtime.converse.assert_not_called()
    def test_azure_nested_cited_answer_reuses_policy_identity_and_strict_schema(self):
        fixture=azure.ModelTests();fixture.setUp();fixture.session.request.side_effect=[azure.Response(fixture.policy),azure.Response({'choices':[{'finish_reason':'stop','message':{'content':RAW}}]})]
        reply=PublicFaq(Mock(return_value=current_catalog()),fixture.model.generate)('What is the refund policy?')
        self.assertEqual(reply['citations'][0]['id'],'refund')
        calls=fixture.session.request.call_args_list;self.assertEqual([c.args[0] for c in calls],['GET','POST']);body=calls[-1].kwargs['json']
        schema=body['response_format']['json_schema'];self.assertTrue(schema['strict']);self.assertEqual(schema['schema']['properties']['citations']['items']['properties']['id']['type'],'string');self.assertNotIn('tools',body)
    def test_google_nested_schema_uses_same_metadata_and_readonly_policy_path(self):
        fixture=gcp.ModelTests();fixture.setUp();fixture.session.request.side_effect=[fixture.metadata,gcp.Response(fixture.cache),gcp.Response(fixture.settings),gcp.Response({'candidates':[{'finishReason':'STOP','content':{'role':'model','parts':[{'text':RAW}]}}]})]
        reply=PublicFaq(Mock(return_value=current_catalog()),fixture.model.generate)('refund')
        self.assertEqual(reply['citations'][0]['revision'],'refund-v1');body=fixture.session.request.call_args.kwargs['json'];schema=body['generationConfig']['responseSchema'];self.assertEqual(schema['type'],'OBJECT');self.assertEqual(schema['properties']['citations']['type'],'ARRAY');self.assertEqual(schema['properties']['citations']['items']['properties']['id']['type'],'STRING');self.assertNotIn('tools',body)
    def test_invalid_owned_schema_or_oversized_data_does_not_make_a_network_call(self):
        for module in [azure,gcp]:
            fixture=module.ModelTests();fixture.setUp()
            for text,schema in [('x'*150001,{'type':'object'}),('input',{'type':'array'}),('',{'type':'object'})]:
                with self.assertRaises(ValueError):fixture.model.generate(text,schema,'Owned operation')
            fixture.session.request.assert_not_called()
    def test_provider_policy_failure_still_blocks_nested_inference(self):
        fixture=azure.ModelTests();fixture.setUp();fixture.session.request.side_effect=[azure.Response({})]
        with self.assertRaises(azure.PolicyUnverified):PublicFaq(Mock(return_value=current_catalog()),fixture.model.generate)('refund')
        self.assertEqual(fixture.session.request.call_count,1);self.assertEqual(fixture.session.request.call_args.args[0],'GET')
        fixture=gcp.ModelTests();fixture.setUp();fixture.c['policy_review']=''
        with self.assertRaises(gcp.PolicyUnverified):PublicFaq(Mock(return_value=current_catalog()),fixture.model.generate)('refund')
        fixture.session.request.assert_not_called()

if __name__=='__main__':unittest.main()
