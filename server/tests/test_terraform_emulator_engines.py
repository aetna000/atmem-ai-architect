import json
import unittest
import xml.etree.ElementTree as ElementTree

from server import terraform_emulator_engines as engines

NS = '{%s}' % engines.CLOUDFRONT_NS
CACHE = '<CachePolicyConfig xmlns="%s"><Name>%%s</Name><MinTTL>0</MinTTL><DefaultTTL>60</DefaultTTL></CachePolicyConfig>' % engines.CLOUDFRONT_NS
DISTRIBUTION = ('<DistributionConfig xmlns="%s"><CallerReference>%%s</CallerReference><Origins><Quantity>1</Quantity><Items><Origin><Id>site</Id><DomainName>b.s3.amazonaws.com</DomainName>'
                '<S3OriginConfig><OriginAccessIdentity></OriginAccessIdentity></S3OriginConfig></Origin></Items></Origins>'
                '<DefaultCacheBehavior><TargetOriginId>%%s</TargetOriginId><ViewerProtocolPolicy>https-only</ViewerProtocolPolicy><CachePolicyId>%%s</CachePolicyId></DefaultCacheBehavior>'
                '<Comment>fixture</Comment><Enabled>%%s</Enabled></DistributionConfig>') % engines.CLOUDFRONT_NS
OPTIMIZED = '658327ea-f89d-4fab-a63d-7e88639e58f6'


def code(reply):
    return ElementTree.fromstring(reply.body).find(f'{NS}Error/{NS}Code').text


class CloudFrontPolicyTests(unittest.TestCase):
    def setUp(self):
        self.engine = engines.CloudFrontEngine()
        self.call = lambda method, path, body=b'', headers=None, query=None: self.engine.handle(method, path, query or {}, headers or {}, body if isinstance(body, bytes) else body.encode())

    def test_lifecycle_uses_optimistic_locking_and_aws_error_codes(self):
        created = self.call('POST', '/2020-05-31/cache-policy', CACHE % 'fixture')
        self.assertEqual((created.operation, created.status), ('CreateCachePolicy', 201))
        document = ElementTree.fromstring(created.body)
        identity, etag = document.find(f'{NS}Id').text, dict(created.headers)['ETag']
        self.assertEqual(document.find(f'{NS}CachePolicyConfig/{NS}DefaultTTL').text, '60')
        self.assertEqual(code(self.call('POST', '/2020-05-31/cache-policy', CACHE % 'fixture')), 'CachePolicyAlreadyExists')
        path = '/2020-05-31/cache-policy/' + identity
        self.assertEqual(dict(self.call('GET', path).headers)['ETag'], etag)
        self.assertEqual(ElementTree.fromstring(self.call('GET', path + '/config').body).tag, NS + 'CachePolicyConfig')
        self.assertEqual(code(self.call('PUT', path, CACHE % 'renamed')), 'InvalidIfMatchVersion')
        self.assertEqual(code(self.call('PUT', path, CACHE % 'renamed', {'If-Match': 'stale'})), 'PreconditionFailed')
        updated = self.call('PUT', path, CACHE % 'renamed', {'If-Match': etag})
        self.assertNotEqual(dict(updated.headers)['ETag'], etag)
        self.assertEqual(code(self.call('DELETE', path, headers={'If-Match': etag})), 'PreconditionFailed')
        self.assertEqual(self.call('DELETE', path, headers={'If-Match': dict(updated.headers)['ETag']}).status, 204)
        self.assertEqual(code(self.call('GET', path)), 'NoSuchCachePolicy')
        self.assertEqual(self.engine.inventory(), [])

    def test_invalid_documents_are_rejected_not_stored(self):
        for body in ('<not xml', '<Other/>', '<CachePolicyConfig><Name>x</Name></CachePolicyConfig>', CACHE % 'has space'):
            self.assertEqual(self.call('POST', '/2020-05-31/cache-policy', body).status, 400)
        self.assertEqual(self.engine.inventory(), [])

    def test_managed_catalog_is_listed_and_immutable(self):
        listed = ElementTree.fromstring(self.call('GET', '/2020-05-31/cache-policy', query={'Type': ['managed']}).body)
        names = {item.find(f'{NS}CachePolicy/{NS}CachePolicyConfig/{NS}Name').text: item.find(f'{NS}CachePolicy/{NS}Id').text for item in listed.iter(NS + 'CachePolicySummary')}
        self.assertEqual(names['Managed-CachingOptimized'], OPTIMIZED)
        self.assertEqual(names['Managed-CachingDisabled'], '4135ea2d-6df8-44a3-9df3-4b5a84be39ad')
        self.assertEqual({item.find(NS + 'Type').text for item in listed.iter(NS + 'CachePolicySummary')}, {'managed'})
        origin = ElementTree.fromstring(self.call('GET', '/2020-05-31/origin-request-policy/b689b0a8-53d0-40ab-baf2-68738e2966ac').body)
        self.assertEqual(origin.find(f'{NS}OriginRequestPolicyConfig/{NS}Name').text, 'Managed-AllViewerExceptHostHeader')
        self.assertEqual(origin.find(f'{NS}OriginRequestPolicyConfig/{NS}HeadersConfig/{NS}HeaderBehavior').text, 'allExcept')
        managed = '/2020-05-31/cache-policy/' + OPTIMIZED
        etag = dict(self.call('GET', managed).headers)['ETag']
        self.assertEqual(code(self.call('DELETE', managed, headers={'If-Match': etag})), 'IllegalDelete')
        self.assertEqual(code(self.call('PUT', managed, CACHE % 'mine', {'If-Match': etag})), 'IllegalUpdate')
        self.assertEqual(ElementTree.fromstring(self.call('GET', '/2020-05-31/cache-policy', query={'Type': ['custom']}).body).find(NS + 'Quantity').text, '0')

    def test_lists_paginate_with_markers(self):
        first = ElementTree.fromstring(self.call('GET', '/2020-05-31/cache-policy', query={'MaxItems': ['3']}).body)
        self.assertEqual(first.find(NS + 'Quantity').text, '3')
        second = ElementTree.fromstring(self.call('GET', '/2020-05-31/cache-policy', query={'MaxItems': ['100'], 'Marker': [first.find(NS + 'NextMarker').text]}).body)
        self.assertEqual(int(second.find(NS + 'Quantity').text), len(engines.MANAGED['cache-policy']) - 3)
        self.assertIsNone(second.find(NS + 'NextMarker'))

    def test_other_cloudfront_paths_pass_to_the_base_emulator(self):
        self.assertIsNone(self.call('GET', '/2020-05-31/origin-access-control'))
        self.assertIsNone(self.call('GET', '/2020-05-31/tagging', query={'Resource': ['arn:aws:cloudfront::123456789012:function/x']}))


