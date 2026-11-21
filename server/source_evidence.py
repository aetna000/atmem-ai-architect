"""Project-scoped immutable source figures, outside browser files and agent writes.

The source digest binds the upload. Image receipts prove byte delivery, not interpretation.
Authorization supplies ProjectScope; callers cannot select storage or tenant identities.
"""
import base64
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from .engineering_sessions import ProjectScope, SessionError
from .source_figures import MAX_IMAGE_BYTES, MAX_FIGURES, MAX_FIGURE_BYTES

MAX_PROJECT_BYTES = 128 * 1024 * 1024
MAX_SOURCES = 64


@dataclass(frozen=True)
class SourceImage:
    metadata: dict
    content: bytes


class SourceEvidence:
    def __init__(self, database):
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self._db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS source_figure_sets (
                tenant TEXT NOT NULL, project TEXT NOT NULL, source TEXT NOT NULL, manifest TEXT NOT NULL,
                PRIMARY KEY(tenant,project,source))''')
            db.execute('''CREATE TABLE IF NOT EXISTS source_figures (
                tenant TEXT NOT NULL, project TEXT NOT NULL, source TEXT NOT NULL, id TEXT NOT NULL,
                sha256 TEXT NOT NULL, content BLOB NOT NULL, PRIMARY KEY(tenant,project,source,id))''')

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _scope(scope, source):
        if not isinstance(scope, ProjectScope) or not isinstance(source, str) or not re.fullmatch('[a-f0-9]{64}', source):
            raise ValueError('A bound project scope and source digest are required.')

    def retain(self, scope, source, figures):
        self._scope(scope, source)
        if not isinstance(figures, list) or len(figures) > MAX_FIGURES:
            raise ValueError('Figure evidence exceeds its explicit count bound.')
        metadata, contents, ids = [], [], set()
        for row in figures:
            row = dict(row)
            ident = row.get('id')
            if not isinstance(ident, str) or not re.fullmatch(r'figure-[1-9][0-9]*', ident) or ident in ids:
                raise ValueError('Figure identifiers must be unique and source-local.')
            ids.add(ident)
            data = row.pop('data', None)
            if row.get('status') == 'available':
                content = base64.b64decode(data, validate=True)
                if not 0 < len(content) <= MAX_IMAGE_BYTES or len(content) != row.get('bytes') or hashlib.sha256(content).hexdigest() != row.get('sha256') or row.get('mime') != 'image/png':
                    raise ValueError('Source figure does not match its receipt.')
                contents.append((scope.tenant, scope.project, source, ident, row['sha256'], content))
            elif data is not None:
                raise ValueError('Unavailable figures cannot include image bytes.')
            metadata.append(row)
        if sum(len(row[-1]) for row in contents) > MAX_FIGURE_BYTES:
            raise ValueError('Source figures exceed their byte bound.')
        manifest = json.dumps(metadata, sort_keys=True, ensure_ascii=False, allow_nan=False)
        if len(manifest.encode()) > 100_000:
            raise ValueError('Source figure metadata exceeds its bound.')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT manifest FROM source_figure_sets WHERE tenant=? AND project=? AND source=?', (scope.tenant, scope.project, source)).fetchone()
            if previous:
                if previous['manifest'] != manifest:
                    raise SessionError('An existing source digest has different figure evidence. Original evidence was preserved.')
            else:
                count = db.execute('SELECT count(*) FROM source_figure_sets WHERE tenant=? AND project=?', (scope.tenant, scope.project)).fetchone()[0]
                used = db.execute('SELECT coalesce(sum(length(content)),0) FROM source_figures WHERE tenant=? AND project=?', (scope.tenant, scope.project)).fetchone()[0]
                if count >= MAX_SOURCES or used + sum(len(row[-1]) for row in contents) > MAX_PROJECT_BYTES:
                    raise ValueError('Project source evidence reached its storage limit. No original evidence was removed.')
                db.execute('INSERT INTO source_figure_sets VALUES (?,?,?,?)', (scope.tenant, scope.project, source, manifest))
                db.executemany('INSERT INTO source_figures VALUES (?,?,?,?,?,?)', contents)
        return {'version': 1, 'figures': metadata, 'manifestSha256': hashlib.sha256(manifest.encode()).hexdigest()}

    def catalog(self, scope, source):
        self._scope(scope, source)
        with self._db() as db:
            row = db.execute('SELECT manifest FROM source_figure_sets WHERE tenant=? AND project=? AND source=?', (scope.tenant, scope.project, source)).fetchone()
        if row is None:
            raise SessionError('Source figure evidence is unavailable in this project. Upload the original document here.')
        manifest = row['manifest']
        return {'version': 1, 'figures': json.loads(manifest), 'manifestSha256': hashlib.sha256(manifest.encode()).hexdigest()}

    def image(self, scope, source, ident, expected_manifest):
        catalog = self.catalog(scope, source)
        if catalog['manifestSha256'] != expected_manifest:
            raise SessionError('Source figure manifest changed from the submitted context.')
        figure = next((row for row in catalog['figures'] if row['id'] == ident), None)
        if not figure or figure['status'] != 'available':
            raise SessionError('This figure cannot be inspected as an image. Its unavailability remains recorded.')
        with self._db() as db:
            row = db.execute('SELECT sha256,content FROM source_figures WHERE tenant=? AND project=? AND source=? AND id=?', (scope.tenant, scope.project, source, ident)).fetchone()
        if row is None:
            raise SessionError('The retained source figure is missing.')
        content = bytes(row['content'])
        if not 0 < len(content) <= MAX_IMAGE_BYTES or hashlib.sha256(content).hexdigest() != row['sha256'] or row['sha256'] != figure['sha256']:
            raise SessionError('Retained source figure integrity check failed.')
        return SourceImage({'sourceSha256': source, 'manifestSha256': expected_manifest, **figure,
                            'boundary': 'Exact normalized image evidence. Delivery does not prove architectural interpretation.'}, content)
