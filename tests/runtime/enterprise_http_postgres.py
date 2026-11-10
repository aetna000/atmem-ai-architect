"""Actual ASGI/JWT/session/SQL/OAuth integration; explicit vendor/model fixtures.

No browser SameSite enforcement, live IdP consent or cloud is claimed here.
"""
import asyncio
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from urllib.parse import parse_qs,urlsplit
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/azure-runtime-sdk'),str(ROOT/'tests/runtime')]
import httpx
import jwt
import psycopg
from cryptography.hazmat.primitives.asymmetric import rsa
import enterprise_auth_postgres as postgres_fixture
from enterprise_auth_store import EnterpriseAuthStore
from enterprise_identity import CompanyIdentity,CompanyPrincipal
from enterprise_sessions import CompanySessions
from enterprise_http import create_app,SourceConnection,COOKIE
from enterprise_oauth import GraphConsent,ConfluenceConsent
from enterprise_oauth_acceptance import OAuthHttp,Profiles,TENANT,CLIENT,CLOUD
from enterprise_knowledge import EnterpriseKnowledge
from enterprise_sources import SourceDocument,SourceDenied,SourceUnavailable,GraphSharePoint,ConfluenceCloud,Reply,checked_url

ORIGIN='https://app.example'
class CompanyHttpIntegration(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixture=postgres_fixture.EnterpriseCredentialTransactions;fixture.setUpClass();cls.owner_dsn=fixture.owner_dsn;cls.app_dsn=fixture.app_dsn;cls.key=fixture.key
        cls.signing=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    async def asyncSetUp(self):
        postgres_fixture.EnterpriseCredentialTransactions.setUp(self)
        with psycopg.connect(self.owner_dsn)as conn:
            for principal in [self.principal,self.other]:conn.execute('INSERT INTO enterprise_auth.source_mappings VALUES(%s,%s,%s,%s,1,true)',(self.account,principal.key,'confluence:'+CLOUD,principal.subject+'-native'))
        key=self.signing
        class Resolver:
            def get_signing_key_from_jwt(self,token):return SimpleNamespace(key=key.public_key())
        self.identity=CompanyIdentity(self.account,self.principal.issuer,'knowledge-api','https://company.example/jwks',jwks=Resolver());self.sessions=CompanySessions(self.store)
        self.graph_http=OAuthHttp();self.confluence_http=OAuthHttp();self.profiles=Profiles()
        self.graph=GraphConsent(self.store,TENANT,CLIENT,ORIGIN+'/oauth/callback/sharepoint','drive','tenant.sharepoint.com',lambda:'SYNTHETIC-CLIENT-SECRET',http=self.graph_http,profile_http=self.profiles)
        self.confluence=ConfluenceConsent(self.store,'client',ORIGIN+'/oauth/callback/confluence',CLOUD,'tenant.atlassian.net',{'ENG':'42'},lambda:'SYNTHETIC-CLIENT-SECRET',http=self.confluence_http,profile_http=self.profiles)
        self.factory_calls=[];self.model_calls=[];self.audit=[];self.fail_model=False;self.revoke_during_model=False
        outer=self
        class Documents:
            def get(self,url,token,*,hosts,limit=2000000):
                checked_url(url,hosts)
                if getattr(outer,'source_offline',False):raise SourceUnavailable('source_request_failed')
                title=getattr(outer,'source_title','Private policy')
                if '/root/search('in url:value={'value':[{'id':'doc','file':{},'parentReference':{'driveId':'drive'}}]}
                elif '/items/doc/content'in url:
                    outer.document_downloads=getattr(outer,'document_downloads',0)+1
                    return Reply(200,{},getattr(outer,'document_bytes',b'Private policy requires ninety days.'))
                elif '/items/doc?'in url:value={'id':'doc','name':title,'eTag':getattr(outer,'source_version','v1'),'file':{'mimeType':getattr(outer,'document_mime','text/plain')},'parentReference':{'driveId':'drive'},'webUrl':'https://tenant.sharepoint.com/policy'}
                elif '/wiki/rest/api/search?'in url:value={'results':[{'content':{'id':'100','type':'page'}}]}
                elif '/wiki/api/v2/pages/100?'in url:value={'id':'100','title':title,'status':'current','spaceId':'42','version':{'number':1},'body':{'storage':{'value':'<p>Private policy requires ninety days.</p>'}}}
                elif url.startswith('https://graph.microsoft.com/v1.0/me?')or url in {'https://api.atlassian.com/me','https://api.atlassian.com/oauth/token/accessible-resources'}:return outer.profiles.get(url,token,hosts=hosts)
                else:raise AssertionError('Unexpected native document request')
                return Reply(200,{},json.dumps(value).encode())
        self.document_http=Documents()
        def make_engine(principal,access,authorize):
            self.factory_calls.append((principal.key,set(access)))
            def generate(payload,schema,instruction):
                self.model_calls.append(True)
                if self.fail_model:raise RuntimeError('PRIVATE-PROMPT-AND-TOKEN')
                if self.revoke_during_model:
                    with psycopg.connect(self.owner_dsn)as conn:conn.execute('UPDATE enterprise_auth.memberships SET active=false WHERE account_id=%s AND principal_key=%s',(self.account,principal.key))
                article=json.loads(payload)['articles'][0]
                quote=getattr(self,'answer_quote','Private policy requires ninety days.')
                return json.dumps({'answer':quote,'abstained':False,'citations':[{'id':article['id'],'quote':quote}]})
            sources=[GraphSharePoint('drive','tenant.sharepoint.com',access['sharepoint'],http=self.document_http),ConfluenceCloud(CLOUD,'tenant.atlassian.net',{'ENG':'42'},access['confluence'],http=self.document_http)]
            return EnterpriseKnowledge(sources,generate,lambda raw,mime:raw.decode(),audit=self.audit.append,authorize=authorize)
        self.engine_factory=make_engine;self.connections={'sharepoint':SourceConnection('SharePoint','graph',self.graph),'confluence':SourceConnection('Confluence','confluence',self.confluence)}
        self.app=create_app(self.identity,self.sessions,self.connections,make_engine,public_origin=ORIGIN)
        self.client=self.new_client();self.clients=[self.client];self.csrf=None
    async def asyncTearDown(self):
        for client in self.clients:await client.aclose()
    def new_client(self):return httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url=ORIGIN,follow_redirects=False)
    def token(self,subject='alice',expired=False):
        now=int(time.time());return jwt.encode({'iss':self.principal.issuer,'sub':subject,'aud':'knowledge-api','iat':now-3600 if expired else now,'exp':now-1 if expired else now+3600,'scp':'knowledge.read'},self.signing,algorithm='RS256',headers={'kid':'owned-key'})
    async def login(self,client=None,subject='alice'):
        client=client or self.client;response=await client.post('/api/session',json={},headers={'Origin':ORIGIN,'Authorization':'Bearer '+self.token(subject)})
        self.assertEqual(response.status_code,200,response.text);self.csrf=response.json()['csrfToken'];return response
    def headers(self,**extra):return {'Origin':ORIGIN,'X-CSRF-Token':self.csrf or'',**extra}
    async def start_graph(self):
        response=await self.client.post('/api/sources/sharepoint/connect',json={},headers=self.headers());self.assertEqual(response.status_code,200,response.text)
        params=parse_qs(urlsplit(response.json()['authorizationUrl']).query);self.graph_http.nonce=params['nonce'][0];return params['state'][0]
    async def finish_graph(self,state,client=None):return await(client or self.client).post('/oauth/callback/sharepoint',data={'code':'SYNTHETIC-CODE','state':state},headers={'Origin':'https://login.microsoftonline.com'})
    async def connect_all(self):
        state=await self.start_graph();response=await self.finish_graph(state);self.assertEqual(response.status_code,303,response.text)
        response=await self.client.post('/api/sources/confluence/connect',json={},headers=self.headers());self.assertEqual(response.status_code,200,response.text)
        state=parse_qs(urlsplit(response.json()['authorizationUrl']).query)['state'][0]
        response=await self.client.get('/oauth/callback/confluence',params={'code':'SYNTHETIC-CODE','state':state});self.assertEqual(response.status_code,303,response.text)

    async def test_signed_out_wrong_token_and_source_actions_do_not_reach_model(self):
        response=await self.client.get('/api/session',headers={'X-Workspace-Request':'session'});self.assertEqual(response.status_code,401)
        response=await self.client.post('/api/ask',json={'question':'policy'},headers={'Origin':ORIGIN});self.assertEqual(response.status_code,401)
        response=await self.client.post('/api/session',json={},headers={'Origin':ORIGIN,'Authorization':'Bearer '+self.token(expired=True)});self.assertEqual(response.status_code,401)
        self.assertEqual(self.factory_calls,[]);self.assertEqual(self.model_calls,[])

    async def test_valid_cookie_from_other_company_is_not_a_login_to_this_workspace(self):
        foreign=CompanyPrincipal('other-company',self.principal.issuer,self.principal.subject,self.principal.expires_at)
        with psycopg.connect(self.owner_dsn)as conn:conn.execute('INSERT INTO enterprise_auth.memberships VALUES(%s,%s,%s,%s,true)',(foreign.account_id,foreign.key,foreign.issuer,foreign.subject))
        cookie=self.sessions.create(foreign);self.client.cookies.set(COOKIE,cookie.token,domain='app.example',path='/')
        response=await self.client.get('/api/session',headers={'X-Workspace-Request':'session'});self.assertEqual(response.status_code,401)
        response=await self.client.post('/api/ask',json={'question':'private policy'},headers={'Origin':ORIGIN,'X-CSRF-Token':cookie.csrf});self.assertEqual(response.status_code,401);self.assertEqual(self.factory_calls,[])

    async def test_login_cookie_flags_hashes_and_reload_csrf(self):
        response=await self.login();cookie=response.headers['set-cookie'];self.assertIn('HttpOnly',cookie);self.assertIn('Secure',cookie);self.assertIn('SameSite=none',cookie);self.assertIn('Path=/',cookie);self.assertNotIn('Domain=',cookie)
        token=self.client.cookies.get(COOKIE)
        with psycopg.connect(self.owner_dsn)as conn:row=conn.execute('SELECT session_sha256,csrf_sha256,nonce_ciphertext FROM enterprise_auth.sessions WHERE account_id=%s',(self.account,)).fetchone()
        self.assertNotIn(token,str(row));self.assertNotIn(self.csrf,str(row));self.assertNotIn(self.token(),str(row))
        response=await self.client.get('/api/session');self.assertEqual(response.status_code,403)
        response=await self.client.get('/api/session',headers={'X-Workspace-Request':'session'});self.assertEqual(response.status_code,200);self.assertEqual(response.json()['csrfToken'],self.csrf);self.assertNotIn('source_subject',response.text)

    async def test_origin_csrf_and_identity_fields_cannot_be_spoofed(self):
        await self.login()
        for headers in [{'Origin':ORIGIN},{'Origin':'https://evil.example','X-CSRF-Token':self.csrf}]:
            response=await self.client.post('/api/sources/sharepoint/connect',json={},headers=headers);self.assertEqual(response.status_code,403)
        response=await self.client.post('/api/session',json={'account':'other-company'},headers={'Origin':ORIGIN,'Authorization':'Bearer '+self.token()});self.assertEqual(response.status_code,400)
        response=await self.client.post('/api/ask',json={'question':'policy','subject':'bob'},headers=self.headers());self.assertEqual(response.status_code,400);self.assertEqual(self.factory_calls,[])
        response=await self.client.options('/api/session',headers={'Origin':'https://evil.example','Access-Control-Request-Headers':'authorization'});self.assertNotIn('access-control-allow-origin',response.headers)

    async def test_duplicate_session_cookies_and_malformed_or_large_questions_fail_closed(self):
        await self.login();token=self.client.cookies.get(COOKIE)
        response=await self.client.get('/api/session',headers={'X-Workspace-Request':'session','Cookie':COOKIE+'='+token+'; '+COOKIE+'='+token});self.assertEqual(response.status_code,401)
        for content in ['{"question":"first","question":"second"}','{"question":"'+('x'*9000)+'"}']:
            response=await self.client.post('/api/ask',content=content,headers={**self.headers(),'Content-Type':'application/json'});self.assertEqual(response.status_code,400)
        self.assertEqual(self.model_calls,[])

    async def test_native_graph_form_post_and_confluence_get_scrub_code_and_replay(self):
        await self.login();state=await self.start_graph();response=await self.finish_graph(state);self.assertEqual(response.status_code,303,response.text)
        self.assertEqual(response.headers['location'],'/?connection=connected&source=sharepoint');self.assertEqual(response.headers['referrer-policy'],'no-referrer');self.assertNotIn(state,response.text)
        response=await self.finish_graph(state);self.assertEqual(response.status_code,400);self.assertIn('Return to your workspace',response.text);self.assertNotIn(state,response.text);self.assertEqual(len([c for c in self.graph_http.calls if c[0]=='POST']),1)
        response=await self.client.post('/api/sources/confluence/connect',json={},headers=self.headers());state=parse_qs(urlsplit(response.json()['authorizationUrl']).query)['state'][0]
        response=await self.client.get('/oauth/callback/confluence',params={'state':state,'code':'SYNTHETIC-CODE'});self.assertEqual(response.status_code,303);self.assertNotIn('SYNTHETIC',response.headers['location'])

    async def test_late_native_consent_response_cannot_reverse_disconnect(self):
        await self.login();await self.connect_all();state=await self.start_graph();native=self.graph_http.post
        def delayed(url,**kwargs):
            result=native(url,**kwargs);self.store.disconnect(self.principal,self.graph.source_id);return result
        self.graph_http.post=delayed
        response=await self.finish_graph(state);self.assertEqual(response.status_code,400);self.assertEqual(self.store.connection_status(self.principal,self.graph.source_id),'revoked')
        response=await self.client.post('/api/ask',json={'question':'policy'},headers=self.headers());self.assertEqual(response.status_code,409);self.assertEqual(self.model_calls,[])

    async def test_callback_wrong_browser_same_person_does_not_consume_original_state(self):
        await self.login();state=await self.start_graph();second=self.new_client();self.clients.append(second);await self.login(second)
        response=await self.finish_graph(state,second);self.assertEqual(response.status_code,400);self.assertFalse(any(c[0]=='POST'for c in self.graph_http.calls))
        response=await self.finish_graph(state);self.assertEqual(response.status_code,303,response.text)

    async def test_login_rotation_preserves_pending_oauth_but_new_person_does_not(self):
        await self.login();state=await self.start_graph();old=self.client.cookies.get(COOKIE);await self.login();self.assertNotEqual(self.client.cookies.get(COOKIE),old)
        response=await self.finish_graph(state);self.assertEqual(response.status_code,303,response.text)
        state=await self.start_graph();await self.login(subject='bob');response=await self.finish_graph(state);self.assertEqual(response.status_code,400);self.assertEqual(len([c for c in self.graph_http.calls if c[0]=='POST']),1)

    async def test_callbacks_reject_wrong_method_duplicates_and_declined_consent_safely(self):
        await self.login();state=await self.start_graph()
        response=await self.client.get('/oauth/callback/sharepoint',params={'code':'SYNTHETIC-CODE','state':state});self.assertEqual(response.status_code,400)
        response=await self.client.post('/oauth/callback/sharepoint',content='state='+state+'&state='+state+'&code=PRIVATE-CODE',headers={'Content-Type':'application/x-www-form-urlencoded'});self.assertEqual(response.status_code,400);self.assertNotIn('PRIVATE-CODE',response.text)
        response=await self.client.post('/oauth/callback/sharepoint',data={'state':state,'error':'access_denied','error_description':'PRIVATE-UPSTREAM-BODY'});self.assertEqual(response.status_code,400);self.assertNotIn('PRIVATE',response.text)
        response=await self.finish_graph(state);self.assertEqual(response.status_code,400);self.assertFalse(any(c[0]=='POST'for c in self.graph_http.calls))

    async def test_question_reaches_current_model_only_after_connections(self):
        await self.login();response=await self.client.post('/api/ask',json={'question':'policy'},headers=self.headers());self.assertEqual(response.status_code,409);self.assertEqual(self.model_calls,[])
        await self.connect_all();response=await self.client.post('/api/ask',json={'question':'policy'},headers=self.headers());self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['citations'][0]['title'],'Private policy');self.assertEqual(len(self.model_calls),1)
        self.assertEqual(self.factory_calls[0][1],{'sharepoint','confluence'});self.assertNotIn('Private policy',json.dumps(self.audit))

    async def test_logout_and_company_revocation_clear_backend_access(self):
        await self.login();response=await self.client.delete('/api/session',headers=self.headers());self.assertEqual(response.status_code,204)
        response=await self.client.post('/api/ask',json={'question':'policy'},headers=self.headers());self.assertEqual(response.status_code,401)
        await self.login()
        with psycopg.connect(self.owner_dsn)as conn:conn.execute('UPDATE enterprise_auth.memberships SET active=false WHERE account_id=%s AND principal_key=%s',(self.account,self.principal.key))
        response=await self.client.get('/api/session',headers={'X-Workspace-Request':'session'});self.assertEqual(response.status_code,403);self.assertIn('workspace owner',response.text)

    async def test_company_revocation_during_model_withholds_private_response(self):
        await self.login();await self.connect_all();self.revoke_during_model=True
        response=await self.client.post('/api/ask',json={'question':'policy'},headers=self.headers());self.assertEqual(response.status_code,403,response.text);self.assertNotIn('Private policy',response.text);self.assertNotIn('ninety',response.text)

    async def test_disconnect_missing_mapping_and_errors_have_actionable_private_safe_messages(self):
        await self.login();await self.connect_all();self.fail_model=True
        response=await self.client.post('/api/ask',json={'question':'policy'},headers=self.headers());self.assertEqual(response.status_code,503);self.assertNotIn('PRIVATE-',response.text)
        response=await self.client.delete('/api/sources/sharepoint',headers=self.headers());self.assertEqual(response.status_code,204)
        response=await self.client.post('/api/ask',json={'question':'policy'},headers=self.headers());self.assertEqual(response.status_code,409)
        with psycopg.connect(self.owner_dsn)as conn:conn.execute('UPDATE enterprise_auth.source_mappings SET active=false WHERE account_id=%s AND source_id=%s',(self.account,'sharepoint:drive'))
        response=await self.client.post('/api/sources/sharepoint/connect',json={},headers=self.headers());self.assertEqual(response.status_code,403);self.assertIn('workspace owner',response.text)

if __name__=='__main__':unittest.main()
