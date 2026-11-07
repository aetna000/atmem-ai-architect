import copy
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from server.app import app,TOKEN
from server.emulation_routes import emulate,EmulationRequest
from server.emulation_worker import Worker,deny_network,EmulationFailure
from server.emulation_adapters import s3_version_notifications

ROOT=Path(__file__).resolve().parents[2]
try:
    import moto
    HAS_MOTO=True
except ImportError:HAS_MOTO=False

def project(scenario):
    root=ROOT/'examples/aws'/scenario
    meta=json.loads((root/'results.json').read_text())
    return json.loads((root/'history'/meta['sourceRun']/'round-2/workspace.json').read_text())

class EmulationBoundaryTests(unittest.TestCase):
    def test_token_and_server_owned_files_boundary(self):
        client=TestClient(app);headers={'Authorization':f'Bearer {TOKEN}'}
        self.assertEqual(client.post('/api/emulation/run',json={'project':{}}).status_code,401)
        self.assertEqual(client.post('/api/emulation/run',headers=headers,json={'project':{},'files':{'evil.py':'raise Exception()'}}).status_code,422)
        self.assertEqual(client.post('/api/emulation/run',headers=headers,json={'project':{},'endpoint':'https://aws.example'}).status_code,422)
    def test_disabled_and_missing_worker_never_pass(self):
        with patch.dict(os.environ,{'ATMEM_ARCHITECT_EMULATION_ENABLED':'0'}):self.assertEqual(emulate(EmulationRequest(project={}))['status'],'unavailable')
        with patch('server.emulation_routes.importlib.util.find_spec',return_value=None):self.assertEqual(emulate(EmulationRequest(project={}))['status'],'unavailable')
    def test_admission_and_timeout_are_not_passes(self):
        client=TestClient(app);headers={'Authorization':f'Bearer {TOKEN}'}
        with patch('server.emulation_routes.LOCK.locked',return_value=True):
            self.assertEqual(client.post('/api/emulation/run',headers=headers,json={'project':{}}).status_code,409)
        with patch('server.emulation_routes.emulate',side_effect=subprocess.TimeoutExpired('worker',90)):
            response=client.post('/api/emulation/run',headers=headers,json={'project':{}})
            self.assertEqual(response.status_code,504);self.assertIn('no pass',response.json()['detail'])
    def test_network_escape_is_denied(self):
        with deny_network():
            with self.assertRaises(EmulationFailure):socket.getaddrinfo('example.com',443)
            with socket.socket() as s:
                with self.assertRaises(EmulationFailure):s.connect(('127.0.0.1',1))
    @unittest.skipUnless(HAS_MOTO,'Optional Moto backend not installed')
    def test_unsupported_and_empty_designs_do_not_pass(self):
        p=project('02-document-compute');p['nodes'][1]['data']['implementation']='not-supported'
        result=emulate(EmulationRequest(project=p));self.assertEqual(result['status'],'blocked')
        p['nodes']=[];p['edges']=[]
        self.assertNotEqual(emulate(EmulationRequest(project=p))['status'],'passed')
    @unittest.skipUnless(HAS_MOTO,'Optional Moto backend not installed')
    def test_worker_never_inherits_real_credentials_or_proxy(self):
        real_run=subprocess.run;calls=[]
        def run(*args,**kwargs):
            calls.append(kwargs['env']);return real_run(*args,**kwargs)
        with patch.dict(os.environ,{'AWS_SECRET_ACCESS_KEY':'do-not-forward','AWS_PROFILE':'private','AWS_ENDPOINT_URL':'https://example.com','HTTPS_PROXY':'https://example.com','ANTHROPIC_API_KEY':'do-not-forward'}),patch('server.emulation_routes.subprocess.run',side_effect=run):
            result=emulate(EmulationRequest(project=project('02-document-compute')))
        self.assertEqual(result['status'],'passed')
        for env in calls:
            self.assertEqual(env['AWS_SECRET_ACCESS_KEY'],'testing')
            for key in ['AWS_PROFILE','AWS_ENDPOINT_URL','HTTPS_PROXY','ANTHROPIC_API_KEY']:self.assertNotIn(key,env)
        self.assertIn('main.tf.json',result['fileDigests']);self.assertFalse(result['cloudOperations'])
        self.assertFalse(Path(calls[0]['HOME']).exists())

