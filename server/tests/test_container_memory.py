import unittest
from pydantic import ValidationError
from server.contracts import Configuration,Data

class ContainerMemoryTests(unittest.TestCase):
    def test_preserves_exact_decimal_and_binary_quantities(self):
        for value in [1000000000,1073741824,51539607552]:
            data=Data(label='Scientific image',kind='resource',provider='ibm',implementation='container-service',config={'containerMemoryBytes':value})
            self.assertEqual(data.model_dump()['config']['containerMemoryBytes'],value)

    def test_rejects_ambiguous_types_and_bounds(self):
        for value in [True,1.5,'1000000000',0,9007199254740992]:
            with self.assertRaises(ValidationError):Configuration(containerMemoryBytes=value)

    def test_container_requirement_cannot_silently_change_other_contracts(self):
        with self.assertRaises(ValidationError):
            Data(label='Other application',kind='resource',provider='aws',implementation='text-statistics',config={'containerMemoryBytes':1000000000})