class CloudFrontDistributionTests(CloudFrontPolicyTests):
    def create(self, reference='ref', origin='site', policy=OPTIMIZED, enabled='true'):
        return self.call('POST', '/2020-05-31/distribution', DISTRIBUTION % (reference, origin, policy, enabled))

    def test_stored_configuration_is_normalized_like_cloudfront_without_changing_sent_values(self):
        created = self.create()
        self.assertEqual(created.status, 201)
        config = ElementTree.fromstring(created.body).find(NS + 'DistributionConfig')
        value = lambda path: config.find('/'.join(NS + part for part in path.split('/'))).text
        self.assertEqual((value('OriginGroups/Quantity'), value('Aliases/Quantity'), value('CacheBehaviors/Quantity'), value('Logging/Enabled')), ('0', '0', '0', 'false'))
        self.assertEqual((value('PriceClass'), value('HttpVersion'), value('Restrictions/GeoRestriction/RestrictionType')), ('PriceClass_All', 'http2', 'none'))
        self.assertEqual(value('DefaultCacheBehavior/AllowedMethods/CachedMethods/Quantity'), '2')
        self.assertEqual((value('Comment'), value('Enabled'), value('DefaultCacheBehavior/CachePolicyId')), ('fixture', 'true', OPTIMIZED))
        self.assertEqual(ElementTree.fromstring(created.body).find(NS + 'Status').text, 'Deployed')

    def test_references_must_exist(self):
        self.assertEqual(code(self.create(origin='missing')), 'NoSuchOrigin')
        self.assertEqual(code(self.create(policy='00000000-0000-0000-0000-000000000000')), 'NoSuchCachePolicy')
        self.assertEqual(self.create().status, 201)
        self.assertEqual(code(self.create()), 'DistributionAlreadyExists')

    def test_delete_requires_disabling_and_releases_attached_policies(self):
        policy = self.call('POST', '/2020-05-31/cache-policy', CACHE % 'attached')
        policy_id, policy_etag = ElementTree.fromstring(policy.body).find(f'{NS}Id').text, dict(policy.headers)['ETag']
        created = self.create(policy=policy_id)
        identity, etag = ElementTree.fromstring(created.body).find(NS + 'Id').text, dict(created.headers)['ETag']
        self.assertEqual(code(self.call('DELETE', '/2020-05-31/cache-policy/' + policy_id, headers={'If-Match': policy_etag})), 'CachePolicyInUse')
        path = '/2020-05-31/distribution/' + identity
        self.assertEqual(code(self.call('DELETE', path, headers={'If-Match': etag})), 'DistributionNotDisabled')
        disabled = self.call('PUT', path + '/config', DISTRIBUTION % ('ref', 'site', policy_id, 'false'), {'If-Match': etag})
        self.assertEqual(disabled.status, 200)
        self.assertEqual(code(self.call('PUT', path + '/config', DISTRIBUTION % ('other', 'site', policy_id, 'false'), {'If-Match': dict(disabled.headers)['ETag']})), 'IllegalUpdate')
        self.assertEqual(self.call('DELETE', path, headers={'If-Match': dict(disabled.headers)['ETag']}).status, 204)
        self.assertEqual(self.call('DELETE', '/2020-05-31/cache-policy/' + policy_id, headers={'If-Match': policy_etag}).status, 204)
        self.assertEqual(self.engine.inventory(), [])

    def test_tags_and_listing(self):
        tagged = ('<DistributionConfigWithTags xmlns="%s">' % engines.CLOUDFRONT_NS) + (DISTRIBUTION % ('t', 'site', OPTIMIZED, 'true')).replace(' xmlns="%s"' % engines.CLOUDFRONT_NS, '') + '<Tags><Items><Tag><Key>a</Key><Value>1</Value></Tag></Items></Tags></DistributionConfigWithTags>'
        created = self.call('POST', '/2020-05-31/distribution', tagged, query={'WithTags': ['']})
        self.assertEqual((created.operation, created.status), ('CreateDistributionWithTags', 201))
        arn = ElementTree.fromstring(created.body).find(NS + 'ARN').text
        tags = lambda: {tag.find(NS + 'Key').text: tag.find(NS + 'Value').text for tag in ElementTree.fromstring(self.call('GET', '/2020-05-31/tagging', query={'Resource': [arn]}).body).iter(NS + 'Tag')}
        self.assertEqual(tags(), {'a': '1'})
        self.call('POST', '/2020-05-31/tagging', '<Tags><Items><Tag><Key>b</Key><Value>2</Value></Tag></Items></Tags>', query={'Resource': [arn], 'Operation': ['Tag']})
        self.call('POST', '/2020-05-31/tagging', '<TagKeys><Items><Key>a</Key></Items></TagKeys>', query={'Resource': [arn], 'Operation': ['Untag']})
        self.assertEqual(tags(), {'b': '2'})
        self.assertEqual(ElementTree.fromstring(self.call('GET', '/2020-05-31/distribution').body).find(NS + 'Quantity').text, '1')