@unittest.skipUnless(HAS_MOTO,'Optional Moto backend not installed')
class EmulationIntegrationTests(unittest.TestCase):
    def test_all_seven_projects_run_actual_generated_code_against_stateful_apis(self):
        manifest=json.loads((ROOT/'examples/aws/manifest.json').read_text())
        for example in manifest['scenarios']:
            with self.subTest(scenario=example['id']):
                result=emulate(EmulationRequest(project=project(example['id'])))
                self.assertEqual(result['status'],'passed',result.get('checks'))
                self.assertEqual(result['terraformApply'],'not_run')
                self.assertEqual(result['cleanup'],'passed')
                self.assertTrue(result['limitations'])
    def test_broken_generated_handler_is_detected(self):
        real_run=subprocess.run
        def run(args,**kwargs):
            if 'emulation_worker.py' in str(args):
                root=Path(args[-1]);file=next((root/'handlers').glob('*.py'))
                file.write_text('def handler(event, context): return {"wordCount":999,"characterCount":999}\n')
            return real_run(args,**kwargs)
        with patch('server.emulation_routes.subprocess.run',side_effect=run):result=emulate(EmulationRequest(project=project('02-document-compute')))
        self.assertEqual(result['status'],'failed');self.assertTrue(any(not c['passed'] for c in result['checks']))
    def test_missing_generated_trigger_is_not_repaired_by_harness(self):
        real_run=subprocess.run
        def run(args,**kwargs):
            if 'emulation_worker.py' in str(args):
                p=Path(args[-1])/'main.tf.json';tf=json.loads(p.read_text());tf['resource'].pop('aws_s3_bucket_notification');p.write_text(json.dumps(tf))
            return real_run(args,**kwargs)
        with patch('server.emulation_routes.subprocess.run',side_effect=run):result=emulate(EmulationRequest(project=project('03-async-documents')))
        self.assertEqual(result['status'],'failed');self.assertIn('notification',result['checks'][-1]['message'])
    def test_moto_adapter_preserves_triggering_version_after_multiple_writes(self):
        import boto3
        from moto import mock_aws
        from moto.s3 import notifications
        original=notifications._get_s3_event
        with mock_aws(),s3_version_notifications(),deny_network():
            s3=boto3.client('s3',region_name='ap-southeast-2');sqs=boto3.client('sqs',region_name='ap-southeast-2')
            bucket='atmem-version-probe';s3.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':'ap-southeast-2'});s3.put_bucket_versioning(Bucket=bucket,VersioningConfiguration={'Status':'Enabled'})
            url=sqs.create_queue(QueueName='probe')['QueueUrl'];arn=sqs.get_queue_attributes(QueueUrl=url,AttributeNames=['QueueArn'])['Attributes']['QueueArn']
            s3.put_bucket_notification_configuration(Bucket=bucket,NotificationConfiguration={'QueueConfigurations':[{'QueueArn':arn,'Events':['s3:ObjectCreated:*']}]})
            first=s3.put_object(Bucket=bucket,Key='a b.txt',Body=b'first')['VersionId'];second=s3.put_object(Bucket=bucket,Key='a b.txt',Body=b'second')['VersionId']
            events=[json.loads(m['Body']) for m in sqs.receive_message(QueueUrl=url,MaxNumberOfMessages=10)['Messages']]
            records=[r for e in events for r in e.get('Records',[])]
            self.assertEqual([r['s3']['object']['versionId'] for r in records],[first,second])
            self.assertEqual(records[0]['s3']['object']['key'],'a+b.txt')
            self.assertEqual(s3.get_object(Bucket=bucket,Key='a b.txt',VersionId=records[0]['s3']['object']['versionId'])['Body'].read(),b'first')
        self.assertIs(notifications._get_s3_event,original)
