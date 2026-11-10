"""Native delegated source consent: MSAL Graph and confidential Atlassian 3LO.

Existing company login is separate. Immutable source-account mappings are read
from the operator-owned store; a browser cannot choose another person's mapping.
Client secrets are injected, not stored in flow records or model context.
"""
from dataclasses import dataclass,field
import hashlib
import json
import re
import secrets
import time
from urllib.parse import urlencode,urlsplit
import msal
import requests
from enterprise_identity import trusted_https
from enterprise_sources import DelegatedAccess,GraphSharePoint,ConfluenceCloud,SourceDenied,SourceUnavailable,NativeHttp,checked_url


@dataclass(frozen=True)
class AuthorizationStart:
    url: str = field(repr=False)
    state: str = field(repr=False)


class TokenHttp:
    """No retries, redirects or environment proxies for rotating-token requests."""
    def __init__(self,host):
        self.host=host;self.session=requests.Session();self.session.trust_env=False
        self.session.mount('https://',requests.adapters.HTTPAdapter(max_retries=0))
    def request(self,method,url,**kwargs):
        checked_url(url,{self.host});kwargs.pop('timeout',None);kwargs.pop('allow_redirects',None)
        try:
            response=self.session.request(method,url,timeout=(3,10),allow_redirects=False,stream=True,**kwargs)
            try:
                body=bytearray()
                for chunk in response.iter_content(8192):
                    body.extend(chunk)
                    if len(body)>1000000:raise SourceUnavailable('oauth_response_too_large')
                response._content=bytes(body);response._content_consumed=True
            finally:response.close()
            return response
        except Exception:raise SourceUnavailable('oauth_transport_unavailable')from None
    def get(self,url,**kwargs):return self.request('GET',url,**kwargs)
    def post(self,url,**kwargs):return self.request('POST',url,**kwargs)


def settings_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def checked_code(code):
    if not isinstance(code,str)or not 1<=len(code)<=8192 or any(ord(c)<33 for c in code):raise SourceDenied('source_consent_required')
    return code

def candidate(principal,mapping,result):
    if not isinstance(result,dict)or not isinstance(result.get('access_token'),str)or not result['access_token']or type(result.get('expires_in'))is not int or not 5<result['expires_in']<=86400 or not isinstance(result.get('token_type','Bearer'),str)or result.get('token_type','Bearer').lower()!='bearer':raise SourceDenied('source_consent_required')
    access=DelegatedAccess(principal.key,mapping.source_subject,result['access_token'],time.time()+result['expires_in']);access.require(principal.key);return access


class GraphConsent:
    SCOPES=['https://graph.microsoft.com/Files.Read','https://graph.microsoft.com/User.Read']
    def __init__(self,store,tenant_id,client_id,redirect_uri,drive_id,sharepoint_host,secret,*,http=None,profile_http=None):
        uuid=r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        if not re.fullmatch(uuid,tenant_id)or not re.fullmatch(uuid,client_id)or not callable(secret):raise ValueError('Use the owned Graph OAuth registration')
        self.store=store;self.tenant=tenant_id;self.client=client_id;self.redirect=trusted_https(redirect_uri);self.drive=drive_id;self.host=sharepoint_host;self.secret=secret;self.http=http or TokenHttp('login.microsoftonline.com');self.profile_http=profile_http or NativeHttp();self.source_id='sharepoint:'+drive_id
        self.settings=settings_hash([tenant_id,client_id,redirect_uri,drive_id,sharepoint_host,self.SCOPES])
    def app(self,cache):
        return msal.ConfidentialClientApplication(self.client,client_credential=self.secret(),authority='https://login.microsoftonline.com/'+self.tenant,token_cache=cache,http_client=self.http,instance_discovery=False,azure_region=False,enable_pii_log=False)
    def start(self,principal,browser_nonce):
        self.store.authorize(principal)
        try:
            app=self.app(msal.SerializableTokenCache());flow=app.initiate_auth_code_flow(self.SCOPES,redirect_uri=self.redirect,state=secrets.token_urlsafe(32),response_mode='form_post',prompt='select_account')
            if not isinstance(flow,dict)or not flow.get('code_verifier')or not flow.get('state')or not flow.get('auth_uri'):raise SourceDenied('source_consent_unavailable')
            checked_url(flow['auth_uri'],{'login.microsoftonline.com'})
            self.store.begin(principal,self.source_id,browser_nonce,{'settings':self.settings,'native':flow},state=flow['state'])
            return AuthorizationStart(flow['auth_uri'],flow['state'])
        except Exception:raise SourceDenied('source_consent_unavailable')from None
    def finish(self,principal,browser_nonce,state,code):
        mapping,flow=self.store.consume(principal,self.source_id,browser_nonce,state)
        try:
            if flow.get('settings')!=self.settings:raise SourceDenied('source_configuration_changed')
            cache=msal.SerializableTokenCache();app=self.app(cache);result=app.acquire_token_by_auth_code_flow(flow['native'],{'state':state,'code':checked_code(code)})
            access=candidate(principal,mapping,result);GraphSharePoint(self.drive,self.host,access,http=self.profile_http).identify(principal.key)
            accounts=[a for a in app.get_accounts()if a.get('local_account_id')==mapping.source_subject and a.get('realm')==self.tenant]
            if len(accounts)!=1:raise SourceDenied('source_identity_mismatch')
            self.store.save(principal,mapping,{'format':'msal-graph-v1','settings':self.settings,'cache':cache.serialize()})
        except Exception:raise SourceDenied('source_consent_required')from None
    def credentials(self,principal):
        def refresh(mapping,material):
            if material.get('format')!='msal-graph-v1'or material.get('settings')!=self.settings:raise SourceDenied('source_configuration_changed')
            cache=msal.SerializableTokenCache();cache.deserialize(material['cache']);app=self.app(cache)
            accounts=[a for a in app.get_accounts()if a.get('local_account_id')==mapping.source_subject and a.get('realm')==self.tenant]
            if len(accounts)!=1:raise SourceDenied('source_identity_mismatch')
            result=app.acquire_token_silent_with_error(self.SCOPES,accounts[0]);access=candidate(principal,mapping,result)
            GraphSharePoint(self.drive,self.host,access,http=self.profile_http).identify(principal.key)
            return {**material,'cache':cache.serialize()},access
        return self.store.credentials(principal,self.source_id,refresh)


