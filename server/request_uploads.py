"""Bounded, temporary, ordered request assembly. Uploaded content is never executed."""
import hashlib
import secrets
import tempfile
import threading
import time

MAX_BYTES = 64 * 1024 * 1024
CHUNK_BYTES = 128 * 1024


class RequestUploads:
    def __init__(self):
        self.rows = {}
        self.lock = threading.Lock()

    def _expire(self):
        for key, row in list(self.rows.items()):
            if time.monotonic() - row['updated'] > 1800:
                self.rows.pop(key)['file'].close()

    def start(self, size, digest):
        with self.lock:
            self._expire()
            if not 0 < size <= MAX_BYTES:
                raise ValueError('Request exceeds the 64 MiB upload limit.')
            if len(self.rows) >= 8 or sum(r['size'] for r in self.rows.values()) + size > 2 * MAX_BYTES:
                raise ValueError('Upload capacity is busy. Retry after current uploads finish.')
            key = secrets.token_hex(24)
            self.rows[key] = dict(file=tempfile.TemporaryFile(), size=size, digest=digest,
                                  received=0, index=0, updated=time.monotonic())
            return {'uploadId': key, 'chunkBytes': CHUNK_BYTES}

    def append(self, key, index, content):
        with self.lock:
            self._expire()
            row = self.rows.get(key)
            if row is None:
                raise ValueError('Upload expired. Start validation again.')
            if index != row['index'] or not 0 < len(content) <= CHUNK_BYTES or row['received'] + len(content) > row['size']:
                raise ValueError('Upload chunk is out of order or exceeds its declared size.')
            row['file'].write(content)
            row.update(received=row['received'] + len(content), index=index + 1, updated=time.monotonic())
            return {'receivedBytes': row['received']}

    def take(self, key):
        with self.lock:
            self._expire()
            row = self.rows.pop(key, None)
            if row is None:
                raise ValueError('Upload expired. Start validation again.')
            try:
                row['file'].seek(0)
                data = row['file'].read()
                if len(data) != row['size'] or hashlib.sha256(data).hexdigest() != row['digest']:
                    raise ValueError('Upload is incomplete or its checksum changed. Retry validation.')
                return data
            finally:
                row['file'].close()

    def cancel(self, key):
        with self.lock:
            row = self.rows.pop(key, None)
            if row:
                row['file'].close()
