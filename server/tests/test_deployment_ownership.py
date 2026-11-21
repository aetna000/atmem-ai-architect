import copy
import unittest
from pydantic import ValidationError
from server.contracts import Data


class DeploymentOwnershipTests(unittest.TestCase):
    def test_imported_state_cannot_be_reinterpreted_as_application_source(self):
        services = {'aws': 'Amazon ECS Fargate', 'azure': 'Azure Container Apps',
                    'gcp': 'Google Cloud Run', 'ibm': 'IBM Code Engine'}
        for provider, service in services.items():
            with self.subTest(provider=provider):
                value = {'label': 'Existing deployment', 'kind': 'resource',
                         'provider': provider, 'service': service,
                         'origin': 'imported Pulumi state',
                         'implementation': 'container-service',
                         'deploymentMode': 'create'}
                before = copy.deepcopy(value)
                with self.assertRaisesRegex(ValidationError, 'Imported cloud-state metadata'):
                    Data.model_validate(value)
                self.assertEqual(value, before)
                value['deploymentMode'] = 'reference'
                self.assertEqual(Data.model_validate(value).origin, 'imported Pulumi state')
                value.update(origin='existing', deploymentMode='create')
                self.assertEqual(Data.model_validate(value).deploymentMode, 'create')
