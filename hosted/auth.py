"""Firebase identity verification; no loopback bootstrap token in hosted mode."""
from dataclasses import dataclass
import hashlib
import os
from .credits import identifier

ADMIN_EMAIL = 'taghia.javad@gmail.com'


class Unauthorized(ValueError): pass
class Forbidden(ValueError): pass
class AuthenticationUnavailable(RuntimeError): pass


@dataclass(frozen=True)
class Identity:
    uid: str
    email: str
    provider: str
    verified: bool

    @classmethod
    def from_verified_claims(cls, claims):
        # Called only after Firebase Admin verifies signature, issuer/audience,
        # expiry, revocation and disabled-user status for the configured project.
        if type(claims) is not dict or type(claims.get('firebase')) is not dict:
            raise Unauthorized('Use a verified Google account')
        try: uid = identifier(claims.get('uid') or claims.get('sub'))
        except ValueError as error: raise Unauthorized('Use a verified Google account') from error
        email = claims.get('email')
        provider = claims.get('firebase', {}).get('sign_in_provider')
        if type(email) is not str or len(email) > 320 or claims.get('email_verified') is not True or provider != 'google.com':
            raise Unauthorized('Use a verified Google account')
        return cls(uid, email.lower(), provider, True)

    @property
    def admin(self):
        return self.verified is True and self.provider == 'google.com' and self.email == ADMIN_EMAIL

    def require_admin(self):
        if not self.admin:
            raise Forbidden('Administrator access required')
        return self


class FirebaseIdentity:
    def __init__(self, project):
        if not project or os.environ.get('FIREBASE_AUTH_EMULATOR_HOST'):
            raise ValueError('An explicit production Firebase project is required; auth emulator bypass is refused')
        import firebase_admin
        name = 'architect-' + hashlib.sha256(project.encode()).hexdigest()[:20]
        try: self.app = firebase_admin.get_app(name)
        except ValueError: self.app = firebase_admin.initialize_app(options={'projectId': project}, name=name)

    def verify(self, authorization):
        if type(authorization) is not str or not authorization.startswith('Bearer ') or not 20 <= len(authorization) <= 8192:
            raise Unauthorized('Sign in with Google')
        from firebase_admin import auth
        try:
            claims = auth.verify_id_token(authorization[7:], app=self.app, check_revoked=True, clock_skew_seconds=0)
            return Identity.from_verified_claims(claims)
        except auth.CertificateFetchError as error:
            raise AuthenticationUnavailable('Identity verification is temporarily unavailable') from error
        except (ValueError, auth.InvalidIdTokenError, auth.UserDisabledError) as error:
            raise Unauthorized('Sign in again with Google') from error
