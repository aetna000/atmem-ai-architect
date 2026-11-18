"""Broker protocol tests use a fake transport/keychain; no network proof claimed."""
import base64
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from server.maintenance.credential_store import MacKeychain, KeychainUnavailable
from server.maintenance.github_adapter import GitHubBroker, GitHubError, GitHubTransport, PollCursor, git_blob_sha, UncertainWrite
from server.maintenance.store import Store


class FakeKeychain:
    def __init__(self):
        self.values = {}
    def put(self, ident, value):
        self.values[ident] = value
    def get(self, ident):
        if ident not in self.values:
            raise KeychainUnavailable('Unavailable')
        return self.values[ident]
    def delete(self, ident):
        self.values.pop(ident, None)


class FakeTransport:
    def __init__(self):
        self.calls, self.status = [], None
        self.metadata = {'id': 100, 'full_name': 'owner/project', 'owner': {'login': 'owner'}, 'default_branch': 'main', 'archived': False}
        self.files = {'main.tf': b'terraform {}\n'}
        self.modes = {}
        self.truncated = False
        self.blob_mismatch = False
    def request(self, token, method, path, body=None, headers=None):
        self.calls.append((method, path))
        if self.status:
            raise GitHubError(self.status)
        if path == '/user':
            data = {'id': 7, 'login': 'customer'}
        elif path == '/repos/owner/project':
            data = self.metadata
        elif '/git/ref/' in path:
            data = {'object': {'sha': 'a' * 40}}
        elif '/commits/' in path:
            data = {'sha': 'a' * 40, 'commit': {'tree': {'sha': 'b' * 40}}}
        elif '/git/trees/' in path:
            data = {'sha': 'b' * 40, 'truncated': self.truncated,
                    'tree': [{'path': name, 'mode': self.modes.get(name, '100644'), 'type': 'blob', 'sha': git_blob_sha(raw), 'size': len(raw)} for name, raw in self.files.items()]}
        elif '/git/blobs/' in path:
            sha = path.rsplit('/', 1)[1]
            raw = next(raw for raw in self.files.values() if git_blob_sha(raw) == sha)
            data = {'sha': sha, 'encoding': 'base64', 'content': base64.b64encode(b'tampered' if self.blob_mismatch else raw).decode()}
        else:
            raise AssertionError('Unexpected fake request: ' + path)
        return {'data': data, 'headers': {}, 'status': 200}


class GitHubBrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Store(Path(self.temp.name) / 'maintenance.sqlite')
        self.keychain, self.transport = FakeKeychain(), FakeTransport()
        self.broker = GitHubBroker(self.db, self.keychain, self.transport)
        self.token = 'github_pat_' + 'x' * 30
        self.connection = self.broker.register('tenant-one', ['project-one'], 'owner', ['owner/project'], self.token, int(time.time()) + 3600)

    def test_keychain_only_selected_owner_project_and_no_direct_writes(self):
        self.assertEqual(self.keychain.get(self.connection.id), self.token)
        self.assertNotIn(self.token.encode(), self.db.path.read_bytes())
        self.assertNotIn(self.token, self.connection.model_dump_json())
        for tenant, project, repository in [('tenant-two', 'project-one', 'owner/project'), ('tenant-one', 'project-two', 'owner/project'), ('tenant-one', 'project-one', 'other/project')]:
            with self.assertRaises(PermissionError):
                self.broker.request(tenant, project, self.connection.id, repository, 'GET', '/git/ref/heads/main')
        with self.assertRaisesRegex(PermissionError, 'coordinator'):
            self.broker.request('tenant-one', 'project-one', self.connection.id, 'owner/project', 'POST', '/git/refs', {})
        self.assertTrue(all(method == 'GET' for method, _ in self.transport.calls))
        with self.assertRaises(ValueError):
            self.broker.register('tenant-one', ['project-one'], 'owner', ['owner/project'], 'ghp_' + 'z' * 36, int(time.time()) + 3600)

    def test_revocation_expiry_owner_change_and_credential_deletion(self):
        self.transport.status = 401
        with self.assertRaises(GitHubError):
            self.broker.request('tenant-one', 'project-one', self.connection.id, 'owner/project', 'GET', '/git/ref/heads/main')
        with self.assertRaises(PermissionError):
            self.broker.connection('tenant-one', 'project-one', self.connection.id)
        self.broker.revoke('tenant-one', 'project-one', self.connection.id)
        self.assertNotIn(self.connection.id, self.keychain.values)
        self.connection.status = 'active';self.connection.expiresAt = int(time.time()) - 1
        self.broker._save(self.connection)
        with self.assertRaises(PermissionError):
            self.broker.connection('tenant-one', 'project-one', self.connection.id)

    def test_exact_source_hashes_completeness_symlinks_and_lfs(self):
        args = ('tenant-one', 'project-one', self.connection.id, 'owner/project', 'a' * 40)
        source = self.broker.materialize(*args, ['main.tf'])
        self.assertEqual(source.files[0].text, 'terraform {}\n')
        self.assertEqual(source.repositoryId, 'github-100')
        self.assertEqual(source.commit, 'a' * 40)
        self.transport.files['other.tf'] = b'output "x" { value = 1 }'
        with self.assertRaisesRegex(ValueError, 'every'):
            self.broker.materialize(*args, ['main.tf'])
        self.transport.files.pop('other.tf')
        self.transport.files['.github/workflows/check.yml'] = b'name: checks'
        with self.assertRaisesRegex(ValueError, 'automation'):
            self.broker.materialize(*args, ['main.tf'])
        self.transport.files.pop('.github/workflows/check.yml')
        self.transport.modes['main.tf'] = '120000'
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.broker.materialize(*args, ['main.tf'])
        self.transport.modes.clear()
        self.transport.blob_mismatch = True
        with self.assertRaisesRegex(ValueError, 'bytes'):
            self.broker.materialize(*args, ['main.tf'])
        self.transport.blob_mismatch = False
        self.transport.files['main.tf'] = b'version https://git-lfs.github.com/spec/v1\n'
        with self.assertRaisesRegex(ValueError, 'LFS'):
            self.broker.materialize(*args, ['main.tf'])
        self.transport.truncated = True
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.broker.materialize(*args, ['main.tf'])

    def test_unknown_keychain_has_no_plaintext_fallback_and_polling_is_bounded(self):
        with patch('server.maintenance.credential_store.sys.platform', 'linux'):
            with self.assertRaises(KeychainUnavailable):
                MacKeychain()
        self.keychain.delete(self.connection.id)
        with self.assertRaises(KeychainUnavailable):
            self.broker.request('tenant-one', 'project-one', self.connection.id, 'owner/project', 'GET', '/git/ref/heads/main')
        cursor = PollCursor(30)
        self.assertTrue(cursor.due(now=0));self.assertFalse(cursor.due(now=29));self.assertTrue(cursor.due(now=30))
        with self.assertRaises(ValueError):
            PollCursor(1)

    def test_transport_timeout_and_server_error_never_retry_or_leak_upstream_error(self):
        import urllib.error
        from unittest.mock import Mock
        transport = GitHubTransport()
        transport.opener = Mock()
        for failure in [urllib.error.URLError('private upstream error'),
                        urllib.error.HTTPError('https://api.github.com/graphql', 502, 'private upstream error', {}, None)]:
            transport.opener.open.side_effect = failure
            with self.assertRaises(UncertainWrite) as raised:
                transport.request(self.token, 'POST', '/graphql', {'query': 'mutation'})
            self.assertNotIn('private upstream', str(raised.exception))
        self.assertEqual(transport.opener.open.call_count, 2)

    def test_transport_rejects_external_origin_and_unreviewed_methods_before_network(self):
        transport = GitHubTransport()
        for method, path in [('GET', 'https://evil.invalid/'), ('GET', '//evil.invalid/'), ('DELETE', '/repos/owner/project')]:
            with self.assertRaises(ValueError):
                transport.request(self.token, method, path)

