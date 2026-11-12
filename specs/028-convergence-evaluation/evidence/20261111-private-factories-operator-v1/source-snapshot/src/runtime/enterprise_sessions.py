"""Opaque, durable company sessions; raw cookies/JWTs never persist in SQL."""
from dataclasses import dataclass,field
import hmac
import secrets
import time
import re
from enterprise_auth_store import digest,secret_binding
from enterprise_identity import CompanyPrincipal
from enterprise_sources import SourceDenied


@dataclass(frozen=True)
class BrowserSession:
    principal: CompanyPrincipal
    id: str = field(repr=False)
    browser_nonce: str = field(repr=False)
    csrf_sha256: str = field(repr=False)
    csrf: str = field(repr=False)

    def require_csrf(self,token):
        secret_binding(token)
        if not hmac.compare_digest(digest(token),self.csrf_sha256):raise SourceDenied('browser_request_denied')


@dataclass(frozen=True)
class CreatedSession:
    token: str = field(repr=False)
    csrf: str = field(repr=False)
    max_age: int


class CompanySessions:
    def __init__(self,auth,*,domain=None):
        if domain is not None and(not isinstance(domain,str)or not re.fullmatch('[0-9a-f]{64}',domain)):raise ValueError('Use the owned company session domain')
        if getattr(auth,'company_domain',None)!=domain:raise ValueError('Session and authority company registrations must match')
        self.auth=auth;self.domain=domain
    def context(self,account,key,session):
        result=['browser-session',account,key,session]
        if self.domain is not None:result+=['company-registration',self.domain]
        return result

    def private(self,row,identity):
        try:
            private=self.auth.box.open(self.context(row['account_id'],row['principal_key'],identity),row['nonce_ciphertext'])
            if set(private)!={'browser_nonce','csrf'}:raise ValueError()
            secret_binding(private['browser_nonce']);secret_binding(private['csrf'])
            if not hmac.compare_digest(digest(private['csrf']),row['csrf_sha256']):raise ValueError()
            return private
        except Exception:raise SourceDenied('company_identity_required')from None

    def create(self,principal,previous=None):
        if previous:
            try:secret_binding(previous)
            except SourceDenied:previous=None
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32);nonce=secrets.token_urlsafe(32);identity=digest(token)
        with self.auth.transaction()as cur:
            self.auth._authorize(cur,principal)
            previous_owner=cur.execute('SELECT account_id,principal_key FROM enterprise_auth.sessions WHERE session_sha256=%s',(digest(previous),)).fetchone()if previous else None
            owners={principal.key}
            if previous_owner and previous_owner['account_id']==principal.account_id:owners.add(previous_owner['principal_key'])
            # A profile switch touches the prior person's browser row and the new
            # person's quota. Lock both owner domains in one deterministic order.
            for owner in sorted(owners):cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('enterprise-session:'+principal.account_id+':'+owner,))
            if previous_owner and previous_owner['account_id']==principal.account_id:
                row=cur.execute('SELECT account_id,principal_key,nonce_ciphertext,csrf_sha256,revoked_at,expires_at>clock_timestamp()AS current FROM enterprise_auth.sessions WHERE session_sha256=%s FOR UPDATE',(digest(previous),)).fetchone()
                if row and row['account_id']==principal.account_id:
                    if row['principal_key']==principal.key and row['current']and row['revoked_at']is None:
                        try:nonce=self.private(row,digest(previous))['browser_nonce']
                        except SourceDenied:pass # New verified login gets a fresh nonce; never inherit an invalid/old-domain one.
                    cur.execute('UPDATE enterprise_auth.sessions SET revoked_at=clock_timestamp()WHERE session_sha256=%s',(digest(previous),))
            cur.execute("DELETE FROM enterprise_auth.sessions WHERE account_id=%s AND principal_key=%s AND expires_at<clock_timestamp()-interval '1 day'",(principal.account_id,principal.key))
            cur.execute('UPDATE enterprise_auth.sessions SET revoked_at=clock_timestamp()WHERE session_sha256 IN(SELECT session_sha256 FROM enterprise_auth.sessions WHERE account_id=%s AND principal_key=%s AND revoked_at IS NULL ORDER BY created_at DESC OFFSET 9)',(principal.account_id,principal.key))
            encrypted=self.auth.box.seal(self.context(principal.account_id,principal.key,identity),{'browser_nonce':nonce,'csrf':csrf})
            cur.execute('INSERT INTO enterprise_auth.sessions(session_sha256,account_id,principal_key,csrf_sha256,nonce_ciphertext,expires_at)VALUES(%s,%s,%s,%s,%s,to_timestamp(%s))',(identity,principal.account_id,principal.key,digest(csrf),encrypted,principal.expires_at))
            self.auth.event(cur,principal,'company-session','session_started')
        return CreatedSession(token,csrf,max(1,min(3600,int(principal.expires_at-time.time()))))

    def authenticate(self,token):
        try:secret_binding(token)
        except SourceDenied:raise SourceDenied('company_identity_required')from None
        identity=digest(token)
        with self.auth.transaction()as cur:
            row=cur.execute('SELECT s.account_id,s.principal_key,s.csrf_sha256,s.nonce_ciphertext,extract(epoch FROM s.expires_at)::bigint AS expires_at,m.issuer,m.subject FROM enterprise_auth.sessions s JOIN enterprise_auth.memberships m USING(account_id,principal_key)WHERE s.session_sha256=%s AND s.revoked_at IS NULL AND s.expires_at>clock_timestamp()',(identity,)).fetchone()
            if not row:raise SourceDenied('company_identity_required')
            principal=CompanyPrincipal(row['account_id'],row['issuer'],row['subject'],row['expires_at'])
            if principal.key!=row['principal_key']:raise SourceDenied('company_identity_required')
            self.auth._authorize(cur,principal)
            private=self.private(row,identity);nonce=private['browser_nonce'];csrf=private['csrf']
        return BrowserSession(principal,identity,nonce,row['csrf_sha256'],csrf)

    def revoke(self,session):
        with self.auth.transaction()as cur:
            self.auth._authorize(cur,session.principal)
            cur.execute('UPDATE enterprise_auth.sessions SET revoked_at=clock_timestamp()WHERE session_sha256=%s AND account_id=%s AND principal_key=%s',(session.id,session.principal.account_id,session.principal.key))
            self.auth.event(cur,session.principal,'company-session','session_ended')
