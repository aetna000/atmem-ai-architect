import json
from pathlib import Path
import subprocess
import unittest
from server.emulation_routes import EmulationRequest,emulate

ROOT=Path(__file__).resolve().parents[2]

class AzureEmulationTests(unittest.TestCase):
    def project(self):
        script="import {azureStructuredProject} from './tests/fixtures/azure-structured-project.mjs'; console.log(JSON.stringify(azureStructuredProject()));"
        return json.loads(subprocess.check_output(['node','--input-type=module','-e',script],cwd=ROOT,text=True))

    def test_emitted_application_executes_with_network_denied_and_explicit_boundaries(self):
        result=emulate(EmulationRequest(project=self.project()))
        self.assertEqual(result['status'],'passed',result)
        self.assertFalse(result['cloudOperations'])
        self.assertEqual(result['backend'],'host-asgi-scripted-azure')
        self.assertGreaterEqual(result['checks'][0]['testsRun'],15)
        self.assertEqual(result['checks'][0]['evidence'],'host-runtime-cryptographic-jwt-scripted-azure-transport')
        self.assertTrue(any('container' in text for text in result['limitations']))

    def test_unimplemented_database_keeps_the_composition_blocked(self):
        project=self.project()
        project['nodes'].append({'id':'ledger','position':{'x':0,'y':0},'data':{'label':'Durable account ledger','provider':'azure','kind':'resource','service':'Azure Database for PostgreSQL'}})
        result=emulate(EmulationRequest(project=project))
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['checks'],[])
