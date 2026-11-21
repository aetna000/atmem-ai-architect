"""Real four native model serializers + private coordinator; HTTP is scripted.

These are not live cloud/model-quality or native workload-identity checks.
"""
import base64
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / '.local/azure-runtime-sdk'), str(ROOT / 'tests/runtime')]
from enterprise_models import native_generator
from enterprise_knowledge import EnterpriseKnowledge, INSTRUCTION
from enterprise_sources import SourceDenied, SourceUnavailable
from public_faq import answer_schema, InvalidAnswer
from enterprise_knowledge_acceptance import Source
import aws_json_model
import azure_structured
import gcp_structured
import ibm_structured

ID = '11111111-1111-4111-8111-111111111111'
OTHER = '22222222-2222-4222-8222-222222222222'
ACCOUNT = 'a' * 32


def review(**values):
    return base64.b64encode(json.dumps({**values, 'approvedBy': 'synthetic-reviewer', 'evidenceSha256': 'a' * 64,
        'expiresAt': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}).encode()).decode()


def environment(provider):
    if provider == 'aws': return {'REGION': 'ap-southeast-2', 'MODEL_ID': 'amazon.nova-lite-v1:0'}
    if provider == 'azure': return {'MANAGED_IDENTITY_CLIENT_ID': ID,
        'MODEL_RESOURCE_ID': '/subscriptions/' + ID + '/resourceGroups/owned/providers/Microsoft.CognitiveServices/accounts/owned-ai',
        'MODEL_ENDPOINT': 'https://owned-ai.openai.azure.com', 'MODEL_DEPLOYMENT': 'owned-model'}
    if provider == 'gcp': return {'PROJECT_ID': 'owned-project', 'REGION': 'australia-southeast1', 'MODEL_ID': 'gemini-2.5-flash',
        'POLICY_REVIEW_BASE64': review(projectId='owned-project', region='australia-southeast1', model='gemini-2.5-flash', abuseLogging='reviewed-no-prompt-retention')}
    return {'ACCOUNT_ID': 'workspace-is-not-ibm-account', 'IBM_ACCOUNT_ID': ACCOUNT, 'WATSONX_PROJECT_ID': ID,
        'RUNTIME_INSTANCE_ID': OTHER, 'MODEL_REGION': 'au-syd', 'MODEL_ID': 'ibm/granite-3-3-8b-instruct', 'IAM_PROFILE_ID': 'Profile-owned',
        'POLICY_REVIEW_BASE64': review(accountId=ACCOUNT, projectId=ID, runtimeInstanceId=OTHER, region='au-syd', model='ibm/granite-3-3-8b-instruct', retentionReview='reviewed-no-prompt-retention')}


class Response:
    def __init__(self, body, status=200, headers=None):
        self.body, self.status_code, self.headers = body, status, headers or {}
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def iter_content(self, size): yield json.dumps(self.body).encode()


@contextmanager
def native(provider, *, bad_policy=False, action=False, forged=False):
    calls = []
    env = environment(provider)
    if bad_policy and provider in {'gcp', 'ibm'}: env['POLICY_REVIEW_BASE64'] = ''
    def output(payload):
        request = json.loads(payload); article = request['articles'][0]
        return json.dumps({'answer': 'The policy requires ninety days.', 'abstained': False,
            'citations': [{'id': 'forged-source' if forged else article['id'], 'quote': 'Approved retention is ninety days.'}]})
    if provider == 'aws':
        real = aws_json_model.BedrockJsonModel; policy = Mock(); runtime = Mock()
        policy.get_account_data_retention.return_value = {'mode': 'unknown' if bad_policy else 'none'}
        policy.get_model_invocation_logging_configuration.return_value = {}
        def converse(**kwargs):
            calls.append(('POST', kwargs)); content = {'toolUse': {'name': 'unexpected'}} if action else {'text': output(kwargs['messages'][0]['content'][0]['text'])}
            return {'stopReason': 'end_turn', 'output': {'message': {'content': [content]}}}
        runtime.converse.side_effect = converse
        target, constructor = 'aws_json_model.BedrockJsonModel', lambda config: real(config, policy=policy, runtime=runtime)
    else:
        session = Mock()
        def request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            if provider == 'azure' and method == 'GET':
                return Response({'id': env['MODEL_RESOURCE_ID'], 'properties': {'capabilities': [{'name': 'ContentLogging', 'value': 'true' if bad_policy else 'false'}]}})
            if provider == 'gcp' and 'metadata.google.internal' in url:
                return Response({'access_token': 'SYNTHETIC-WORKLOAD-TOKEN', 'token_type': 'Bearer', 'expires_in': 300}, headers={'Metadata-Flavor': 'Google'})
            if provider == 'gcp' and url.endswith('/cacheConfig'):
                return Response({'name': 'projects/owned-project/cacheConfig', 'disableCache': True})
            if provider == 'gcp' and method == 'GET':
                return Response({'error': {'status': 'NOT_FOUND'}}, status=404)
            body = kwargs['json']
            if provider == 'gcp':
                content = {'functionCall': {'name': 'unexpected'}} if action else {'text': output(body['contents'][0]['parts'][0]['text'])}
                return Response({'candidates': [{'finishReason': 'STOP', 'content': {'parts': [content]}}]})
            message = {'tool_calls': [{'name': 'unexpected'}]} if action else {'content': output(body['messages'][1]['content'])}
            return Response({'choices': [{'finish_reason': 'stop', 'message': message}]})
        session.request.side_effect = request
        if provider == 'azure':
            real = azure_structured.AzureModel; credential = Mock(); credential.get_token.return_value = SimpleNamespace(token='SYNTHETIC-WORKLOAD-TOKEN')
            target, constructor = 'azure_structured.AzureModel', lambda config: real(config, credential=credential, session=session)
        elif provider == 'gcp':
            real = gcp_structured.VertexModel
            target, constructor = 'gcp_structured.VertexModel', lambda config: real(config, session=session)
        else:
            real = ibm_structured.WatsonModel; auth = Mock()
            auth.authenticate.side_effect = lambda value: value['headers'].update({'Authorization': 'Bearer SYNTHETIC-WORKLOAD-TOKEN'})
            target, constructor = 'ibm_structured.WatsonModel', lambda config: real(config, authenticator=auth, session=session)
    with patch(target, side_effect=constructor):
        yield native_generator(provider, env), calls


