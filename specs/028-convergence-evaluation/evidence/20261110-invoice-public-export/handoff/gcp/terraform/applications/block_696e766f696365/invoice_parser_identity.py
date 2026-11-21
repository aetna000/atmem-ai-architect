"""Parser-only Entra workload authorization; no application/cloud credentials.

The issuer/key endpoint, audience and exact worker identities are compiler-owned.
Staff/delegated tokens and another application in the same tenant grant no access.
This module does not claim that a valid token proves a native deployment exists.
"""
import re
import hmac
import jwt

UUID=r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

class EntraParserVerifier:
    def __init__(self,tenant,audience,worker_client,worker_principal,*,jwks=None):
        if any(not isinstance(value,str)or not re.fullmatch(UUID,value)for value in [tenant,audience,worker_client,worker_principal]):raise ValueError('Use exact owned Entra parser and worker identities')
        self.tenant=tenant;self.audience=audience;self.worker_client=worker_client;self.worker_principal=worker_principal
        self.issuer='https://login.microsoftonline.com/'+tenant+'/v2.0'
        self.jwks=jwks or jwt.PyJWKClient('https://login.microsoftonline.com/'+tenant+'/discovery/v2.0/keys',timeout=2,lifespan=300)
    def __call__(self,token):
        try:
            if not isinstance(token,str)or not 1<=len(token)<=16384:raise ValueError('Invalid workload token')
            header=jwt.get_unverified_header(token)
            if header.get('alg')!='RS256'or not isinstance(header.get('kid'),str)or not 1<=len(header['kid'])<=200:raise ValueError('Invalid workload signing key')
            key=self.jwks.get_signing_key_from_jwt(token).key
            claims=jwt.decode(token,key,algorithms=['RS256'],issuer=self.issuer,audience=self.audience,leeway=30,options={'require':['iss','aud','iat','nbf','exp','tid','oid','azp','ver','roles']})
            if(claims['aud']!=self.audience or claims['tid']!=self.tenant or claims['oid']!=self.worker_principal or claims['azp']!=self.worker_client or claims['ver']!='2.0'
               or'scp'in claims or claims.get('idtyp','app')!='app'or not isinstance(claims['roles'],list)or not 1<=len(claims['roles'])<=100 or any(not isinstance(role,str)for role in claims['roles'])or'Parser.Invoke'not in claims['roles']
               or any(type(claims[name])is not int for name in ['iat','nbf','exp'])or not 0<claims['exp']-claims['iat']<=86700):raise ValueError('Caller is not the owned parser worker')
            return self.worker_principal
        except Exception:raise PermissionError('Authorized parser worker required')from None

class SharedParserVerifier:
    """Private TLS RPC admission only; this token confers no cloud/data authority."""
    def __init__(self,token):
        if not isinstance(token,str)or not re.fullmatch(r'[0-9a-f]{64}',token):raise ValueError('Use a separately provisioned 256-bit parser token')
        self._token=token
    def __call__(self,token):
        if not isinstance(token,str)or not re.fullmatch(r'[0-9a-f]{64}',token)or not hmac.compare_digest(self._token,token):raise PermissionError('Authorized parser worker required')
        return'owned-worker'
