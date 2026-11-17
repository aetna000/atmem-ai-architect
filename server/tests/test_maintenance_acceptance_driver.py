"""The real acceptance driver must remain inert before explicit scoped approval."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[2] / 'scripts/maintenance-github-acceptance.py'
spec = importlib.util.spec_from_file_location('maintenance_acceptance', PATH)
driver = importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)


class AcceptanceDriverTests(unittest.TestCase):
    def test_default_plan_is_local_and_names_only_exact_disposable_scope(self):
        output = io.StringIO()
        with patch('sys.argv', [str(PATH)]), patch.object(driver.GitHubBroker, '__init__', side_effect=AssertionError('No broker in plan')), contextlib.redirect_stdout(output):
            driver.main()
        plan = json.loads(output.getvalue())
        self.assertEqual(len(plan['repositories']), 4)
        self.assertTrue(all(item['visibility'] == 'private' for item in plan['repositories']))
        self.assertTrue(all(item['repository'].startswith('aetna000/atmem-maintenance-r3-') for item in plan['repositories']))
        self.assertEqual(plan['scopeDigest'], driver.digest({k: v for k, v in plan.items() if k != 'scopeDigest'}))
        self.assertIn('v1.0.0', plan['repositories'][1]['files']['main.tf'])

    def test_missing_scope_confirmation_creates_no_state_and_selects_no_keychain(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('sys.argv', [str(PATH), 'prepare', '--home', folder]), patch.object(driver.GitHubBroker, '__init__', side_effect=AssertionError('No broker before approval')):
                with self.assertRaisesRegex(ValueError, 'approved disposable scope'):
                    driver.main()
            self.assertEqual(list(Path(folder).iterdir()), [])
        for owner in ['aetna000/existing-repo', '../other', 'https://github.com/aetna000']:
            with self.assertRaises(ValueError):driver.scope(owner)
