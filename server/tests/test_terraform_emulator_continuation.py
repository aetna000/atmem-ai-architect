"""Regressions recovered from the interrupted emulator qualification."""
import json
import importlib.util
import unittest
from server import terraform_emulator as emulator

requires_runtime = unittest.skipUnless(importlib.util.find_spec('flask') is not None, 'Run SDK engine tests with .local/terraform-emulator-runtime/bin/python; the app environment intentionally excludes Flask.')


class ReadbackTests(unittest.TestCase):
    @requires_runtime
    def test_user_parameters_retain_source_values_and_apply_methods(self):
        import boto3
        from moto import mock_aws
        with mock_aws():
            emulator.install_rds_parameter_source_adapter()
            emulator.install_rds_parameter_source_adapter()
            c = boto3.client('rds', region_name='ap-southeast-2', aws_access_key_id='testing', aws_secret_access_key='testing')
            c.create_db_parameter_group(DBParameterGroupName='first', DBParameterGroupFamily='postgres16', Description='fixture')
            c.create_db_parameter_group(DBParameterGroupName='second', DBParameterGroupFamily='postgres16', Description='fixture')
            original = {'ParameterName':'log_min_duration_statement', 'ParameterValue':'500', 'ApplyMethod':'immediate'}
            c.modify_db_parameter_group(DBParameterGroupName='first', Parameters=[original])
            stored = c.describe_db_parameters(DBParameterGroupName='first', Source='user')['Parameters']
            self.assertEqual(stored, [dict(original, Source='user')])
            self.assertNotIn('Source', original)
            self.assertEqual(c.describe_db_parameters(DBParameterGroupName='second')['Parameters'], [])
            values={'name':'first','parameter':[{'name':original['ParameterName'],'value':'500','apply_method':'immediate'}]}
            self.assertTrue(all(check[1] for check in emulator._rds_parameters(lambda _:c,values)))
            c.modify_db_parameter_group(DBParameterGroupName='first', Parameters=[dict(original,ParameterValue='700',ApplyMethod='pending-reboot')])
            self.assertFalse(all(check[1] for check in emulator._rds_parameters(lambda _:c,values)))
            with self.assertRaises(c.exceptions.DBParameterGroupNotFoundFault):
                c.modify_db_parameter_group(DBParameterGroupName='missing', Parameters=[original])

    def test_custom_engine_crash_and_gap_are_nonretryable_and_recorded(self):
        import io
        from types import SimpleNamespace
        def app(environ,start):
            raise AssertionError('A claimed custom operation must not fall through')
        for broken in (True, False):
            def handle(*args):
                if broken:raise RuntimeError('engine regression')
                return emulator.engines.Reply('CreateQueue',400,b'{"__type":"EmulatorNotImplemented"}', 'application/x-amz-json-1.0')
            log=emulator.RequestLog(app)
            log.engines=[SimpleNamespace(name='test-engine',service='sqs',handle=handle)]
            environ={'PATH_INFO':'/','REQUEST_METHOD':'POST','CONTENT_LENGTH':'2','wsgi.input':io.BytesIO(b'{}'),
                     'HTTP_X_AMZ_TARGET':'AmazonSQS.CreateQueue','HTTP_AUTHORIZATION':'AWS4-HMAC-SHA256 Credential=testing/20261117/ap-southeast-2/sqs/aws4_request, SignedHeaders=host, Signature=0'}
            started=[]
            body=b''.join(log(environ,lambda status,headers:started.append(status)))
            self.assertEqual(started,['400 Bad Request'])
            self.assertIn(b'EmulatorInternalError' if broken else b'EmulatorNotImplemented',body)
            self.assertEqual(len(log.calls),1)
            self.assertTrue(log.calls[0]['emulatorError' if broken else 'notImplemented'])

    @requires_runtime
    def test_sdk_requests_use_custom_engines_without_polluting_provider_telemetry(self):
        import boto3
        from moto import mock_aws
        with mock_aws():
            backend=emulator.MotoAwsBackend()
            backend.start()
            try:
                client=backend.client('cloudfront')
                policy=client.get_cache_policy(Id='658327ea-f89d-4fab-a63d-7e88639e58f6')['CachePolicy']
                self.assertEqual(policy['CachePolicyConfig']['Name'],'Managed-CachingOptimized')
                self.assertEqual(backend.log.calls,[])
                # Querying engine inventories does not lose engine-owned resources.
                self.assertEqual(backend.log.engines[0].inventory(),[])
            finally:
                backend.stop()

