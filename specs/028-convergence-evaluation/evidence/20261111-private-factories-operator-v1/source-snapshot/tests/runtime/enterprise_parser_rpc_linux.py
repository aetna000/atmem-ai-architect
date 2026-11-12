"""Actual loopback HTTP admission and extraction inside the isolated Linux image."""
import http.client
import json
from pathlib import Path
import sys
import threading
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src/runtime'))
from enterprise_parser_service import DocumentServer
from enterprise_document_cli import installed_parser
from invoice_parser_identity import SharedParserVerifier

ROOT = Path(__file__).resolve().parents[2]
TOKEN = 'f' * 64  # synthetic fixture, no company/cloud/source authority


class NativeDocumentRpc(unittest.TestCase):
    def setUp(self):
        verify = SharedParserVerifier(TOKEN)
        def authorize(headers):
            if len(headers) != 1 or not headers[0].startswith('Bearer '):
                raise PermissionError()
            verify(headers[0][7:])
        self.server = DocumentServer(('127.0.0.1', 0), installed_parser(), authorize)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.raw = (ROOT / 'benchmarks/convergence/fixtures/enterprise-documents/policy.docx').read_bytes()
        self.mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, *, headers=None, raw=None, duplicate_type=False, duplicate_auth=False):
        raw = self.raw if raw is None else raw
        supplied = {'Authorization': 'Bearer ' + TOKEN, 'Content-Length': str(len(raw)), 'Content-Type': self.mime}
        supplied.update(headers or {})
        client = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=45)
        try:
            client.putrequest('POST', '/extract')
            for name, value in supplied.items():
                if value is not None:
                    client.putheader(name, value)
            if duplicate_type:
                client.putheader('Content-Type', 'text/plain')
            if duplicate_auth:
                client.putheader('Authorization', 'Bearer ' + TOKEN)
            client.endheaders(raw)
            response = client.getresponse()
            return response.status, json.loads(response.read(1201001))
        finally:
            client.close()

    def test_owned_caller_gets_actual_docx(self):
        status, value = self.request()
        self.assertEqual(status, 200)
        self.assertIn('twenty days', value['document']['text'])

    def test_missing_wrong_and_duplicate_credentials_denied(self):
        for token in [None, 'Bearer ' + 'a' * 64, 'Basic invalid']:
            with self.subTest(token=bool(token)):
                self.assertEqual(self.request(headers={'Authorization': token})[0], 403)
        self.assertEqual(self.request(duplicate_auth=True)[0], 403)

    def test_duplicate_type_and_ambiguous_framing_denied(self):
        self.assertEqual(self.request(duplicate_type=True)[0], 415)
        self.assertEqual(self.request(headers={'Transfer-Encoding': 'chunked'})[0], 411)
        self.assertEqual(self.request(headers={'Content-Length': '10000001'}, raw=b'')[0], 413)

    def test_busy_parser_returns_retryable_status(self):
        self.server.slot.acquire()
        try:
            self.assertEqual(self.request()[0], 429)
        finally:
            self.server.slot.release()

    def test_mime_mismatch_never_returns_partial_text(self):
        status, value = self.request(headers={'Content-Type': 'text/plain'})
        self.assertEqual(status, 422)
        self.assertEqual(value, {'status': 'rejected', 'reason': 'mime_mismatch'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
