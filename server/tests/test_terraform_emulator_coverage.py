"""Coverage must never promote partial lifecycle evidence into qualification."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('emulator_coverage', Path(__file__).resolve().parents[2] / 'scripts/qualify-terraform-emulator.py')
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)


class CoverageEvidenceTests(unittest.TestCase):
    def report(self, status='passed', **resource):
        return {'status': status, 'resources': [{'type': 'aws_apprunner_service', 'applied': True, **resource}], 'stages': []}

    def test_apply_without_successful_teardown_is_not_qualified(self):
        report = self.report('failed')
        report['stages'] = [{'name': 'Destroy', 'status': 'failed'}]
        self.assertEqual(coverage.classify(report)['aws_apprunner_service']['result'], 'applied-in-failing-fixture')

    def test_known_missing_api_and_deadline_are_different(self):
        gap = self.report('unsupported', applied=False, error='Operation not implemented', emulatorGap=True)
        deadline = self.report('blocked', applied=False, error='Execution deadline', emulatorGap=False, timedOut=True)
        self.assertEqual(coverage.classify(gap)['aws_apprunner_service']['result'], 'emulator-gap')
        self.assertNotEqual(coverage.classify(deadline)['aws_apprunner_service']['result'], 'emulator-gap')

    def test_provider_refresh_does_not_become_sdk_evidence(self):
        row = coverage.classify(self.report())['aws_apprunner_service']
        self.assertEqual(row['result'], 'qualified')
        self.assertEqual(row['sdkVerified'], 0)

    def test_failed_sdk_comparison_is_retained(self):
        row = coverage.classify(self.report('failed', checks=[{'passed': False}]))['aws_apprunner_service']
        self.assertEqual(row['sdkVerified'], 0)
        self.assertNotEqual(row['result'], 'qualified')


if __name__ == '__main__':
    unittest.main()
