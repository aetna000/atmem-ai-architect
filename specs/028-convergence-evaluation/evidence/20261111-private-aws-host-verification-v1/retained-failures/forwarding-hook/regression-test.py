"""Fixed probe observations and native ECS/SSM schemas; no account calls."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'tests/runtime'),str(ROOT/'.local/aws-web-runtime-sdk')]
from enterprise_aws_hosts import EcsHostPolicy,HostApi,VerifiedHosts,command_document
from enterprise_aws_host_probe import inspect_host
from enterprise_aws_jobs_contract import config,native_check
from enterprise_aws_execution_contract import verified_hosts,Ecs,Objects,MemoryLedger
from enterprise_aws_jobs import EcsDocuments
from enterprise_sources import SourceUnavailable
from botocore.model import ServiceModel


class Api:
    def __init__(self,models):
        self.models=models;self.calls=[];self.pending=0;self.mutation=None
    def call(self,service,operation,**values):
        name=''.join(v.title()for v in operation.split('_'));native_check(values,self.models[service].operation_model(name).input_shape)
        self.calls.append((service,operation,copy.deepcopy(values)));c=config();member=verified_hosts(c).members[0]
        if operation=='list_container_instances':return {'containerInstanceArns':[member[0]]}
        if operation=='describe_container_instances':
            return {'containerInstances':[{'containerInstanceArn':member[0],'ec2InstanceId':member[1],'agentConnected':True,'status':'ACTIVE',
                    'attributes':[{'name':'atmem-document-policy','value':c['hostPolicySha256']}]}],'failures':[]}
        if operation=='get_document':
            document=command_document(c)
            if self.mutation=='command':document['parameters']={'commands':{'type':'String'}}
            return {'DocumentVersion':'1','Content':json.dumps(document)}
        if operation=='send_command':return {'Command':{'CommandId':'12345678-1234-1234-1234-123456789abc'}}
        if operation=='get_command_invocation':
            if self.pending:self.pending-=1;return {'Status':'Pending'}
            observation={'format':'enterprise-aws-host-observation-v1','policySha256':c['hostPolicySha256'],'clusterArn':c['clusterArn'],'bootId':'12345678-1234-1234-1234-123456789abc'}
            if self.mutation=='policy':observation['policySha256']='0'*64
            if self.mutation=='extra':observation['private']='PRIVATE'
            reply={'Status':'Success','CommandId':values['CommandId'],'InstanceId':values['InstanceId'],
                   'DocumentName':c['hostDocumentArn'],'DocumentVersion':'1','ResponseCode':0,'StandardErrorContent':'',
                   'StandardOutputContent':json.dumps(observation)}
            if self.mutation=='identity':reply['InstanceId']='i-'+'b'*17
            if self.mutation=='version':reply['DocumentVersion']='2'
            if self.mutation=='stderr':reply['StandardErrorContent']='PRIVATE runtime body'
            if self.mutation=='code':reply['ResponseCode']=1
            return reply
        raise AssertionError(operation)


class NativeHostInspection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models={}
        for service,version in [('ecs','2014-11-13'),('ssm','2014-11-06')]:
            path=ROOT/f'tests/fixtures/providers/aws-{service}-{version}-botocore-1.43.123.json.gz'
            if hashlib.sha256(path.read_bytes()).hexdigest()!=json.loads(path.with_suffix('.provenance.json').read_text())['sha256']:raise ValueError('Native schema changed')
            cls.models[service]=ServiceModel(json.loads(gzip.decompress(path.read_bytes())),service_name=service)
    def setUp(self):self.api=Api(self.models);self.verifier=EcsHostPolicy(config(),api=self.api,poll_seconds=.01)
    def test_exact_document_native_requests_and_returned_hosts_are_bound(self):
        proof=self.verifier(config());placement=proof.placement(config())
        self.assertEqual(placement,[{'type':'memberOf','expression':"ec2InstanceId in ['i-"+'a'*17+"']"}])
        sent=next(value for _,op,value in self.api.calls if op=='send_command')
        self.assertEqual(sent['DocumentHash'],config()['hostDocumentHash']);self.assertEqual(sent['DocumentHashType'],'Sha256')
        self.assertEqual(sent['DocumentVersion'],'1');self.assertNotIn('Parameters',sent)
        self.assertFalse(sent['CloudWatchOutputConfig']['CloudWatchOutputEnabled']);self.assertNotIn('OutputS3BucketName',sent)
    def test_pending_invocation_is_polled_but_only_success_can_qualify(self):
        self.api.pending=1;self.assertIsInstance(self.verifier(config()),VerifiedHosts)
        self.assertEqual(sum(op=='get_command_invocation'for _,op,_ in self.api.calls),2)
    def test_command_mutation_rejected_before_remote_command_submission(self):
        self.api.mutation='command'
        with self.assertRaisesRegex(SourceUnavailable,'^document_host_verification_unavailable$'):self.verifier(config())
        self.assertNotIn('send_command',[op for _,op,_ in self.api.calls])
    def test_wrong_identity_policy_version_errors_and_extra_output_never_qualify(self):
        for mutation in ['policy','identity','version','stderr','code','extra']:
            with self.subTest(mutation=mutation):
                self.api.mutation=mutation
                with self.assertRaisesRegex(SourceUnavailable,'^document_host_verification_unavailable$'):self.verifier(config())
    def test_empty_or_paginated_pool_and_disconnected_agent_fail_closed(self):
        original=self.api.call
        for mutation in ['empty','page','agent']:
            def call(service,operation,**values):
                value=original(service,operation,**values)
                if operation=='list_container_instances':
                    if mutation=='empty':value['containerInstanceArns']=[]
                    if mutation=='page':value['nextToken']='more'
                if operation=='describe_container_instances'and mutation=='agent':value['containerInstances'][0]['agentConnected']=False
                return value
            self.api.call=call
            with self.assertRaises(SourceUnavailable):self.verifier(config())
            self.api.call=original
    def test_expired_duplicate_foreign_or_unbounded_host_proofs_are_rejected(self):
        valid=verified_hosts(config())
        for proof in [VerifiedHosts(valid.policy_sha256,valid.members,0),VerifiedHosts(valid.policy_sha256,valid.members,float('inf')),
                      VerifiedHosts(valid.policy_sha256,valid.members*2,time.monotonic()+120),
                      VerifiedHosts(valid.policy_sha256,((valid.members[0][0].replace('123456789012','000000000000'),valid.members[0][1]),),time.monotonic()+120)]:
            with self.assertRaises(SourceUnavailable):proof.placement(config())
    def test_real_controller_pins_launch_to_verified_instances_and_checks_final_host(self):
        api=Ecs(self.models['ecs']);objects=Objects();runner=EcsDocuments(config(),api=api,objects=objects,ledger=MemoryLedger(),host_check=self.verifier,poll_seconds=.01)
        self.assertEqual(runner.from_source(b'policy','text/plain',lambda:None)['text'],'policy')
        launched=next(value for op,value in api.calls if op=='run_task')
        self.assertEqual(launched['placementConstraints'],verified_hosts(config()).placement(config()))
        original=api.call
        def wrong(operation,**values):
            value=original(operation,**values)
            if operation=='describe_tasks':value['tasks'][0]['containerInstanceArn']='unreviewed'
            return value
        api.call=wrong
        with self.assertRaises(SourceUnavailable):runner.from_source(b'policy','text/plain',lambda:None)
    def test_false_or_unstructured_host_callback_cannot_admit_work(self):
        objects=Objects();runner=EcsDocuments(config(),api=object(),objects=objects,ledger=MemoryLedger(),host_check=lambda value:None)
        with self.assertRaisesRegex(SourceUnavailable,'verification_required'):runner.from_source(b'policy','text/plain',lambda:None)
        self.assertEqual(objects.calls,[])
    def test_fixed_document_has_no_caller_interpolation_or_secret_inputs(self):
        document=command_document(config());self.assertEqual(document['parameters'],{})
        command=document['mainSteps'][0]['inputs']['runCommand'][0]
        self.assertNotIn('{{',command);self.assertNotIn('PRIVATE',command)
        self.assertTrue(command.startswith('exec /usr/bin/python3 -I -c '))
    def test_host_api_only_allows_fixed_inspection_operations_and_sanitizes_failures(self):
        class Broken:
            def send_command(self,**values):raise RuntimeError('PRIVATE upstream')
        api=HostApi('ap-southeast-2',ssm=Broken())
        with self.assertRaisesRegex(SourceUnavailable,'^document_host_verification_unavailable$'):api.call('ssm','send_command')
        with self.assertRaises(ValueError):api.call('ssm','update_document')


class ProbeObservations(unittest.TestCase):
    def setUp(self):
        self.expected={'format':'enterprise-aws-host-policy-v1','clusterArn':config()['clusterArn'],'policySha256':config()['hostPolicySha256']}
        self.ecs={'ECS_CLUSTER':self.expected['clusterArn'],'ECS_ENABLE_TASK_IAM_ROLE':'true','ECS_ENGINE_TASK_CLEANUP_WAIT_DURATION':'1s',
                  'ECS_ENABLE_TASK_IAM_ROLE_NETWORK_HOST':'false','ECS_INSTANCE_ATTRIBUTES':json.dumps({'atmem-document-policy':self.expected['policySha256']})}
        self.files={'/etc/ecs/ecs.config':'\n'.join(key+'='+value for key,value in self.ecs.items()),'/etc/docker/daemon.json':json.dumps({'log-driver':'none','live-restore':False}),
                    '/proc/sys/kernel/random/boot_id':'12345678-1234-1234-1234-123456789abc'}
        self.mode=None;self.calls=[]
    def command(self,argv):
        self.calls.append(argv)
        if argv[1]=='info':
            if 'LoggingDriver'in argv[-1]:return json.dumps('json-file'if self.mode=='logging'else'none')
            if 'LiveRestoreEnabled'in argv[-1]:return json.dumps(self.mode=='restore')
            return json.dumps(['name=seccomp,profile=unconfined'if self.mode=='seccomp'else'name=seccomp,profile=builtin'])
        if argv[1]=='network':return json.dumps({'com.docker.network.bridge.name':'other'if self.mode=='bridge'else'docker0'})
        if argv[1]=='inspect':
            changed={**self.ecs}
            if self.mode=='agent':changed['ECS_ENGINE_TASK_CLEANUP_WAIT_DURATION']='3h'
            return json.dumps([key+'='+value for key,value in changed.items()])
        destination='fd00:ec2::254/128'if 'ip6tables'in argv[0]else'169.254.169.254/32'
        if argv[-1]=='FORWARD':return '-A FORWARD -j ACCEPT'if self.mode=='hook'else'-A FORWARD -j DOCKER-USER'
        rule='-A DOCKER-USER -i docker0 -d '+destination+' -j DROP'
        return ('-A DOCKER-USER -j ACCEPT\n'if self.mode=='shadowed'else'')+rule
    def inspect(self):return inspect_host(self.expected,read=lambda name:self.files[name],command=self.command)
    def test_probe_returns_only_bound_observation_after_read_only_checks(self):
        result=self.inspect();self.assertEqual(set(result),{'format','policySha256','clusterArn','bootId'})
        self.assertEqual(result['policySha256'],self.expected['policySha256']);self.assertEqual(len(self.calls),7)
        self.assertTrue(all('-S'in argv or argv[1]in {'info','network','inspect'}for argv in self.calls))
    def test_actual_logging_restore_seccomp_bridge_agent_and_shadowed_rules_fail(self):
        for mode in ['logging','restore','seccomp','bridge','agent','shadowed','hook']:
            with self.subTest(mode=mode):
                self.mode=mode
                with self.assertRaises(ValueError):self.inspect()
    def test_wrong_cluster_cleanup_or_duplicate_config_fails_before_docker(self):
        original=self.files['/etc/ecs/ecs.config']
        for changed in [original.replace('1s','3h'),original.replace('cluster/document-parser','cluster/other'),original+'\nECS_CLUSTER=other']:
            self.files['/etc/ecs/ecs.config']=changed
            with self.assertRaises(ValueError):self.inspect()
        self.assertEqual(self.calls,[])
    def test_missing_or_malformed_host_state_is_not_adopted(self):
        self.files['/etc/docker/daemon.json']='invalid'
        with self.assertRaises(ValueError):self.inspect()


if __name__=='__main__':unittest.main(verbosity=2)
