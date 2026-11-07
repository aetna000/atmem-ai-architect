import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock
spec=importlib.util.spec_from_file_location('catalog_admin',Path(__file__).resolve().parents[2]/'src/runtime/catalog_admin.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class CatalogAdminTests(unittest.TestCase):
    def document(self):return {'id':'doc','title':'Policy','text':'Synthetic policy','allowedSubjects':['alice'],'allowedRegions':['AU']}
    def test_create_is_atomic_and_capacity_bounded(self):
        client=Mock();result=module.put_document(client,'catalog',self.document())
        ops=client.transact_write_items.call_args.kwargs['TransactItems']
        self.assertEqual(ops[0]['Put']['ConditionExpression'],'attribute_not_exists(recordId)');self.assertEqual(ops[1]['Update']['ExpressionAttributeValues'][':limit'],{'N':'100'});self.assertTrue(result['revision'])
    def test_update_and_delete_require_exact_revision(self):
        client=Mock();module.put_document(client,'catalog',self.document(),'old')
        self.assertEqual(client.put_item.call_args.kwargs['ExpressionAttributeValues'],{':expected':{'S':'old'}})
        module.delete_document(client,'catalog','doc','old')
        self.assertEqual(client.transact_write_items.call_args.kwargs['TransactItems'][0]['Delete']['ConditionExpression'],'revision = :expected')
        with self.assertRaises(ValueError):module.delete_document(client,'catalog','doc','')
    def test_acl_fields_are_required_and_not_defaulted_public(self):
        bad=self.document();del bad['allowedSubjects']
        with self.assertRaises(ValueError):module.validate_document(bad)
        revoked={**self.document(),'allowedSubjects':[]};self.assertEqual(module.validate_document(revoked)['allowedSubjects'],[])
