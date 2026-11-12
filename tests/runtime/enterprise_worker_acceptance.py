"""Owned process configuration and native worker selection, no cloud/SQL calls."""
import asyncio
import copy
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'tests/runtime'),str(ROOT/'.local/azure-runtime-sdk')]
from enterprise_configuration import read_deployment,read_owned_json
from enterprise_worker import executor_configuration,build_executor,run_worker,worker_runtime
import enterprise_worker
from enterprise_deployment_fixture import metadata,REVISION
from enterprise_google_jobs_acceptance import config as google_config


def aws_config():
    prefix='arn:aws:';region='ap-southeast-2';account='123456789012'
    return {'format':'enterprise-aws-document-job-v2','accountId':account,'region':region,'bucket':'owned-document-bytes',
        'clusterArn':prefix+'ecs:'+region+':'+account+':cluster/document-parser','hostPolicySha256':'e'*64,
        'hostDocumentArn':prefix+'ssm:'+region+':'+account+':document/owned-document-host-probe','hostDocumentHash':'f'*64,'hostDocumentVersion':'1',
        'workerRoleArn':prefix+'iam::'+account+':role/question-worker','transferRoleArn':prefix+'iam::'+account+':role/document-transfer','executionRoleArn':prefix+'iam::'+account+':role/document-pull',
        'parserImage':account+'.dkr.ecr.'+region+'.amazonaws.com/document-parser@sha256:'+'a'*64,
        'transferImage':account+'.dkr.ecr.'+region+'.amazonaws.com/document-transfer@sha256:'+'b'*64,
        'taskDefinitionArn':prefix+'ecs:'+region+':'+account+':task-definition/document-owned-parser:1'}


def envelope(provider):
    return {'format':'enterprise-document-executor-v1','provider':provider,'parserRevision':REVISION,
            'configuration':aws_config()if provider=='aws'else google_config()}


def environment(provider):
    native=envelope(provider)['configuration']
    return {'ENTERPRISE_DOCUMENT_EXECUTOR_JSON':json.dumps(envelope(provider)),**(
        {'REGION':native['region'],'AWS_ACCOUNT_ID':native['accountId'],'WORKER_ROLE_ARN':native['workerRoleArn']}if provider=='aws'else
        {'REGION':native['region'],'PROJECT_ID':native['projectId'],'DATABASE_SERVICE_ACCOUNT':native['workerServiceAccount']})}


