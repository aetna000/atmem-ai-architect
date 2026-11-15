"""X-only identity and server-side whitelist, checked on every application action."""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import re
import uuid
from .auth import FirebaseIdentity, Unauthorized, Forbidden, AuthenticationUnavailable
from .credits import CreditError, Conflict, digest, identifier


def x_id(value):
    if type(value) is not str or not re.fullmatch(r'[1-9][0-9]{0,19}',value):
        raise CreditError('Use the immutable numeric X account ID')
    return value


@dataclass(frozen=True)
class XIdentity:
    firebase_uid: str
    x_id: str
    display_name: str
    admin: bool = False

    @property
    def uid(self): return self.x_id

    def require_admin(self):
        if not self.admin:raise Forbidden('Administrator access required')
        return self

    @classmethod
    def from_verified_claims(cls, claims):
        try:
            firebase = claims['firebase']
            ids = firebase['identities']['twitter.com']
            if firebase['sign_in_provider'] != 'twitter.com' or type(ids) is not list or len(ids) != 1:
                raise Unauthorized('Sign in with X')
            uid = identifier(claims.get('uid') or claims.get('sub'))
            subject = x_id(ids[0])
            name = claims.get('name')
            if type(name) is not str or not name.strip():name='X account'
            name = ''.join(c for c in name if ord(c)>=32)[:120]
            # Names, handles, email and client roles never establish identity or access.
            return cls(uid,subject,name)
        except (KeyError,TypeError,ValueError) as error:
            raise Unauthorized('Sign in with X') from error


class FirebaseXIdentity(FirebaseIdentity):
    def verify(self, authorization):
        if type(authorization) is not str or not authorization.startswith('Bearer ') or not 20 <= len(authorization) <= 8192:
            raise Unauthorized('Sign in with X')
        from firebase_admin import auth
        try:
            claims=auth.verify_id_token(authorization[7:],app=self.app,check_revoked=True,clock_skew_seconds=0)
            return XIdentity.from_verified_claims(claims)
        except auth.CertificateFetchError as error:raise AuthenticationUnavailable('Identity verification is temporarily unavailable') from error
        except (ValueError,auth.InvalidIdTokenError,auth.UserDisabledError) as error:raise Unauthorized('Sign in again with X') from error


class XWhitelist:
    def __init__(self, store, *, admin_ids, initial_ids=()):
        self.store=store
        self.admin_ids=frozenset(x_id(value) for value in admin_ids)
        self.initial_ids=frozenset(x_id(value) for value in initial_ids)
        if not self.admin_ids:raise ValueError('Configure at least one explicit administrator X ID')
        if len(self.admin_ids|self.initial_ids)>500:raise ValueError('Pilot whitelist is limited to 500 accounts')

    def _entry(self, tx, subject):
        record=tx.get('x_access',digest(subject))
        if subject in self.admin_ids:return dict(xId=subject,allowed=True,role='admin',revision=record['revision'] if record else 0,bootstrap=True)
        return record or dict(xId=subject,allowed=subject in self.initial_ids,role='user',revision=0,bootstrap=False)

    def authorize(self, identity):
        record=self.store.transaction(lambda tx:self._entry(tx,identity.x_id))
        if not record['allowed']:raise Forbidden('This X account is not whitelisted. Contact the administrator')
        return replace(identity,admin=record['role']=='admin')

    def update(self, actor, subject, *, allowed, role, revision):
        subject=x_id(subject)
        if type(allowed) is not bool or role not in {'user','admin'} or type(revision) is not int or revision<0:
            raise CreditError('Use the current whitelist revision and a supported role')
        audit=uuid.uuid4().hex
        def apply(tx):
            current_actor=self._entry(tx,actor.x_id)
            if not current_actor['allowed'] or current_actor['role']!='admin':raise Forbidden('Administrator access required')
            previous=self._entry(tx,subject)
            index=tx.get('x_access_index','members') or {'ids':[]}
            if previous['revision']!=revision:raise Conflict('Whitelist changed. Reload before saving')
            if subject in self.admin_ids and (not allowed or role!='admin'):raise Conflict('Bootstrap administrators are configured by the operator')
            ids=sorted(set(index['ids'])|{subject})
            if len(set(ids)|self.admin_ids|self.initial_ids)>500:raise CreditError('Pilot whitelist is full')
            record=dict(xId=subject,allowed=allowed,role=role,revision=revision+1,bootstrap=subject in self.admin_ids)
            tx.set('x_access',digest(subject),record);tx.set('x_access_index','members',{'ids':ids})
            tx.create('audit',audit,dict(kind='x_whitelist_updated',actor=actor.x_id,subject=subject,
                       previous=previous,updated=record,createdAt=datetime.now(timezone.utc).isoformat()))
            return record
        return self.store.transaction(apply)

    def list(self, actor):
        def apply(tx):
            own=self._entry(tx,actor.x_id)
            if not own['allowed'] or own['role']!='admin':raise Forbidden('Administrator access required')
            index=tx.get('x_access_index','members') or {'ids':[]}
            return [self._entry(tx,key) for key in sorted(set(index['ids'])|self.admin_ids|self.initial_ids)]
        return self.store.transaction(apply)
