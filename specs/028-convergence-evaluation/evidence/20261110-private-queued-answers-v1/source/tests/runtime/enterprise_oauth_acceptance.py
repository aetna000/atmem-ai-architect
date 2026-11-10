"""Actual MSAL code/cache/refresh, scripted OAuth/profile HTTP, no vendor login."""
import base64
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from urllib.parse import parse_qs,urlsplit
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/azure-runtime-sdk')]
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from enterprise_identity import CompanyPrincipal
from enterprise_oauth import GraphConsent,ConfluenceConsent,TokenHttp
from enterprise_sources import Reply,SourceDenied,SourceUnavailable

TENANT='11111111-1111-4111-8111-111111111111';CLIENT='22222222-2222-4222-8222-222222222222';CLOUD='33333333-3333-4333-8333-333333333333'
class Response:
    def __init__(self,value,status=200):self.text=json.dumps(value);self.status_code=status;self.headers={}
    def json(self):return json.loads(self.text)
    def raise_for_status(self):
        if self.status_code>=400:raise RuntimeError('SYNTHETIC-UPSTREAM-FAILURE')
class OAuthHttp:
    def __init__(self):self.calls=[];self.nonce=None;self.key=rsa.generate_private_key(public_exponent=65537,key_size=2048);self.error=False
    def get(self,url,**kwargs):
        self.calls.append(('GET',url,kwargs));base='https://login.microsoftonline.com/'+TENANT
        if url.endswith('/.well-known/openid-configuration'):return Response({'authorization_endpoint':base+'/oauth2/v2.0/authorize','token_endpoint':base+'/oauth2/v2.0/token','issuer':base+'/v2.0','jwks_uri':base+'/discovery/v2.0/keys'})
        raise AssertionError('Unexpected native MSAL discovery endpoint')
    def post(self,url,**kwargs):
        self.calls.append(('POST',url,kwargs))
        if self.error:return Response({'error':'invalid_grant','error_description':'PRIVATE-UPSTREAM-BODY'},400)
        n=len([call for call in self.calls if call[0]=='POST']);tokens={'access_token':'SYNTHETIC_ACCESS_'+str(n),'refresh_token':'SYNTHETIC_REFRESH_'+str(n),'token_type':'Bearer','expires_in':3600}
        if 'login.microsoftonline.com'in url:
            data=kwargs['data'];assert data['client_secret']=='SYNTHETIC-CLIENT-SECRET';now=int(time.time())
            if data.get('grant_type')=='authorization_code':assert data.get('code_verifier')
            tokens.update({'scope':' '.join(GraphConsent.SCOPES+['openid','profile','offline_access']),'id_token':jwt.encode({'aud':CLIENT,'iss':'https://login.microsoftonline.com/'+TENANT+'/v2.0','sub':'synthetic-source-sub','oid':'alice-native','tid':TENANT,'iat':now,'exp':now+3600,'nonce':self.nonce,'preferred_username':'synthetic@example.test'},self.key,algorithm='RS256'),'client_info':base64.urlsafe_b64encode(json.dumps({'uid':'alice-native','utid':TENANT}).encode()).decode().rstrip('=')})
        else:assert kwargs['json']['client_secret']=='SYNTHETIC-CLIENT-SECRET'
        return Response(tokens)
class Profiles:
    def __init__(self):self.wrong=False;self.calls=[]
    def get(self,url,token,**kwargs):
        self.calls.append((url,token));subject='bob-native'if self.wrong else'alice-native'
        if 'graph.microsoft.com'in url:value={'id':subject}
        elif url.endswith('/me'):value={'account_id':subject,'account_status':'active'}
        else:value=[{'id':CLOUD,'url':'https://tenant.atlassian.net','scopes':['read:page:confluence','search:confluence']}]
        return Reply(200,{},json.dumps(value).encode())
class MemoryStore:
    def __init__(self,principal,source_id):self.principal=principal;self.mapping=SimpleNamespace(source_id=source_id,source_subject='alice-native',version=1);self.pending={};self.material=None
    def authorize(self,principal):assert principal==self.principal
    def begin(self,principal,source_id,browser,flow,state=None):
        self.authorize(principal);assert source_id==self.mapping.source_id;state=state or'SYNTHETIC-STATE';self.pending[state]=(browser,flow);return state
    def consume(self,principal,source_id,browser,state):
        self.authorize(principal)
        if state not in self.pending or self.pending[state][0]!=browser:raise SourceDenied('oauth_state_unavailable')
        _,flow=self.pending.pop(state);return self.mapping,flow
    def save(self,principal,mapping,material):self.authorize(principal);assert mapping==self.mapping;self.material=material
    def credentials(self,principal,source_id,refresh):
        self.authorize(principal)
        if not self.material:raise SourceDenied('source_reconnection_required')
        self.material,access=refresh(self.mapping,self.material);return access