class StepFunctionsTests(unittest.TestCase):
    def validate(self, definition):
        engine = engines.StepFunctionsValidationEngine(lambda region: ['arn:aws:states:ap-southeast-2:123456789012:stateMachine:known'])
        body = json.dumps({'definition': definition if isinstance(definition, str) else json.dumps(definition)}).encode()
        return json.loads(engine.handle('POST', '/', {}, {'X-Amz-Target': 'AWSStepFunctions.ValidateStateMachineDefinition'}, body).body)

    def test_valid_definitions_pass(self):
        self.assertEqual(self.validate({'StartAt': 'Done', 'States': {'Done': {'Type': 'Succeed'}}}), {'result': 'OK', 'diagnostics': [], 'truncated': False})
        nested = {'StartAt': 'Fan', 'States': {'Fan': {'Type': 'Parallel', 'End': True, 'Branches': [{'StartAt': 'A', 'States': {'A': {'Type': 'Pass', 'End': True}}}]}}}
        choice = {'StartAt': 'Pick', 'States': {'Pick': {'Type': 'Choice', 'Choices': [{'Variable': '$.a', 'IsPresent': True, 'Next': 'Work'}], 'Default': 'Stop'},
                                               'Work': {'Type': 'Task', 'Resource': 'arn:aws:states:::sqs:sendMessage', 'Next': 'Wait', 'Catch': [{'ErrorEquals': ['States.ALL'], 'Next': 'Stop'}]},
                                               'Wait': {'Type': 'Wait', 'Seconds': 1, 'End': True}, 'Stop': {'Type': 'Fail'}}}
        for definition in (nested, choice):
            self.assertEqual(self.validate(definition)['result'], 'OK')

    def test_broken_definitions_fail_with_located_diagnostics(self):
        cases = {
            'INVALID_JSON_DESCRIPTION': '{not json',
            'MISSING_TRANSITION_TARGET': {'StartAt': 'Nowhere', 'States': {'A': {'Type': 'Succeed'}}},
            'INVALID_STATE_TYPE': {'StartAt': 'A', 'States': {'A': {'Type': 'Dance', 'End': True}}},
            'MISSING_TRANSITION': {'StartAt': 'A', 'States': {'A': {'Type': 'Pass'}}},
            'MISSING_RESOURCE': {'StartAt': 'A', 'States': {'A': {'Type': 'Task', 'End': True}}},
            'MISSING_CHOICES': {'StartAt': 'A', 'States': {'A': {'Type': 'Choice'}}},
            'MISSING_STATES': {'StartAt': 'A'},
        }
        for expected, definition in cases.items():
            result = self.validate(definition)
            self.assertEqual(result['result'], 'FAIL', expected)
            self.assertIn(expected, [item['code'] for item in result['diagnostics']])
        nested = self.validate({'StartAt': 'Fan', 'States': {'Fan': {'Type': 'Parallel', 'End': True, 'Branches': [{'StartAt': 'A', 'States': {'A': {'Type': 'Pass', 'Next': 'Gone'}}}]}}})
        self.assertEqual(nested['diagnostics'][0]['location'], '/States/Fan/Branches/0/States/A/Next')

    def test_versions_are_listed_only_for_existing_machines(self):
        engine = engines.StepFunctionsValidationEngine(lambda region: ['arn:aws:states:ap-southeast-2:123456789012:stateMachine:known'])
        ask = lambda arn: engine.handle('POST', '/', {}, {'X-Amz-Target': 'AWSStepFunctions.ListStateMachineVersions'}, json.dumps({'stateMachineArn': arn}).encode())
        self.assertEqual(json.loads(ask('arn:aws:states:ap-southeast-2:123456789012:stateMachine:known').body), {'stateMachineVersions': []})
        self.assertEqual(json.loads(ask('arn:aws:states:ap-southeast-2:123456789012:stateMachine:other').body)['__type'], 'StateMachineDoesNotExist')
        self.assertEqual(json.loads(ask('nonsense').body)['__type'], 'InvalidArn')
        self.assertIsNone(engine.handle('POST', '/', {}, {'X-Amz-Target': 'AWSStepFunctions.CreateStateMachine'}, b'{}'))


