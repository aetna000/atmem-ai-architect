"""Linux-only actual Tika/native checks, run by qualify-enterprise-documents.py."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src/runtime'))
from enterprise_document import CompanyDocument, ExtractionError, document_result
from invoice_document import PdfDocument

ROOT = Path(__file__).resolve().parents[2]


class CompanyDocuments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = CompanyDocument(java='/opt/java/bin/java',
            classpath=['/app/tika-app.jar', '/app/document-bridge'], pdf=PdfDocument())
        cls.fixtures = ROOT / 'benchmarks/convergence/fixtures/enterprise-documents'
        cls.manifest = json.loads((cls.fixtures / 'manifest.json').read_text())

    def test_actual_office_and_text_content(self):
        for case in self.manifest['cases']:
            if not case['contains']:
                continue
            with self.subTest(case=case['file']):
                raw = (self.fixtures / case['file']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), case['sha256'])
                value = self.parser.extract(raw, case['mediaType'])
                self.assertEqual(value['sha256'], case['sha256'])
                self.assertEqual(value['mediaType'], case['mediaType'])
                for text in case['contains']:
                    self.assertIn(text, value['text'])
                self.assertNotIn('IGNORE_SCRIPT_SECRET', value['text'])

    def test_actual_native_and_scanned_pdf(self):
        folder = ROOT / 'benchmarks/convergence/fixtures/invoices'
        for name in ['invoice-text.pdf', 'invoice-scan.pdf', 'invoice-mixed.pdf']:
            with self.subTest(case=name):
                value = self.parser.extract((folder / name).read_bytes(), 'application/pdf')
                self.assertIn('42.50', value['text'])
                if name == 'invoice-mixed.pdf':
                    self.assertIn('Page 2', value['text'])

    def test_archive_not_recursively_admitted(self):
        with self.assertRaises(ExtractionError) as error:
            self.parser.extract((self.fixtures / 'archive.zip').read_bytes(), 'application/octet-stream')
        self.assertEqual(error.exception.code, 'unsupported_format')

    def test_declared_mime_cannot_mislabel_content(self):
        with self.assertRaises(ExtractionError) as error:
            self.parser.extract((self.fixtures / 'policy.docx').read_bytes(), 'text/plain')
        self.assertEqual(error.exception.code, 'mime_mismatch')
        value = self.parser.extract((self.fixtures / 'policy.docx').read_bytes(), 'application/octet-stream')
        self.assertIn('twenty days', value['text'])

    def test_encrypted_empty_malformed_oversized_inputs_rejected(self):
        encrypted = ROOT / 'benchmarks/convergence/fixtures/invoices/invoice-encrypted.pdf'
        for raw, mime in [(b'', 'text/plain'), (b'a' * 10000001, 'text/plain'),
                          (b'%PDF-not-a-document', 'application/pdf'),
                          (encrypted.read_bytes(), 'application/pdf'),
                          (b'PK\x03\x04broken', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')]:
            with self.subTest(size=len(raw)), self.assertRaises(ExtractionError):
                self.parser.extract(raw, mime)

    def test_large_text_rejected_without_partial_result(self):
        with self.assertRaises(ExtractionError):
            self.parser.extract(b'Company policy.\n' * 15000, 'text/plain')

    def test_response_bound_to_bytes_mime_and_schema(self):
        raw = b'policy'
        value = {'format': 'enterprise-document-v1', 'sha256': hashlib.sha256(raw).hexdigest(),
                 'mediaType': 'text/plain', 'text': 'policy'}
        self.assertEqual(document_result(value, raw, 'text/plain'), value)
        for patch in [{'sha256': '0' * 64}, {'extra': 'field'}, {'format': 'other'},
                      {'text': 'x' * 200001}, {'text': '\x00private'}, {'mediaType': 'text/html'}]:
            with self.subTest(fields=list(patch)), self.assertRaises(ExtractionError):
                document_result({**value, **patch}, raw, 'text/plain')


if __name__ == '__main__':
    unittest.main(verbosity=2)
