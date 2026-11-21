import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from server.emulation_routes import EmulationRequest,emulate

ROOT=Path(__file__).resolve().parents[2]
class IbmStructuredEmulationTests(unittest.TestCase):
    def project(self):
        return json.loads(subprocess.check_output(['node','--input-type=module','-e',"import {ibmStructuredProject} from './tests/fixtures/ibm-structured-project.mjs';console.log(JSON.stringify(ibmStructuredProject()));"],cwd=ROOT,text=True))
    def test_emitted_source_uses_isolated_runtime_and_explicit_scripted_boundaries(self):
        result=emulate(EmulationRequest(project=self.project()))
        self.assertEqual(result['status'],'passed',result);self.assertEqual(result['backend'],'host-asgi-scripted-ibm');self.assertFalse(result['cloudOperations'])
        self.assertGreaterEqual(result['checks'][0]['testsRun'],12);self.assertEqual(result['checks'][0]['evidence'],'host-runtime-cryptographic-jwt-scripted-ibm-transport')
    def test_missing_worker_does_not_skip_sdk_checks_or_claim_success(self):
        with patch('server.emulation_routes.setting',side_effect=lambda name:'/no-such-ibm-runtime' if name=='IBM_EMULATION_PYTHON' else None):
            result=emulate(EmulationRequest(project=self.project()))
        self.assertEqual(result['status'],'unavailable');self.assertEqual(result['checks'],[])
    def test_unimplemented_state_keeps_runtime_checks_blocked(self):
        project=self.project();project['nodes'].append({'id':'ledger','position':{'x':0,'y':0},'data':{'label':'Durable tenant ledger','kind':'resource','provider':'ibm','service':'IBM Cloudant'}})
        result=emulate(EmulationRequest(project=project));self.assertEqual(result['status'],'blocked');self.assertEqual(result['checks'],[])
