"""Mounted per-file protocol: bounded input, exact binding, no log disclosure."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src/runtime'))
from enterprise_document_contract import ExtractionError
from enterprise_document_job import execute, request, result, MAX_ENVELOPE


class Parser:
    def __init__(self): self.calls = []
    def extract(self, raw, mime):
        self.calls.append((raw, mime))
        return {'format': 'enterprise-document-v1', 'sha256': hashlib.sha256(raw).hexdigest(), 'mediaType': mime, 'text': raw.decode()}


class MountedDocumentJob(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'input'; self.source.mkdir()
        self.target = self.root / 'output'; self.target.mkdir()
        self.raw = b'PRIVATE fixture document text'
        self.identifier = 'a' * 64
        self.metadata = request(self.raw, 'text/plain', self.identifier)
        (self.source / 'document').write_bytes(self.raw)
        (self.source / 'request.json').write_text(json.dumps(self.metadata))
        self.parser = Parser()

    def run_job(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            value = execute(self.parser, self.source, self.target)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), '')
        self.assertNotIn('PRIVATE', json.dumps(value))
        return value

    def rejected(self):
        self.assertEqual(self.run_job()[1], 2)
        self.assertFalse((self.target / 'result.json').exists())

    def test_result_is_bound_to_one_request_and_private_text_is_only_in_result_file(self):
        self.assertEqual(self.run_job(), ({'status': 'ok'}, 0))
        encoded = (self.target / 'result.json').read_bytes()
        document = result(self.raw, 'text/plain', self.identifier, encoded)
        self.assertEqual(document['text'], self.raw.decode())
        self.assertEqual((self.target / 'result.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.target.iterdir()), [self.target / 'result.json'])
        for raw, mime, identifier in [(b'other', 'text/plain', self.identifier), (self.raw, 'text/html', self.identifier), (self.raw, 'text/plain', 'b' * 64)]:
            with self.assertRaises(ExtractionError): result(raw, mime, identifier, encoded)

    def test_duplicate_metadata_is_rejected_without_parse(self):
        (self.source / 'request.json').write_text(json.dumps(self.metadata)[:-1] + ',"requestId":"' + self.identifier + '"}')
        self.rejected(); self.assertEqual(self.parser.calls, [])

    def test_input_hash_or_request_shape_cannot_be_changed(self):
        for patch in [{'sha256': '0' * 64}, {'requestId': '../private'}, {'mediaType': 'text/plain; charset=utf-8'}, {'url': 'https://private.invalid'}]:
            (self.source / 'request.json').write_text(json.dumps({**self.metadata, **patch}))
            self.rejected()
        self.assertEqual(self.parser.calls, [])

    def test_symlink_and_fifo_inputs_are_not_followed_or_blocked(self):
        document = self.source / 'document'
        outside = self.root / 'private'; outside.write_bytes(self.raw)
        document.unlink(); document.symlink_to(outside)
        self.rejected()
        document.unlink(); os.mkfifo(document)
        self.rejected()
        self.assertEqual(self.parser.calls, [])

    def test_symlink_mounts_and_reused_directory_are_rejected(self):
        alias = self.root / 'alias'; alias.symlink_to(self.source)
        self.assertEqual(execute(self.parser, alias, self.target)[1], 2)
        self.assertEqual(execute(self.parser, self.source, self.source)[1], 2)
        self.assertEqual(self.parser.calls, [])

    def test_stale_result_or_symlink_never_overwrites_or_parses(self):
        destination = self.target / 'result.json'
        destination.write_bytes(b'old result')
        self.assertEqual(self.run_job()[1], 2)
        self.assertEqual(destination.read_bytes(), b'old result')
        destination.unlink()
        outside = self.root / 'private'; outside.write_bytes(b'preserved')
        destination.symlink_to(outside)
        self.assertEqual(self.run_job()[1], 2)
        self.assertEqual(outside.read_bytes(), b'preserved')
        self.assertEqual(self.parser.calls, [])

    def test_empty_oversized_and_nonregular_input_are_rejected_before_parse(self):
        document = self.source / 'document'
        for raw in [b'', b'x' * 10000001]:
            document.write_bytes(raw); self.rejected()
        document.unlink(); document.mkdir(); self.rejected()
        self.assertEqual(self.parser.calls, [])

    def test_oversized_metadata_is_rejected_before_parse(self):
        (self.source / 'request.json').write_bytes(b' ' * 2049)
        self.rejected(); self.assertEqual(self.parser.calls, [])

    def test_parser_failure_does_not_publish_partial_or_log_private_failure(self):
        def fail(raw, mime): raise RuntimeError(raw.decode())
        self.parser.extract = fail
        self.rejected()
        self.assertEqual(list(self.target.iterdir()), [])

    def test_parser_forgery_and_partial_output_are_rejected(self):
        self.parser.extract = lambda raw, mime: {'format': 'enterprise-document-v1', 'sha256': '0' * 64, 'mediaType': mime, 'text': 'forged'}
        self.rejected()
        for encoded in [b'', b'{}', b'NaN', b' ' * (MAX_ENVELOPE + 1), b'{"format":"x","format":"y"}']:
            with self.assertRaises(ExtractionError): result(self.raw, 'text/plain', self.identifier, encoded)


if __name__ == '__main__': unittest.main(verbosity=2)
