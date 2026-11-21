import json
import subprocess
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from server.app import app, TOKEN
from server.terraform_routes import validate, ValidationRequest

class TerraformTests(unittest.TestCase):
    def test_requires_token_and_rejects_executable_files(self):
        client=TestClient(app)
        self.assertEqual(client.post('/api/terraform/validate',json={'project':{}}).status_code,401)
        self.assertEqual(client.post('/api/terraform/validate',headers={'Authorization':f'Bearer {TOKEN}'},json={'project':{},'files':{'main.tf':'malicious'}}).status_code,422)

    def test_missing_binary_is_not_a_pass(self):
        with patch.dict('os.environ',{},clear=True), patch('server.terraform_routes.shutil.which',return_value=None):
            self.assertEqual(validate(ValidationRequest(project={}))['status'],'unavailable')

    def test_only_server_generated_config_runs_without_credentials(self):
        replies=[subprocess.CompletedProcess([],0,json.dumps({'main.tf.json':'{}'}),''),subprocess.CompletedProcess([],0,'Initialized',''),subprocess.CompletedProcess([],0,'{"valid":true}','')]
        with patch.dict('os.environ',{'AWS_SECRET_ACCESS_KEY':'never-pass','TF_CLI_ARGS':'-bad','ATFORMA_TERRAFORM_BIN':'/trusted/terraform'}), patch('server.terraform_routes.shutil.which',return_value='/trusted/node'), patch('server.terraform_routes.subprocess.run',side_effect=replies) as run:
            result=validate(ValidationRequest(project={}))
        self.assertEqual(result['status'],'passed')
        calls=run.call_args_list
        self.assertEqual(calls[1].args[0][2:],['init','-backend=false','-input=false','-no-color'])
        self.assertEqual(calls[2].args[0][2:],['validate','-json'])
        for call in calls:
            self.assertNotIn('AWS_SECRET_ACCESS_KEY',call.kwargs['env'])
            self.assertNotIn('TF_CLI_ARGS',call.kwargs['env'])

    def test_init_failure_stops_before_validation(self):
        replies=[subprocess.CompletedProcess([],0,json.dumps({'main.tf.json':'{}'}),''),subprocess.CompletedProcess([],1,'','Provider unavailable')]
        with patch.dict('os.environ',{'ATFORMA_TERRAFORM_BIN':'/trusted/terraform'}), patch('server.terraform_routes.shutil.which',return_value='/trusted/node'), patch('server.terraform_routes.subprocess.run',side_effect=replies) as run:
            result=validate(ValidationRequest(project={}))
        self.assertEqual(result['status'],'failed');self.assertEqual(run.call_count,2)

    def test_generated_support_files_and_local_acceptance_checks_are_exercised(self):
        from pathlib import Path
        generated={'main.tf.json':'{}','handlers/demo.py':'def handler(event, context): return {}','app-tests/demo_test.py':'# generated test','tests/storage-access.tftest.hcl':'mock_provider "aws" {}'}
        def invoke(args,**kwargs):
            if args[-1].endswith('terraform-render.mjs'):return subprocess.CompletedProcess(args,0,json.dumps(generated),'')
            folder=Path(kwargs.get('cwd') or args[1].removeprefix('-chdir='))
            self.assertTrue((folder/'handlers/demo.py').exists())
            self.assertNotIn('AWS_ACCESS_KEY_ID',kwargs['env'])
            return subprocess.CompletedProcess(args,0,'passed','')
        with patch.dict('os.environ',{'ATFORMA_TERRAFORM_BIN':'/trusted/terraform','AWS_ACCESS_KEY_ID':'never-pass'}),patch('server.terraform_routes.shutil.which',return_value='/trusted/node'),patch('server.terraform_routes.subprocess.run',side_effect=invoke) as run:
            result=validate(ValidationRequest(project={}))
        self.assertEqual(result['status'],'passed');self.assertEqual(len(result['checks']),4)
        self.assertIn('handlers/demo.py',result['fileDigests']);self.assertEqual(run.call_count,5)

    def test_generation_inconsistency_stops_before_provider_execution(self):
        generated={'main.tf.json':'{}','generation-quality.json':json.dumps({'fatalFindings':[{'code':'execution-hook','message':'Unreviewed provisioner'}]})}
        reply=subprocess.CompletedProcess([],0,json.dumps(generated),'')
        with patch.dict('os.environ',{'ATFORMA_TERRAFORM_BIN':'/trusted/terraform'}), patch('server.terraform_routes.shutil.which',return_value='/trusted/node'), patch('server.terraform_routes.subprocess.run',return_value=reply) as run:
            result=validate(ValidationRequest(project={}))
        self.assertEqual(result['status'],'failed')
        self.assertEqual(run.call_count,1)
        self.assertFalse(result['checks'][0]['passed'])
        self.assertIn('generation-quality.json',result['fileDigests'])

    def test_admitted_modules_run_their_own_schemas_and_nonempty_mock_tests(self):
        generated={'main.tf.json':'{}','units/unit_61/main.tf.json':'{}','units/unit_61/tests/unit.tftest.hcl':'mock_provider "aws" {}','generation-quality.json':json.dumps({'fatalFindings':[],'modules':[{'id':'a','path':'units/unit_61','module':'unit_61'}]})}
        def invoke(args,**kwargs):
            self.assertNotIn('AWS_SECRET_ACCESS_KEY',kwargs['env'])
            if args[-1].endswith('terraform-render.mjs'):return subprocess.CompletedProcess(args,0,json.dumps(generated),'')
            return subprocess.CompletedProcess(args,0,'Success! 4 passed, 0 failed.' if args[2]=='test' else 'Valid','')
        with patch.dict('os.environ',{'ATFORMA_TERRAFORM_BIN':'/trusted/terraform','AWS_SECRET_ACCESS_KEY':'never-pass'}),patch('server.terraform_routes.shutil.which',return_value='/trusted/node'),patch('server.terraform_routes.subprocess.run',side_effect=invoke) as runner:
            result=validate(ValidationRequest(project={}))
        self.assertEqual(result['status'],'passed');self.assertEqual(result['checks'][-1]['testsReported'],4)
        calls=runner.call_args_list;self.assertEqual(len(calls),6)
        for call in calls[3:]:self.assertTrue(call.args[0][1].endswith('/units/unit_61'))

    def test_module_zero_skipped_or_failed_mock_tests_never_pass(self):
        for output,code in [('Success! 0 passed, 0 failed.',0),('Success! 4 passed, 0 failed, 1 skipped.',0),('Success! 4 passed, 0 failed.',1)]:
            generated={'main.tf.json':'{}','generation-quality.json':json.dumps({'fatalFindings':[],'modules':[{'id':'a','path':'units/unit_61'}]})}
            def invoke(args,**kwargs):
                if args[-1].endswith('terraform-render.mjs'):return subprocess.CompletedProcess(args,0,json.dumps(generated),'')
                return subprocess.CompletedProcess(args,code if args[2]=='test' else 0,output if args[2]=='test' else 'Valid','')
            with patch.dict('os.environ',{'ATFORMA_TERRAFORM_BIN':'/trusted/terraform'}),patch('server.terraform_routes.shutil.which',return_value='/trusted/node'),patch('server.terraform_routes.subprocess.run',side_effect=invoke):
                result=validate(ValidationRequest(project={}))
            self.assertEqual(result['status'],'failed');self.assertFalse(result['checks'][-1]['passed'])
