import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import MagicMock
from botocore.exceptions import ClientError

spec=importlib.util.spec_from_file_location('storage_qualification',Path(__file__).resolve().parents[2]/'scripts/aws-storage-verify.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class StorageQualificationTests(unittest.TestCase):
    def clients(self):
        s3=MagicMock();anon=MagicMock()
        s3.get_public_access_block.return_value={'PublicAccessBlockConfiguration':dict.fromkeys(['BlockPublicAcls','IgnorePublicAcls','BlockPublicPolicy','RestrictPublicBuckets'],True)}
        s3.get_bucket_versioning.return_value={'Status':'Enabled'}
        s3.get_bucket_encryption.return_value={'ServerSideEncryptionConfiguration':{'Rules':[{'ApplyServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]}}
        s3.get_bucket_ownership_controls.return_value={'OwnershipControls':{'Rules':[{'ObjectOwnership':'BucketOwnerEnforced'}]}}
        s3.get_bucket_policy.return_value={'Policy':'{"Statement":[{"Effect":"Deny","Principal":"*","Action":"s3:*","Resource":["arn:aws:s3:::test-bucket","arn:aws:s3:::test-bucket/*"],"Condition":{"Bool":{"aws:SecureTransport":"false"}}}]}'}
        s3.put_object.side_effect=[{'VersionId':'own-v1'},{'VersionId':'own-v2'}]
        s3.get_object.side_effect=[{'Body':io.BytesIO(b'synthetic qualification document\n')},{'Body':io.BytesIO(b'synthetic updated document\n')}]
        anon.get_object.side_effect=ClientError({'Error':{'Code':'AccessDenied'}},'GetObject')
        return s3,anon

    def test_success_deletes_only_versions_created_by_run(self):
        s3,anon=self.clients();result=module.verify(s3,anon,'test-bucket','123456789012')
        self.assertEqual(result['status'],'passed');self.assertEqual(result['writesAttempted'],2)
        self.assertEqual(result['cleanup'],'created_versions_deleted')
        calls=s3.delete_object.call_args_list
        self.assertEqual([c.kwargs['VersionId'] for c in calls],['own-v1','own-v2'])
        self.assertTrue(all(c.kwargs['Key']==result['objectKey'] for c in calls))
        s3.delete_bucket.assert_not_called()

    def test_failed_preflight_never_writes(self):
        s3,anon=self.clients();s3.get_bucket_versioning.return_value={}
        result=module.verify(s3,anon,'test-bucket','123456789012')
        self.assertEqual(result['status'],'failed');s3.put_object.assert_not_called();s3.delete_object.assert_not_called()

    def test_failed_read_cleans_known_versions_and_records_failure(self):
        s3,anon=self.clients();s3.get_object.side_effect=RuntimeError('synthetic failure')
        result=module.verify(s3,anon,'test-bucket','123456789012')
        self.assertEqual(result['status'],'failed');self.assertEqual(result['cleanup'],'created_versions_deleted');self.assertEqual(s3.delete_object.call_count,1)

    def test_missing_write_version_never_guesses_a_delete(self):
        s3,anon=self.clients();s3.put_object.side_effect=[{}]
        result=module.verify(s3,anon,'test-bucket','123456789012')
        self.assertEqual(result['status'],'failed');self.assertEqual(result['cleanup'],'uncertain_write');self.assertTrue(result['objectKey']);s3.delete_object.assert_not_called()

    def test_cleanup_failure_is_not_a_pass(self):
        s3,anon=self.clients();s3.delete_object.side_effect=RuntimeError('denied')
        result=module.verify(s3,anon,'test-bucket','123456789012')
        self.assertEqual(result['status'],'failed');self.assertEqual(result['cleanup'],'failed')

    def test_journal_records_the_object_key_before_any_write(self):
        s3,anon=self.clients();events=[]
        def put(**kwargs):
            self.assertEqual(events[-1]['stage'],'write_pending')
            self.assertEqual(events[-1]['objectKey'],kwargs['Key'])
            return {'VersionId':f"own-v{len([x for x in events if x['stage']=='write_pending'])}"}
        s3.put_object.side_effect=put
        result=module.verify(s3,anon,'test-bucket','123456789012',lambda value:events.append(value))
        self.assertEqual(result['status'],'passed')
        self.assertEqual(events[-1]['stage'],'cleanup_pending')

    def test_unscoped_tls_statement_is_not_accepted(self):
        s3,anon=self.clients();s3.get_bucket_policy.return_value={'Policy':'{"Statement":[{"Effect":"Deny","Condition":{"Bool":{"aws:SecureTransport":"false"}}}]}'}
        result=module.verify(s3,anon,'test-bucket','123456789012')
        self.assertEqual(result['status'],'failed');s3.put_object.assert_not_called()


class DeploymentPromptTests(unittest.TestCase):
    def test_prompt_separates_physical_resources_from_payloads(self):
        from server.prompts import SYSTEM_PROMPT
        self.assertIn('distinguish physical deployment resources from actors and payloads',SYSTEM_PROMPT)
        self.assertIn('not a separately provisioned output service',SYSTEM_PROMPT)
        self.assertIn('direct IAM-authenticated Lambda invocation',SYSTEM_PROMPT)

class QualificationSkillTests(unittest.TestCase):
    def test_updated_reviewed_skills_have_matching_versions_and_integrity(self):
        from server.skills import registry
        catalog={s['id']:s for s in registry()}
        for name in ['aws','terraform','devops']:
            self.assertTrue(catalog[name]['integrity'])
            self.assertEqual(catalog[name]['version'],{'aws':'1.4.0','terraform':'1.3.1','devops':'1.1.0'}[name])
        self.assertIn('schema-valid empty configuration',catalog['terraform']['instructions'])
        self.assertIn('Stop retrying a model',catalog['devops']['instructions'])

    def test_published_skill_entries_fit_the_memory_boundary(self):
        from server.skills import registry, publication_text
        from server.memory_service import safe
        for skill in registry():
            text=publication_text(skill)
            self.assertLessEqual(len(text),1900,skill['id'])
            self.assertTrue(safe(text),skill['id'])

class StorageAccessContractTests(unittest.TestCase):
    def test_typed_contract_round_trip_and_invalid_values(self):
        from server.contracts import Project
        p={'version':1,'revision':1,'name':'Storage','nodes':[
          {'id':'operator','position':{'x':0,'y':0},'data':{'label':'Operator','kind':'resource','provider':'tools','origin':'existing','binding':'aws-iam-principal'}},
          {'id':'bucket','position':{'x':100,'y':0},'data':{'label':'Bucket','kind':'source','provider':'aws','service':'Amazon S3'}}],
          'edges':[{'id':'access','source':'operator','target':'bucket','access':'s3-read-write'}]}
        parsed=Project.model_validate(p).model_dump()
        self.assertEqual(parsed['nodes'][0]['data']['binding'],'aws-iam-principal')
        self.assertEqual(parsed['edges'][0]['access'],'s3-read-write')
        p['edges'][0]['access']='s3:*'
        with self.assertRaises(ValueError):Project.model_validate(p)
        p['edges'][0]['access']='s3-read'
        p['nodes'][0]['data']['binding']='create-admin-role'
        with self.assertRaises(ValueError):Project.model_validate(p)
