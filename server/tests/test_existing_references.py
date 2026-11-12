import unittest
from server.contracts import Data
from server.emulation_routes import emulate,EmulationRequest
from server.tests.test_emulation import project,HAS_MOTO

class ExistingReferenceTests(unittest.TestCase):
    def test_reference_contract_accepts_existing_service(self):
        value=Data(label='atmem.ai',kind='resource',provider='gcp',origin='existing',binding='existing-service',service='Firebase Hosting')
        self.assertEqual(value.binding,'existing-service')

    @unittest.skipUnless(HAS_MOTO,'Optional Moto backend not installed')
    def test_existing_site_does_not_block_real_generated_runtime_checks(self):
        p=project('02-document-compute')
        p['nodes'].append({'id':'existing-site','type':'resource','position':{'x':0,'y':0},'data':{'label':'atmem.ai','kind':'resource','provider':'gcp','origin':'existing','service':'Firebase Hosting'}})
        result=emulate(EmulationRequest(project=p))
        self.assertEqual(result['status'],'passed',result)
        self.assertTrue(result['checks'])
        self.assertIn('existing-references.json',result['fileDigests'])
        self.assertFalse(result['cloudOperations'])
        self.assertEqual(result['terraformApply'],'not_run')
        p['edges'].append({'id':'unimplemented-site-flow','source':'existing-site','target':p['nodes'][0]['id'],'label':'Requires implementation'})
        blocked=emulate(EmulationRequest(project=p))
        self.assertEqual(blocked['status'],'blocked')
        self.assertEqual(blocked['checks'],[])
