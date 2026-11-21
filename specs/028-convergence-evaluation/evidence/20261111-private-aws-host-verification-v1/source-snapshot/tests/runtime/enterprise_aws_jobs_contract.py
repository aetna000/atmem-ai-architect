"""Offline native ECS request checks, not a launched task or whole-project pass."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/aws-web-runtime-sdk')]
from enterprise_aws_jobs import configuration,task_definition
from enterprise_document_job import request
from botocore.model import ServiceModel
from botocore.validate import validate_parameters
import gzip


def config():
    return {'format':'enterprise-aws-document-job-v1','accountId':'123456789012','region':'ap-southeast-2',
            'bucket':'owned-document-bytes','clusterArn':'arn:aws:ecs:ap-southeast-2:123456789012:cluster/document-parser','hostPolicySha256':'e'*64,
            'hostDocumentArn':'arn:aws:ssm:ap-southeast-2:123456789012:document/owned-document-host-probe','hostDocumentHash':'f'*64,'hostDocumentVersion':'1',
            'workerRoleArn':'arn:aws:iam::123456789012:role/question-worker',
            'transferRoleArn':'arn:aws:iam::123456789012:role/document-transfer',
            'executionRoleArn':'arn:aws:iam::123456789012:role/document-image-pull',
            'parserImage':'123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/document-parser@sha256:'+'a'*64,
            'transferImage':'123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/document-transfer@sha256:'+'b'*64}


def native_check(value,shape):
    validate_parameters(value,shape)
    def enums(value,shape):
        if shape.type_name=='structure':
            for key,item in value.items():enums(item,shape.members[key])
        elif shape.type_name=='list':
            for item in value:enums(item,shape.member)
        elif shape.type_name=='map':
            for key,item in value.items():enums(key,shape.key);enums(item,shape.value)
        elif shape.type_name=='string'and shape.enum and value not in shape.enum:raise ValueError('Unsupported native enum: '+shape.name)
    enums(value,shape)


class AwsDocumentTaskContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=ROOT/'tests/fixtures/providers/aws-ecs-2014-11-13-botocore-1.43.123.json.gz'
        provenance=json.loads(path.with_suffix('.provenance.json').read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest()!=provenance['sha256']:raise ValueError('Native ECS schema changed')
        cls.model=ServiceModel(json.loads(gzip.decompress(path.read_bytes())),service_name='ecs')
    def setUp(self):
        self.config=config();self.request=request(b'OWNED SYNTHETIC DOCUMENT','text/plain','c'*64)
        self.plan=task_definition(self.config,self.request,'"'+'d'*32+'"')
    def test_generated_definition_passes_official_native_structure_and_enums(self):
        native_check(self.plan,self.model.operation_model('RegisterTaskDefinition').input_shape)
    def test_shape_checker_rejects_unknown_field_and_invalid_enum(self):
        for mutation in ['unknown','enum']:
            value=copy.deepcopy(self.plan)
            if mutation=='unknown':value['containerDefinitions'][1]['unknownNetworkControl']=True
            else:value['requiresCompatibilities']=['INVENTED']
            with self.assertRaises(Exception):native_check(value,self.model.operation_model('RegisterTaskDefinition').input_shape)
    def test_only_parser_network_is_disabled_and_no_credentials_or_exec_are_supplied(self):
        download,parser,upload=self.plan['containerDefinitions']
        self.assertTrue(parser['disableNetworking']);self.assertNotIn('environment',parser)
        self.assertNotIn('disableNetworking',download);self.assertNotIn('disableNetworking',upload)
        self.assertEqual(self.plan['taskRoleArn'],self.config['transferRoleArn'])
        self.assertNotIn(self.config['workerRoleArn'],json.dumps(self.plan))
        for container in [download,parser,upload]:
            for field in ['secrets','environmentFiles','volumesFrom','portMappings','credentialSpecs']:self.assertNotIn(field,container)
            self.assertNotIn('logConfiguration',container)
    def test_success_dependencies_do_not_stop_task_before_upload(self):
        download,parser,upload=self.plan['containerDefinitions']
        self.assertFalse(download['essential']);self.assertFalse(parser['essential']);self.assertTrue(upload['essential'])
        self.assertEqual(parser['dependsOn'],[{'containerName':'download','condition':'SUCCESS'}])
        self.assertEqual(upload['dependsOn'],[{'containerName':'parser','condition':'SUCCESS'}])
        self.assertNotIn('restartPolicy',parser)
    def test_mounts_are_fresh_task_local_and_parser_cannot_write_raw_input(self):
        self.assertEqual(self.plan['placementConstraints'],[{'type':'memberOf','expression':'attribute:atmem-document-policy == '+'e'*64}])
        self.assertEqual(self.plan['volumes'],[{'name':side,'dockerVolumeConfiguration':{'scope':'task','driver':'local'}}for side in ['input','output']])
        parser=self.plan['containerDefinitions'][1]
        self.assertEqual(parser['mountPoints'],[{'sourceVolume':'input','containerPath':'/input','readOnly':True},{'sourceVolume':'output','containerPath':'/output','readOnly':False}])
        self.assertTrue(parser['readonlyRootFilesystem']);self.assertFalse(parser['privileged'])
        self.assertEqual(parser['user'],'10001:10001');self.assertEqual(parser['linuxParameters']['capabilities'],{'drop':['ALL']})
    def test_cross_account_region_mutable_artifacts_and_shared_roles_are_rejected(self):
        changes=[('clusterArn',self.config['clusterArn'].replace('ap-southeast-2','us-east-1')),
                 ('executionRoleArn',self.config['workerRoleArn']),('transferRoleArn',self.config['transferRoleArn'].replace('123456789012','222222222222')),
                 ('parserImage',self.config['parserImage'].split('@')[0]+':latest'),('parserImage',self.config['transferImage']),
                 ('region','us-gov-west-1'),('bucket','../../unowned')]
        for key,value in changes:
            with self.subTest(field=key):
                changed={**self.config,key:value}
                with self.assertRaises(ValueError):configuration(changed)
    def test_only_bounded_exact_byte_metadata_enters_definition(self):
        encoded=json.dumps(self.plan)
        self.assertNotIn('OWNED SYNTHETIC DOCUMENT',encoded)
        for mutation in [{**self.request,'question':'private'},{**self.request,'requestId':'../arbitrary'},{**self.request,'sha256':'bad'}]:
            with self.assertRaises(ValueError):task_definition(self.config,mutation,'"'+'d'*32+'"')
        with self.assertRaises(ValueError):task_definition(self.config,self.request,'arbitrary-response')
    def test_configuration_and_metadata_are_not_mutated_or_aliased(self):
        before=copy.deepcopy(self.config);original=copy.deepcopy(self.request)
        self.plan['containerDefinitions'][0]['environment'][0]['value']='changed'
        self.assertEqual(self.config,before);self.assertEqual(self.request,original)


if __name__=='__main__':unittest.main(verbosity=2)
