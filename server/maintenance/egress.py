"""Optional model boundary. The first deterministic recipe never sends source to a model."""
from datetime import datetime, timezone
from typing import Protocol

from .inventory import SECRET, SENSITIVE_PATH, safe_path, sha
from .store import digest


class ModelAdapter(Protocol):
    def propose(self, payload: dict, *, max_cost_micros: int, timeout_seconds: int) -> dict: ...


def selection(files, *, backend, model, vendor_terms, credential_owner):
    if any(not isinstance(v, str) or not v or len(v) > 2000 for v in [backend, model, vendor_terms, credential_owner]):
        raise ValueError('Disclose backend, model, terms and credential owner')
    for path, text in files.items():
        safe_path(path)
        if SENSITIVE_PATH.search(path) or SECRET.search(text):
            raise ValueError('Sensitive model source denied')
    value = {'backend': backend, 'model': model, 'vendorTerms': vendor_terms,
             'credentialOwner': credential_owner,
             'files': {path: {'sha256': sha(text), 'dataClass': 'terraform_source'} for path, text in sorted(files.items())}}
    return {**value, 'digest': digest(value)}


def request_payload(files, approved, *, findings='', previous_output='', confirmation, now=None):
    now = datetime.now(timezone.utc).timestamp() if now is None else now
    if (set(confirmation) != {'selectionDigest', 'actor', 'expiresAt', 'revoked'} or confirmation['revoked'] is not False
        or not confirmation['actor'] or confirmation['expiresAt'] <= now
        or confirmation['selectionDigest'] != approved['digest']):
        raise ValueError('Fresh source-selection confirmation required')
    current = selection(files, backend=approved['backend'], model=approved['model'],
                        vendor_terms=approved['vendorTerms'], credential_owner=approved['credentialOwner'])
    if current != approved:
        raise ValueError('Source or processing terms changed; reconfirm egress')
    if SECRET.search(findings) or SECRET.search(previous_output):
        raise ValueError('Sensitive derived model context denied')
    payload = {'files': files, 'findings': findings, 'previousOutput': previous_output}
    if len(str(payload).encode()) > 8_000_000:
        raise ValueError('Model payload too large; no content was truncated')
    return payload, {'selectionDigest': approved['digest'], 'payloadDigest': digest(payload),
                     'filter': 'sensitive-path-and-pattern-v1', 'status': 'filtered',
                     'limit': 'Pattern checks cannot prove arbitrary source secret-free.'}
