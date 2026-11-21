"""Independent public IAM catalog regressions; no SDK/account calls."""
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('owned_infrastructure_verifier',ROOT/'scripts/verify-aws-document-infrastructure.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)


class NativeAuthorization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.metadata=verifier.catalogs()
    def policy(self,action,resource,condition=None):
        return {'Statement':[{'Effect':'Allow','Action':[action],'Resource':resource,**({'Condition':condition}if condition else{})}]}
    def test_native_cluster_registration_and_task_actions_have_distinct_resources(self):
        prefix='arn:aws:ecs:ap-southeast-2:123456789012:'
        for action,resource in [('ecs:RegisterContainerInstance','cluster/owned'),('ecs:DeregisterContainerInstance','cluster/owned'),('ecs:Poll','container-instance/owned/*'),('ecs:RunTask','task-definition/document-owned:1'),('ecs:StopTask','task/owned/*')]:
            with self.subTest(action=action):
                self.assertEqual(verifier.policy_shape(self.policy(action,prefix+resource),self.metadata),[action])
                with self.assertRaises(ValueError):verifier.policy_shape(self.policy(action,prefix+'service/wrong/wrong'),self.metadata)
    def test_unknown_actions_and_inapplicable_condition_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unknown native IAM action'):verifier.policy_shape(self.policy('ecs:InventPermission','*'),self.metadata)
        with self.assertRaisesRegex(ValueError,'Unsupported native condition'):verifier.policy_shape(self.policy('ecs:DescribeTaskDefinition','*',{'ArnEquals':{'ecs:cluster':'owned'}}),self.metadata)
    def test_exact_resource_scope_and_native_conditions_survive_validation(self):
        policy=self.policy('ecs:RunTask','arn:aws:ecs:ap-southeast-2:123456789012:task-definition/document-owned:1',{'Bool':{'ecs:enable-execute-command':'false'},'ArnEquals':{'ecs:cluster':'arn:aws:ecs:ap-southeast-2:123456789012:cluster/owned'}})
        self.assertEqual(verifier.policy_shape(policy,self.metadata),['ecs:RunTask'])
    def test_fixed_ssm_document_and_tag_condition_use_native_resource_contracts(self):
        policy=self.policy('ssm:SendCommand','arn:aws:ec2:ap-southeast-2:123456789012:instance/*',{'StringEquals':{'ssm:resourceTag/atmem-document-policy':'a'*64}})
        self.assertEqual(verifier.policy_shape(policy,self.metadata),['ssm:SendCommand'])
        with self.assertRaises(ValueError):verifier.policy_shape(self.policy('ssm:GetDocument','arn:aws:ssm:ap-southeast-2:123456789012:parameter/private'),self.metadata)
    def test_native_s3_object_and_bucket_authority_are_distinct(self):
        self.assertEqual(verifier.policy_shape(self.policy('s3:PutObject','arn:aws:s3:::owned/document-jobs/*'),self.metadata),['s3:PutObject'])
        for action,resource in [('s3:PutObject','arn:aws:s3:::owned'),('s3:GetBucketVersioning','arn:aws:s3:::owned/document-jobs/*')]:
            with self.assertRaises(ValueError):verifier.policy_shape(self.policy(action,resource),self.metadata)


if __name__=='__main__':unittest.main(verbosity=2)
