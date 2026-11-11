"""Immutable local artifact adapter; snapshots never execute generated code.

Capture uses directory-relative, no-follow opens and rejects symlinks/special files.
Runtime validation is separate: neither capture nor agent completion proves quality.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import uuid
import zipfile

from .engineering_sessions import SessionError


class EngineeringArtifacts:
    EXCLUDED = {'.worker-tmp', '.tools', '.git', '.terraform', '__pycache__'}

    def __init__(self, store, *, max_bytes=64_000_000, max_files=2000):
        self.store, self.db = store, store.db
        self.max_bytes, self.max_files = max_bytes, max_files
        self.db.execute('''CREATE TABLE IF NOT EXISTS engineering_artifacts (
            id TEXT PRIMARY KEY, session TEXT NOT NULL, run TEXT NOT NULL,
            manifest TEXT NOT NULL, archive BLOB NOT NULL)''')
        self.db.commit()

    def capture(self, scope, session, workspace, *, expected_inputs=None):
        before = self.store.get(scope, session)
        if before['state'] != 'idle' or before['last_status'] is None:
            raise SessionError('Artifact capture requires a settled engineering run')
        if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'):
            raise SessionError('This platform has no qualified artifact capture adapter')
        output, files, exclusions = io.BytesIO(), [], []
        total = 0
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        def walk(directory, prefix, archive):
            nonlocal total
            names = sorted(os.listdir(directory))
            for name in names:
                relative = f'{prefix}/{name}' if prefix else name
                if any(ord(c) < 32 for c in name) or '\\' in name or name in {'.', '..'}:
                    raise SessionError('Artifact contains an unsupported filename')
                if name in self.EXCLUDED:
                    exclusions.append(relative)
                    continue
                descriptor = os.open(name, flags, dir_fd=directory)
                try:
                    first = os.fstat(descriptor)
                    if stat.S_ISDIR(first.st_mode):
                        # Count directories too: huge empty trees must not bypass bounds.
                        files.append({'path': relative+'/', 'kind': 'directory'})
                        if len(files) > self.max_files:
                            raise SessionError('Artifact entry limit exceeded; no partial package was saved')
                        archive.writestr(relative+'/', b'')
                        walk(descriptor, relative, archive)
                    elif stat.S_ISREG(first.st_mode):
                        if first.st_nlink != 1 or first.st_size + total > self.max_bytes:
                            raise SessionError('Artifact is linked or exceeds the byte limit; no partial package was saved')
                        chunks, size = [], 0
                        while True:
                            chunk = os.read(descriptor, min(1_000_000, self.max_bytes-total-size+1))
                            if not chunk: break
                            chunks.append(chunk)
                            size += len(chunk)
                            if total+size > self.max_bytes:
                                raise SessionError('Artifact byte limit exceeded; no partial package was saved')
                        final = os.fstat(descriptor)
                        if (first.st_size,first.st_mtime_ns,first.st_ctime_ns) != (final.st_size,final.st_mtime_ns,final.st_ctime_ns) or size != first.st_size:
                            raise SessionError('Artifact changed during capture; retry after work settles')
                        content = b''.join(chunks)
                        files.append({'path': relative, 'kind': 'file', 'bytes': size,
                                      'sha256': hashlib.sha256(content).hexdigest()})
                        if len(files) > self.max_files:
                            raise SessionError('Artifact entry limit exceeded; no partial package was saved')
                        info = zipfile.ZipInfo(relative)
                        info.compress_type = zipfile.ZIP_DEFLATED
                        info.external_attr = (stat.S_IFREG | (0o755 if first.st_mode & 0o111 else 0o644)) << 16
                        archive.writestr(info, content)
                        total += size
                    else:
                        raise SessionError('Artifact contains a special file; no package was saved')
                finally:
                    os.close(descriptor)
        try:
            root = os.open(Path(workspace), flags | os.O_DIRECTORY)
            try:
                with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                    walk(root, '', archive)
            finally:
                os.close(root)
        except OSError:
            raise SessionError('Artifact contains an unavailable or unsafe entry; no package was saved') from None
        after = self.store.get(scope, session)
        if (after['state'], after['run'], after['last_status']) != ('idle',before['run'],before['last_status']):
            raise SessionError('Engineering run changed during capture; no package was saved')
        pinned = expected_inputs or {}
        observed = {entry['path']:entry.get('sha256') for entry in files}
        if any(observed.get(path)!=digest for path,digest in pinned.items()):
            raise SessionError('Pinned project evidence or reviewed instructions changed; restore the original inputs before capture')
        data = output.getvalue()
        ident = str(uuid.uuid4())
        manifest = {'id': ident, 'sessionId': session, 'runId': before['run'],
                    'model': before['model'], 'effort': before['effort'],
                    'turnStatus': before['last_status'], 'sha256': hashlib.sha256(data).hexdigest(),
                    'bytes': len(data), 'files': files, 'excluded': exclusions,
                    'pinnedInputs': pinned,
                    'validation': 'not_established_by_artifact_capture'}
        with self.db:
            self.db.execute('INSERT INTO engineering_artifacts VALUES (?,?,?,?,?)',
                            (ident,session,before['run'],json.dumps(manifest),data))
        return manifest

    def get(self, scope, session, artifact):
        self.store.get(scope, session)
        row = self.db.execute('SELECT manifest,archive FROM engineering_artifacts WHERE id=? AND session=?',
                              (artifact,session)).fetchone()
        if row is None:
            raise SessionError('Artifact is unavailable for this project and session')
        return json.loads(row['manifest']), bytes(row['archive'])

    def manifests(self,scope,session):
        self.store.get(scope,session)
        rows=self.db.execute('SELECT manifest FROM engineering_artifacts WHERE session=? ORDER BY rowid DESC LIMIT 20',(session,)).fetchall()
        return [json.loads(row['manifest']) for row in rows]
