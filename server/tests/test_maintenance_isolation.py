import json
import os
from pathlib import Path
import unittest

from server.maintenance.workers import MaintenanceWorker
from server.maintenance.isolation import qualify


class RegistrationTests(unittest.TestCase):
    def test_missing_or_unqualified_registration_never_executes(self):
        with self.assertRaises(ValueError):
            MaintenanceWorker({}, {})
        config = {'schemaVersion': 1, 'imageId': 'sha256:' + 'a' * 64, 'platform': 'linux/amd64',
                  'endpoint': 'unix:///not/a/socket', 'qualificationDigest': 'a' * 64, 'runnerDigest': 'a' * 64}
        with self.assertRaisesRegex(ValueError, 'not qualified'):
            MaintenanceWorker(config, {})


@unittest.skipUnless(os.getenv('ATMEM_MAINTENANCE_TEST_CONFIG'), 'Explicit qualified local Docker registration required')
class RealIsolationTests(unittest.TestCase):
    def test_hostile_source_provider_boundary_timeout_cancel_and_output(self):
        config = json.loads(Path(os.environ['ATMEM_MAINTENANCE_TEST_CONFIG']).read_text())
        result = qualify(config['endpoint'], config['imageId'], config['platform'])
        self.assertEqual(result['status'], 'passed', result)
        self.assertTrue(all(result['results']['hostile']['findings'].values()))

    def test_changed_runner_and_false_qualification_denied(self):
        path = Path(os.environ['ATMEM_MAINTENANCE_TEST_CONFIG'])
        config, report = json.loads(path.read_text()), json.loads(path.with_suffix('.qualification.json').read_text())
        report['status'] = 'failed'
        with self.assertRaises(ValueError):
            MaintenanceWorker(config, report)
        config['runnerDigest'] = 'b' * 64
        with self.assertRaises(ValueError):
            MaintenanceWorker(config, report)
