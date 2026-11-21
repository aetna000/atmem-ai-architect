"""One-file mounted job transport; never write source or result text to logs.

The launcher owns two distinct per-file mounts: read-only /input and writable
/output. This protocol is not a sandbox. Native workloads must separately remove
credentials, contain network/processes, bound resources and delete both mounts.
"""
import hashlib
import json
import os
import re
import stat
import uuid
from enterprise_document_contract import MAX_INPUT, MAX_TEXT, ExtractionError, document_result, media_type

MAX_ENVELOPE = MAX_TEXT * 6 + 4096


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value: raise ExtractionError('invalid_document')
        value[key] = item
    return value


def request(raw, declared, request_id):
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_INPUT or
        not isinstance(request_id, str) or not re.fullmatch('[0-9a-f]{64}', request_id)):
        raise ExtractionError('invalid_document')
    return {'format': 'enterprise-document-job-v1', 'requestId': request_id,
            'sha256': hashlib.sha256(raw).hexdigest(), 'mediaType': media_type(declared)}


def result(raw, declared, request_id, encoded):
    """Consumer check after the isolated job exits successfully, before caching."""
    expected = request(raw, declared, request_id)
    if not isinstance(encoded, bytes) or not 0 < len(encoded) <= MAX_ENVELOPE:
        raise ExtractionError('invalid_document')
    try:
        value = json.loads(encoded, object_pairs_hook=unique)
        if (not isinstance(value, dict) or set(value) != {'format', 'requestId', 'status', 'document'} or
            value['format'] != expected['format'] or value['requestId'] != request_id or value['status'] != 'ok'):
            raise ValueError()
        return document_result(value['document'], raw, expected['mediaType'])
    except Exception:
        raise ExtractionError('invalid_document') from None


def read_file(directory_fd, name, limit):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= limit:
            raise ExtractionError('invalid_document')
        raw = stream.read(limit + 1)
        if not 0 < len(raw) <= limit or len(raw) != info.st_size:
            raise ExtractionError('invalid_document')
        return raw


def write_result(directory_fd, value):
    # Exclusive publication refuses an old/stale output and any symlink target.
    # The launcher consumes only after successful process exit; a crashed partial
    # temporary file cannot look like a complete result.
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
    if len(encoded) > MAX_ENVELOPE: raise ExtractionError('extraction_failed')
    temporary = '.result-' + uuid.uuid4().hex
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, 'result.json', src_dir_fd=directory_fd, dst_dir_fd=directory_fd, follow_symlinks=False)
        os.fsync(directory_fd)
    finally:
        try: os.unlink(temporary, dir_fd=directory_fd)
        except FileNotFoundError: pass


def execute(parser, input_path='/input', output_path='/output'):
    """Extract one document using fixed mount paths; errors contain no input data."""
    source = target = None
    try:
        source = os.open(input_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        target = os.open(output_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        left, right = os.fstat(source), os.fstat(target)
        if (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino):
            raise ExtractionError('invalid_document')
        # Do not parse if the destination already exists (including a symlink).
        try: os.stat('result.json', dir_fd=target, follow_symlinks=False)
        except FileNotFoundError: pass
        else: raise ExtractionError('invalid_document')
        metadata = json.loads(read_file(source, 'request.json', 2048), object_pairs_hook=unique)
        raw = read_file(source, 'document', MAX_INPUT)
        if not isinstance(metadata, dict) or set(metadata) != {'format', 'requestId', 'sha256', 'mediaType'}:
            raise ExtractionError('invalid_document')
        expected = request(raw, metadata['mediaType'], metadata['requestId'])
        if metadata != expected: raise ExtractionError('invalid_document')
        document = document_result(parser.extract(raw, expected['mediaType']), raw, expected['mediaType'])
        write_result(target, {'format': expected['format'], 'requestId': expected['requestId'], 'status': 'ok', 'document': document})
        return {'status': 'ok'}, 0
    except ExtractionError as failure:
        return {'status': 'rejected', 'reason': failure.code}, 2
    except Exception:
        return {'status': 'rejected', 'reason': 'extraction_unavailable'}, 2
    finally:
        for fd in (target, source):
            if fd is not None: os.close(fd)