class AppRunnerTests(unittest.TestCase):
    @requires_runtime
    def test_sdk_lifecycle_update_tags_missing_and_inventory(self):
        from moto import mock_aws
        with mock_aws():
            backend=emulator.MotoAwsBackend();backend.start()
            try:
                c=backend.client('apprunner')
                source={'AutoDeploymentsEnabled':False,'ImageRepository':{'ImageIdentifier':'public.ecr.aws/example/app:1','ImageRepositoryType':'ECR_PUBLIC','ImageConfiguration':{'Port':'8000'}}}
                service=c.create_service(ServiceName='example-service',SourceConfiguration=source,Tags=[{'Key':'Purpose','Value':'test'}])['Service']
                arn=service['ServiceArn']
                self.assertEqual(c.describe_service(ServiceArn=arn)['Service']['SourceConfiguration'],source)
                expected={'arn':arn,'source_configuration':[{'auto_deployments_enabled':False,'image_repository':[{'image_identifier':source['ImageRepository']['ImageIdentifier'],'image_repository_type':'ECR_PUBLIC','image_configuration':[{'port':'8000'}]}]}]}
                self.assertTrue(all(check[1] for check in emulator._apprunner_service(lambda _:c,expected)))
                self.assertEqual(len(c.list_services()['ServiceSummaryList']),1)
                with self.assertRaises(c.exceptions.InvalidRequestException):c.create_service(ServiceName='example-service',SourceConfiguration=source)
                c.update_service(ServiceArn=arn,InstanceConfiguration={'Cpu':'2048','Memory':'4096'})
                self.assertEqual(c.describe_service(ServiceArn=arn)['Service']['InstanceConfiguration']['Memory'],'4096')
                import copy
                changed=copy.deepcopy(source);changed['ImageRepository']['ImageConfiguration']['Port']='9000'
                c.update_service(ServiceArn=arn,SourceConfiguration=changed)
                checks=emulator._apprunner_service(lambda _:c,expected)
                self.assertFalse(next(check[1] for check in checks if check[0]=='Image port matches'))
                c.tag_resource(ResourceArn=arn,Tags=[{'Key':'Other','Value':'two'}]);c.untag_resource(ResourceArn=arn,TagKeys=['Purpose'])
                self.assertEqual(c.list_tags_for_resource(ResourceArn=arn)['Tags'],[{'Key':'Other','Value':'two'}])
                self.assertTrue(any(x.startswith('apprunner:') for x in backend.remaining_resources()))
                self.assertEqual(c.delete_service(ServiceArn=arn)['Service']['Status'],'DELETED')
                with self.assertRaises(c.exceptions.ResourceNotFoundException):c.describe_service(ServiceArn=arn)
                self.assertEqual(c.list_services()['ServiceSummaryList'],[])
                self.assertFalse(any(x.startswith('apprunner:') for x in backend.remaining_resources()))
            finally:backend.stop()