class CognitoTests(unittest.TestCase):
    def test_delete_resource_server_changes_only_that_server(self):
        class Pool:
            resource_servers = {'https://api': object(), 'https://other': object()}
        pools = {'ap-southeast-2_abc': Pool()}
        engine = engines.CognitoResourceServerEngine(lambda region: pools if region == 'ap-southeast-2' else {})
        ask = lambda **request: engine.handle('POST', '/', {}, {'X-Amz-Target': 'AWSCognitoIdentityProviderService.DeleteResourceServer'}, json.dumps(request).encode())
        self.assertEqual(ask(UserPoolId='ap-southeast-2_abc', Identifier='https://api').status, 200)
        self.assertEqual(list(Pool.resource_servers), ['https://other'])
        self.assertEqual(json.loads(ask(UserPoolId='ap-southeast-2_abc', Identifier='https://api').body)['__type'], 'ResourceNotFoundException')
        self.assertEqual(json.loads(ask(UserPoolId='us-east-1_zzz', Identifier='x').body)['__type'], 'ResourceNotFoundException')
        self.assertEqual(json.loads(ask(UserPoolId='ap-southeast-2_abc').body)['__type'], 'InvalidParameterException')


class DispatchTests(unittest.TestCase):
    def test_only_engines_of_the_called_service_see_the_request(self):
        environ = {'REQUEST_METHOD': 'GET', 'QUERY_STRING': 'Type=managed', 'HTTP_IF_MATCH': 'E1'}
        built = [engines.CloudFrontEngine(), engines.StepFunctionsValidationEngine()]
        engine, reply = engines.dispatch(built, 'cloudfront', environ, '/2020-05-31/cache-policy', b'')
        self.assertEqual((engine.name, reply.operation), ('atmem-cloudfront', 'ListCachePolicies'))
        self.assertIsNone(engines.dispatch(built, 's3', environ, '/2020-05-31/cache-policy', b''))
        self.assertIsNone(engines.dispatch(built, 'cloudfront', environ, '/2020-05-31/function', b''))


if __name__ == '__main__':
    unittest.main()
