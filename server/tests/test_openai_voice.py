import time
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from fastapi.testclient import TestClient
from server.app import app, TOKEN
from server import openai_voice as voice


class OpenAIVoiceTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app)
        self.headers={'Authorization':'Bearer '+TOKEN}

    def transport(self, response):
        client=AsyncMock()
        client.__aenter__.return_value=client
        client.post.return_value=response
        return client

    def test_dedicated_voice_key_never_replaces_architect_credentials(self):
        from server.app import ARCHITECT
        with patch.object(voice,'_voice_key',None),patch.dict(ARCHITECT.keys,{'openai':'architect-key'}):
            self.assertEqual(self.client.post('/api/voice/openai/credentials',json={'key':'voice-key'}).status_code,401)
            response=self.client.post('/api/voice/openai/credentials',json={'key':'voice-key'},headers=self.headers)
            self.assertEqual(response.status_code,200)
            self.assertNotIn('voice-key',response.text)
            self.assertEqual(voice.api_key(),'voice-key')
            self.assertEqual(ARCHITECT.keys['openai'],'architect-key')
            self.assertEqual(self.client.post('/api/voice/openai/credentials',json={'key':'bad','provider':'openai'},headers=self.headers).status_code,422)
            self.assertEqual(self.client.post('/api/voice/openai/credentials',json={'key':''},headers=self.headers).status_code,200)
            self.assertEqual(voice.api_key(),'architect-key')

    def test_status_does_not_probe_api_or_disclose_credentials(self):
        with patch.object(voice,'api_key',return_value='private-key'), patch.object(voice.httpx,'AsyncClient') as network:
            result=self.client.get('/api/voice/openai/status')
            self.assertTrue(result.json()['available'])
            self.assertFalse(result.json()['audioStoredByArchitect'])
            self.assertNotIn('private-key',result.text)
            network.assert_not_called()

    def test_missing_key_auth_origin_and_overrides_cannot_create_a_session(self):
        with patch.object(voice,'api_key',return_value=None),patch.object(voice.httpx,'AsyncClient') as network:
            self.assertEqual(self.client.post('/api/voice/openai/session',json={}).status_code,401)
            self.assertEqual(self.client.post('/api/voice/openai/session',json={},headers={**self.headers,'Origin':'https://foreign.example'}).status_code,403)
            self.assertEqual(self.client.post('/api/voice/openai/session',json={},headers=self.headers).status_code,503)
            for override in [{'model':'another-model'},{'key':'private-key'},{'endpoint':'http://elsewhere'},{'session':{}}]:
                self.assertEqual(self.client.post('/api/voice/openai/session',json=override,headers=self.headers).status_code,422)
            network.assert_not_called()

    def test_ephemeral_only_credentials_no_automatic_responses_or_tools(self):
        upstream=httpx.Response(200,json={'value':'ek_synthetic','expires_at':time.time()+60,'session':{'private':'do not forward'}})
        client=self.transport(upstream)
        with patch.object(voice,'api_key',return_value='private-long-lived'),patch.object(voice.httpx,'AsyncClient',return_value=client):
            response=self.client.post('/api/voice/openai/session',json={},headers=self.headers)
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['value'],'ek_synthetic')
            self.assertNotIn('private-long-lived',response.text)
            self.assertNotIn('do not forward',response.text)
            self.assertEqual(response.headers['cache-control'],'no-store')
            args=client.post.call_args
            self.assertEqual(args.args[0],voice.TOKEN_URL)
            body=args.kwargs['json']
            self.assertEqual(body['expires_after']['seconds'],60)
            session=body['session']
            self.assertEqual(session['model'],voice.MODEL)
            self.assertEqual(session['tools'],[])
            self.assertFalse(session['audio']['input']['turn_detection']['create_response'])
            self.assertFalse(session['audio']['input']['turn_detection']['interrupt_response'])
            self.assertEqual(session['audio']['output']['voice'],'marin')
            self.assertNotIn('voice',session)
            self.assertNotIn('format',session['audio']['input'])

    def test_upstream_rejection_bad_tokens_and_transport_errors_are_sanitized(self):
        for status,body in [(401,{'detail':'private-long-lived'}),(429,{'detail':'secret'}),(500,{'detail':'private path'}),
                            (200,{'value':'sk_private','expires_at':time.time()+60}),
                            (200,{'value':'ek_expired','expires_at':time.time()-1})]:
            client=self.transport(httpx.Response(status,json=body))
            with self.subTest(status=status,body=body),patch.object(voice,'api_key',return_value='private-long-lived'),patch.object(voice.httpx,'AsyncClient',return_value=client):
                response=self.client.post('/api/voice/openai/session',json={},headers=self.headers)
                self.assertIn(response.status_code,[429,502,503])
                for value in ['private-long-lived','private path','sk_private','ek_expired']:
                    self.assertNotIn(value,response.text)
