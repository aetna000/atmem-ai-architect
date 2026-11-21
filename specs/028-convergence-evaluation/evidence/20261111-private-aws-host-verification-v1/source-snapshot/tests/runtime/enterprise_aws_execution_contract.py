"""Native SDK contracts and real local files; AWS APIs are explicit fixtures."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'tests/runtime'),str(ROOT/'.local/aws-web-runtime-sdk')]
from enterprise_aws_jobs import EcsDocuments,EcsDocumentApi,transfer_metadata
from enterprise_aws_objects import S3DocumentObjects,object_key
from enterprise_aws_transfer import metadata,download,upload
from enterprise_document_job import request
from enterprise_sources import SourceUnavailable,SourceDenied
from enterprise_aws_jobs_contract import config,native_check,AwsDocumentTaskContract
from enterprise_google_jobs_acceptance import MemoryLedger
from enterprise_aws_hosts import VerifiedHosts


def verified_hosts(value):
    return VerifiedHosts(value['hostPolicySha256'],(('arn:aws:ecs:'+value['region']+':'+value['accountId']+':container-instance/document-parser/'+'a'*32,'i-'+'a'*17),),time.monotonic()+120)


def envelope(raw,identifier):
    return json.dumps({'format':'enterprise-document-job-v1','requestId':identifier,'status':'ok',
        'document':{'format':'enterprise-document-v1','sha256':hashlib.sha256(raw).hexdigest(),
                    'mediaType':'text/plain','text':raw.decode()}}).encode()


class Objects:
    def __init__(self):self.raw=None;self.calls=[];self.forge=False
    def put(self,identifier,side,raw):self.raw=raw;self.calls.append(('put',identifier,side));return '"'+'d'*32+'"'
    def load(self,identifier,side,condition=None):
        self.calls.append(('load',identifier,side))
        return envelope(b'FORGED'if self.forge else self.raw,identifier)
    def delete(self,identifier,side):self.calls.append(('delete',identifier,side))


class Ecs:
    def __init__(self,model):
        self.model=model;self.calls=[];self.definition=None;self.task=None
        self.register_lost=self.run_lost=self.delete_failure=self.foreign=self.running=False
        self.exit_code=0
    def call(self,operation,**values):
        name=''.join(piece.title()for piece in operation.split('_'))
        native_check(values,self.model.operation_model(name).input_shape)
        self.calls.append((operation,copy.deepcopy(values)))
        owned=config();prefix='arn:aws:ecs:'+owned['region']+':'+owned['accountId']+':'
        if operation=='register_task_definition':
            self.definition=prefix+'task-definition/'+values['family']+':1'
            if self.register_lost:raise SourceUnavailable('lost_registration_ack')
            return {'taskDefinition':{'taskDefinitionArn':self.definition}}
        if operation=='run_task':
            self.task={'taskArn':prefix+'task/document-parser/'+'f'*32,'clusterArn':owned['clusterArn'],
                       'startedBy':values['startedBy'],'taskDefinitionArn':self.definition,'containerInstanceArn':verified_hosts(owned).members[0][0]}
            if self.run_lost:raise SourceUnavailable('lost_run_ack')
            return {'tasks':[copy.deepcopy(self.task)],'failures':[]}
        if operation=='describe_tasks':
            value={**self.task,'lastStatus':'RUNNING'if self.running else'STOPPED',
                   'containers':[{'name':name,'lastStatus':'STOPPED','exitCode':self.exit_code if name=='parser'else 0}for name in ['download','parser','upload']]}
            if self.foreign:value['startedBy']='unowned'
            return {'tasks':[value],'failures':[]}
        if operation=='list_tasks':return {'taskArns':[self.task['taskArn']]if self.task else[]}
        if operation=='stop_task':self.running=False;return {'task':copy.deepcopy(self.task)}
        if operation=='list_task_definitions':return {'taskDefinitionArns':[self.definition]if self.definition else[]}
        if operation=='deregister_task_definition':return {'taskDefinition':{'taskDefinitionArn':self.definition}}
        if operation=='delete_task_definitions':
            if self.delete_failure:return {'failures':[{'reason':'PRIVATE upstream'}]}
            return {'taskDefinitions':[],'failures':[]}
        raise AssertionError(operation)


class AwsExecution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):AwsDocumentTaskContract.setUpClass();cls.model=AwsDocumentTaskContract.model
    def setUp(self):
        self.api=Ecs(self.model);self.objects=Objects();self.ledger=MemoryLedger();self.checked=[]
        self.runner=EcsDocuments(config(),api=self.api,objects=self.objects,ledger=self.ledger,
            host_check=lambda value:(self.checked.append(value),verified_hosts(value))[1],poll_seconds=.01)
        self.raw=b'PRIVATE owned policy.'
    def test_success_executes_native_shapes_validates_result_and_cleans_both_objects(self):
        guards=[];value=self.runner.from_source(self.raw,'text/plain',lambda:guards.append(True))
        self.assertEqual(value['text'],self.raw.decode());self.assertGreater(len(guards),5)
        self.assertEqual(self.checked,[config()]);self.assertEqual(self.ledger.rows,{})
        self.assertEqual([v[2]for v in self.objects.calls if v[0]=='delete'],['input','result'])
        self.assertNotIn(self.raw.decode(),json.dumps(self.api.calls))
        launch=next(value for op,value in self.api.calls if op=='run_task')
        self.assertEqual(launch['launchType'],'EC2');self.assertFalse(launch['enableExecuteCommand'])
    def test_untracked_initial_revocation_and_failed_host_policy_create_no_remote_bytes(self):
        self.runner.ledger=None
        with self.assertRaises(SourceUnavailable):self.runner.from_source(self.raw,'text/plain',lambda:None)
        self.runner.ledger=self.ledger
        def denied():raise SourceDenied('revoked')
        with self.assertRaises(SourceDenied):self.runner.from_source(self.raw,'text/plain',denied)
        def bad_host(value):raise SourceUnavailable('host_policy_changed')
        self.runner.host_check=bad_host
        with self.assertRaises(SourceUnavailable):self.runner.from_source(self.raw,'text/plain',lambda:None)
        self.assertEqual(self.api.calls,[]);self.assertEqual(self.objects.calls,[]);self.assertEqual(self.ledger.rows,{})
    def test_lost_registration_ack_still_finds_and_removes_owned_definition(self):
        self.api.register_lost=True
        with self.assertRaisesRegex(SourceUnavailable,'lost_registration_ack'):self.runner.from_source(self.raw,'text/plain',lambda:None)
        self.assertIn('delete_task_definitions',[op for op,_ in self.api.calls])
        self.assertEqual(next(iter(self.ledger.rows.values()))['state'],'settling')
    def test_lost_run_ack_stops_live_task_before_owned_object_cleanup(self):
        self.api.run_lost=True;self.api.running=True
        with self.assertRaisesRegex(SourceUnavailable,'lost_run_ack'):self.runner.from_source(self.raw,'text/plain',lambda:None)
        self.assertIn('stop_task',[op for op,_ in self.api.calls]);self.assertFalse(self.api.running)
        self.assertEqual(next(iter(self.ledger.rows.values()))['state'],'settling')
    def test_nonzero_parser_exit_and_forged_result_never_yield_text(self):
        self.api.exit_code=2
        with self.assertRaises(SourceUnavailable):self.runner.from_source(self.raw,'text/plain',lambda:None)
        self.assertFalse(any(v[0]=='load'for v in self.objects.calls))
        self.api.exit_code=0;self.objects.forge=True
        with self.assertRaises(ValueError):self.runner.from_source(self.raw,'text/plain',lambda:None)
    def test_cleanup_failure_withholds_success_and_keeps_persistent_retry_debt(self):
        self.api.delete_failure=True
        with self.assertRaisesRegex(SourceUnavailable,'cleanup_unavailable'):self.runner.from_source(self.raw,'text/plain',lambda:None)
        row=next(iter(self.ledger.rows.values()));self.assertEqual(row['phase'],'succeeded');self.assertEqual(row['state'],'pending')
        self.assertEqual([v[2]for v in self.objects.calls if v[0]=='delete'],['input','result'])
    def test_foreign_task_is_never_stopped_or_adopted(self):
        self.api.running=True;self.api.foreign=True
        with self.assertRaises(SourceUnavailable):self.runner.from_source(self.raw,'text/plain',lambda:None)
        self.assertNotIn('stop_task',[op for op,_ in self.api.calls])
    def test_runtime_target_and_configuration_are_immutable(self):
        env={'REGION':config()['region'],'AWS_ACCOUNT_ID':config()['accountId'],'WORKER_ROLE_ARN':config()['workerRoleArn']}
        self.runner.bind_runtime('aws',env)
        for provider,changed in [('gcp',env),('aws',{**env,'REGION':'us-east-1'}),('aws',{**env,'WORKER_ROLE_ARN':config()['transferRoleArn']})]:
            with self.assertRaises(ValueError):self.runner.bind_runtime(provider,changed)
        with self.assertRaises(TypeError):self.runner.config['region']='us-east-1'
    def test_repeated_native_page_token_is_bounded(self):
        def repeated(operation,**values):return {'taskArns':[],'nextToken':'same'}
        self.api.call=repeated
        with self.assertRaises(SourceUnavailable):self.runner.listed('list_tasks','taskArns',cluster=config()['clusterArn'])
    def test_native_sdk_wrapper_sanitizes_errors_and_rejects_other_operations(self):
        class Broken:
            def run_task(self,**value):raise RuntimeError('PRIVATE native response')
        api=EcsDocumentApi('ap-southeast-2',client=Broken())
        with self.assertRaisesRegex(SourceUnavailable,'^document_job_unavailable$'):api.call('run_task')
        with self.assertRaises(ValueError):api.call('execute_command')


class S3:
    def __init__(self):self.calls=[];self.version={};self.region='ap-southeast-2';self.body=io.BytesIO(b'policy');self.encryption='AES256';self.etag='"'+'a'*32+'"'
    def get_bucket_location(self,**values):self.calls.append(('location',values));return {'LocationConstraint':self.region}
    def get_bucket_versioning(self,**values):self.calls.append(('versioning',values));return self.version
    def put_object(self,**values):self.calls.append(('put',values));return {'ETag':self.etag,'ServerSideEncryption':self.encryption}
    def get_object(self,**values):self.calls.append(('get',values));return {'Body':self.body,'ContentLength':6,'ETag':self.etag,'ServerSideEncryption':self.encryption}
    def delete_object(self,**values):self.calls.append(('delete',values));return {}


class AwsObjects(unittest.TestCase):
    def setUp(self):
        self.api=S3();self.objects=S3DocumentObjects('owned-document-bytes','ap-southeast-2','123456789012',client=self.api);self.identifier='c'*64
    def test_owner_conditional_write_hash_and_read_are_native_and_bounded(self):
        token=self.objects.put(self.identifier,'input',b'policy');self.assertEqual(token,self.api.etag)
        self.assertEqual(self.objects.load(self.identifier,'input',token),b'policy');self.assertTrue(self.api.body.closed)
        sent=next(value for op,value in self.api.calls if op=='put')
        self.assertEqual(sent['IfNoneMatch'],'*');self.assertEqual(sent['ServerSideEncryption'],'AES256');self.assertIn('ChecksumSHA256',sent)
        for _,value in self.api.calls:self.assertEqual(value['ExpectedBucketOwner'],'123456789012')
    def test_versioned_suspended_or_foreign_region_rejects_before_writing(self):
        for version,region in [({'Status':'Enabled'},'ap-southeast-2'),({'Status':'Suspended'},'ap-southeast-2'),({},'us-east-1')]:
            self.api.version=version;self.api.region=region
            with self.assertRaises(SourceUnavailable):self.objects.put(self.identifier,'input',b'policy')
        self.assertFalse(any(op=='put'for op,_ in self.api.calls))
    def test_wrong_etag_length_encryption_and_stream_failure_withhold_bytes(self):
        for mutation in ['etag','length','encryption','read']:
            api=S3();self.objects.client=api
            if mutation=='etag':api.etag='"'+'b'*32+'"'
            if mutation=='length':api.body=io.BytesIO(b'long policy')
            if mutation=='encryption':api.encryption='aws:kms'
            if mutation=='read':api.body.close()
            with self.assertRaises(SourceUnavailable):self.objects.load(self.identifier,'input','"'+'a'*32+'"')
            self.assertTrue(api.body.closed)
    def test_invalid_object_key_is_never_forwarded(self):
        for identifier,side in [('../other','input'),(self.identifier,'../../result')]:
            with self.assertRaises(ValueError):object_key(identifier,side)
        self.assertEqual(self.api.calls,[])
    def test_actual_sdk_stubber_accepts_owner_and_conditional_shapes_without_network(self):
        import boto3
        from botocore.stub import Stubber
        client=boto3.Session().client('s3',region_name='ap-southeast-2',aws_access_key_id='OWNED_SYNTHETIC_ID',aws_secret_access_key='OWNED_SYNTHETIC_NOT_A_CREDENTIAL')
        owner={'Bucket':'owned-document-bytes','ExpectedBucketOwner':'123456789012'}
        with Stubber(client)as stub:
            stub.add_response('get_bucket_location',{'LocationConstraint':'ap-southeast-2'},owner)
            stub.add_response('get_bucket_versioning',{},owner)
            import base64
            expected={**owner,'Key':object_key(self.identifier,'input'),'Body':b'policy','IfNoneMatch':'*','ContentType':'application/octet-stream','ServerSideEncryption':'AES256','ChecksumSHA256':base64.b64encode(hashlib.sha256(b'policy').digest()).decode()}
            stub.add_response('put_object',{'ETag':self.api.etag,'ServerSideEncryption':'AES256'},expected)
            self.objects.client=client;self.assertEqual(self.objects.put(self.identifier,'input',b'policy'),self.api.etag);stub.assert_no_pending_responses()
        client.close()


class AwsTransferFiles(unittest.TestCase):
    def test_metadata_rejects_extra_fields_duplicate_keys_and_noncanonical_request(self):
        value=transfer_metadata(config(),request(b'policy','text/plain','c'*64),'"'+'a'*32+'"')
        self.assertEqual(metadata(json.dumps(value)),value)
        for encoded in [json.dumps({**value,'token':'PRIVATE'}),'{}',json.dumps(value)[:-1]+',"bucket":"other"}']:
            with self.assertRaises(ValueError):metadata(encoded)
    def test_fresh_file_handoff_binds_bytes_and_rejects_reuse_and_symlinks(self):
        raw=b'policy';identifier='c'*64;value=transfer_metadata(config(),request(raw,'text/plain',identifier),'"'+'a'*32+'"')
        class NativeBytes:
            def __init__(self):self.uploads=[]
            def load(self,*args):return raw
            def put(self,*args):self.uploads.append(args)
        objects=NativeBytes()
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);(root/'input').mkdir();(root/'output').mkdir()
            # Host fixture mocks UID ownership only; actual CHOWN is a Linux gate.
            with patch('enterprise_aws_transfer.os.fchown'):
                download(value,objects,folder)
                with self.assertRaises(ValueError):download(value,objects,folder)
            encoded=envelope(raw,identifier);(root/'output/result.json').write_bytes(encoded)
            upload(value,objects,folder);self.assertEqual(objects.uploads,[(identifier,'result',encoded)])
            (root/'output/result.json').unlink();(root/'output/result.json').symlink_to(root/'input/document')
            with self.assertRaises(OSError):upload(value,objects,folder)


if __name__=='__main__':unittest.main(verbosity=2)
