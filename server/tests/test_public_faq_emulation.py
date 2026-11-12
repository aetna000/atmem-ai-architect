import json
from pathlib import Path
import subprocess
import unittest
from server.emulation_routes import EmulationRequest,emulate

ROOT=Path(__file__).resolve().parents[2]
class PublicFaqEmulationTests(unittest.TestCase):
    def project(self,provider):
        return json.loads(subprocess.check_output(['node','--input-type=module','-e',"import {publicFaqProject} from './tests/fixtures/public-faq-project.mjs';console.log(JSON.stringify(publicFaqProject("+json.dumps(provider)+")));"],cwd=ROOT,text=True))
    def test_public_lifecycle_executes_without_cloud_or_real_model_claims(self):
        for provider in ['aws','azure','gcp','ibm']:
            with self.subTest(provider=provider):
                result=emulate(EmulationRequest(project=self.project(provider)))
                self.assertEqual(result['status'],'passed',result);self.assertEqual(result['backend'],'host-asgi-scripted-public-catalog');self.assertFalse(result['cloudOperations']);self.assertEqual(result['modelMode'],'scripted-fixture');self.assertGreaterEqual(result['checks'][0]['testsRun'],30)
                self.assertEqual(result['checks'][0]['evidence'],'host-asgi-scripted-public-catalog-'+provider)
    def test_additional_unimplemented_scope_blocks_runtime_instead_of_disappearing(self):
        project=self.project('aws');project['nodes'].append({'id':'private','position':{'x':0,'y':0},'data':{'label':'Required private documents','kind':'resource','provider':'aws','service':'Amazon S3'}})
        result=emulate(EmulationRequest(project=project));self.assertEqual(result['status'],'blocked');self.assertEqual(result['checks'],[])