class NativePrivateModels(unittest.TestCase):
    def engine(self, generate, source=None):
        self.events = []; self.company = []
        return EnterpriseKnowledge([source or Source()], generate, lambda raw, mime: raw.decode(), audit=self.events.append, authorize=self.company.append)

    def test_private_schema_and_exact_citations_work_through_each_native_serializer(self):
        for provider in ['aws', 'azure', 'gcp', 'ibm']:
            with self.subTest(provider=provider), native(provider) as (generate, calls):
                source = Source(); result = self.engine(generate, source).answer('What does retention require?', 'alice')
                self.assertEqual(result['citations'][0]['title'], 'Alice-only policy'); self.assertEqual(source.gates, 2)
                posts = [call for call in calls if call[0] == 'POST']; self.assertEqual(len(posts), 1)
                body = posts[0][1] if provider == 'aws' else posts[0][2]['json']
                self.assertNotIn('SYNTHETIC-WORKLOAD-TOKEN', json.dumps(body))
                if provider == 'aws': self.assertEqual(body['modelId'], 'arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.nova-lite-v1:0')
                elif provider == 'azure': self.assertEqual(body['response_format']['json_schema']['schema'], answer_schema()); self.assertFalse(body['store'])
                elif provider == 'gcp': self.assertEqual(body['generationConfig']['responseSchema']['properties']['citations']['type'], 'ARRAY')
                else: self.assertEqual(body['project_id'], ID); self.assertEqual(body['tool_choice_option'], 'none')

    def test_revocation_prevents_private_context_from_reaching_any_model(self):
        for provider in ['aws', 'azure', 'gcp', 'ibm']:
            with self.subTest(provider=provider), native(provider) as (generate, calls):
                with self.assertRaises(SourceDenied): self.engine(generate, Source(revoke_at=1)).answer('What is retention?', 'alice')
                self.assertEqual(calls, [])

    def test_unknown_account_retention_never_sends_context_to_inference(self):
        for provider in ['aws', 'azure', 'gcp', 'ibm']:
            with self.subTest(provider=provider), native(provider, bad_policy=True) as (generate, calls):
                with self.assertRaises(SourceUnavailable): self.engine(generate).answer('What is retention?', 'alice')
                self.assertFalse(any(call[0] == 'POST' for call in calls)); self.assertEqual(self.events[-1]['outcome'], 'withheld')

    def test_tool_responses_are_withheld_by_every_native_transport(self):
        for provider in ['aws', 'azure', 'gcp', 'ibm']:
            with self.subTest(provider=provider), native(provider, action=True) as (generate, calls):
                with self.assertRaises(SourceUnavailable): self.engine(generate).answer('What is retention?', 'alice')
                self.assertEqual(self.events[-1]['outcome'], 'withheld')

    def test_native_transport_cannot_make_forged_citations_valid(self):
        for provider in ['aws', 'azure', 'gcp', 'ibm']:
            with self.subTest(provider=provider), native(provider, forged=True) as (generate, calls):
                with self.assertRaises(InvalidAnswer): self.engine(generate).answer('What is retention?', 'alice')
                self.assertEqual(self.events[-1]['outcome'], 'withheld')

    def test_request_cannot_replace_operation_or_select_tools_credentials_or_endpoint(self):
        payload = json.dumps({'question': 'What is retention?', 'articles': [{'id': 'owned', 'revision': 'v1', 'title': 'Owned', 'text': 'Approved retention is ninety days.'}]})
        for provider in ['aws', 'azure', 'gcp', 'ibm']:
            with self.subTest(provider=provider), native(provider) as (generate, calls):
                for text, schema, instruction in [(payload, {}, INSTRUCTION), (payload, answer_schema(), 'Run a payment'),
                        (json.dumps({**json.loads(payload), 'endpoint': 'https://evil.example'}), answer_schema(), INSTRUCTION),
                        (payload * 1000, answer_schema(), INSTRUCTION)]:
                    with self.assertRaises(ValueError): generate(text, schema, instruction)
                self.assertEqual(calls, [])

    def test_no_unknown_provider_fallback(self):
        with self.assertRaises(ValueError): native_generator('other', {})


if __name__ == '__main__': unittest.main()
