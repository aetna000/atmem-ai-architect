"""Independently reconcile pinned wheel metadata against emitted runtime locks."""
import json
from pathlib import Path
import unittest
from packaging.utils import canonicalize_name
from server.runtime_dependency_locks import dependency_gaps

ROOT=Path(__file__).resolve().parents[2]

class RuntimeLockTests(unittest.TestCase):
    def test_all_runtime_dependency_graphs_are_closed_for_the_deployment_platform(self):
        for name in ['azure-python-lock.json','web-python-lock.json']:
            lock=json.loads((ROOT/'src/runtime'/name).read_text())
            self.assertEqual(dependency_gaps(lock),set(),name)

    def test_missing_fastapi_dependency_is_detected_without_an_ambient_sdk_masking_it(self):
        lock=json.loads((ROOT/'src/runtime/web-python-lock.json').read_text())
        lock['sources']=[row for row in lock['sources'] if canonicalize_name(row['name'])!='opentelemetry-api']
        self.assertIn('fastapi requires opentelemetry-api',dependency_gaps(lock))

    def test_incompatible_pin_is_detected(self):
        lock=json.loads((ROOT/'src/runtime/web-python-lock.json').read_text())
        next(row for row in lock['sources'] if canonicalize_name(row['name'])=='h11')['version']='0.1.0'
        self.assertTrue(any('incompatible h11' in gap for gap in dependency_gaps(lock)))
