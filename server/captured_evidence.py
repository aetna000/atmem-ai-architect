"""Owned capture export without model workers or caller-selected filesystem paths.

Local adapter only. Hosted adapters need their own authenticated scope and storage.
No captured code or repository instructions are executed by this reader.
"""
from contextlib import closing
from dataclasses import dataclass
import hashlib
import io
import json
import os
import re
from pathlib import Path
import sqlite3
import stat
import zipfile
import zlib
from .engineering_sessions import SessionError
from .engineering_contexts import MAX_CONTEXT_BYTES, validate_context
from .reviewed_drafts import LocalReviewedDrafts, MAX_ARCHIVE_BYTES

MAX_FILES=2000


def retain_initial_input(store, scope, session, content):
    """Persist exact input outside the model-writable workspace, once per session."""
    store.get(scope,session)
    # Initial inputs predate the canonical saved-context schema in some sessions.
    # Keep the existing create contract: custody binds opaque bytes to the owned
    # session, not a reinterpretation as current canonical project requirements.
    if not isinstance(content,bytes) or not 0<len(content)<=MAX_CONTEXT_BYTES:
        raise ValueError('Initial input exceeds its explicit byte bound.')
    digest=hashlib.sha256(content).hexdigest()
    with store.db:
        store.db.execute('''CREATE TABLE IF NOT EXISTS engineering_initial_inputs (
            session TEXT PRIMARY KEY, sha256 TEXT NOT NULL, content BLOB NOT NULL)''')
        existing=store.db.execute('SELECT sha256,content FROM engineering_initial_inputs WHERE session=?',(session,)).fetchone()
        if existing:
            if existing['sha256']!=digest or bytes(existing['content'])!=content:
                raise SessionError('The retained initial input cannot be replaced.')
        else:
            store.db.execute('INSERT INTO engineering_initial_inputs VALUES (?,?,?)',(session,digest,content))
    return digest


def safe(name,directory=False):
    value=name[:-1] if directory and name.endswith('/') else name
    return (isinstance(value,str) and 0<len(value)<=500 and not any(ord(c)<32 or ord(c)==127 for c in value)
            and not any(c in value for c in '\\:') and all(part not in {'','.','..'} for part in value.split('/')))


def _legacy_input(workspace):
    # Workspace path comes only from an owned server registration. Never a browser
    # path, never a path named by source text, never an arbitrary file within it.
    flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK
    root=os.open(workspace,flags|os.O_DIRECTORY)
    try:
        descriptor=os.open('project-context.json',flags,dir_fd=root)
        try:
            before=os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or not 0<before.st_size<=MAX_CONTEXT_BYTES:
                raise SessionError('Historical initial input is unsafe or exceeds its bound.')
            chunks=[];total=0
            while True:
                chunk=os.read(descriptor,min(1_000_000,MAX_CONTEXT_BYTES-total+1))
                if not chunk:break
                chunks.append(chunk);total+=len(chunk)
                if total>MAX_CONTEXT_BYTES:raise SessionError('Historical initial input exceeds its bound.')
            after=os.fstat(descriptor)
            identity=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
            if identity(before)!=identity(after) or total!=before.st_size:raise SessionError('Historical initial input changed during retrieval.')
            return b''.join(chunks)
        finally:os.close(descriptor)
    finally:os.close(root)


@dataclass(frozen=True)
class CapturedEvidence:
    content:bytes
    receipt:dict


