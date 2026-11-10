"""Native Office->private HTTP parser->retrieval->citation composition.

Only Microsoft HTTP and model responses are scripted. The source/coordinator code,
document bytes, JVM/OCR and local RPC are actual. Loopback RPC is HTTP inside the
network-isolated container; it is not evidence of cloud TLS/ingress permissions.
"""
import http.client
import json
from pathlib import Path
import sys
import threading
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src/runtime'))
from enterprise_document import document_result
from enterprise_document_cli import installed_parser
from enterprise_parser_service import DocumentServer
from enterprise_sources import DelegatedAccess, GraphSharePoint, Reply, SourceDenied, SourceUnavailable
from enterprise_knowledge import EnterpriseKnowledge

ROOT = Path(__file__).resolve().parents[2]
QUOTE = 'Staff receive twenty days of paid leave.'
MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


class NativeDocumentComposition(unittest.TestCase):
    def setUp(self):
        self.server = DocumentServer(('127.0.0.1', 0), installed_parser(), lambda headers: None)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.raw = (ROOT / 'benchmarks/convergence/fixtures/enterprise-documents/policy.docx').read_bytes()
        self.version, self.revoked, self.outage = 'v1', False, False
        self.downloads, self.parses, self.models, self.events = 0, 0, [], []
        self.after_decode = lambda: None
        self.after_model = lambda: None
        owner = self
        class NativeGraphFixture:
            def get(self, url, token, *, hosts, limit=2000000):
                if owner.outage:
                    raise SourceUnavailable('source_request_failed')
                if owner.revoked:
                    raise SourceDenied('source_access_denied')
                if '/me?' in url:
                    value = {'id': 'native-alice'}
                elif '/search(' in url:
                    value = {'value': [{'id': 'item1', 'file': {}, 'parentReference': {'driveId': 'drive1'}}]}
                elif url.endswith('/content'):
                    owner.downloads += 1
                    return Reply(200, {}, owner.raw)
                else:
                    value = {'id': 'item1', 'name': 'Employee policy', 'eTag': owner.version,
                        'file': {'mimeType': MIME}, 'parentReference': {'driveId': 'drive1'},
                        'webUrl': 'https://tenant.sharepoint.com/policy'}
                return Reply(200, {}, json.dumps(value).encode())
        access = DelegatedAccess('alice', 'native-alice', 'SYNTHETIC-DELEGATED', time.time() + 3600)
        self.source = GraphSharePoint('drive1', 'tenant.sharepoint.com', access, http=NativeGraphFixture())
        def generate(payload, schema, instruction):
            context = json.loads(payload)
            self.models.append(context)
            article = context['articles'][0]
            self.assertIn(QUOTE, article['text'])
            self.after_model()
            return json.dumps({'answer': 'The policy provides twenty days of paid leave.', 'abstained': False,
                               'citations': [{'id': article['id'], 'quote': QUOTE}]})
        self.engine = EnterpriseKnowledge([self.source], generate, self.decode,
            audit=self.events.append, authorize=lambda subject: self.assertEqual(subject, 'alice'))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def decode(self, raw, mime):
        self.parses += 1
        client = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=45)
        try:
            client.request('POST', '/extract', body=raw, headers={'Content-Type': mime})
            response = client.getresponse()
            self.assertEqual(response.status, 200)
            value = json.loads(response.read(1201001))
            text = document_result(value['document'], raw, mime)['text']
        finally:
            client.close()
        self.after_decode()
        return text

    def test_real_office_text_reaches_context_and_exact_citation(self):
        value = self.engine.answer('How much paid leave do staff receive?', 'alice')
        self.assertEqual(value['citations'][0]['quote'], QUOTE)
        self.assertEqual(value['citations'][0]['url'], 'https://tenant.sharepoint.com/policy')
        self.assertEqual((self.downloads, self.parses, len(self.models)), (1, 1, 1))
        self.assertNotIn(QUOTE, json.dumps(self.events))
        self.assertNotIn('Employee policy', json.dumps(self.events))

    def test_revocation_while_parsing_denies_model_context(self):
        self.after_decode = lambda: setattr(self, 'revoked', True)
        with self.assertRaises(SourceDenied):
            self.engine.answer('How much paid leave?', 'alice')
        self.assertEqual(self.parses, 1)
        self.assertEqual(self.models, [])

    def test_edit_during_model_withholds_answer_and_citation(self):
        self.after_model = lambda: setattr(self, 'version', 'v2')
        with self.assertRaises(SourceUnavailable):
            self.engine.answer('How much paid leave?', 'alice')
        self.assertEqual(len(self.models), 1)
        self.assertEqual(self.events[-1]['outcome'], 'withheld')

    def test_outage_recovery_performs_fresh_download_and_parse(self):
        self.engine.answer('How much paid leave?', 'alice')
        self.outage = True
        with self.assertRaises(SourceUnavailable):
            self.engine.answer('How much paid leave?', 'alice')
        self.assertEqual(self.downloads, 1)
        self.outage = False
        self.engine.answer('How much paid leave?', 'alice')
        self.assertEqual((self.downloads, self.parses, len(self.models)), (2, 2, 2))


if __name__ == '__main__':
    unittest.main(verbosity=2)
