import json,subprocess,unittest
from pathlib import Path
from server.emulation_routes import EmulationRequest,emulate
ROOT=Path(__file__).resolve().parents[2]
class StructuredEmulationTests(unittest.TestCase):
    def test_product_worker_executes_generated_structured_web_without_cloud_access(self):
        code="import {structuredWebProject} from './tests/fixtures/structured-web-project.mjs';console.log(JSON.stringify(structuredWebProject()));"
        project=json.loads(subprocess.check_output(['node','--input-type=module','-e',code],cwd=ROOT,text=True))
        report=emulate(EmulationRequest(project=project))
        self.assertEqual(report['status'],'passed',report)
        self.assertFalse(report['cloudOperations']);self.assertEqual(report['modelMode'],'scripted-fixture')
        checks=[c for c in report['checks'] if 'structured operation' in c['name']]
        self.assertEqual(len(checks),1);self.assertTrue(checks[0]['passed']);self.assertEqual(checks[0]['evidence'],'host-runtime-with-scripted-policy-identity-model-fixtures')
        self.assertTrue(any('JWT' in limit for limit in report['limitations']) or any('Cognito' in limit for limit in report['limitations']))
