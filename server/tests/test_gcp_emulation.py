import json
from pathlib import Path
import subprocess
import unittest
from server.emulation_routes import EmulationRequest,emulate

ROOT=Path(__file__).resolve().parents[2]
class GoogleStructuredEmulationTests(unittest.TestCase):
    def project(self):
        return json.loads(subprocess.check_output(['node','--input-type=module','-e',"import {gcpStructuredProject} from './tests/fixtures/gcp-structured-project.mjs';console.log(JSON.stringify(gcpStructuredProject()));"],cwd=ROOT,text=True))
    def test_emitted_application_uses_real_local_signatures_and_scripted_cloud_boundaries(self):
        result=emulate(EmulationRequest(project=self.project()))
        self.assertEqual(result['status'],'passed',result)
        self.assertEqual(result['backend'],'host-asgi-scripted-gcp');self.assertFalse(result['cloudOperations'])
        self.assertGreaterEqual(result['checks'][0]['testsRun'],9)
        self.assertEqual(result['checks'][0]['evidence'],'host-runtime-cryptographic-jwt-scripted-gcp-transport')
        self.assertTrue(any('container' in item for item in result['limitations']))
    def test_unimplemented_state_keeps_checks_blocked(self):
        project=self.project();project['nodes'].append({'id':'ledger','position':{'x':0,'y':0},'data':{'label':'Durable ledger','provider':'gcp','kind':'resource','service':'Cloud SQL'}})
        result=emulate(EmulationRequest(project=project));self.assertEqual(result['status'],'blocked');self.assertEqual(result['checks'],[])
