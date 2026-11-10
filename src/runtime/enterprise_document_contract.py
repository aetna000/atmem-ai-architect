"""Byte-bound document protocol shared by app/cache and isolated parser.

Standard-library validation only: no subprocess, native parser, URL or secrets.
"""
import hashlib
import re

MAX_INPUT = 10000000
MAX_TEXT = 200000
MEDIA_TYPES = frozenset({'application/pdf', 'text/plain', 'text/html', 'application/rtf',
    'application/msword', 'application/vnd.ms-excel', 'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.oasis.opendocument.text', 'application/vnd.oasis.opendocument.spreadsheet',
    'application/vnd.oasis.opendocument.presentation'})


class ExtractionError(ValueError):
    def __init__(self, code):
        if code not in {'document_too_large', 'invalid_document', 'unsupported_format',
                        'extraction_failed', 'extraction_timeout', 'extraction_unavailable', 'mime_mismatch'}:
            raise ValueError('Unknown extraction failure')
        self.code = code
        super().__init__(code)


def media_type(value):
    if not isinstance(value, str) or len(value) > 200 or any(ord(c) < 32 for c in value):
        raise ExtractionError('invalid_document')
    result = value.split(';', 1)[0].strip().lower()
    if not re.fullmatch(r'[a-z0-9.+-]+/[a-z0-9.+-]+', result):
        raise ExtractionError('invalid_document')
    return {'text/rtf': 'application/rtf', 'application/x-rtf': 'application/rtf'}.get(result, result)


def document_result(value, raw, declared):
    """Validate the entire byte-bound response at both sides of the RPC boundary."""
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_INPUT:
        raise ExtractionError('invalid_document')
    if not isinstance(value, dict) or set(value) != {'format', 'sha256', 'mediaType', 'text'}:
        raise ExtractionError('invalid_document')
    if value['format'] != 'enterprise-document-v1' or value['sha256'] != hashlib.sha256(raw).hexdigest():
        raise ExtractionError('invalid_document')
    actual = media_type(value['mediaType'])
    if actual not in MEDIA_TYPES or actual != value['mediaType']:
        raise ExtractionError('unsupported_format')
    expected = media_type(declared)
    if actual != expected and expected != 'application/octet-stream':
        raise ExtractionError('mime_mismatch')
    text = value['text']
    if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > MAX_TEXT or '\x00' in text:
        raise ExtractionError('invalid_document')
    return value
