"""Native staff login bindings. Database membership remains authoritative for roles.

Configuration is compiler/operator-owned. Never derive a signing-key URL, tenant,
issuer, OAuth audience or processing role from caller claims or document content.
JWT validity is bounded by expiry, not a claim of continuous IdP revocation.
"""
from dataclasses import dataclass
import re
import uuid
import jwt
from durable_workflow import Denied

UUID=r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

class CognitoStaffVerifier:
    def __init__(self,region,pool_id,client_id,scope,*,jwks=None):
        if(not isinstance(region,str)or not re.fullmatch(r'[a-z]{2}-[a-z]+-[0-9]',region)
           or not isinstance(pool_id,str)or not re.fullmatch(re.escape(region)+r'_[A-Za-z0-9]{1,55}',pool_id)
           or not isinstance(client_id,str)or not re.fullmatch(r'[a-z0-9]{1,128}',client_id)
           or not isinstance(scope,str)or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}/process',scope)):raise ValueError('Use the exact owned Cognito pool/client/scope')
        self.issuer='https://cognito-idp.'+region+'.amazonaws.com/'+pool_id;self.client_id=client_id;self.scope=scope
        self.jwks=jwks or jwt.PyJWKClient(self.issuer+'/.well-known/jwks.json',timeout=2,lifespan=300)
    def __call__(self,token):
        try:
            if not isinstance(token,str)or not 1<=len(token)<=16384:raise Denied('Verified staff identity required')
            key=self.jwks.get_signing_key_from_jwt(token).key
            # Cognito ACCESS tokens bind the app client in client_id, rather than
            # the ID token's aud. Never accept an ID token as an API credential.
            claims=jwt.decode(token,key,algorithms=['RS256'],issuer=self.issuer,options={'verify_aud':False,'require':['iss','sub','exp','iat','client_id','token_use','scope','username']})
            if(claims['token_use']!='access'or claims['client_id']!=self.client_id
               or not isinstance(claims['scope'],str)or self.scope not in claims['scope'].split()
               or not isinstance(claims['sub'],str)or str(uuid.UUID(claims['sub']))!=claims['sub']
               or not isinstance(claims['username'],str)or not claims['username']
               or any(type(claims[name])is not int for name in ['iat','exp'])or not 0<claims['exp']-claims['iat']<=3600):raise Denied('Verified staff identity required')
            return claims['sub']
        except Exception:raise Denied('Verified staff identity required')from None

@dataclass(frozen=True)
class StaffIdentity:
    verify:object
    public_configuration:dict
    token_header:str|None=None

def native_staff_identity(provider,settings,*,jwks=None):
    if not isinstance(settings,dict)or any(not isinstance(value,str)for value in settings.values()):raise ValueError('Use owned native staff identity settings')
    patterns={
        'aws':{'REGION':r'[a-z]{2}-[a-z]+-[0-9]','POOL_ID':r'[a-z]{2}-[a-z]+-[0-9]_[A-Za-z0-9]{1,55}','CLIENT_ID':r'[a-z0-9]{1,128}','AUTH_ORIGIN':r'https://[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\.auth\.[a-z]{2}-[a-z]+-[0-9]\.amazoncognito\.com','AUTH_SCOPE':r'[A-Za-z0-9_.-]{1,80}/process'},
        'azure':{'TENANT_ID':UUID,'API_CLIENT_ID':UUID,'SPA_CLIENT_ID':UUID},
        'gcp':{'PROJECT_NUMBER':r'[0-9]{6,20}','REGION':r'[a-z]+-[a-z]+[0-9]','SERVICE_NAME':r'[a-z][a-z0-9-]{4,47}[a-z0-9]'},
        'ibm':{'APPID_TENANT_ID':UUID,'APPID_CLIENT_ID':UUID,'APPID_ISSUER':r'https://[a-z]{2}-[a-z]+\.appid\.cloud\.ibm\.com/oauth/v4/'+UUID,'AUTH_SCOPE':r'[A-Za-z0-9_.-]{1,80}/process'}}
    if provider not in patterns or set(settings)!=set(patterns[provider])or any(not re.fullmatch(patterns[provider][name],value)for name,value in settings.items()):raise ValueError('Use exact reviewed native staff identity settings')
    c=dict(settings)
    if provider=='aws':
        if not c['AUTH_ORIGIN'].endswith('.auth.'+c['REGION']+'.amazoncognito.com'):raise ValueError('Cognito authorization region differs from the owned pool')
        verify=CognitoStaffVerifier(c['REGION'],c['POOL_ID'],c['CLIENT_ID'],c['AUTH_SCOPE'],jwks=jwks)
        public={'mode':'oauth-pkce','authOrigin':c['AUTH_ORIGIN'],'authorizationEndpoint':c['AUTH_ORIGIN']+'/oauth2/authorize','tokenEndpoint':c['AUTH_ORIGIN']+'/oauth2/token','clientId':c['CLIENT_ID'],'scopes':'openid '+c['AUTH_SCOPE']}
    elif provider=='azure':
        from azure_structured import EntraVerifier
        verify=EntraVerifier(c,jwks);authority='https://login.microsoftonline.com/'+c['TENANT_ID']+'/oauth2/v2.0'
        public={'mode':'oauth-pkce','authOrigin':'https://login.microsoftonline.com','authorizationEndpoint':authority+'/authorize','tokenEndpoint':authority+'/token','clientId':c['SPA_CLIENT_ID'],'scopes':'openid api://'+c['API_CLIENT_ID']+'/access_as_user'}
    elif provider=='gcp':
        from gcp_structured import IapVerifier
        return StaffIdentity(IapVerifier(c,jwks),{'mode':'proxy','loginPath':'/','logoutPath':None},'x-goog-iap-jwt-assertion')
    else:
        from ibm_structured import AppIdVerifier
        if not c['APPID_ISSUER'].endswith('/oauth/v4/'+c['APPID_TENANT_ID']):raise ValueError('App ID issuer tenant differs from the owned tenant')
        verify=AppIdVerifier(c,jwks);issuer=c['APPID_ISSUER'];origin=issuer.split('/oauth/v4/')[0]
        public={'mode':'oauth-pkce','authOrigin':origin,'authorizationEndpoint':issuer+'/authorization','tokenEndpoint':issuer+'/token','clientId':c['APPID_CLIENT_ID'],'scopes':'openid '+c['AUTH_SCOPE']}
    return StaffIdentity(verify,public)
