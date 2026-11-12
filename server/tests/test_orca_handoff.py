import base64
import io
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from server.orca_handoff import unpack_package, open_package


def encoded(entries):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return base64.b64encode(stream.getvalue()).decode()


class OrcaHandoffTests(unittest.TestCase):
    def test_retains_bytes_and_creates_fresh_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = encoded([('spec-kit/spec.md', 'résumé'), ('implementation/main.py', b'print(1)\n')])
            first = unpack_package(archive, directory, 'project1')
            second = unpack_package(archive, directory, 'project1')
            self.assertNotEqual(first, second)
            self.assertEqual((first/'spec-kit/spec.md').read_text(), 'résumé')
            self.assertEqual((first/'implementation/main.py').read_bytes(), b'print(1)\n')

    def test_rejects_escaping_and_windows_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ['../escape', '/absolute', 'C:/drive', 'a\\b', 'CON.txt', 'a/file.', 'A', 'a']:
                entries = [('A', 'one'), ('a', 'two')] if name in {'A', 'a'} else [(name, 'bad')]
                with self.subTest(name=name), self.assertRaises(ValueError):
                    unpack_package(encoded(entries), directory, 'project1')
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_rejects_links(self):
        entry = zipfile.ZipInfo('link')
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            unpack_package(encoded([(entry, '../outside')]), directory, 'project1')

    def test_uses_documented_folder_command_without_shell_or_project_execution(self):
        with tempfile.TemporaryDirectory() as directory, patch('server.orca_handoff.orca_command', return_value='/tools/orca'), patch('server.orca_handoff.subprocess.run') as run:
            result = open_package(encoded([('spec.md', 'scope')]), directory, 'project1')
            self.assertTrue(result['opened'])
            self.assertEqual(run.call_args_list[1].args[0], ['/tools/orca', 'repo', 'add', '--path', result['path'], '--kind', 'folder', '--json'])
            self.assertNotIn('shell', run.call_args.kwargs)

    def test_missing_orca_creates_no_folder(self):
        with tempfile.TemporaryDirectory() as directory, patch('server.orca_handoff.orca_command', side_effect=ValueError('Install Orca')):
            with self.assertRaisesRegex(ValueError, 'Install Orca'):
                open_package(encoded([('spec.md', 'scope')]), directory, 'project1')
            self.assertEqual(list(Path(directory).iterdir()), [])