class LocalCapturedEvidence:
    def __init__(self,database):self.path=Path(database)

    def read(self,scope,artifact_id,draft_sha256,context_sha256):
        # Existing reader proves completed owned capture, submitted context, exact
        # draft and review seal. Re-read pins below so corruption/races fail closed.
        reviewed=LocalReviewedDrafts(self.path).read(scope,artifact_id,draft_sha256,context_sha256)
        try:
            with closing(sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
                db.row_factory=sqlite3.Row;db.execute('BEGIN')
                row=db.execute('''SELECT a.manifest,length(a.archive) AS size,a.session,a.run,s.workspace
                    FROM engineering_artifacts a JOIN engineering_sessions s ON s.id=a.session
                    JOIN engineering_runs r ON r.id=a.run AND r.session=s.id AND r.status='completed'
                    WHERE a.id=? AND s.tenant=? AND s.project=?''',(artifact_id,scope.tenant,scope.project)).fetchone()
                if row is None or not 0<row['size']<=MAX_ARCHIVE_BYTES:raise SessionError('Captured evidence is unavailable in this project.')
                manifest=json.loads(row['manifest'])
                if manifest.get('sha256')!=reviewed.receipt['artifactSha256'] or manifest.get('bytes')!=row['size'] or manifest.get('id')!=artifact_id or manifest.get('sessionId')!=row['session'] or manifest.get('runId')!=row['run'] or manifest.get('kind')!='delivery' or manifest.get('turnStatus')!='completed':
                    raise SessionError('Captured evidence identity changed during retrieval.')
                context=db.execute('''SELECT c.sha256,length(c.content) AS size,c.id FROM engineering_context_submissions r
                    JOIN engineering_contexts c ON c.id=r.context AND c.session=r.session
                    WHERE r.request=? AND r.session=?''',(row['run'],row['session'])).fetchone()
                if context is None or not 0<context['size']<=MAX_CONTEXT_BYTES or context['sha256']!=context_sha256:raise SessionError('Submitted capture context is unavailable.')
                submitted=bytes(db.execute('SELECT content FROM engineering_contexts WHERE id=?',(context['id'],)).fetchone()[0])
                if hashlib.sha256(submitted).hexdigest()!=context_sha256:raise SessionError('Submitted capture context digest failed.')
                validate_context(submitted,scope.project)
                event=db.execute('SELECT payload FROM engineering_events WHERE session=? ORDER BY sequence LIMIT 1',(row['session'],)).fetchone()
                if event is None:raise SessionError('Historical initial input receipt is unavailable.')
                initial_event=json.loads(event['payload'])
                pin=initial_event.get('inputDigests',{}).get('project-context.json',initial_event.get('contextSha256'))
                if initial_event.get('kind')!='created' or not isinstance(pin,str) or not re.fullmatch(r'[a-f0-9]{64}',pin) or pin!=initial_event.get('contextSha256'):
                    raise SessionError('Historical initial input pin is unavailable or inconsistent.')
                retained=None
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='engineering_initial_inputs'").fetchone():
                    retained=db.execute('SELECT sha256,length(content) AS size FROM engineering_initial_inputs WHERE session=?',(row['session'],)).fetchone()
                if retained is not None:
                    if retained['sha256']!=pin or not 0<retained['size']<=MAX_CONTEXT_BYTES:raise SessionError('Retained initial input receipt failed.')
                    initial=bytes(db.execute('SELECT content FROM engineering_initial_inputs WHERE session=?',(row['session'],)).fetchone()[0]);origin='retained_control_store'
                else:
                    workspace=db.execute('SELECT path FROM engineering_workspaces WHERE id=? AND tenant=? AND project=?',(row['workspace'],scope.tenant,scope.project)).fetchone()
                    if workspace is None:raise SessionError('Historical initial input is unavailable.')
                    initial=_legacy_input(workspace['path']);origin='legacy_registered_workspace_with_creation_pin'
                if hashlib.sha256(initial).hexdigest()!=pin:raise SessionError('Historical initial input digest failed.')
                archive=bytes(db.execute('SELECT archive FROM engineering_artifacts WHERE id=?',(artifact_id,)).fetchone()[0])
            if hashlib.sha256(archive).hexdigest()!=manifest['sha256']:raise SessionError('Captured archive digest failed.')
            records=manifest.get('files')
            if not isinstance(records,list) or len(records)>MAX_FILES:raise SessionError('Captured file inventory exceeds its bound.')
            expected={};known=set()
            for record in records:
                name=record.get('path');directory=record.get('kind')=='directory'
                if record.get('kind') not in {'file','directory'} or not safe(name,directory) or name.rstrip('/').lower() in known:raise SessionError('Captured file inventory is unsafe or ambiguous.')
                known.add(name.rstrip('/').lower());expected[name]=record
            with zipfile.ZipFile(io.BytesIO(archive)) as package:
                entries=package.infolist();seen=set();expanded=0
                if len(entries)>MAX_FILES:raise SessionError('Captured archive entry bound exceeded.')
                for entry in entries:
                    name=entry.filename;record=expected.get(name)
                    if name in seen or record is None or entry.is_dir()!=(record['kind']=='directory'):raise SessionError('Captured archive inventory mismatch.')
                    seen.add(name);expanded+=entry.file_size
                    if expanded>MAX_ARCHIVE_BYTES:raise SessionError('Captured archive expansion bound exceeded.')
                    mode=stat.S_IFMT(entry.external_attr>>16)
                    if mode not in ((0,stat.S_IFDIR) if entry.is_dir() else (0,stat.S_IFREG)):raise SessionError('Captured archive contains a special file.')
                    if entry.is_dir():
                        if entry.file_size:raise SessionError('Captured directory has unexpected content.')
                    else:
                        if type(record.get('bytes')) is not int or entry.file_size!=record['bytes']:raise SessionError('Captured file length receipt failed.')
                        body=package.read(entry)
                        if len(body)!=record['bytes'] or hashlib.sha256(body).hexdigest()!=record.get('sha256'):raise SessionError('Captured file digest failed.')
                if seen!=set(expected):raise SessionError('Captured archive is missing inventory files.')
                if package.read('architecture.canvas.json')!=reviewed.content:raise SessionError('Captured draft changed during retrieval.')
                review=package.read('architecture.review.md')
                if hashlib.sha256(review).hexdigest()!=reviewed.receipt['reviewSha256']:raise SessionError('Captured review changed during retrieval.')
            initial_receipt={'projectId':scope.project,'sessionId':row['session'],'sha256':pin,'bytes':len(initial),'source':origin,
                'boundary':'Exact historical initial context, not the current design or the submitted refinement context.'}
            payloads={'capture.zip':archive,'capture-manifest.json':json.dumps(manifest).encode(),'submitted-context.json':submitted,
                'initial-context.json':initial,'initial-context-receipt.json':json.dumps(initial_receipt).encode()}
            if sum(map(len,payloads.values()))>MAX_ARCHIVE_BYTES:raise SessionError('Captured evidence bundle exceeds its byte bound.')
            output=io.BytesIO()
            with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as package:
                for name,body in payloads.items():package.writestr(name,body)
            content=output.getvalue()
            if len(content)>MAX_ARCHIVE_BYTES:raise SessionError('Captured evidence transport exceeds its byte bound.')
            return CapturedEvidence(content,{**reviewed.receipt,'bundleSha256':hashlib.sha256(content).hexdigest(),'bundleBytes':len(content),'initialContextSha256':pin,
                'boundary':'Capture and input byte custody only; no code execution, semantic approval or deployment.'})
        except SessionError:raise
        except (OSError,sqlite3.Error,ValueError,KeyError,TypeError,AttributeError,zipfile.BadZipFile,zlib.error,RuntimeError):
            raise SessionError('Captured evidence is unavailable or failed integrity checks.')from None
