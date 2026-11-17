"""Selected-repository GitHub broker. Credentials stay in the OS keychain.

The transport pins GitHub's API origin, rejects redirects and ambient proxies,
bounds data, sanitizes errors, and never retries uncertain mutations implicitly.
"""
import base64
import hashlib
import json
import re
from pathlib import PurePosixPath
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4

from pydantic import Field

from .credential_store import MacKeychain, KeychainUnavailable
from .inventory import snapshot, safe_path, SENSITIVE_PATH, AUTOMATION
from .models import Record, Identifier

REPOSITORY = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$')
COMMIT = re.compile(r'^[a-f0-9]{40}$')


class GitHubError(RuntimeError):
    def __init__(self, status, reason='GitHub operation unavailable'):
        self.status = status
        super().__init__(reason)


class UncertainWrite(GitHubError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


class GitHubTransport:
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, token, method, path, body=None, headers=None):
        if method not in {'GET', 'POST'} or not path.startswith('/') or path.startswith('//') or any(ord(c) < 32 for c in path):
            raise ValueError('Unreviewed GitHub transport operation')
        encoded = None if body is None else json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        if encoded is not None and len(encoded) > 16_000_000:
            raise ValueError('GitHub request exceeds the explicit bound')
        request = urllib.request.Request('https://api.github.com' + path, data=encoded, method=method,
            headers={'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json',
                     'X-GitHub-Api-Version': '2026-03-10', 'User-Agent': 'AtMem-Architect-maintenance',
                     **(headers or {}), 'Authorization': 'Bearer ' + token})
        try:
            with self.opener.open(request, timeout=20) as response:
                raw = response.read(10_000_001)
                if len(raw) > 10_000_000:
                    error = UncertainWrite if method != 'GET' else GitHubError
                    raise error(413, 'GitHub response exceeds the explicit bound')
                return {'data': json.loads(raw) if raw else None, 'headers': dict(response.headers), 'status': response.status}
        except urllib.error.HTTPError as error:
            if error.code == 304:
                return {'data': None, 'headers': dict(error.headers), 'status': 304}
            # Never expose response bodies, URL userinfo, request headers or tokens.
            failure = UncertainWrite if method != 'GET' and (error.code >= 500 or error.code == 408) else GitHubError
            raise failure(error.code, 'GitHub denied or could not complete the scoped operation') from None
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError):
            error = UncertainWrite if method != 'GET' else GitHubError
            raise error(0, 'GitHub response uncertain; reconcile before retrying') from None
        except (ValueError, UnicodeError):
            error = UncertainWrite if method != 'GET' else GitHubError
            raise error(0, 'GitHub response could not be verified') from None


class Connection(Record):
    id: Identifier
    tenantId: Identifier
    projectIds: list[Identifier] = Field(min_length=1, max_length=100)
    resourceOwner: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9-]{0,99}$')
    tokenOwnerId: int = Field(ge=1)
    tokenOwnerLogin: str = Field(min_length=1, max_length=100)
    repositories: dict[str, int] = Field(min_length=1, max_length=100)
    expiresAt: int = Field(ge=1)
    status: str = Field(pattern=r'^(active|revoked|permission_required)$')
    createdAt: int = Field(ge=1)


def repo_path(repository):
    if not REPOSITORY.fullmatch(repository):
        raise ValueError('Select an exact GitHub repository')
    return '/repos/' + repository