class TagTransport(FakeTransport):
    def __init__(self):
        super().__init__()
        self.tag_reads, self.move, self.cycle = 0, False, False
    def request(self, token, method, path, body=None, headers=None):
        if '/git/ref/tags/' in path:
            self.tag_reads += 1
            return {'data': {'object': {'type': 'tag', 'sha': 'c' * 40}}, 'headers': {}, 'status': 200}
        if '/git/tags/' in path:
            commit = 'd' * 40 if self.move and self.tag_reads > 1 else 'a' * 40
            return {'data': {'object': {'type': 'tag' if self.cycle else 'commit', 'sha': 'c' * 40 if self.cycle else commit}}, 'headers': {}, 'status': 200}
        return super().request(token, method, path, body, headers)


class ReleasedArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db = Store(Path(self.temp.name) / 'maintenance.sqlite')
        self.remote = TagTransport()
        self.broker = GitHubBroker(self.db, FakeKeychain(), self.remote)
        self.connection = self.broker.register('tenant-one', ['project-one'], 'owner', ['owner/project'], 'github_pat_' + 'x' * 30, int(time.time()) + 3600)
        self.args = ('tenant-one', 'project-one', self.connection.id, 'owner/project')

    def test_annotated_release_fetch_requires_full_set_and_byte_equality(self):
        files, proof = self.broker.released_module(*self.args, 'v2.0.0', '.', {'main.tf': 'terraform {}\n'})
        self.assertEqual(files, {'main.tf': 'terraform {}\n'})
        self.assertEqual(proof['commit'], 'a' * 40)
        self.assertEqual(proof['tagObject'], 'c' * 40)
        self.assertEqual(proof['source'], 'git::https://github.com/owner/project.git?ref=' + 'a' * 40)
        with self.assertRaisesRegex(ValueError, 'bytes'):
            self.broker.released_module(*self.args, 'v2.0.0', '.', {'main.tf': '# different'})
        self.remote.files['README.md'] = b'additional release file'
        with self.assertRaisesRegex(ValueError, 'file set'):
            self.broker.released_module(*self.args, 'v2.0.0', '.', {'main.tf': 'terraform {}\n'})

    def test_moving_tags_cycles_and_non_tag_refs_are_denied(self):
        from server.maintenance.store import Conflict
        self.remote.move = True
        with self.assertRaises(Conflict):
            self.broker.released_module(*self.args, 'v2.0.0', '.', {'main.tf': 'terraform {}\n'})
        self.remote.move = False;self.remote.cycle = True
        with self.assertRaises(ValueError):
            self.broker.resolve_tag(*self.args, 'v2.0.0')
        for tag in ['../main', 'refs/tags/../../main', 'v2^{commit}', 'v2\nmalicious']:
            with self.assertRaises(ValueError):self.broker.resolve_tag(*self.args, tag)