class ExtendedEngineTests(unittest.TestCase):
    @requires_runtime
    def test_serverless_aws_owned_key_idempotency_and_policy_deletion(self):
        from moto import mock_aws
        with mock_aws():
            backend=emulator.MotoAwsBackend();backend.start()
            try:
                c=backend.client('opensearchserverless')
                policy=json.dumps({'Rules':[{'ResourceType':'collection','Resource':['collection/example-*']}],'AWSOwnedKey':True})
                c.create_security_policy(name='example-policy',type='encryption',policy=policy)
                a=c.create_collection(name='example-first',type='VECTORSEARCH',clientToken='first-token')['createCollectionDetail']
                b=c.create_collection(name='example-first',type='VECTORSEARCH',clientToken='first-token')['createCollectionDetail']
                self.assertEqual(a['id'],b['id']);self.assertEqual(len(c.list_collections()['collectionSummaries']),1)
                with self.assertRaises(c.exceptions.ConflictException):c.create_collection(name='example-second',type='SEARCH',clientToken='first-token')
                c.delete_security_policy(name='example-policy',type='encryption')
                self.assertEqual(c.batch_get_collection(ids=[a['id']])['collectionDetails'][0]['id'],a['id'])
                with self.assertRaises(c.exceptions.ValidationException):c.create_collection(name='example-third',type='SEARCH')
                with self.assertRaises(c.exceptions.ResourceNotFoundException):c.delete_security_policy(name='example-policy',type='encryption')
                c.delete_collection(id=a['id']);self.assertEqual(c.list_collections()['collectionSummaries'],[])
            finally:backend.stop()

    @requires_runtime
    def test_guardrail_sdk_roundtrip_update_and_reject_invalid_filter(self):
        from moto import mock_aws
        with mock_aws():
            backend=emulator.MotoAwsBackend();backend.start()
            try:
                c=backend.client('bedrock');values={'name':'test-content','blockedInputMessaging':'Input blocked','blockedOutputsMessaging':'Output blocked','contentPolicyConfig':{'filtersConfig':[{'type':'HATE','inputStrength':'HIGH','outputStrength':'HIGH'}]}}
                created=c.create_guardrail(**values,clientRequestToken='original-token',tags=[{'key':'Purpose','value':'test'}]);identity=created['guardrailId'];arn=created['guardrailArn']
                self.assertEqual(c.create_guardrail(**values,clientRequestToken='original-token',tags=[{'key':'Purpose','value':'test'}])['guardrailId'],identity)
                self.assertEqual(c.get_guardrail(guardrailIdentifier=identity)['contentPolicy']['filters'],values['contentPolicyConfig']['filtersConfig'])
                expected={'guardrail_id':identity,'name':values['name'],'blocked_input_messaging':values['blockedInputMessaging'],'blocked_outputs_messaging':values['blockedOutputsMessaging'],'content_policy_config':[{'filters_config':[{'type':'HATE','input_strength':'HIGH','output_strength':'HIGH'}]}]}
                self.assertTrue(all(check[1] for check in emulator._bedrock_guardrail(lambda _:c,expected)))
                self.assertEqual(c.list_tags_for_resource(resourceARN=arn)['tags'],[{'key':'Purpose','value':'test'}])
                c.update_guardrail(guardrailIdentifier=identity,**dict(values,blockedInputMessaging='New blocked'))
                self.assertEqual(c.get_guardrail(guardrailIdentifier=identity)['blockedInputMessaging'],'New blocked')
                checks=emulator._bedrock_guardrail(lambda _:c,expected)
                self.assertFalse(next(check[1] for check in checks if check[0]=='Blocked input message matches'))
                with self.assertRaises(c.exceptions.ValidationException):
                    c.create_guardrail(**dict(values,contentPolicyConfig={'filtersConfig':[{'type':'HATE','inputStrength':'INVALID','outputStrength':'HIGH'}]}))
                c.delete_guardrail(guardrailIdentifier=identity)
                with self.assertRaises(c.exceptions.ResourceNotFoundException):c.get_guardrail(guardrailIdentifier=identity)
                self.assertEqual(c.list_guardrails()['guardrails'],[])
            finally:backend.stop()

