"""Immutable local artifact adapter; snapshots never execute generated code.

Capture uses directory-relative, no-follow opens and rejects symlinks/special files.
Runtime validation is separate: neither capture nor agent completion proves quality.
"""
import hashlib
import io
import json
import os
from pathlib import Path,PurePosixPath
import re
import stat
import uuid
import zipfile

from .engineering_sessions import SessionError


class EngineeringArtifacts:
    TABLE = 'engineering_artifacts'
    KIND = 'delivery'
    EXCLUDED = {'.worker-tmp', '.tools', '.git', '.terraform', '__pycache__'}

    def __init__(self, store, *, max_bytes=64_000_000, max_files=2000):
        self.store, self.db = store, store.db
        self.max_bytes, self.max_files = max_bytes, max_files
        self.db.execute(f'''CREATE TABLE IF NOT EXISTS {self.TABLE} (
            id TEXT PRIMARY KEY, session TEXT NOT NULL, run TEXT NOT NULL,
            manifest TEXT NOT NULL, archive BLOB NOT NULL)''')
        self.db.commit()

    def _require_state(self,row):
        if row['state']!='idle' or row['last_status'] is None:
            raise SessionError('Artifact capture requires a settled engineering run')

    @staticmethod
    def _state_identity(row):
        return tuple(row[key] for key in ['state','run','turn','last_status'])

    def _persist(self,manifest,data):
        with self.db:
            self.db.execute(f'INSERT INTO {self.TABLE} VALUES (?,?,?,?,?)',
                (manifest['id'],manifest['sessionId'],manifest['runId'],json.dumps(manifest),data))
        return manifest

    def capture(self, scope, session, workspace, *, expected_inputs=None):
        if expected_inputs is not None:
            if not isinstance(expected_inputs,dict) or any(not isinstance(name,str) or not PurePosixPath(name).parts or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or '\\' in name or not isinstance(digest,str) or not re.fullmatch(r'[a-f0-9]{64}',digest) for name,digest in expected_inputs.items()):
                raise ValueError('Pinned inputs require relative names and actual SHA-256 digests')
        before = self.store.get(scope, session)
        self._require_state(before)
        if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'):
            raise SessionError('This platform has no qualified artifact capture adapter')
        output, files, exclusions = io.BytesIO(), [], []
        total = 0
        observed_stats={}
        def identity(info):return tuple(getattr(info,key) for key in ['st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns'])
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        def walk(directory, prefix, archive):
            nonlocal total
            observed_stats[prefix]=identity(os.fstat(directory))
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
                    observed_stats[relative]=identity(first)
                    if stat.S_ISDIR(first.st_mode):
                        # Count directories too: huge empty trees must not bypass bounds.
                        files.append({'path': relative+'/', 'kind': 'directory'})
                        if len(files) > self.max_files:
                            raise SessionError('Artifact entry limit exceeded; no partial package was saved')
                        info=zipfile.ZipInfo(relative+'/');info.external_attr=(stat.S_IFDIR|0o755)<<16
                        archive.writestr(info,b'')
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
                # Recheck the entire observed tree: an earlier file or directory
                # may change after its individual read while another is captured.
                audited=set()
                def audit(directory,prefix):
                    if identity(os.fstat(directory))!=observed_stats.get(prefix):raise SessionError('Source changed during snapshot; no partial evidence was saved')
                    audited.add(prefix)
                    for name in sorted(os.listdir(directory)):
                        if name in self.EXCLUDED:continue
                        relative=f'{prefix}/{name}' if prefix else name
                        descriptor=os.open(name,flags,dir_fd=directory)
                        try:
                            info=os.fstat(descriptor)
                            if identity(info)!=observed_stats.get(relative):raise SessionError('Source changed during snapshot; no partial evidence was saved')
                            audited.add(relative)
                            if stat.S_ISDIR(info.st_mode):audit(descriptor,relative)
                        finally:os.close(descriptor)
                audit(root,'')
                if audited!=set(observed_stats):raise SessionError('Source entries changed during snapshot; no partial evidence was saved')
            finally:
                os.close(root)
        except OSError:
            raise SessionError('Artifact contains an unavailable or unsafe entry; no package was saved') from None
        after = self.store.get(scope, session)
        self._require_state(after)
        if self._state_identity(after)!=self._state_identity(before):
            raise SessionError('Engineering run changed during capture; no package was saved')
        pinned = expected_inputs or {}
        observed = {entry['path']:entry.get('sha256') for entry in files}
        if any(observed.get(path)!=digest for path,digest in pinned.items()):
            raise SessionError('Pinned project evidence or reviewed instructions changed; restore the original inputs before capture')
        data = output.getvalue()
        ident = str(uuid.uuid4())
        manifest = {'id': ident, 'sessionId': session, 'runId': before['run'],
                    'model': before['model'], 'effort': before['effort'],
                    'kind':self.KIND,'turnStatus': 'in_progress' if self.KIND=='working_checkpoint' else before['last_status'], 'sha256': hashlib.sha256(data).hexdigest(),
                    'bytes': len(data), 'files': files, 'excluded': exclusions,
                    'pinnedInputs': pinned,
                    'validation': 'not_established_by_artifact_capture'}
        return self._persist(manifest,data)

    def get(self, scope, session, artifact):
        self.store.get(scope, session)
        row = self.db.execute(f'SELECT manifest,archive FROM {self.TABLE} WHERE id=? AND session=?',
                              (artifact,session)).fetchone()
        if row is None:
            raise SessionError('Artifact is unavailable for this project and session')
        return json.loads(row['manifest']), bytes(row['archive'])

    def manifests(self,scope,session):
        self.store.get(scope,session)
        rows=self.db.execute(f'SELECT manifest FROM {self.TABLE} WHERE session=? ORDER BY rowid DESC LIMIT 20',(session,)).fetchall()
        return [json.loads(row['manifest']) for row in rows]

    def contains(self,scope,session,artifact):
        self.store.get(scope,session)
        return self.db.execute(f'SELECT 1 FROM {self.TABLE} WHERE id=? AND session=?',(artifact,session)).fetchone() is not None


