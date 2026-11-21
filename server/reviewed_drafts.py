"""Read original reviewed draft bytes from owned immutable captures without a model.

This is a local read-only adapter. Hosted adapters must supply authenticated scope
and equivalent artifact/context custody; browser claims never supply tenancy/paths.
"""
from dataclasses import dataclass
from contextlib import closing
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import stat
import zipfile
import zlib
from .engineering_sessions import ProjectScope, SessionError
from .engineering_contexts import MAX_CONTEXT_BYTES, validate_context

MAX_ARCHIVE_BYTES=64_000_000
MAX_CANVAS_BYTES=2_000_000
MAX_REVIEW_BYTES=250_000
SHA=re.compile(r'[a-f0-9]{64}')

@dataclass(frozen=True)
class ReviewedDraft:
    content: bytes
    receipt: dict

class LocalReviewedDrafts:
    def __init__(self,database):self.path=Path(database)

    def read(self,scope,artifact_id,draft_sha256,context_sha256):
        if not isinstance(scope,ProjectScope) or not isinstance(artifact_id,str) or not re.fullmatch(r'[a-f0-9-]{36}',artifact_id) or any(not isinstance(value,str) or not SHA.fullmatch(value)for value in [draft_sha256,context_sha256]):
            raise ValueError('An owned artifact and exact draft/context digests are required.')
        if not self.path.is_file() or self.path.is_symlink():raise SessionError('Reviewed draft is unavailable in this project.')
        try:
            # No schema initialization, model worker, native thread or live workspace.
            with closing(sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
                db.row_factory=sqlite3.Row;db.execute('BEGIN')
                row=db.execute('''SELECT a.id,a.session,a.run,a.manifest,length(a.archive) AS size
                    FROM engineering_artifacts a JOIN engineering_sessions s ON s.id=a.session
                    JOIN engineering_runs r ON r.id=a.run AND r.session=a.session AND r.status='completed'
                    WHERE a.id=? AND s.tenant=? AND s.project=?''',(artifact_id,scope.tenant,scope.project)).fetchone()
                if row is None:raise SessionError('Reviewed draft is unavailable in this project.')
                manifest=json.loads(row['manifest'])
                if not isinstance(manifest,dict)or not isinstance(manifest.get('files'),list)or len(manifest['files'])>2000:raise SessionError('Reviewed draft capture receipt is invalid.')
                if manifest.get('id')!=artifact_id or manifest.get('sessionId')!=row['session'] or manifest.get('runId')!=row['run'] or manifest.get('kind')!='delivery' or manifest.get('turnStatus')!='completed':
                    raise SessionError('A completed owned capture is required for reviewed draft evidence.')
                if not 0<row['size']<=MAX_ARCHIVE_BYTES or manifest.get('bytes')!=row['size']:raise SessionError('Reviewed draft archive exceeds its bound or receipt.')
                context=db.execute('''SELECT c.id,c.sha256,length(c.content) AS size
                    FROM engineering_context_submissions r JOIN engineering_contexts c ON c.id=r.context AND c.session=r.session
                    WHERE r.request=? AND r.session=?''',(row['run'],row['session'])).fetchone()
                if context is None or not 0<context['size']<=MAX_CONTEXT_BYTES:raise SessionError('Submitted context evidence is unavailable.')
                context_bytes=bytes(db.execute('SELECT content FROM engineering_contexts WHERE id=?',(context['id'],)).fetchone()[0])
                if context['sha256']!=context_sha256 or hashlib.sha256(context_bytes).hexdigest()!=context_sha256:raise SessionError('Submitted context digest does not match the reviewed draft.')
                validate_context(context_bytes,scope.project)
                archive=bytes(db.execute('SELECT archive FROM engineering_artifacts WHERE id=?',(artifact_id,)).fetchone()[0])
            if hashlib.sha256(archive).hexdigest()!=manifest.get('sha256'):raise SessionError('Reviewed draft archive integrity check failed.')
            with zipfile.ZipFile(io.BytesIO(archive)) as package:
                def member(name,limit):
                    entries=[item for item in package.infolist()if item.filename==name]
                    records=[item for item in manifest['files']if isinstance(item,dict)and item.get('path')==name]
                    if len(entries)!=1 or len(records)!=1:raise SessionError('Reviewed draft has missing or ambiguous captured files.')
                    entry,record=entries[0],records[0]
                    if record.get('kind')!='file' or not 0<entry.file_size<=limit or record.get('bytes')!=entry.file_size or stat.S_IFMT(entry.external_attr>>16)not in (0,stat.S_IFREG):raise SessionError('Reviewed draft file exceeds its bound or receipt.')
                    content=package.read(entry)
                    if len(content)!=entry.file_size or hashlib.sha256(content).hexdigest()!=record.get('sha256'):raise SessionError('Reviewed draft file integrity check failed.')
                    return content
                content=member('architecture.canvas.json',MAX_CANVAS_BYTES)
                review=member('architecture.review.md',MAX_REVIEW_BYTES)
            if hashlib.sha256(content).hexdigest()!=draft_sha256:raise SessionError('Reviewed draft digest does not match the captured bytes.')
            value=json.loads(content.decode('utf-8'),parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite JSON')))
            if not isinstance(value,dict)or isinstance(value.get('version'),bool)or value.get('version')!=1:raise SessionError('Captured draft is not a supported JSON proposal.')
            if f'Draft SHA-256: {draft_sha256}'not in review.decode('utf-8').replace('\r\n','\n').split('\n'):raise SessionError('The capture has no exact review seal for this draft.')
            return ReviewedDraft(content,{'artifactId':artifact_id,'artifactSha256':manifest['sha256'],'draftSha256':draft_sha256,'contextSha256':context_sha256,'bytes':len(content),'reviewSha256':hashlib.sha256(review).hexdigest(),
                'boundary':'Exact original captured proposal and review seal; not approval of later edits, implementation or deployment.'})
        except SessionError:raise
        except (OSError,sqlite3.Error,ValueError,KeyError,TypeError,zipfile.BadZipFile,zlib.error,RuntimeError):
            raise SessionError('Reviewed draft evidence is unavailable or failed integrity checks.')from None