class ConfluenceConsent:
    SCOPES=['read:me','read:page:confluence','search:confluence','offline_access']
    def __init__(self,store,client_id,redirect_uri,cloud_id,site_host,spaces,secret,*,http=None,profile_http=None):
        if not isinstance(client_id,str)or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',client_id)or not callable(secret):raise ValueError('Use the owned Atlassian OAuth registration')
        self.store=store;self.client=client_id;self.redirect=trusted_https(redirect_uri);self.cloud=cloud_id;self.host=site_host;self.spaces=spaces;self.secret=secret;self.http=http or TokenHttp('auth.atlassian.com');self.profile_http=profile_http or NativeHttp();self.source_id='confluence:'+cloud_id
        self.settings=settings_hash([client_id,redirect_uri,cloud_id,site_host,spaces,self.SCOPES])
    def start(self,principal,browser_nonce):
        state=self.store.begin(principal,self.source_id,browser_nonce,{'settings':self.settings})
        params={'audience':'api.atlassian.com','client_id':self.client,'scope':' '.join(self.SCOPES),'redirect_uri':self.redirect,'state':state,'response_type':'code','prompt':'consent'}
        # Cloud 3LO uses its documented confidential-client exchange. Do not claim
        # Data Center's separate PKCE support applies to the Cloud API.
        return AuthorizationStart('https://auth.atlassian.com/authorize?'+urlencode(params),state)
    def token(self,body):
        try:
            response=self.http.post('https://auth.atlassian.com/oauth/token',json={'client_id':self.client,'client_secret':self.secret(),**body})
            if response.status_code!=200:raise SourceDenied('source_consent_required')
            value=response.json()
            if not isinstance(value,dict)or not isinstance(value.get('refresh_token'),str)or not 1<=len(value['refresh_token'])<=32768:raise SourceDenied('source_consent_required')
            return value
        except Exception:raise SourceDenied('source_consent_required')from None
    def verified(self,principal,mapping,result):
        access=candidate(principal,mapping,result);ConfluenceCloud(self.cloud,self.host,self.spaces,access,http=self.profile_http).identify(principal.key);return access
    def finish(self,principal,browser_nonce,state,code):
        mapping,flow=self.store.consume(principal,self.source_id,browser_nonce,state)
        if flow.get('settings')!=self.settings:raise SourceDenied('source_configuration_changed')
        result=self.token({'grant_type':'authorization_code','code':checked_code(code),'redirect_uri':self.redirect});self.verified(principal,mapping,result)
        self.store.save(principal,mapping,{'format':'atlassian-3lo-v1','settings':self.settings,'tokens':result})
    def credentials(self,principal):
        def refresh(mapping,material):
            if material.get('format')!='atlassian-3lo-v1'or material.get('settings')!=self.settings:raise SourceDenied('source_configuration_changed')
            # Refresh on demand rather than retaining access decisions. Rotating
            # credential use is fenced durably by the store before this POST.
            result=self.token({'grant_type':'refresh_token','refresh_token':material['tokens']['refresh_token']});access=self.verified(principal,mapping,result)
            return {**material,'tokens':result},access
        return self.store.credentials(principal,self.source_id,refresh)
