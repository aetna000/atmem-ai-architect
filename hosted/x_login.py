"""Short-lived X OAuth2 identity exchange. No content API or persistent X tokens."""
import base64
import hashlib
import hmac
import re
import secrets
import time
from urllib.parse import urlencode
import httpx
from .auth import Unauthorized, AuthenticationUnavailable
from .x_access import XIdentity, x_id

# X's documented /2/users/me minimum; never request offline, social graph or write access.
SCOPES = ('users.read', 'tweet.read')
CALLBACK = 'https://atmem.ai/architect/auth/x'
ORIGIN = 'https://atmem.ai'
MARKER = 'oauth2-v1'


def challenge(verifier):
    if not isinstance(verifier, str) or not re.fullmatch(r'[A-Za-z0-9_~.\-]{43,128}', verifier):
        raise Unauthorized('Start X sign-in again')
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')


class FirebaseXTokenIssuer:
    def __init__(self, project, signer):
        import firebase_admin
        name = 'architect-x-oauth2-' + project
        try: self.app = firebase_admin.get_app(name)
        except ValueError:
            self.app = firebase_admin.initialize_app(options={'projectId': project, 'serviceAccountId': signer}, name=name)

    def issue(self, subject, name):
        from firebase_admin import auth
        # Reuse existing Firebase identities. Application data remains keyed by immutable X ID.
        matches = auth.get_users([auth.ProviderIdentifier('twitter.com', subject)], app=self.app)
        if len(matches.users) > 1: raise Unauthorized('X identity could not be verified')
        user = matches.users[0] if matches.users else None
        if not user:
            uid = 'architect-x-' + subject
            try: user = auth.get_user(uid, app=self.app)
            except auth.UserNotFoundError: user = None
            if user and user.provider_data:
                raise Unauthorized('X identity could not be verified')
        if user and user.disabled: raise Unauthorized('This account is disabled')
        uid = user.uid if user else 'architect-x-' + subject
        return auth.create_custom_token(uid, {'architect_x_login': MARKER, 'architect_x_id': subject,
                                             'name': name}, app=self.app).decode()


class XLogin:
    """Bounded durable one-use PKCE state; secrets and upstream tokens stay server-side."""
    def __init__(self, store, access, credentials, issuer, *, client=None, clock=time.time):
        self.store, self.access, self.issuer, self.clock = store, access, issuer, clock
        self.client_id, self.client_secret = credentials['clientId'], credentials['clientSecret']
        if not all(isinstance(v, str) and v for v in (self.client_id, self.client_secret)):
            raise ValueError('Configure X OAuth2 credentials')
        self.client = client or httpx.Client(timeout=10, follow_redirects=False)

    def start(self, code_challenge):
        if not isinstance(code_challenge, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', code_challenge):
            raise Unauthorized('Start X sign-in again')
        # Fixed pool bounds abandoned login records without retaining browser identifiers.
        slots = secrets.SystemRandom().sample(range(256), 8)
        nonce, now = secrets.token_urlsafe(32), self.clock()
        def reserve(tx):
            records = [(str(slot), tx.get('x_login', str(slot))) for slot in slots]
            for slot, record in records:
                if not record or record['expires'] <= now:
                    state = slot + '.' + nonce
                    tx.set('x_login', slot, {'stateHash': hashlib.sha256(state.encode()).hexdigest(),
                                            'challenge': code_challenge, 'expires': now + 300})
                    return state
            raise AuthenticationUnavailable('X sign-in is busy. Try again shortly')
        state = self.store.transaction(reserve)
        return {'state': state, 'authorizationUrl': 'https://x.com/i/oauth2/authorize?' + urlencode({
            'response_type': 'code', 'client_id': self.client_id, 'redirect_uri': CALLBACK,
            'scope': ' '.join(SCOPES), 'state': state,
            'code_challenge': code_challenge, 'code_challenge_method': 'S256'})}

    def finish(self, state, code, verifier):
        if not isinstance(state, str) or not re.fullmatch(r'(?:0|[1-9][0-9]{0,2})\.[A-Za-z0-9_-]{43}', state):
            raise Unauthorized('Start X sign-in again')
        if int(state.split('.')[0]) > 255 or not isinstance(code, str) or not 1 <= len(code) <= 2048:
            raise Unauthorized('Start X sign-in again')
        expected, now = challenge(verifier), self.clock()
        def consume(tx):
            slot = state.split('.')[0]
            record = tx.get('x_login', slot)
            if not record or record['expires'] <= now or not hmac.compare_digest(record['stateHash'], hashlib.sha256(state.encode()).hexdigest()) or not hmac.compare_digest(record['challenge'], expected):
                raise Unauthorized('Start X sign-in again')
            tx.delete('x_login', slot)
        self.store.transaction(consume)
        token = None
        verified = False
        try:
            response = self.client.post('https://api.x.com/2/oauth2/token',
                auth=(self.client_id, self.client_secret), data={'grant_type': 'authorization_code',
                'code': code, 'redirect_uri': CALLBACK, 'code_verifier': verifier})
            if response.status_code != 200: raise Unauthorized('X sign-in did not finish. Try again')
            grant = response.json()
            token = grant.get('access_token')
            if not isinstance(token, str) or not 1 <= len(token) <= 8192:
                raise AuthenticationUnavailable('X sign-in is temporarily unavailable')
            token_type, scopes = grant.get('token_type'), grant.get('scope')
            if not isinstance(token_type, str) or token_type.lower() != 'bearer' or not isinstance(scopes, str) or set(scopes.split()) != set(SCOPES) or grant.get('refresh_token'):
                raise AuthenticationUnavailable('X returned unexpected permissions. Sign-in stopped')
            # Only /me, with default id/name/username fields. No timeline, lists or settings requests.
            response = self.client.get('https://api.x.com/2/users/me', headers={'Authorization': 'Bearer ' + token})
            if response.status_code == 402:
                raise AuthenticationUnavailable('X sign-in needs operator API access configuration')
            if response.status_code != 200:
                raise AuthenticationUnavailable('X identity verification is temporarily unavailable')
            data = response.json()['data']
            subject = x_id(data['id'])
            name = data.get('name')
            name = ''.join(c for c in name if ord(c) >= 32)[:120] if isinstance(name, str) else 'X account'
            self.access.authorize(XIdentity('oauth2-pending', subject, name or 'X account'))
            verified = True
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            if isinstance(error, (Unauthorized, AuthenticationUnavailable)):
                raise
            # Never surface upstream responses, authorization codes, keys or tokens.
            from .auth import Forbidden
            if isinstance(error, Forbidden): raise
            raise AuthenticationUnavailable('X sign-in is temporarily unavailable') from None
        finally:
            if token:
                try:
                    revoked = self.client.post('https://api.x.com/2/oauth2/revoke',
                        auth=(self.client_id, self.client_secret), data={'token': token, 'token_type_hint': 'access_token'})
                    if revoked.status_code != 200: raise httpx.RequestError('Revocation failed')
                except httpx.HTTPError:
                    if verified:
                        raise AuthenticationUnavailable('X permission cleanup failed. Try sign-in again') from None
        return {'firebaseToken': self.issuer.issue(subject, name or 'X account')}
