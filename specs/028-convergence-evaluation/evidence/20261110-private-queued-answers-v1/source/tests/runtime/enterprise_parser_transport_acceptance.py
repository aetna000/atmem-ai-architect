"""Application/RPC contract fault tests; HTTP responses are explicit fixtures."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / '.local/azure-runtime-sdk')]
from enterprise_parser_transport import DocumentClient
from enterprise_sources import SourceUnavailable


class Response:
    def __init__(self, body, status=200):
        self.body, self.status_code, self.closed = body, status, False
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.closed = True
    def iter_content(self, size):
        for offset in range(0, len(self.body), 8192):
            yield self.body[offset:offset + 8192]


class Session:
    def __init__(self, response):
        self.response, self.calls, self.trust_env = response, [], True
    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class DocumentTransport(unittest.TestCase):
    def response(self, **patch):
        return json.dumps({'status': 'ok', 'document': {'format': 'enterprise-document-v1',
            'sha256': hashlib.sha256(b'policy').hexdigest(), 'mediaType': 'text/plain', 'text': 'policy', **patch}}).encode()

    def test_fixed_endpoint_byte_body_owned_auth_and_redirect_boundary(self):
        session = Session(Response(self.response()))
        client = DocumentClient('https://parser.internal/extract', lambda: 'Bearer SYNTHETIC', session=session)
        self.assertEqual(client(b'policy', 'text/plain; charset=utf-8'), 'policy')
        url, call = session.calls[0]
        self.assertEqual(url, 'https://parser.internal/extract')
        self.assertEqual(call['data'], b'policy')
        self.assertEqual(call['headers'], {'Authorization': 'Bearer SYNTHETIC', 'Content-Type': 'text/plain'})
        self.assertFalse(call['allow_redirects'])
        self.assertFalse(session.trust_env)
        self.assertTrue(session.response.closed)

    def test_unowned_endpoint_shapes_rejected_before_request(self):
        for url in ['http://parser.internal/extract', 'https://user:pass@parser.internal/extract',
                    'https://parser.internal/extract?url=private', 'https://parser.internal/other',
                    'https://parser.internal:0/extract', 'https://parser.internal/extract#fragment']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                DocumentClient(url, None)

    def test_non_success_never_uses_partial_document_or_error_body(self):
        for status in [301, 302, 403, 408, 422, 429, 500, 503]:
            session = Session(Response(b'PRIVATE-UPSTREAM-TOKEN', status))
            client = DocumentClient('https://parser.internal/extract', None, session=session)
            with self.subTest(status=status), self.assertRaises(SourceUnavailable) as error:
                client(b'policy', 'text/plain')
            self.assertNotIn('PRIVATE', str(error.exception))
            self.assertTrue(session.response.closed)

    def test_digest_mime_format_limits_and_duplicate_json_enforced(self):
        for body in [self.response(sha256='0' * 64), self.response(mediaType='text/html'),
                     self.response(format='other'), self.response(text='x' * 200001),
                     self.response(text='\x00secret'), b'{"status":"ok","status":"ok","document":{}}',
                     b'NaN', b' ' * 1201001]:
            client = DocumentClient('https://parser.internal/extract', None, session=Session(Response(body)))
            with self.subTest(size=len(body)), self.assertRaises(SourceUnavailable):
                client(b'policy', 'text/plain')

    def test_bad_admission_and_request_input_do_not_reach_network(self):
        session = Session(Response(self.response()))
        for authorization in [lambda: 'Bearer bad\r\nInjected: value', lambda: 'Basic nope']:
            client = DocumentClient('https://parser.internal/extract', authorization, session=session)
            with self.assertRaises(SourceUnavailable):
                client(b'policy', 'text/plain')
        client = DocumentClient('https://parser.internal/extract', None, session=session)
        for raw, mime in [(b'', 'text/plain'), (b'policy', 'text/plain\r\nInjected: value'), (b'a' * 10000001, 'text/plain')]:
            with self.assertRaises(SourceUnavailable):
                client(raw, mime)
        self.assertEqual(session.calls, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
