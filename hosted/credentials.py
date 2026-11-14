"""Tenant-bound encrypted BYOK storage; plaintext is returned only to the broker.

Encryption keys must come from separately mounted secrets. Workers and browsers
must never receive the keyring or direct database access. Storage is not provider
verification; a configured key may still be expired or lack model permissions.
"""
import base64
import json
import os
import uuid
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from .credits import CreditError, Conflict, digest, identifier

PROVIDERS = frozenset({'openai', 'anthropic'})


class CredentialsUnavailable(RuntimeError): pass


class CredentialVault:
    def __init__(self, store, ledger, *, keyring, active_key):
        if (not keyring or active_key not in keyring or
                any(type(k) is not str or not k.isalnum() or len(k) > 40 or type(v) is not bytes or len(v) != 32
                    for k,v in keyring.items())):
            raise ValueError('Supply an explicit versioned 256-bit encryption keyring')
        self.store, self.ledger, self.keyring, self.active_key = store, ledger, keyring.copy(), active_key

    @classmethod
    def configured(cls, store, ledger):
        # The environment contains mounted Secret Manager content, never public
        # Firebase config. No generated key or plaintext fallback on restart.
        try:
            value = json.loads(os.environ['ARCHITECT_BYOK_KEYRING'])
            keys = {k:base64.b64decode(v, validate=True) for k,v in value['keys'].items()}
            return cls(store, ledger, keyring=keys, active_key=value['activeKey'])
        except (KeyError, ValueError, TypeError, AttributeError) as error:
            raise CredentialsUnavailable('BYOK encryption is not configured') from error

    @staticmethod
    def _path(uid, provider):
        identifier(uid)
        if provider not in PROVIDERS: raise CreditError('Choose OpenAI or Anthropic')
        return digest(uid) + '-' + provider

    @staticmethod
    def _aad(uid, provider): return json.dumps(['architect-byok-v1', uid, provider], separators=(',', ':')).encode()

    @staticmethod
    def _public(record):
        return {'configured':bool(record and record.get('active')), 'revision':record['revision'] if record else 0,
                'verified':False}

    def status(self, uid, provider):
        key = self._path(uid, provider)
        def apply(tx):
            self.ledger._account(tx, uid)
            return self._public(tx.get('credentials', key))
        return self.store.transaction(apply)

    def update(self, uid, provider, api_key, expected_revision):
        key = self._path(uid, provider)
        if (type(api_key) is not str or not 20 <= len(api_key) <= 512 or
                any(not c.isascii() or c.isspace() or ord(c) < 33 or ord(c) > 126 for c in api_key)):
            raise CreditError('Enter a valid provider API key')
        if type(expected_revision) is not int or expected_revision < 0: raise CreditError('Use the current key revision')
        nonce = os.urandom(12)
        cipher = AESGCM(self.keyring[self.active_key]).encrypt(nonce, api_key.encode(), self._aad(uid, provider))
        now = datetime.now(timezone.utc).isoformat(); audit_id = uuid.uuid4().hex
        def apply(tx):
            _, account = self.ledger._account(tx, uid)
            previous = tx.get('credentials', key)
            if account['disabled']: raise CreditError('Account is unavailable')
            if (previous['revision'] if previous else 0) != expected_revision: raise Conflict('Provider key changed. Reload before saving')
            record = dict(uid=uid, provider=provider, active=True, revision=expected_revision+1,
                          keyId=self.active_key, nonce=base64.b64encode(nonce).decode(),
                          ciphertext=base64.b64encode(cipher).decode(), updatedAt=now)
            tx.set('credentials', key, record)
            tx.create('audit', audit_id, dict(uid=uid, provider=provider, kind='byok_updated', createdAt=now))
            return self._public(record)
        return self.store.transaction(apply)

    def remove(self, uid, provider, expected_revision):
        key = self._path(uid, provider)
        if type(expected_revision) is not int or expected_revision < 0: raise CreditError('Use the current key revision')
        now = datetime.now(timezone.utc).isoformat(); audit_id = uuid.uuid4().hex
        def apply(tx):
            self.ledger._account(tx, uid)
            previous = tx.get('credentials', key)
            if (previous['revision'] if previous else 0) != expected_revision: raise Conflict('Provider key changed. Reload before removing')
            record = dict(uid=uid, provider=provider, active=False, revision=expected_revision+1, updatedAt=now)
            tx.set('credentials', key, record)
            tx.create('audit', audit_id, dict(uid=uid, provider=provider, kind='byok_removed', createdAt=now))
            return self._public(record)
        return self.store.transaction(apply)

    def for_broker(self, uid, provider):
        """Never expose this return value via any HTTP handler or worker artifact."""
        key = self._path(uid, provider)
        def apply(tx):
            _, account = self.ledger._account(tx, uid)
            record = tx.get('credentials', key)
            if account['disabled'] or not record or not record.get('active'):
                raise CredentialsUnavailable('Configure a provider key before using it')
            return record
        record = self.store.transaction(apply)
        try:
            if record['uid'] != uid or record['provider'] != provider: raise InvalidTag
            cipher = base64.b64decode(record['ciphertext'], validate=True)
            nonce = base64.b64decode(record['nonce'], validate=True)
            return AESGCM(self.keyring[record['keyId']]).decrypt(nonce, cipher, self._aad(uid, provider)).decode()
        except (KeyError, ValueError, InvalidTag) as error:
            raise CredentialsUnavailable('Provider key cannot be decrypted with the configured keyring') from error
