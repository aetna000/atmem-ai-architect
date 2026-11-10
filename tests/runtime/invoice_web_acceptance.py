"""Public browser configuration must not widen auth origins or expose private data."""
from pathlib import Path
import sys
import unittest
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/azure-runtime-sdk')]
import httpx
from invoice_http import create_app

class InvoiceBrowserBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def config(self):return{'mode':'oauth-pkce','authOrigin':'https://identity.example.test','authorizationEndpoint':'https://identity.example.test/tenant/authorize','tokenEndpoint':'https://identity.example.test/tenant/token','clientId':'public-client','scopes':'openid invoices/review'}
    def app(self,config):
        def deny(token):raise PermissionError('No signed-in fixture identity')
        return create_app(deny,None,None,account_id=str(uuid.uuid4()),public_origin='https://invoices.example.test',web_config=config)
    async def test_public_assets_and_config_do_not_make_private_routes_public(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app(self.config())),base_url='https://invoices.example.test')as client:
            for path in ['/','/app.js','/app.css','/config.json']:
                response=await client.get(path);self.assertEqual(response.status_code,200);self.assertEqual(response.headers['cache-control'],'no-store');self.assertIn("connect-src 'self' https://identity.example.test;",response.headers['content-security-policy'])
            for path in ['/api/session','/api/invoices']:
                self.assertEqual((await client.get(path)).status_code,403)
            for path in ['/workflow_connection.py','/workflow_schema.sql','/.env','/app.js/../workflow_connection.py']:
                self.assertEqual((await client.get(path)).status_code,404)
    async def test_csp_injection_cross_authority_and_private_config_fields_are_rejected(self):
        for changes in [{'authOrigin':"https://identity.example.test';script-src *"},{'tokenEndpoint':'https://attacker.invalid/token'},{'authorizationEndpoint':'https://user:secret@identity.example.test/authorize'},{'clientSecret':'never-ship-this'},{'authOrigin':'http://identity.example.test'}]:
            with self.subTest(changes=list(changes)),self.assertRaises(ValueError):self.app({**self.config(),**changes})
    async def test_proxy_navigation_cannot_leave_the_owned_origin(self):
        for path in ['//attacker.invalid/login','https://attacker.invalid/login','/\\attacker.invalid','/login\nLocation:https://attacker.invalid']:
            with self.subTest(path=repr(path)),self.assertRaises(ValueError):self.app({'mode':'proxy','loginPath':path,'logoutPath':'/logout'})
        self.app({'mode':'proxy','loginPath':'/login','logoutPath':'/logout'})
    async def test_cross_origin_asset_and_api_requests_remain_denied(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app(self.config())),base_url='https://invoices.example.test')as client:
            for path in ['/config.json','/api/invoices']:
                response=await client.get(path,headers={'Origin':'https://attacker.invalid'});self.assertEqual(response.status_code,403)
                self.assertNotIn('access-control-allow-origin',response.headers)

class CodeEngineOriginTests(unittest.TestCase):
    def environment(self):return{'PUBLIC_ORIGIN_MODE':'code-engine-default','REGION':'au-syd','CE_REGION':'au-syd','CE_APP':'invoice-api','SERVICE_NAME':'invoice-api','CE_SUBDOMAIN':'project-fixture','CE_DOMAIN':'au-syd.codeengine.appdomain.cloud'}
    def test_native_origin_is_derived_from_exact_owned_platform_metadata_without_a_terraform_cycle(self):
        from invoice_native import native_public_origin
        env=self.environment();origin='https://invoice-api.project-fixture.au-syd.codeengine.appdomain.cloud';self.assertEqual(native_public_origin('ibm',env),origin);self.assertEqual(native_public_origin('ibm',{**env,'PUBLIC_ORIGIN':origin}),origin)
        self.assertEqual(native_public_origin('aws',{'PUBLIC_ORIGIN':'https://explicit.example.test'}),'https://explicit.example.test')
    def test_request_headers_foreign_domains_apps_regions_and_conflicting_explicit_origins_are_not_trusted(self):
        from invoice_native import native_public_origin
        for changes in [{'CE_APP':'foreign-app'},{'CE_REGION':'us-south'},{'CE_DOMAIN':'au-syd.codeengine.appdomain.cloud.attacker.test'},{'CE_SUBDOMAIN':'invalid/../project'},{'PUBLIC_ORIGIN':'https://attacker.test'},{'CE_DOMAIN':'au-syd.codeengine.dev.appdomain.cloud'}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):native_public_origin('ibm',{**self.environment(),**changes})

if __name__=='__main__':unittest.main(verbosity=2)
