"""Regress the native list/inspect harness failure without cloud operations."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / 'tests/runtime')]
spec = importlib.util.spec_from_file_location('owned_azure_host_qualifier', ROOT / 'scripts/qualify-enterprise-azure-host.py')
qualifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualifier)


class NativeListInspectRegression(unittest.TestCase):
    def test_container_list_is_not_rewritten_as_a_container_inspection(self):
        class Engine:
            def call(self, method, path, body=None, **options):
                if path == qualifier.API + '/containers/json?all=1':
                    return [{'Id': 'a' * 64, 'Image': 'physical'}]
                return {'Id': 'a' * 64, 'Config': {'Image': 'physical'}, 'Mounts': ['unchanged']}
        facade = qualifier.FixtureRegistryEngine(Engine(), {'native': 'physical'})
        listed = facade.call('GET', qualifier.API + '/containers/json?all=1')
        self.assertEqual(listed, [{'Id': 'a' * 64, 'Image': 'physical'}])
        self.assertEqual(facade.observations, [])
        inspected = facade.call('GET', qualifier.API + '/containers/' + 'a' * 64 + '/json')
        self.assertEqual(inspected['Config']['Image'], 'native')
        self.assertEqual(inspected['Mounts'], ['unchanged'])
        self.assertEqual(facade.observations[0]['nativeContainer']['Config']['Image'], 'physical')


if __name__ == '__main__': unittest.main()
