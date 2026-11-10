"""Actual private file lifecycle; no native secret-service or cloud account call."""
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / '.local/azure-runtime-sdk')]
from cryptography.fernet import Fernet
from enterprise_secrets import SecretFiles, FIELDS
from enterprise_sources import SourceUnavailable


def environment(provider):
    values = {'ENTERPRISE_ENCRYPTION_KEY': Fernet.generate_key().decode(), 'SHAREPOINT_CLIENT_SECRET': 'SYNTHETIC-GRAPH-SECRET',
              'CONFLUENCE_CLIENT_SECRET': 'SYNTHETIC-CONFLUENCE-SECRET'}
    if provider != 'gcp': values['DATABASE_CA_PEM'] = '-----BEGIN CERTIFICATE-----\nSYNTHETIC-CA\n-----END CERTIFICATE-----'
    if provider == 'ibm': values['DATABASE_PASSWORD'] = 'SYNTHETIC-DATABASE-PASSWORD'
    return values


class NativePrivateSecrets(unittest.TestCase):
    def test_all_four_native_injections_become_private_files_without_export_values(self):
        old = os.umask(0)
        try:
            for provider in ['aws', 'azure', 'gcp', 'ibm']:
                for role in ['api', 'worker']:
                    original = environment(provider)
                    with SecretFiles(provider, original, role) as secrets:
                        self.assertEqual(stat.S_IMODE(secrets.directory.stat().st_mode), 0o700)
                        for direct, value in original.items():
                            name = next(name for name, row in FIELDS.items() if row[0] == direct)
                            path = Path(secrets.env[FIELDS[name][1]])
                            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                            self.assertEqual(secrets.read(name), value); self.assertNotIn(direct, secrets.env)
                            self.assertNotIn(value, repr(secrets))
                        directory = secrets.directory
                    self.assertFalse(directory.exists())
                    with self.assertRaises(SourceUnavailable): secrets.read('encryption')
        finally: os.umask(old)

    def test_mounted_native_files_are_read_without_replacement_or_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            original = environment('gcp'); mounted = {}
            for direct, value in original.items():
                pointer = next(row[1] for row in FIELDS.values() if row[0] == direct)
                path = Path(directory) / direct; path.write_text(value); mounted[pointer] = str(path)
            with SecretFiles('gcp', mounted, 'worker') as secrets:
                self.assertIsNone(secrets.directory); self.assertEqual(secrets.read('graph'), original['SHAREPOINT_CLIENT_SECRET'])
            self.assertTrue(all(Path(path).exists() for path in mounted.values()))

    def test_native_oauth_reader_observes_mounted_secret_change_without_env_fallback(self):
        with SecretFiles('gcp', environment('gcp'), 'api') as secrets:
            read = secrets.reader('graph'); self.assertEqual(read(), 'SYNTHETIC-GRAPH-SECRET')
            path = Path(secrets.env['SHAREPOINT_CLIENT_SECRET_FILE']); path.write_text('SYNTHETIC-ROTATED-SECRET')
            self.assertEqual(read(), 'SYNTHETIC-ROTATED-SECRET'); path.unlink()
            with self.assertRaises(SourceUnavailable): read()

    def test_missing_or_invalid_keys_do_not_generate_replacements(self):
        original = environment('gcp')
        for value in ['', 'not-a-key', original['ENTERPRISE_ENCRYPTION_KEY'] + '\n', 'x' * 100]:
            with self.assertRaises(ValueError): SecretFiles('gcp', {**original, 'ENTERPRISE_ENCRYPTION_KEY': value}, 'worker')
        missing = dict(original); missing.pop('ENTERPRISE_ENCRYPTION_KEY')
        with self.assertRaises(ValueError): SecretFiles('gcp', missing, 'worker')

    def test_conflicts_relative_missing_and_oversized_files_fail_closed(self):
        original = environment('gcp')
        with self.assertRaises(ValueError): SecretFiles('gcp', {**original, 'SHAREPOINT_CLIENT_SECRET_FILE': '/owned/file'}, 'api')
        original.pop('SHAREPOINT_CLIENT_SECRET')
        with self.assertRaises(ValueError): SecretFiles('gcp', {**original, 'SHAREPOINT_CLIENT_SECRET_FILE': 'relative'}, 'api')
        with self.assertRaises(SourceUnavailable): SecretFiles('gcp', {**original, 'SHAREPOINT_CLIENT_SECRET_FILE': '/no-such-owned-secret'}, 'api')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'secret'; path.write_bytes(b'x' * 16001)
            with self.assertRaises(SourceUnavailable): SecretFiles('gcp', {**original, 'SHAREPOINT_CLIENT_SECRET_FILE': str(path)}, 'api')

    def test_static_cloud_and_action_authority_never_silently_enters_private_roles(self):
        for provider in ['aws', 'azure', 'gcp', 'ibm']:
            for name in ['AWS_ACCESS_KEY_ID', 'AZURE_CLIENT_SECRET', 'GOOGLE_APPLICATION_CREDENTIALS', 'IBMCLOUD_API_KEY', 'OPENAI_API_KEY', 'PARSER_SHARED_TOKEN', 'DESTINATION_TOKEN']:
                with self.assertRaises(ValueError): SecretFiles(provider, {**environment(provider), name: 'SYNTHETIC-UNEXPECTED'}, 'worker')
            if provider != 'ibm':
                with self.assertRaises(ValueError): SecretFiles(provider, {**environment(provider), 'DATABASE_PASSWORD': 'SYNTHETIC'}, 'api')

    def test_actual_process_environment_drops_direct_values_after_success(self):
        values = environment('gcp')
        with patch.dict(os.environ, values, clear=True):
            with SecretFiles('gcp', os.environ, 'api') as secrets:
                self.assertTrue(all(key not in os.environ for key in values))
                self.assertEqual(secrets.read('confluence'), values['CONFLUENCE_CLIENT_SECRET'])

    def test_partial_write_failure_cleans_owned_files_and_preserves_external_files(self):
        import enterprise_secrets
        original = environment('gcp'); created = []
        real = enterprise_secrets.tempfile.mkdtemp
        open_file = enterprise_secrets.os.open
        writes = []
        def make(**kwargs):
            path = real(**kwargs); created.append(Path(path)); return path
        def fail_second_write(path, flags, *args, **kwargs):
            if flags & os.O_CREAT:
                writes.append(path)
                if len(writes) == 2: raise OSError('SYNTHETIC WRITE FAILURE')
            return open_file(path, flags, *args, **kwargs)
        # Fail the secret write, while preserving the OS directory operations
        # required to exercise actual cleanup of the first successfully written key.
        with patch('enterprise_secrets.tempfile.mkdtemp', side_effect=make), patch('enterprise_secrets.os.open', side_effect=fail_second_write):
            with self.assertRaises(OSError): SecretFiles('gcp', original, 'worker')
        self.assertEqual(len(writes), 2); self.assertEqual(len(created), 1); self.assertFalse(created[0].exists())


if __name__ == '__main__': unittest.main()