class KnowledgeBaseTests(unittest.TestCase):
    @requires_runtime
    def test_registration_keeps_configuration_and_rejects_missing_collection(self):
        from moto import mock_aws
        with mock_aws():
            backend=emulator.MotoAwsBackend();backend.start()
            try:
                vector=backend.client('opensearchserverless');c=backend.client('bedrock-agent')
                vector.create_security_policy(name='knowledge-policy',type='encryption',policy=json.dumps({'Rules':[{'ResourceType':'collection','Resource':['collection/knowledge-vectors']}],'AWSOwnedKey':True}))
                collection=vector.create_collection(name='knowledge-vectors',type='VECTORSEARCH')['createCollectionDetail']
                values={'name':'knowledge-example','roleArn':'arn:aws:iam::123456789012:role/example',
                        'knowledgeBaseConfiguration':{'type':'VECTOR','vectorKnowledgeBaseConfiguration':{'embeddingModelArn':'arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.titan-embed-text-v2:0'}},
                        'storageConfiguration':{'type':'OPENSEARCH_SERVERLESS','opensearchServerlessConfiguration':{'collectionArn':collection['arn'],'vectorIndexName':'documents','fieldMapping':{'vectorField':'embedding','textField':'text','metadataField':'metadata'}}}}
                created=c.create_knowledge_base(**values,clientToken='original-knowledge-token-0000000000000000',tags={'Purpose':'test'})['knowledgeBase'];identity=created['knowledgeBaseId'];arn=created['knowledgeBaseArn']
                self.assertEqual(c.create_knowledge_base(**values,clientToken='original-knowledge-token-0000000000000000',tags={'Purpose':'test'})['knowledgeBase']['knowledgeBaseId'],identity)
                self.assertEqual(c.get_knowledge_base(knowledgeBaseId=identity)['knowledgeBase']['storageConfiguration'],values['storageConfiguration'])
                expected={'id':identity,'name':values['name'],'role_arn':values['roleArn'],'knowledge_base_configuration':[{'type':'VECTOR','vector_knowledge_base_configuration':[{'embedding_model_arn':values['knowledgeBaseConfiguration']['vectorKnowledgeBaseConfiguration']['embeddingModelArn']}]}],'storage_configuration':[{'type':'OPENSEARCH_SERVERLESS','opensearch_serverless_configuration':[{'collection_arn':collection['arn'],'vector_index_name':'documents','field_mapping':[{'vector_field':'embedding','text_field':'text','metadata_field':'metadata'}]}]}]}
                self.assertTrue(all(check[1] for check in emulator._knowledge_base(lambda _:c,expected)))
                self.assertEqual(c.list_tags_for_resource(resourceArn=arn)['tags'],{'Purpose':'test'})
                c.update_knowledge_base(knowledgeBaseId=identity,**dict(values,name='renamed'))
                self.assertEqual(c.get_knowledge_base(knowledgeBaseId=identity)['knowledgeBase']['name'],'renamed')
                expected['name']='renamed'
                import copy
                for field in ('collection_arn','vector_index_name'):
                    wrong=copy.deepcopy(expected);wrong['storage_configuration'][0]['opensearch_serverless_configuration'][0][field]='wrong'
                    self.assertFalse(all(check[1] for check in emulator._knowledge_base(lambda _:c,wrong)))
                wrong=copy.deepcopy(expected);wrong['storage_configuration'][0]['opensearch_serverless_configuration'][0]['field_mapping'][0]['vector_field']='wrong'
                checks=emulator._knowledge_base(lambda _:c,wrong)
                self.assertFalse(next(check[1] for check in checks if check[0]=='Vector field mapping matches'))
                bad=json.loads(json.dumps(values));bad['storageConfiguration']['opensearchServerlessConfiguration']['collectionArn']='arn:aws:aoss:ap-southeast-2:123456789012:collection/missing'
                with self.assertRaises(c.exceptions.ValidationException):c.create_knowledge_base(**bad)
                c.delete_knowledge_base(knowledgeBaseId=identity)
                with self.assertRaises(c.exceptions.ResourceNotFoundException):c.get_knowledge_base(knowledgeBaseId=identity)
                self.assertEqual(c.list_knowledge_bases()['knowledgeBaseSummaries'],[])
                vector.delete_collection(id=collection['id']);vector.delete_security_policy(name='knowledge-policy',type='encryption')
            finally:backend.stop()


if __name__=='__main__':
    unittest.main()