class NativeOAuthProtocols(unittest.TestCase):
    def setUp(self):self.principal=CompanyPrincipal('company1','https://company.example/issuer','alice',int(time.time())+3600);self.http=OAuthHttp();self.profiles=Profiles()
    def graph(self):
        self.store=MemoryStore(self.principal,'sharepoint:drive');return GraphConsent(self.store,TENANT,CLIENT,'https://app.example/oauth/graph','drive','tenant.sharepoint.com',lambda:'SYNTHETIC-CLIENT-SECRET',http=self.http,profile_http=self.profiles)
    def confluence(self):
        self.store=MemoryStore(self.principal,'confluence:'+CLOUD);return ConfluenceConsent(self.store,'client','https://app.example/oauth/confluence',CLOUD,'tenant.atlassian.net',{'ENG':'42'},lambda:'SYNTHETIC-CLIENT-SECRET',http=self.http,profile_http=self.profiles)
    def test_token_http_forbids_cross_host_redirects_retries_and_environment_proxy(self):
        http=TokenHttp('auth.atlassian.com');self.assertFalse(http.session.trust_env);self.assertEqual(http.session.get_adapter('https://').max_retries.total,0);calls=[]
        class Stream:
            status_code=302;closed=False
            def iter_content(self,size):return iter([b'{}'])
            def close(self):self.closed=True
        response=Stream()
        def request(method,url,**kwargs):calls.append((method,url,kwargs));return response
        http.session.request=request
        result=http.post('https://auth.atlassian.com/oauth/token',json={'refresh_token':'SYNTHETIC'},allow_redirects=True)
        self.assertEqual(result.status_code,302);self.assertTrue(response.closed);self.assertFalse(calls[0][2]['allow_redirects']);self.assertEqual(calls[0][2]['timeout'],(3,10))
        with self.assertRaises(SourceUnavailable):http.post('https://evil.example/token',json={'refresh_token':'SYNTHETIC'})
        self.assertEqual(len(calls),1)

    def test_token_http_uncertain_transport_body_is_hidden(self):
        http=TokenHttp('auth.atlassian.com')
        def uncertain(*args,**kwargs):raise RuntimeError('PRIVATE-REFRESH-SECRET-HTTP-BODY')
        http.session.request=uncertain
        with self.assertRaisesRegex(SourceUnavailable,'oauth_transport_unavailable')as caught:http.post('https://auth.atlassian.com/oauth/token',json={'refresh_token':'SYNTHETIC'})
        self.assertNotIn('PRIVATE',str(caught.exception))

    def test_msal_native_code_pkce_cache_and_rotating_refresh(self):
        driver=self.graph();start=driver.start(self.principal,'browser');params=parse_qs(urlsplit(start.url).query);self.http.nonce=params['nonce'][0];self.assertEqual(params['response_mode'],['form_post']);self.assertEqual(params['code_challenge_method'],['S256']);self.assertNotIn('SYNTHETIC-CLIENT-SECRET',start.url)
        driver.finish(self.principal,'browser',start.state,'SYNTHETIC-CODE');self.assertEqual(self.store.material['format'],'msal-graph-v1')
        self.assertEqual(driver.credentials(self.principal).source_subject,'alice-native');self.assertEqual(len([c for c in self.http.calls if c[0]=='POST']),1)
        cache=json.loads(self.store.material['cache']);cache.pop('AccessToken',None);self.store.material['cache']=json.dumps(cache)
        self.assertEqual(driver.credentials(self.principal).source_subject,'alice-native');posts=[c for c in self.http.calls if c[0]=='POST'];self.assertEqual(posts[-1][2]['data']['grant_type'],'refresh_token');self.assertEqual(posts[-1][2]['data']['refresh_token'],'SYNTHETIC_REFRESH_1');self.assertIn('SYNTHETIC_REFRESH_2',self.store.material['cache'])
    def test_msal_profile_mismatch_and_state_replay_do_not_save_credentials(self):
        driver=self.graph();start=driver.start(self.principal,'browser');self.http.nonce=parse_qs(urlsplit(start.url).query)['nonce'][0];self.profiles.wrong=True
        with self.assertRaises(SourceDenied):driver.finish(self.principal,'browser',start.state,'SYNTHETIC-CODE')
        self.assertIsNone(self.store.material)
        with self.assertRaises(SourceDenied):driver.finish(self.principal,'browser',start.state,'SYNTHETIC-CODE')
        self.assertEqual(len([c for c in self.http.calls if c[0]=='POST']),1)
    def test_msal_settings_change_consumes_state_without_token_request(self):
        driver=self.graph();start=driver.start(self.principal,'browser');driver.settings='changed'
        with self.assertRaises(SourceDenied):driver.finish(self.principal,'browser',start.state,'SYNTHETIC-CODE')
        self.assertFalse(any(c[0]=='POST'for c in self.http.calls))
    def test_confluence_native_confidential_exchange_and_refresh_rotation(self):
        driver=self.confluence();start=driver.start(self.principal,'browser');params=parse_qs(urlsplit(start.url).query);self.assertEqual(params['audience'],['api.atlassian.com']);self.assertIn('offline_access',params['scope'][0]);self.assertNotIn('code_challenge',params);self.assertNotIn('SYNTHETIC-CLIENT-SECRET',start.url)
        driver.finish(self.principal,'browser',start.state,'SYNTHETIC-CODE');self.assertEqual(driver.credentials(self.principal).source_subject,'alice-native');posts=[c for c in self.http.calls if c[0]=='POST'];self.assertEqual(posts[0][2]['json']['grant_type'],'authorization_code');self.assertEqual(posts[1][2]['json']['refresh_token'],'SYNTHETIC_REFRESH_1');self.assertEqual(self.store.material['tokens']['refresh_token'],'SYNTHETIC_REFRESH_2')
    def test_confluence_error_and_profile_mismatch_never_save(self):
        driver=self.confluence();start=driver.start(self.principal,'browser');self.http.error=True
        with self.assertRaises(SourceDenied)as caught:driver.finish(self.principal,'browser',start.state,'SYNTHETIC-CODE')
        self.assertNotIn('PRIVATE',str(caught.exception));self.assertIsNone(self.store.material)
        self.http.error=False;start=driver.start(self.principal,'browser');self.profiles.wrong=True
        with self.assertRaises(SourceDenied):driver.finish(self.principal,'browser',start.state,'SYNTHETIC-CODE')
        self.assertIsNone(self.store.material)

if __name__=='__main__':unittest.main()
