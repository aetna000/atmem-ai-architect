"""Trusted, sequential Google Batch byte transfer; never execute a document.

Only the download/upload runnables have native VM network/identity access. They
use fixed native APIs and one bounded per-file mount. The parser never runs in
this image, and no service is left listening for it.
"""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from enterprise_document_contract import MAX_INPUT
from enterprise_document_job import MAX_ENVELOPE, read_file, request, result, unique
from enterprise_google_jobs import GoogleDocumentApi, GoogleDocumentObjects, transfer_metadata


def metadata(encoded):
    if not isinstance(encoded, str) or not 0 < len(encoded.encode()) <= 4096: raise ValueError('Invalid owned transfer metadata')
    value = json.loads(encoded, object_pairs_hook=unique)
    fields = {'format', 'projectId', 'region', 'bucket', 'request', 'inputGeneration'}
    if not isinstance(value, dict) or set(value) != fields or value['format'] != 'enterprise-google-document-transfer-v1': raise ValueError('Invalid owned transfer metadata')
    import re
    for key, pattern in {'projectId': '[a-z][a-z0-9-]{4,28}[a-z0-9]', 'region': '[a-z]+-[a-z]+[1-9][0-9]?', 'bucket': '[a-z0-9][a-z0-9-]{1,61}[a-z0-9]'}.items():
        if not isinstance(value[key], str) or not re.fullmatch(pattern, value[key]): raise ValueError('Invalid owned transfer destination')
    if value != transfer_metadata(value, value['request'], value['inputGeneration']): raise ValueError('Invalid owned transfer metadata')
    return value


def directory(parent, name, *, create=False):
    if create: os.mkdir(name, 0o700, dir_fd=parent)
    return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)


def download(value, objects, mount='/work'):
    """Root/CHOWN only to prepare isolated UID10001 mounts, then this exits."""
    expected = value['request']; identifier = expected['requestId']
    raw = objects.load(identifier, 'input', value['inputGeneration'])
    if request(raw, expected['mediaType'], identifier) != expected: raise ValueError('Document input binding changed')
    root = source = target = None
    try:
        root = os.open(mount, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        # Refuse previous per-file state, even if contents appear compatible.
        source = directory(root, 'input', create=True)
        target = directory(root, 'output', create=True)
        for name, content in [('document', raw), ('request.json', json.dumps(expected, separators=(',', ':')).encode())]:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400, dir_fd=source)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content); stream.flush(); os.fsync(stream.fileno()); os.fchown(stream.fileno(), 10001, 10001)
        os.fchmod(source, 0o500); os.fchown(source, 10001, 10001); os.fchown(target, 10001, 10001)
        os.fsync(source); os.fsync(target); os.fsync(root)
    finally:
        for fd in (target, source, root):
            if fd is not None: os.close(fd)


def upload(value, objects, mount='/work'):
    root = source = target = None
    try:
        root = os.open(mount, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        source, target = directory(root, 'input'), directory(root, 'output')
        raw = read_file(source, 'document', MAX_INPUT)
        expected = value['request']
        if request(raw, expected['mediaType'], expected['requestId']) != expected: raise ValueError('Document input binding changed')
        encoded = read_file(target, 'result.json', MAX_ENVELOPE)
        result(raw, expected['mediaType'], expected['requestId'], encoded)
        objects.put(expected['requestId'], 'result', encoded)
    finally:
        for fd in (target, source, root):
            if fd is not None: os.close(fd)


def main():
    # No document content, token, upstream response or traceback enters job logs.
    try:
        if sys.argv[1:] not in [['download'], ['upload']]: raise ValueError()
        mode = sys.argv[1]
        if os.getuid() != (0 if mode == 'download' else 10001): raise ValueError()
        value = metadata(os.environ['DOCUMENT_JOB'])
        objects = GoogleDocumentObjects(value['bucket'], GoogleDocumentApi())
        (download if mode == 'download' else upload)(value, objects)
    except Exception:
        raise SystemExit(2) from None


if __name__ == '__main__': main()
