import json
from pathlib import Path
import socket
import subprocess
import unittest
from server.emulation_routes import emulate,EmulationRequest
from server.storage_emulation_worker import loopback_only
ROOT=Path(__file__).resolve().parents[2]

def fixtures():
    result=subprocess.run(['node','--input-type=module','-e',"import {CLOUD_STORAGE_SCENARIOS} from './src/cloud-storage-scenarios.mjs';console.log(JSON.stringify(CLOUD_STORAGE_SCENARIOS))"],cwd=ROOT,text=True,capture_output=True,check=True)
    return json.loads(result.stdout)

class StorageEmulationTests(unittest.TestCase):
    def test_live_local_apis_run_generated_clients(self):
        for scenario in fixtures():
            with self.subTest(provider=scenario['id']):
                result=emulate(EmulationRequest(project=scenario['project']))
                if result['status']=='unavailable':self.skipTest(result['message'])
                self.assertEqual(result['status'],'passed',result)
                self.assertGreaterEqual(len(result['checks']),3)
                self.assertFalse(result['cloudOperations']);self.assertEqual(result['terraformApply'],'not_run')
                self.assertIn('storage_client.py',result['fileDigests'])
                if scenario['id']=='ibm':self.assertEqual(result['backend'],'moto-s3-compatibility')
    def test_missing_access_cannot_produce_pass(self):
        for scenario in fixtures():
            scenario['project']['edges'][0].pop('access')
            result=emulate(EmulationRequest(project=scenario['project']))
            self.assertIn(result['status'],['blocked','unavailable'])
    def test_local_worker_cannot_reach_external_or_unrelated_local_services(self):
        with loopback_only(32123):
            with self.assertRaises(RuntimeError):socket.getaddrinfo('example.com',443)
            with self.assertRaises(RuntimeError):socket.getaddrinfo('127.0.0.1',12345)
            with socket.socket() as sock:
                with self.assertRaises(RuntimeError):sock.connect(('127.0.0.1',12345))
                with self.assertRaises(RuntimeError):sock.connect_ex(('8.8.8.8',443))
