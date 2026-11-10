"""Application-side fixed private HTTPS document parser adapter."""
import json
import time
from urllib.parse import urlsplit
import requests
from enterprise_document_contract import MAX_INPUT, document_result, media_type
from enterprise_sources import SourceUnavailable


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate response field')
        result[key] = value
    return result


class DocumentClient:
    def __init__(self, endpoint, authorization, *, session=None):
        try:
            target = urlsplit(endpoint)
            if (not isinstance(endpoint, str) or len(endpoint) > 2000 or target.scheme != 'https'
                or not target.hostname or target.path != '/extract' or target.query or target.fragment
                or target.username or target.password or (target.port is not None and not 1 <= target.port <= 65535)
                or any(ord(c) < 33 or ord(c) > 126 for c in endpoint)):
                raise ValueError()
        except (TypeError, ValueError):
            raise ValueError('Supply the fixed private HTTPS /extract endpoint') from None
        if authorization is not None and not callable(authorization):
            raise ValueError('Supply an owned workload admission adapter')
        self.endpoint, self.authorization = endpoint, authorization
        # No shared session mutation during parallel source extraction.
        self.session = session

    def __call__(self, raw, declared):
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_INPUT:
            raise SourceUnavailable('source_document_unsupported')
        session = self.session or requests.Session()
        session.trust_env = False
        try:
            headers = {'Content-Type': media_type(declared)}
            if self.authorization is not None:
                token = self.authorization()
                if not isinstance(token, str) or not token.startswith('Bearer ') or not 8 <= len(token) <= 20000 or any(ord(c) < 33 or ord(c) > 126 for c in token[7:]):
                    raise ValueError('Invalid caller admission')
                headers['Authorization'] = token
            deadline = time.monotonic() + 125
            with session.post(self.endpoint, data=raw, headers=headers, timeout=(2, 115), allow_redirects=False, stream=True) as response:
                if response.status_code != 200:
                    raise SourceUnavailable('document_extraction_unavailable')
                content = bytearray()
                for chunk in response.iter_content(1):
                    content.extend(chunk)
                    if len(content) > 1201000 or time.monotonic() > deadline:
                        raise ValueError('Unconfirmed extraction boundary')
            value = json.loads(content, object_pairs_hook=unique_object,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite output')))
            if not isinstance(value, dict) or set(value) != {'status', 'document'} or value['status'] != 'ok':
                raise ValueError('Unconfirmed extraction result')
            return document_result(value['document'], raw, declared)['text']
        except SourceUnavailable:
            raise
        except Exception:
            raise SourceUnavailable('document_extraction_unavailable') from None
        finally:
            if self.session is None:
                session.close()