class OwnedWorkerConfiguration(unittest.TestCase):
    def cli(self,args=(),env=None):
        entry=enterprise_worker.__file__
        # The host uses its reviewed SDK fixture directory; a clean image uses
        # installed dependencies and /app. Never assume host repository paths.
        helper="import runpy,sys;sys.path.insert(0,"+repr(str(ROOT/'.local/azure-runtime-sdk'))+");sys.argv="+repr([entry,*args])+";runpy.run_path("+repr(entry)+",run_name='__main__')"
        return subprocess.run([sys.executable,'-I','-c',helper],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
    def test_deployment_uses_native_environment_or_mounted_configuration_without_mutating_them(self):
        owned=metadata('owned','aws');env={'ENTERPRISE_DEPLOYMENT_JSON':json.dumps(owned)};before=copy.deepcopy(env)
        self.assertEqual(read_deployment(environment=env),owned);self.assertEqual(env,before)
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'deployment.json';path.write_text(json.dumps(owned))
            self.assertEqual(read_deployment(environment={'ENTERPRISE_DEPLOYMENT_FILE':str(path)}),owned)
            with self.assertRaises(ValueError):read_deployment(path,environment=env)
    def test_duplicate_oversize_nonfinite_relative_or_conflicting_metadata_is_rejected(self):
        def load(env):return read_owned_json('owned.json','JSON','FILE',env)
        for env in [{'JSON':'{"provider":"aws","provider":"gcp"}'},{'JSON':'"'+'é'*17000+'"'},
                    {'JSON':'{"x":NaN}'},{'JSON':'{}','FILE':'/owned'},{'FILE':'relative/file'},{'JSON':None},{'JSON':''}]:
            with self.subTest(keys=list(env)):
                with self.assertRaises(ValueError):load(env)
    def test_only_exact_provider_revision_and_native_shape_are_accepted(self):
        owned=metadata('owned','aws');valid=envelope('aws');original=copy.deepcopy(valid)
        result=executor_configuration(valid,owned);result['configuration']['bucket']='changed';self.assertEqual(valid,original)
        for change in [{**valid,'provider':'gcp'},{**valid,'parserRevision':'b'*64},{**valid,'factory':'arbitrary.module'},
                       {**valid,'configuration':{**valid['configuration'],'url':'https://unowned.example'}},
                       {**valid,'configuration':{**valid['configuration'],'parserImage':'registry.example/parser:latest'}}]:
            with self.assertRaises(ValueError):executor_configuration(change,owned)
    def test_aws_and_google_construct_only_their_bound_native_controller_without_network(self):
        with patch('requests.Session.request',side_effect=AssertionError('No startup HTTP')):
            for provider,name in [('aws','EcsDocuments'),('gcp','GoogleBatchDocuments')]:
                with self.subTest(provider=provider):
                    executor=build_executor(metadata('owned',provider),environment(provider))
                    self.assertEqual(type(executor.run).__name__,name);self.assertEqual(executor.artifact_revision,REVISION)
                    self.assertIsNone(executor.run.ledger)
    def test_wrong_native_worker_identity_fails_before_secrets_or_runtime_construction(self):
        for provider,key,value in [('aws','WORKER_ROLE_ARN',aws_config()['transferRoleArn']),('gcp','DATABASE_SERVICE_ACCOUNT',google_config()['vmServiceAccount'])]:
            with self.subTest(provider=provider),patch('enterprise_worker.NativeRuntime')as runtime:
                env={**environment(provider),key:value}
                with self.assertRaises(ValueError):worker_runtime(metadata('owned',provider),env)
                runtime.assert_not_called()
    def test_unimplemented_cloud_never_falls_back_to_a_different_provider(self):
        for provider in ['azure','ibm']:
            value={**envelope('aws'),'provider':provider}
            with self.assertRaisesRegex(ValueError,'implementation is required'):executor_configuration(value,metadata('owned',provider))
    def test_configured_factory_owns_executor_and_does_not_accept_an_injected_override(self):
        with self.assertRaises(ValueError):worker_runtime(metadata('owned','aws'),environment('aws'),executor=object())
    def test_worker_runtime_closes_after_normal_exit_and_queue_failure(self):
        class Runtime:
            def __init__(self,fail):self.closed=False;self.fail=fail;self.concurrency=None
            def worker(self):return self
            async def run(self,**values):
                self.concurrency=values['concurrency']
                if self.fail:raise RuntimeError('PRIVATE upstream')
            def close(self):self.closed=True
        for fail in [False,True]:
            runtime=Runtime(fail)
            if fail:
                with self.assertRaises(RuntimeError):asyncio.run(run_worker(runtime,concurrency=1))
            else:asyncio.run(run_worker(runtime,concurrency=1))
            self.assertTrue(runtime.closed);self.assertEqual(runtime.concurrency,1)
    def test_cli_rejects_unowned_arguments_without_reading_secrets_or_connecting(self):
        run=self.cli(['https://unowned.example/PRIVATE'])
        self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,b'');self.assertNotIn(b'PRIVATE',run.stderr);self.assertNotIn(b'Traceback',run.stderr)
    def test_cli_configuration_failure_does_not_log_raw_metadata_or_traceback(self):
        import os
        values={**os.environ,'ENTERPRISE_DEPLOYMENT_JSON':'PRIVATE BROKEN CONFIGURATION'}
        run=self.cli(env=values)
        self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,b'');self.assertNotIn(b'PRIVATE BROKEN',run.stderr);self.assertNotIn(b'Traceback',run.stderr)
    def test_api_factory_does_not_read_or_construct_worker_configuration(self):
        import os
        from enterprise_native import app_factory
        owned=metadata('owned','aws')
        with patch.dict(os.environ,{'ENTERPRISE_DEPLOYMENT_JSON':json.dumps(owned),'ENTERPRISE_DOCUMENT_EXECUTOR_JSON':'PRIVATE INVALID WORKER CONFIG'}),patch('enterprise_native.NativeRuntime')as runtime:
            app_factory();runtime.assert_called_once_with(owned,os.environ,'api')


if __name__=='__main__':unittest.main(verbosity=2)
