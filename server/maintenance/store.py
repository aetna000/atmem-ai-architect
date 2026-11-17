"""SQLite aggregate CAS and fencing. Credentials and publication grants do not belong here."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

from .models import MigrationProject


class Conflict(ValueError):
    pass


def digest(value):
    def portable(item):
        if isinstance(item, float) and item.is_integer():
            return int(item)
        if isinstance(item, dict):
            return {key: portable(val) for key, val in item.items()}
        if isinstance(item, list):
            return [portable(val) for val in item]
        return item
    return hashlib.sha256(json.dumps(portable(value), sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.is_symlink():
            raise ValueError('Linked maintenance database denied')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Parent may be an existing product directory; do not change its permissions.
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        os.close(fd)
        os.chmod(self.path, 0o600)
        with self.transaction() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS projects (
                tenant TEXT NOT NULL, project TEXT NOT NULL, revision INTEGER NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(tenant, project));
              CREATE TABLE IF NOT EXISTS leases (
                tenant TEXT NOT NULL, project TEXT NOT NULL, epoch INTEGER NOT NULL,
                owner TEXT NOT NULL, expires REAL NOT NULL, PRIMARY KEY(tenant, project));
              CREATE TABLE IF NOT EXISTS audit (
                seq INTEGER PRIMARY KEY, tenant TEXT NOT NULL, project TEXT NOT NULL,
                kind TEXT NOT NULL, revision INTEGER NOT NULL, at REAL NOT NULL);
            ''')

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA busy_timeout=10000')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _load(db, tenant, project):
        row = db.execute('SELECT payload FROM projects WHERE tenant=? AND project=?', (tenant, project)).fetchone()
        if row is None:
            raise KeyError('Maintenance project unavailable')
        return MigrationProject.model_validate_json(row['payload'])

    def get(self, tenant, project):
        with self.transaction() as db:
            return self._load(db, tenant, project)

    def create(self, project):
        project = MigrationProject.model_validate(project.model_dump())
        if len(project.model_dump_json().encode()) > 64_000_000:
            raise ValueError('Maintenance aggregate exceeds 64 MB; no content was truncated')
        if project.revision != 0:
            raise Conflict('New aggregate requires revision zero')
        with self.transaction() as db:
            try:
                db.execute('INSERT INTO projects VALUES(?,?,?,?)',
                           (project.tenantId, project.projectId, 0, project.model_dump_json()))
            except sqlite3.IntegrityError:
                raise Conflict('Project already exists') from None
            self._audit(db, project, 'created')
        return project

    def save(self, project, expected_revision, *, lease=None):
        project = MigrationProject.model_validate(project.model_dump())
        if len(project.model_dump_json().encode()) > 64_000_000:
            raise ValueError('Maintenance aggregate exceeds 64 MB; no content was truncated')
        with self.transaction() as db:
            if lease is not None:
                owner, epoch = lease
                live = db.execute('SELECT * FROM leases WHERE tenant=? AND project=?',
                                  (project.tenantId, project.projectId)).fetchone()
                if live is None or live['owner'] != owner or live['epoch'] != epoch or live['expires'] <= time.time():
                    raise Conflict('Executor lease expired or fenced')
            # All writes use CAS, including cancellation and status updates.
            project.revision = expected_revision + 1
            result = db.execute('UPDATE projects SET revision=?,payload=? WHERE tenant=? AND project=? AND revision=?',
                                (project.revision, project.model_dump_json(), project.tenantId, project.projectId, expected_revision))
            if result.rowcount != 1:
                raise Conflict('Project changed; reload before continuing')
            self._audit(db, project, 'updated')
        return project

    def acquire(self, tenant, project, owner, seconds=30):
        if type(seconds) is not int or not 1 <= seconds <= 1200:
            raise ValueError('Lease duration exceeds bounds')
        with self.transaction() as db:
            self._load(db, tenant, project)
            row = db.execute('SELECT * FROM leases WHERE tenant=? AND project=?', (tenant, project)).fetchone()
            if row and row['expires'] > time.time():
                raise Conflict('Another executor owns this project')
            epoch = row['epoch'] + 1 if row else 1
            db.execute('INSERT OR REPLACE INTO leases VALUES(?,?,?,?,?)',
                       (tenant, project, epoch, owner, time.time() + seconds))
            return epoch

    def fence(self, tenant, project):
        with self.transaction() as db:
            self._load(db, tenant, project)
            db.execute('UPDATE leases SET epoch=epoch+1, expires=0 WHERE tenant=? AND project=?', (tenant, project))

    def release(self, tenant, project, owner, epoch):
        with self.transaction() as db:
            db.execute('UPDATE leases SET expires=0 WHERE tenant=? AND project=? AND owner=? AND epoch=?',
                       (tenant, project, owner, epoch))

    def delete(self, tenant, project):
        with self.transaction() as db:
            self._load(db, tenant, project)
            db.execute('DELETE FROM projects WHERE tenant=? AND project=?', (tenant, project))
            db.execute('UPDATE leases SET epoch=epoch+1,expires=0 WHERE tenant=? AND project=?', (tenant, project))
            db.execute('DELETE FROM audit WHERE tenant=? AND project=?', (tenant, project))

    @staticmethod
    def _audit(db, project, kind):
        db.execute('INSERT INTO audit(tenant,project,kind,revision,at) VALUES(?,?,?,?,?)',
                   (project.tenantId, project.projectId, kind, project.revision, time.time()))
