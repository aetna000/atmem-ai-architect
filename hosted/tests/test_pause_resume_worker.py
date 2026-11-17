"""Operator safety tests. No Google Cloud calls, VM starts or model jobs."""
from contextlib import redirect_stdout
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'deploy/pause-resume-worker.py'
spec = importlib.util.spec_from_file_location('pause_resume_worker', PATH)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class PauseResumeWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name);self.state = self.root / 'state'
        script = '#!/bin/bash\nexit 0\n'
        self.config = {'project': 'fixture-project', 'zone': 'us-central1-a', 'instance': 'worker-fixture', 'instanceId': '1234',
                       'machineType': 'e2-medium', 'serviceAccount': 'worker@fixture-project.iam.gserviceaccount.com',
                       'disks': [{'name': 'boot', 'boot': True, 'deviceName': 'boot', 'autoDelete': True, 'sizeGb': 30},
                                 {'name': 'state', 'boot': False, 'deviceName': 'state', 'autoDelete': False, 'sizeGb': 30}],
                       'network': 'workers', 'subnet': 'workers', 'internalIp': '10.1.0.2',
                       'startupScriptSha256': hashlib.sha256(script.encode()).hexdigest()}
        self.config_path = self.root / 'config.json';self.config_path.write_text(json.dumps(self.config))
        base = 'https://www.googleapis.com/compute/v1/projects/fixture-project/'
        self.row = {'id': '1234', 'name': 'worker-fixture', 'zone': base + 'zones/us-central1-a', 'status': 'TERMINATED',
                    'machineType': base + 'zones/us-central1-a/machineTypes/e2-medium', 'deletionProtection': True,
                    'disks': [{'source': base + 'zones/us-central1-a/disks/' + d['name'], 'boot': d['boot'],
                               'deviceName': d['deviceName'], 'autoDelete': d['autoDelete'], 'diskSizeGb': str(d['sizeGb']),
                               'mode': 'READ_WRITE', 'interface': 'SCSI'} for d in self.config['disks']],
                    'networkInterfaces': [{'name': 'nic0', 'network': base + 'global/networks/workers',
                                           'subnetwork': base + 'regions/us-central1/subnetworks/workers', 'networkIP': '10.1.0.2',
                                           'accessConfigs': [{'name': 'external-nat', 'type': 'ONE_TO_ONE_NAT', 'networkTier': 'PREMIUM'}]}],
                    'serviceAccounts': [{'email': self.config['serviceAccount'], 'scopes': ['https://www.googleapis.com/auth/cloud-platform']}],
                    'metadata': {'items': [{'key': 'startup-script', 'value': script}]}}

    def invoke(self, action, *, rows=None, extra=()):
        output = io.StringIO()
        with patch.object(worker, 'CONFIG_PATH', self.config_path), patch.object(worker, 'describe', side_effect=rows or [copy.deepcopy(self.row), copy.deepcopy(self.row)]), \
             patch.object(worker, 'run', return_value='') as command, patch.object(worker, 'cloud', return_value='[]'), \
             patch.object(worker, 'readiness', return_value={'ready': True, 'modelJobsSubmitted': 0}) as ready, \
             patch('sys.argv', ['pause-resume-worker.py', action, '--state-dir', str(self.state), *extra]), redirect_stdout(output):
            result = worker.main()
        return result, json.loads(output.getvalue()), command, ready

    def test_repeated_stopped_shutdown_preserves_pause_baseline_and_reports_drift(self):
        worker.capture(self.config, self.row, self.state)
        before = (self.state / 'latest-pause.json').read_bytes()
        source = (self.state / 'startup-script-preserved.sh').read_bytes()
        changed = copy.deepcopy(self.row);changed['machineType'] = changed['machineType'].replace('e2-medium', 'e2-standard-8')
        code, report, command, _ = self.invoke('stop', rows=[changed])
        self.assertEqual(code, 1);self.assertFalse(report['configurationMatchesPaused'])
        self.assertEqual((self.state / 'latest-pause.json').read_bytes(), before)
        self.assertEqual((self.state / 'startup-script-preserved.sh').read_bytes(), source)
        command.assert_not_called()
        code, report, command, _ = self.invoke('stop')
        self.assertEqual(code, 0);self.assertEqual(report['status'], 'TERMINATED')
        self.assertEqual((self.state / 'latest-pause.json').read_bytes(), before)
        command.assert_not_called()

    def test_fresh_checkout_rejects_replaced_disks_or_changed_identity_before_start(self):
        for mutate in ['disk', 'account', 'machine', 'network', 'instance']:
            row = copy.deepcopy(self.row)
            if mutate == 'disk':row['disks'][1]['source'] += '-other'
            elif mutate == 'account':row['serviceAccounts'][0]['email'] = 'other@example.invalid'
            elif mutate == 'machine':row['machineType'] += '-other'
            elif mutate == 'network':row['networkInterfaces'][0]['network'] += '-other'
            else:row['id'] = 'another-instance'
            with self.subTest(mutate=mutate), patch.object(worker, 'CONFIG_PATH', self.config_path), \
                 patch.object(worker, 'describe', return_value=row), patch.object(worker, 'run') as command, \
                 patch('sys.argv', ['worker', 'start', '--state-dir', str(self.state)]):
                with self.assertRaises(RuntimeError):worker.main()
                command.assert_not_called()
        self.assertFalse((self.state / 'latest-pause.json').exists())

    def test_first_start_compares_captured_baseline_again_after_start(self):
        changed = copy.deepcopy(self.row);changed['status'] = 'RUNNING';changed['disks'][1]['autoDelete'] = True
        with patch.object(worker, 'CONFIG_PATH', self.config_path), patch.object(worker, 'describe', side_effect=[self.row, changed]), \
             patch.object(worker, 'run', return_value='') as command, patch.object(worker, 'readiness') as ready, \
             patch('sys.argv', ['worker', 'start', '--state-dir', str(self.state)]):
            with self.assertRaisesRegex(RuntimeError, 'running.*configuration'):worker.main()
            self.assertEqual(command.call_count, 1);ready.assert_not_called()
        saved = json.loads((self.state / 'latest-pause.json').read_text())
        self.assertFalse(saved['configuration']['disks'][1]['autoDelete'])

    def test_start_is_idempotent_and_dry_run_never_starts_compute(self):
        worker.capture(self.config, self.row, self.state)
        running = copy.deepcopy(self.row);running['status'] = 'RUNNING'
        running['networkInterfaces'][0]['accessConfigs'][0]['natIP'] = '192.0.2.1'
        code, report, command, ready = self.invoke('start', rows=[running, running])
        self.assertEqual(code, 0);command.assert_not_called();ready.assert_called_once()
        self.assertEqual(report['verifiedServiceAccounts'], [self.config['serviceAccount']])
        self.assertTrue(report['readiness']['ready'])
        code, report, command, ready = self.invoke('start', extra=['--dry-run'])
        self.assertEqual(code, 0);self.assertTrue(report['dryRun'])
        command.assert_not_called();ready.assert_not_called()
