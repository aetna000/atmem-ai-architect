"""Durable single-VM transaction adapter. No process-local concurrency guarantee."""
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from .credits import Conflict


class SQLiteTransactions:
    def __init__(self, path):
        self.path = Path(path).absolute()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        parent = self.path.parent.lstat()
        if stat.S_ISLNK(parent.st_mode) or parent.st_uid != os.getuid() or parent.st_mode & 0o077:
            raise ValueError('Database directory must be private and owned by the service user')
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError('Database must be a private regular file owned by the service user')
        finally: os.close(fd)
        connection=sqlite3.connect(self.path)
        try:
            connection.execute('PRAGMA journal_mode=WAL')
            connection.execute('CREATE TABLE IF NOT EXISTS records (collection TEXT NOT NULL, key TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(collection,key))')
            connection.commit()
        finally:connection.close()

    def transaction(self, callback):
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        try:
            connection.execute('PRAGMA synchronous=FULL')
            connection.execute('BEGIN IMMEDIATE')
            result = callback(_Transaction(connection))
            connection.commit()
            return result
        except BaseException:
            connection.rollback(); raise
        finally: connection.close()


class _Transaction:
    def __init__(self, connection): self.connection = connection

    @staticmethod
    def _path(collection, key):
        if not re.fullmatch('[a-z][a-z0-9_]{1,40}',collection) or not re.fullmatch('[a-z0-9_-]{1,200}',key):
            raise ValueError('Unrecognized internal record path')
        return collection,key

    def get(self, collection, key):
        row = self.connection.execute('SELECT body FROM records WHERE collection=? AND key=?',self._path(collection,key)).fetchone()
        return json.loads(row[0]) if row else None

    def set(self, collection, key, value):
        self.connection.execute('INSERT INTO records VALUES (?,?,?) ON CONFLICT(collection,key) DO UPDATE SET body=excluded.body',
                                (*self._path(collection,key),json.dumps(value,allow_nan=False,separators=(',',':'))))

    def create(self, collection, key, value):
        try:self.connection.execute('INSERT INTO records VALUES (?,?,?)',(*self._path(collection,key),json.dumps(value,allow_nan=False,separators=(',',':'))))
        except sqlite3.IntegrityError as error:raise Conflict('Immutable record already exists') from error

    def delete(self, collection, key):
        self.connection.execute('DELETE FROM records WHERE collection=? AND key=?',self._path(collection,key))
