import asyncio,json,unittest
from unittest.mock import patch
from hosted.terraform_emulation import run_isolated
from hosted.native_runtime import NativeWorkspaceRuntime
from server.local_validation import ValidationSpec

class IsolatedEmulationTests(unittest.TestCase):
 def test_only_explicit_emulation_profile_has_long_deadline(self):
  image='sha256:'+'a'*64
  with self.assertRaises(ValueError):ValidationSpec('standard-check',image,('/usr/bin/python',),timeout_seconds=1500)
  spec=ValidationSpec('emulation-check',image,('/usr/bin/python',),timeout_seconds=1500,isolation_profile='terraform-emulation-v1')
  self.assertEqual(spec.timeout_seconds,1500)
 def test_no_complete_container_report_cannot_become_pass(self):
  with patch('hosted.terraform_emulation.DockerValidationWorker') as factory:
   factory.return_value.run.return_value={'status':'passed','output':'partial output','exitCode':0}
   report=run_isolated({'main.tf':'# fixture'},image='sha256:'+'a'*64,endpoint='unix:///not-used')
   self.assertEqual(report['status'],'failed')
   spec=factory.return_value.run.call_args.args[2]
   self.assertEqual(spec.isolation_profile,'terraform-emulation-v1')
   self.assertTrue(spec.executable_scratch)
 def test_container_failure_overrides_claimed_pass(self):
  with patch('hosted.terraform_emulation.DockerValidationWorker') as factory:
   factory.return_value.run.return_value={'status':'failed','output':'ATMEM_EMULATION_REPORT:'+json.dumps({'status':'passed'}),'exitCode':1}
   self.assertEqual(run_isolated({'main.tf':'# fixture'},image='sha256:'+'a'*64,endpoint='unix:///not-used')['status'],'failed')
 def test_native_dispatch_rejects_other_project_before_execution(self):
  runtime=NativeWorkspaceRuntime.__new__(NativeWorkspaceRuntime);runtime.uid='user';runtime.paths={'/api/terraform/emulate'};runtime.methods={'/api/terraform/emulate':['POST']}
  job={'uid':'user','projectId':'owned','path':'/api/terraform/emulate'}
  with self.assertRaisesRegex(ValueError,'another project'):
   asyncio.run(runtime.dispatch(job,{'project':{'id':'other'}},b'',model='unused',policy={}))
