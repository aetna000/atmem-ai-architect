import asyncio, json, unittest
from unittest.mock import AsyncMock, patch
from server.local_providers import call_cli, strict_schema, capabilities
from server.contracts import ArchitectResponse
from fastapi.testclient import TestClient
from server.app import app, TOKEN, ARCHITECT

class ProviderTests(unittest.TestCase):
    def test_all_four_account_clients_are_discoverable_without_tokens(self):
        with patch('server.local_providers.shutil.which',return_value='/usr/bin/client'):
            result=capabilities()
        self.assertEqual(set(result),{'claude-code','codex','copilot','gemini-cli'})
        self.assertTrue(all(v['installed'] for v in result.values()))
    def test_codex_invocation_is_ephemeral_and_uses_native_auth(self):
        async def check():
            with patch('server.local_providers.shutil.which',return_value='/bin/codex'),patch('server.local_providers.communicate',new=AsyncMock(return_value='{"message":"ok","phase":"Discovery","proposal":null}')) as transport:
                result=await call_cli('codex','default','context','system',ArchitectResponse.model_json_schema(),AsyncMock(return_value=False))
                args=transport.call_args.args[0]
                self.assertIn('--ephemeral',args);self.assertIn('--ignore-user-config',args);self.assertIn('read-only',args);self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',args);self.assertEqual(result['message'],'ok')
        asyncio.run(check())
    def test_gemini_adapter_disables_tools_extensions_and_hooks(self):
        async def fake(args,prompt,cwd,disconnected,env,timeout=150):
            self.assertEqual(timeout,150)
            from pathlib import Path
            settings=json.loads(Path(env['GEMINI_CLI_SYSTEM_SETTINGS_PATH']).read_text())
            self.assertEqual(settings['tools']['core'],[]);self.assertFalse(settings['hooksConfig']['enabled']);self.assertIn('plan',args)
            return '{"response":"{\\"message\\":\\"ok\\",\\"phase\\":\\"Discovery\\",\\"proposal\\":null}"}'
        async def check():
            with patch('server.local_providers.shutil.which',return_value='/bin/gemini'),patch('server.local_providers.communicate',new=fake):
                result=await call_cli('gemini-cli','default','context','system',ArchitectResponse.model_json_schema(),AsyncMock(return_value=False));self.assertEqual(result['message'],'ok')
        asyncio.run(check())
    def test_strict_schema_keeps_all_fields_required_without_mutating_original(self):
        schema={'type':'object','properties':{'optional':{'type':'string'}},'required':[]}
        result=strict_schema(schema);self.assertEqual(result['required'],['optional']);self.assertEqual(schema['required'],[])
    def test_credentials_are_write_only_ephemeral_and_removable(self):
        client=TestClient(app);headers={'Authorization':f'Bearer {TOKEN}'}
        result=client.post('/api/credentials',headers=headers,json={'provider':'openai','key':'test-key-not-real'})
        self.assertEqual(result.status_code,200);self.assertNotIn('test-key-not-real',result.text)
        self.assertTrue(client.get('/api/session').json()['providers']['openai']['available'])
        result=client.post('/api/credentials',headers=headers,json={'provider':'openai','key':''});self.assertEqual(result.status_code,200);self.assertNotIn('openai',ARCHITECT.keys)
    def test_credentials_require_local_session(self):
        self.assertEqual(TestClient(app).post('/api/credentials',json={'provider':'openai','key':'example'}).status_code,401)

if __name__=='__main__':unittest.main()


class ProviderFailureExplanationTests(unittest.TestCase):
    def test_usage_auth_and_model_errors_are_actionable_without_raw_output(self):
        from server.local_providers import provider_failure
        for text,expected in [("You've hit your session limit · resets tomorrow. secret-token",'usage or rate limit'),('Authentication failed secret-token','sign in again'),('model_not_found secret-token','not available')]:
            message=provider_failure(text);self.assertIn(expected,message);self.assertNotIn('secret-token',message)
        self.assertIn('No changes were applied',provider_failure('unknown raw secret-token'))
