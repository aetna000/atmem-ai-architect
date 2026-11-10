"""Trusted Azure transfer stages; the untrusted parser never runs in this image."""
import json
import os
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from enterprise_azure_objects import AzureDocumentObjects, etag
from enterprise_document_contract import MAX_INPUT, MEDIA_TYPES, media_type
from enterprise_document_job import MAX_ENVELOPE, read_file, request, result, unique
from enterprise_sources import SourceUnavailable


def metadata(encoded):
    if not isinstance(encoded, str) or not 0 < len(encoded.encode()) <= 4096:
        raise ValueError('Use bounded owned transfer metadata')
    value = json.loads(encoded, object_pairs_hook=unique)
    fields = {'format', 'subscriptionId', 'region', 'resourceGroup', 'storageAccount',
              'container', 'transferClientId', 'request', 'inputETag'}
    if not isinstance(value, dict) or set(value) != fields or value['format'] != 'enterprise-azure-document-transfer-v1':
        raise ValueError('Use the exact Azure document transfer metadata')
    # Constructing the native destination validates every identifier without
    # acquiring a token or making an HTTP call. Close the unstarted session.
    objects = document_objects(value)
    objects.close()
    expected = value['request']
    if (not isinstance(expected, dict) or set(expected) != {'format', 'requestId', 'sha256', 'mediaType'} or
            expected['format'] != 'enterprise-document-job-v1' or
            not isinstance(expected['requestId'], str) or not re.fullmatch('[0-9a-f]{64}', expected['requestId']) or
            not isinstance(expected['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', expected['sha256']) or
            media_type(expected['mediaType']) != expected['mediaType'] or
            expected['mediaType'] not in MEDIA_TYPES | {'application/octet-stream'}):
        raise ValueError('Use the exact supported byte-bound request')
    try: etag(value['inputETag'])
    except SourceUnavailable: raise ValueError('Use the acknowledged native input ETag') from None
    return value


def document_objects(value):
    return AzureDocumentObjects(subscription=value['subscriptionId'], resource_group=value['resourceGroup'],
        region=value['region'], account=value['storageAccount'], container=value['container'], client_id=value['transferClientId'])


def directories(input_path, output_path):
    source = target = None
    try:
        source = os.open(input_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        target = os.open(output_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        left, right = os.fstat(source), os.fstat(target)
        if (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino):
            raise ValueError('Use distinct per-file volumes')
        return source, target
    except BaseException:
        for fd in [target, source]:
            if fd is not None: os.close(fd)
        raise


def download(value, objects, input_path='/input', output_path='/output'):
    source, target = directories(input_path, output_path)
    try:
        if os.listdir(source) or os.listdir(target):
            raise ValueError('Use fresh per-file volumes')
        expected = value['request']
        identifier = expected['requestId']
        raw = objects.load(identifier, 'input', value['inputETag'])
        if request(raw, expected['mediaType'], identifier) != expected:
            raise ValueError('Input bytes changed')
        for name, data in [('document', raw), ('request.json', json.dumps(expected, separators=(',', ':')).encode())]:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444, dir_fd=source)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
                os.fchmod(stream.fileno(), 0o444)
        # Batch maps a native non-admin UID. Fresh isolated output is writable
        # by that UID; only its parser and the trusted collector receive mounts.
        os.fchmod(source, 0o555)
        os.fchmod(target, 0o777)
        os.fsync(source)
        os.fsync(target)
    finally:
        os.close(target)
        os.close(source)


def upload(value, objects, input_path='/input', output_path='/output'):
    source, target = directories(input_path, output_path)
    try:
        expected = value['request']
        identifier = expected['requestId']
        raw = read_file(source, 'document', MAX_INPUT)
        if request(raw, expected['mediaType'], identifier) != expected:
            raise ValueError('Input binding changed')
        encoded = read_file(target, 'result.json', MAX_ENVELOPE)
        result(raw, expected['mediaType'], identifier, encoded)
        objects.put(identifier, 'result', encoded)
    finally:
        os.close(target)
        os.close(source)


def main():
    objects = None
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in {'download', 'upload'}:
            raise ValueError('Use the fixed Azure transfer stage')
        value = metadata(os.environ.get('DOCUMENT_JOB', ''))
        objects = document_objects(value)
        if sys.argv[1] == 'download': download(value, objects)
        else: upload(value, objects)
    except Exception:
        raise SystemExit('Owned Azure document transfer could not complete.') from None
    finally:
        if objects is not None: objects.close()


if __name__ == '__main__':
    main()