class WorkingCheckpoints(EngineeringArtifacts):
    """Internal check inputs only; never listed/downloaded as delivery artifacts."""
    TABLE='engineering_checkpoints'
    KIND='working_checkpoint'

    def _require_state(self,row):
        if row['state']!='running' or not row['run'] or not row['turn']:
            raise SessionError('A working checkpoint requires a confirmed active engineering turn')

    def capture(self,scope,session,workspace,*,expected_inputs=None):
        if not expected_inputs:raise SessionError('Working checkpoints require pinned original engineering inputs')
        return super().capture(scope,session,workspace,expected_inputs=expected_inputs)

    def _persist(self,manifest,data):
        rows=self.db.execute(f'SELECT manifest FROM {self.TABLE} WHERE session=? AND run=?',(manifest['sessionId'],manifest['runId'])).fetchall()
        previous=[json.loads(row['manifest']) for row in rows]
        for row in previous:
            if row['sha256']==manifest['sha256']:return row
        if len(previous)>=16 or sum(row['bytes'] for row in previous)+len(data)>128_000_000:
            raise SessionError('This run reached its bounded working-checkpoint storage limit')
        return super()._persist(manifest,data)


class CheckSources:
    """Validator-side resolver; delivery HTTP endpoints keep the delivery store."""
    def __init__(self,*sources):self.sources=sources
    def contains(self,scope,session,artifact):return any(source.contains(scope,session,artifact) for source in self.sources)
    def get(self,scope,session,artifact):
        for source in self.sources:
            if source.contains(scope,session,artifact):return source.get(scope,session,artifact)
        raise SessionError('Check source is unavailable for this project and session')