def git_blob_sha(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


class GitHubBroker:
    def __init__(self, store, keychain=None, transport=None):
        self.store = store
        self.keychain = keychain if keychain is not None else MacKeychain()
        self.transport = transport or GitHubTransport()
        with store.transaction() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS github_connections (
                tenant TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(tenant,id))''')

    def _save(self, connection):
        connection = Connection.model_validate(connection.model_dump())
        with self.store.transaction() as db:
            db.execute('INSERT OR REPLACE INTO github_connections VALUES(?,?,?)',
                       (connection.tenantId, connection.id, connection.model_dump_json()))
        return connection

    def connection(self, tenant, project, ident):
        with self.store.transaction() as db:
            row = db.execute('SELECT payload FROM github_connections WHERE tenant=? AND id=?', (tenant, ident)).fetchone()
        if row is None:
            raise PermissionError('Repository connection unavailable')
        value = Connection.model_validate_json(row['payload'])
        if project not in value.projectIds or value.status != 'active' or value.expiresAt <= time.time():
            raise PermissionError('Repository connection expired, revoked or outside this project')
        return value

    def register(self, tenant, projects, resource_owner, repositories, token, expires_at):
        # Called by an out-of-band CLI prompt, never a model/browser/tool argument.
        if not isinstance(token, str) or not re.fullmatch(r'github_pat_[A-Za-z0-9_]{20,1000}', token):
            raise ValueError('Use a customer-owned fine-grained GitHub token')
        if type(expires_at) is not int or not time.time() < expires_at <= time.time() + 366 * 86400:
            raise ValueError('Set an explicit token expiry within one year')
        if not repositories or len(repositories) > 100 or len(set(r.lower() for r in repositories)) != len(repositories):
            raise ValueError('Select unique repositories within one resource owner')
        viewer = self.transport.request(token, 'GET', '/user')['data']
        selected = {}
        for repository in repositories:
            metadata = self.transport.request(token, 'GET', repo_path(repository))['data']
            if (metadata.get('full_name', '').lower() != repository.lower() or
                metadata.get('owner', {}).get('login', '').lower() != resource_owner.lower() or metadata.get('archived')):
                raise PermissionError('Repository owner, identity or archive state does not match selection')
            default = metadata.get('default_branch')
            if not default:
                raise PermissionError('Repository has no usable default branch')
            self.transport.request(token, 'GET', repo_path(repository) + '/git/ref/heads/' + urllib.parse.quote(default, safe=''))
            selected[metadata['full_name']] = metadata['id']
        connection = Connection(id=str(uuid4()), tenantId=tenant, projectIds=projects, resourceOwner=resource_owner,
            tokenOwnerId=viewer['id'], tokenOwnerLogin=viewer['login'], repositories=selected,
            expiresAt=expires_at, status='active', createdAt=int(time.time()))
        self.keychain.put(connection.id, token)
        try:
            return self._save(connection)
        except Exception:
            self.keychain.delete(connection.id)
            raise

    def revoke(self, tenant, project, ident):
        with self.store.transaction() as db:
            row = db.execute('SELECT payload FROM github_connections WHERE tenant=? AND id=?', (tenant, ident)).fetchone()
        if row is None:
            raise PermissionError('Repository connection unavailable')
        connection = Connection.model_validate_json(row['payload'])
        if project not in connection.projectIds:
            raise PermissionError('Connection is outside this project')
        connection.status = 'revoked'
        self._save(connection)  # Stop new operations before touching the credential store.
        self.keychain.delete(connection.id)
        return {'id': ident, 'status': 'revoked', 'credentialDeletionConfirmed': True}

    def request(self, tenant, project, ident, repository, method, suffix='', body=None):
        connection = self.connection(tenant, project, ident)
        if repository not in connection.repositories:
            raise PermissionError('Repository is outside the selected connection')
        token = self.keychain.get(connection.id)
        try:
            viewer = self.transport.request(token, 'GET', '/user')['data']
            if viewer.get('id') != connection.tokenOwnerId:
                raise PermissionError('Credential owner changed; reconnect explicitly')
            metadata = self.transport.request(token, 'GET', repo_path(repository))['data']
            if (metadata.get('id') != connection.repositories[repository] or metadata.get('full_name') != repository or
                metadata.get('owner', {}).get('login', '').lower() != connection.resourceOwner.lower() or metadata.get('archived')):
                raise PermissionError('Repository identity changed or became unavailable')
            if method != 'GET':
                raise PermissionError('Remote writes require the publication coordinator')
            if not suffix.startswith('/') or '?' in suffix and not suffix.startswith(('/git/trees/', '/pulls?')):
                raise ValueError('Select a reviewed repository read')
            allowed = ('/git/ref/', '/git/tags/', '/git/commits/', '/git/trees/', '/git/blobs/', '/commits/', '/branches/', '/rules/branches/', '/pulls', '/actions/workflows')
            if not suffix.startswith(allowed) or '..' in suffix or '\\' in suffix or '#' in suffix:
                raise ValueError('Unreviewed repository read')
            return self.transport.request(token, 'GET', repo_path(repository) + suffix)
        except GitHubError as error:
            if error.status in {401, 403}:
                connection.status = 'revoked' if error.status == 401 else 'permission_required'
                self._save(connection)
            raise

    def repository_metadata(self, tenant, project, ident, repository):
        connection = self.connection(tenant, project, ident)
        if repository not in connection.repositories:
            raise PermissionError('Repository is outside the selected connection')
        token = self.keychain.get(connection.id)
        try:
            viewer = self.transport.request(token, 'GET', '/user')['data']
            value = self.transport.request(token, 'GET', repo_path(repository))['data']
            if (viewer.get('id') != connection.tokenOwnerId or value.get('id') != connection.repositories[repository]
                or value.get('full_name') != repository or value.get('archived')
                or value.get('owner', {}).get('login', '').lower() != connection.resourceOwner.lower()):
                raise PermissionError('Repository or credential identity changed')
            return value
        except GitHubError as error:
            if error.status in {401, 403}:
                connection.status = 'revoked' if error.status == 401 else 'permission_required'
                self._save(connection)
            raise

    def publication_write(self, tenant, project, ident, repository, kind, body, guard):
        """Private coordinator boundary: fixed operations, fresh identity, durable guard.

        The HTTP adapter never exposes kind/path/body dispatch. A guard must verify
        the live ledger authorization/fence and durably record exact intent after
        network permission reads, immediately before this fixed mutation.
        """
        connection = self.connection(tenant, project, ident)
        if repository not in connection.repositories:
            raise PermissionError('Repository is outside the selected connection')
        token = self.keychain.get(connection.id)
        try:
            viewer = self.transport.request(token, 'GET', '/user')['data']
            metadata = self.transport.request(token, 'GET', repo_path(repository))['data']
            if (viewer.get('id') != connection.tokenOwnerId or metadata.get('id') != connection.repositories[repository]
                or metadata.get('full_name') != repository or metadata.get('archived')
                or metadata.get('owner', {}).get('login', '').lower() != connection.resourceOwner.lower()):
                raise PermissionError('Repository or credential identity changed')
            paths = {'blob': '/git/blobs', 'tree': '/git/trees', 'commit': '/git/commits', 'ref': '/git/refs', 'pull': '/pulls'}
            if kind not in paths:
                raise ValueError('Unreviewed publication operation')
            if kind == 'ref':
                ref = body.get('ref', '')
                if not ref.startswith('refs/heads/atmem-upgrades/') or ref.removeprefix('refs/heads/') == metadata.get('default_branch'):
                    raise PermissionError('Default, tag and unapproved proposal refs are forbidden')
            if kind == 'tree' and any(AUTOMATION.search(item.get('path', '')) for item in body.get('tree', [])):
                raise PermissionError('Automation file changes are forbidden')
            guard(metadata)  # Durable exact-intent and authorization check, not a model decision.
            return self.transport.request(token, 'POST', repo_path(repository) + paths[kind], body)
        except GitHubError as error:
            if error.status in {401, 403}:
                connection.status = 'revoked' if error.status == 401 else 'permission_required'
                self._save(connection)
            raise

    def materialize(self, tenant, project, ident, repository, commit, paths):
        if not COMMIT.fullmatch(commit) or not isinstance(paths, list) or not 1 <= len(paths) <= 1000 or len(set(paths)) != len(paths):
            raise ValueError('Select an immutable commit and bounded unique file paths')
        for path in paths:
            safe_path(path)
            if SENSITIVE_PATH.search(path) or any(part in {'.git', '.terraform', 'node_modules', '.venv'} for part in path.split('/')):
                raise ValueError('Sensitive or installed source paths are excluded')
        record = self.request(tenant, project, ident, repository, 'GET', '/commits/' + commit)['data']
        if record.get('sha') != commit:
            raise ValueError('Requested immutable revision did not match GitHub')
        tree_id = record['commit']['tree']['sha']
        tree = self.request(tenant, project, ident, repository, 'GET', '/git/trees/' + tree_id + '?recursive=1')['data']
        if tree.get('truncated') or tree.get('sha') != tree_id or len(tree.get('tree', [])) > 20000:
            raise ValueError('Repository tree is incomplete or exceeds the discovery bound')
        entries = {item['path']: item for item in tree['tree']}
        if len(entries) != len(tree['tree']):
            raise ValueError('Ambiguous repository tree')
        roots = {str(PurePosixPath(path).parent) for path in paths if path.endswith(('.tf', '.tf.json', '.tftest.hcl'))}
        if not roots:
            raise ValueError('Select complete Terraform root configuration')
        required = {path for path, item in entries.items() if item.get('type') != 'tree' and
                    (AUTOMATION.search(path) or str(PurePosixPath(path).parent) in roots and
                     path.endswith(('.tf', '.tf.json', '.tftest.hcl', '.lock.hcl')))}
        if not required <= set(paths):
            raise ValueError('Include every selected-root configuration and repository automation file')
        files, total = {}, 0
        for path in paths:
            item = entries.get(path)
            if item is None or item.get('type') != 'blob' or item.get('mode') not in {'100644', '100755'}:
                raise ValueError('Selected source is missing, a symlink, or an unresolved submodule')
            if not 0 <= item.get('size', 2_000_001) <= 2_000_000:
                raise ValueError('Selected source exceeds its file bound')
            blob = self.request(tenant, project, ident, repository, 'GET', '/git/blobs/' + item['sha'])['data']
            if blob.get('encoding') != 'base64' or blob.get('sha') != item['sha']:
                raise ValueError('GitHub blob identity or encoding mismatch')
            try:
                raw = base64.b64decode(''.join(blob['content'].splitlines()), validate=True)
                text = raw.decode('utf-8')
            except (ValueError, UnicodeError, KeyError):
                raise ValueError('Source must be lossless UTF-8 text') from None
            if len(raw) != item['size'] or git_blob_sha(raw) != item['sha']:
                raise ValueError('Fetched source bytes do not match the immutable Git tree')
            if text.startswith('version https://git-lfs.github.com/spec/'):
                raise ValueError('Git LFS source requires explicit materialization')
            total += len(raw)
            if total > 8_000_000:
                raise ValueError('Selected source exceeds 8 MB; no bytes were truncated')
            files[path] = text
        # Repository identity is numeric and immutable; names are not cache keys.
        connection = self.connection(tenant, project, ident)
        result = snapshot(files, 'github-' + str(connection.repositories[repository]), commit=commit)
        return result


class PollCursor:
    """Caller-driven local polling; no hidden background network activity."""
    def __init__(self, interval_seconds=60):
        if type(interval_seconds) is not int or not 30 <= interval_seconds <= 3600:
            raise ValueError('Polling interval must be 30–3600 seconds')
        self.interval, self.next = interval_seconds, 0.0

    def due(self, *, now=None):
        current = time.monotonic() if now is None else now
        if current < self.next:
            return False
        self.next = current + self.interval
        return True
