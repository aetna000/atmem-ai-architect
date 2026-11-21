"""Existing company API identity; no replacement IdP or source-token claims.

Issuer, API audience, JWKS URL, delegated scope and account are operator-owned
configuration. Live membership remains a separate required database check.
"""
from dataclasses import dataclass,field
import hashlib
import re
import time
from urllib.parse import urlsplit
import jwt
from enterprise_sources import SourceDenied


def trusted_https(value):
    try:parts=urlsplit(value);port=parts.port
    except (TypeError,ValueError):raise ValueError('Invalid owned identity endpoint')from None
    if parts.scheme!='https'or not parts.hostname or (port is not None and not 1<=port<=65535)or parts.username or parts.password or parts.query or parts.fragment or any(ord(c)<33 for c in value):raise ValueError('Invalid owned identity endpoint')
    return value


@dataclass(frozen=True)
class CompanyPrincipal:
    account_id: str
    issuer: str
    subject: str = field(repr=False)
    expires_at: int

    @property
    def key(self):return hashlib.sha256((self.issuer+'\0'+self.subject).encode()).hexdigest()

    def require(self):
        if type(self.expires_at)is not int or self.expires_at<=time.time()+5:raise SourceDenied('company_identity_expired')


class CompanyIdentity:
    def __init__(self,account_id,issuer,audience,jwks_uri,scope='knowledge.read',*,jwks=None):
        if not isinstance(account_id,str)or not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}',account_id):raise ValueError('Use the owned company account')
        if not isinstance(audience,str)or not 1<=len(audience)<=300 or not isinstance(scope,str)or not re.fullmatch(r'[A-Za-z0-9_./:-]{1,200}',scope):raise ValueError('Use the owned API audience and delegated scope')
        self.account_id=account_id;self.issuer=trusted_https(issuer);self.audience=audience;self.scope=scope
        self.jwks_uri=trusted_https(jwks_uri)
        self.jwks=jwks or jwt.PyJWKClient(self.jwks_uri,timeout=3,lifespan=300,cache_keys=False)

    def verify(self,token):
        try:
            if not isinstance(token,str)or not 1<=len(token)<=16384:raise ValueError('Invalid token')
            key=self.jwks.get_signing_key_from_jwt(token).key
            claims=jwt.decode(token,key,algorithms=['RS256'],issuer=self.issuer,audience=self.audience,options={'require':['iss','sub','aud','exp','iat']})
            scope=claims.get('scp',claims.get('scope'))
            if not isinstance(scope,str)or self.scope not in scope.split()or claims['aud']!=self.audience or not isinstance(claims['sub'],str)or not 1<=len(claims['sub'].encode())<=255 or any(ord(c)<32 for c in claims['sub'])or any(type(claims[k])is not int for k in ['iat','exp'])or not 0<claims['exp']-claims['iat']<=3600:raise ValueError('Invalid company API credential')
            principal=CompanyPrincipal(self.account_id,self.issuer,claims['sub'],claims['exp']);principal.require();return principal
        except Exception:raise SourceDenied('company_identity_required')from None
