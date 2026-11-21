"""General company-document decoding in a separate credentialless parser service.

This module accepts bytes, never caller-selected URLs or parser configuration.
The JVM/native tools must be contained by the deployment's network/resource sandbox;
process deadlines alone are not isolation. Invoice PDF protocol is unchanged.
"""
import base64
import hashlib
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import tempfile
import time

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


class CompanyDocument:
    def __init__(self, *, java, classpath, pdf, timeout=30):
        if not Path(java).is_absolute() or not Path(java).is_file():
            raise ValueError('Supply the installed pinned Java executable')
        if not isinstance(classpath, (list, tuple)) or not classpath or any(not Path(p).is_absolute() or not Path(p).exists() for p in classpath):
            raise ValueError('Supply the fixed bridge and verified Tika classpath')
        if not callable(getattr(pdf, 'extract', None)) or type(timeout) is not int or not 1 <= timeout <= 110:
            raise ValueError('Supply the bounded native PDF extractor and timeout')
        self.java = java
        self.classpath = os.pathsep.join(str(p) for p in classpath)
        self.pdf = pdf
        self.timeout = timeout

    def extract(self, raw, declared):
        if not isinstance(raw, bytes) or not raw:
            raise ExtractionError('invalid_document')
        if len(raw) > MAX_INPUT:
            raise ExtractionError('document_too_large')
        declared = media_type(declared)
        digest = hashlib.sha256(raw).hexdigest()
        if raw.startswith(b'%PDF-'):
            from invoice_document import DocumentError
            try:
                parsed = self.pdf.extract(raw, digest)
            except DocumentError as failure:
                raise ExtractionError('extraction_timeout' if failure.code == 'extraction_timeout' else 'extraction_failed') from None
            pages = []
            for page in parsed['pages']:
                native, ocr = page['text'].strip(), page['ocr'].strip()
                # Both channels matter for mixed text/image pages. Do not discard
                # image-only facts because a page also has a native-text header.
                body = native if native == ocr else '\n'.join(part for part in (native, ocr) if part)
                pages.append(f"Page {page['number']}\n{body}")
            detected, text = 'application/pdf', '\n\n'.join(pages)
        else:
            detected, text = self._tika(raw)
        return document_result({'format': 'enterprise-document-v1', 'sha256': digest,
                                'mediaType': detected, 'text': text}, raw, declared)

    def _tika(self, raw):
        with tempfile.TemporaryDirectory(prefix='atmem-company-document-') as temporary:
            folder = Path(temporary)
            source = folder / 'input'
            source.write_bytes(raw)
            source.chmod(0o600)
            process = None
            try:
                # No JAVA_TOOL_OPTIONS, CLASSPATH, proxy, application or workload
                # credentials enter the parser. Child tools share the outer group.
                process = subprocess.Popen([self.java, '-Xmx256m', '-XX:ActiveProcessorCount=1',
                    '-Djava.awt.headless=true', '-Djava.io.tmpdir=' + temporary,
                    '-cp', self.classpath, 'EnterpriseDocument', str(source)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    cwd=folder, start_new_session=True, env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': temporary,
                                    'TMPDIR': temporary, 'LANG': 'C.UTF-8', 'OMP_THREAD_LIMIT': '1',
                                    'TESSDATA_PREFIX': '/usr/share/tesseract-ocr/5/tessdata'})
                deadline = time.monotonic() + self.timeout
                output = bytearray()
                with selectors.DefaultSelector() as selector:
                    os.set_blocking(process.stdout.fileno(), False)
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while selector.get_map():
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise ExtractionError('extraction_timeout')
                        for key, _ in selector.select(min(remaining, .1)):
                            chunk = os.read(key.fd, 8192)
                            if not chunk:
                                selector.unregister(key.fileobj)
                            else:
                                output.extend(chunk)
                                if len(output) > 270000:
                                    raise ExtractionError('extraction_failed')
                try:
                    code = process.wait(timeout=max(.01, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    raise ExtractionError('extraction_timeout') from None
                lines = output.decode('ascii').splitlines()
                if code == 2 and lines == ['rejected', 'unsupported_format']:
                    raise ExtractionError('unsupported_format')
                if code != 0 or len(lines) != 3 or lines[0] != 'ok':
                    raise ExtractionError('extraction_failed')
                return lines[1], base64.b64decode(lines[2], validate=True).decode('utf-8')
            except ExtractionError:
                raise
            except Exception:
                raise ExtractionError('extraction_unavailable') from None
            finally:
                if process is not None:
                    # Kill the entire private group, including an OCR child that
                    # outlived a failed/crashed JVM. Never leave document workers.
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                    process.stdout.close()
