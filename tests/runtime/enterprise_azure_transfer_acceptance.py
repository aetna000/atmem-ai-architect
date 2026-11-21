"""Actual filesystem/byte-contract checks with explicit temporary-blob fixtures."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / '.local/azure-runtime-sdk'), str(ROOT / 'tests/runtime')]
from enterprise_azure_jobs_acceptance import config
from enterprise_azure_jobs import transfer_metadata
from enterprise_azure_transfer import metadata, download, upload, main
from enterprise_document_job import request


class Objects:
    def __init__(self, raw): self.raw, self.calls = raw, []
    def load(self, *args): self.calls.append(('load', args)); return self.raw
    def put(self, *args): self.calls.append(('put', args))


class AzureTransferContract(unittest.TestCase):
    def setUp(self):
        self.raw = b'private document'
        self.identifier = 'd' * 64
        self.value = transfer_metadata(config(), request(self.raw, 'text/plain', self.identifier), '"0x8DA123ABCDEF"')
        self.temporary = tempfile.TemporaryDirectory()
        self.source = Path(self.temporary.name) / 'input'
        self.target = Path(self.temporary.name) / 'output'
        self.source.mkdir(); self.target.mkdir()
        self.objects = Objects(self.raw)

    def tearDown(self):
        self.source.chmod(0o700)
        self.target.chmod(0o700)
        self.temporary.cleanup()

    def stage(self):
        download(self.value, self.objects, str(self.source), str(self.target))

    def encoded_result(self):
        return json.dumps({'format': 'enterprise-document-job-v1', 'requestId': self.identifier,
            'status': 'ok', 'document': {'format': 'enterprise-document-v1',
                'sha256': hashlib.sha256(self.raw).hexdigest(), 'mediaType': 'text/plain', 'text': 'private answer'}}).encode()

    def test_bounded_metadata_selects_only_transfer_identity(self):
        self.assertEqual(metadata(json.dumps(self.value)), self.value)
        for changed in [{**self.value, 'workerClientId': config()['workerClientId']},
                        {**self.value, 'storageAccount': 'owned.attacker.example'},
                        {**self.value, 'inputETag': '*'},
                        {**self.value, 'transferClientId': 'default'},
                        {**self.value, 'request': {**self.value['request'], 'mediaType': 'text/x-python'}}]:
            with self.assertRaises(ValueError): metadata(json.dumps(changed))
        with self.assertRaises(ValueError): metadata(json.dumps(self.value)[:-1] + ',"format":"foreign"}')
        with self.assertRaises(ValueError): metadata(' ' * 4097)

    def test_download_preserves_bytes_with_native_uid_compatible_permissions(self):
        self.stage()
        self.assertEqual((self.source / 'document').read_bytes(), self.raw)
        self.assertEqual(json.loads((self.source / 'request.json').read_bytes()), self.value['request'])
        self.assertEqual(stat.S_IMODE(self.source.stat().st_mode), 0o555)
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o777)
        for name in ['document', 'request.json']:
            self.assertEqual(stat.S_IMODE((self.source / name).stat().st_mode), 0o444)
        self.assertEqual(self.objects.calls, [('load', (self.identifier, 'input', self.value['inputETag']))])

    def test_existing_content_is_never_adopted(self):
        (self.target / 'stale').write_text('old output')
        with self.assertRaises(ValueError): self.stage()
        self.assertEqual(self.objects.calls, [])

    def test_mismatched_native_bytes_publish_no_file(self):
        self.objects.raw = b'foreign input'
        with self.assertRaises(ValueError): self.stage()
        self.assertEqual(list(self.source.iterdir()), [])
        self.assertEqual(list(self.target.iterdir()), [])

    def test_alias_and_symlink_mounts_are_rejected(self):
        with self.assertRaises(ValueError): download(self.value, self.objects, str(self.source), str(self.source))
        link = Path(self.temporary.name) / 'linked'
        link.symlink_to(self.source)
        with self.assertRaises(OSError): download(self.value, self.objects, str(link), str(self.target))
        self.assertEqual(self.objects.calls, [])

    def test_upload_checks_outer_and_inner_byte_identity(self):
        self.stage()
        encoded = self.encoded_result()
        (self.target / 'result.json').write_bytes(encoded)
        upload(self.value, self.objects, str(self.source), str(self.target))
        self.assertEqual(self.objects.calls[-1], ('put', (self.identifier, 'result', encoded)))
        value = json.loads(encoded); value['document']['sha256'] = 'e' * 64
        (self.target / 'result.json').write_text(json.dumps(value))
        self.objects.calls.clear()
        with self.assertRaises(ValueError): upload(self.value, self.objects, str(self.source), str(self.target))
        self.assertEqual(self.objects.calls, [])

    def test_symlink_and_fifo_outputs_are_not_followed_or_blocked_on(self):
        self.stage()
        result = self.target / 'result.json'
        result.symlink_to(self.source / 'document')
        with self.assertRaises(OSError): upload(self.value, self.objects, str(self.source), str(self.target))
        result.unlink()
        os.mkfifo(result)
        with self.assertRaises(ValueError): upload(self.value, self.objects, str(self.source), str(self.target))
        self.assertFalse(any(call[0] == 'put' for call in self.objects.calls))

    def test_cli_errors_do_not_print_metadata_or_document(self):
        with patch.dict(os.environ, {'DOCUMENT_JOB': 'PRIVATE SOURCE TOKEN'}, clear=True), patch.object(sys, 'argv', ['transfer', 'download']):
            with self.assertRaises(SystemExit) as raised: main()
        self.assertEqual(str(raised.exception), 'Owned Azure document transfer could not complete.')

    def test_cli_sanitizes_cleanup_errors_and_still_closes(self):
        owned = unittest.mock.Mock()
        owned.close.side_effect = RuntimeError('PRIVATE PROVIDER TOKEN')
        with patch.dict(os.environ, {'DOCUMENT_JOB': '{}'}, clear=True), \
                patch.object(sys, 'argv', ['transfer', 'download']), \
                patch('enterprise_azure_transfer.metadata', return_value=self.value), \
                patch('enterprise_azure_transfer.document_objects', return_value=owned), \
                patch('enterprise_azure_transfer.download'):
            with self.assertRaises(SystemExit) as raised: main()
        self.assertEqual(str(raised.exception), 'Owned Azure document transfer could not complete.')
        owned.close.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
