"""Private byte-only company-document RPC; credentialless parser workload.

Network admission, TLS and egress isolation are mandatory infrastructure controls.
The service accepts no URL, model input, parser option or company/source identity.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time
sys.path.insert(0, str(Path(__file__).resolve().parent))
from enterprise_document import ExtractionError, MAX_INPUT, media_type
from enterprise_document_cli import installed_parser


class DocumentServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 16

    def __init__(self, address, parser, authorize):
        if not callable(getattr(parser, 'extract', None)) or not callable(authorize):
            raise ValueError('Supply the owned parser and explicit caller admission adapter')
        self.parser, self.authorize = parser, authorize
        self.slot = threading.BoundedSemaphore(1)
        super().__init__(address, DocumentHandler)


class DocumentHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'

    def log_message(self, *args):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def reply(self, status, value):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        for key, value in [('Content-Type', 'application/json'), ('Content-Length', str(len(body))),
                           ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff')]:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.reply(200, {'status': 'running'}) if self.path == '/healthz' else self.reply(404, {'status': 'rejected'})

    def do_POST(self):
        if self.path != '/extract':
            self.reply(404, {'status': 'rejected'})
            return
        try:
            self.server.authorize(self.headers.get_all('Authorization') or [])
        except Exception:
            self.reply(403, {'status': 'rejected', 'reason': 'access_denied'})
            return
        lengths = self.headers.get_all('Content-Length') or []
        types = self.headers.get_all('Content-Type') or []
        if self.headers.get('Transfer-Encoding') or len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
            self.reply(411, {'status': 'rejected', 'reason': 'invalid_request'})
            return
        if len(lengths[0]) > 10 or not 1 <= int(lengths[0]) <= MAX_INPUT:
            self.reply(413, {'status': 'rejected', 'reason': 'document_too_large'})
            return
        try:
            if len(types) != 1:
                raise ExtractionError('invalid_document')
            declared = media_type(types[0])
        except ExtractionError:
            self.reply(415, {'status': 'rejected', 'reason': 'invalid_document'})
            return
        if not self.server.slot.acquire(blocking=False):
            self.reply(429, {'status': 'rejected', 'reason': 'busy'})
            return
        try:
            remaining, body, deadline = int(lengths[0]), bytearray(), time.monotonic() + 15
            while remaining:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise TimeoutError()
                self.connection.settimeout(min(5, left))
                chunk = self.rfile.read1(min(remaining, 65536))
                if not chunk:
                    raise ValueError()
                body.extend(chunk)
                remaining -= len(chunk)
            self.connection.settimeout(5)
            document = self.server.parser.extract(bytes(body), declared)
            self.reply(200, {'status': 'ok', 'document': document})
        except ExtractionError as failure:
            self.reply(422, {'status': 'rejected', 'reason': failure.code})
        except (TimeoutError, socket.timeout):
            self.reply(408, {'status': 'rejected', 'reason': 'upload_timeout'})
        except ValueError:
            self.reply(400, {'status': 'rejected', 'reason': 'invalid_request'})
        except Exception:
            self.reply(503, {'status': 'rejected', 'reason': 'extraction_unavailable'})
        finally:
            self.server.slot.release()


def main():
    forbidden = ['DATABASE_PASSWORD', 'DATABASE_PASSWORD_FILE', 'DATABASE_HOST', 'DATABASE_CONNECTION_NAME',
        'DESTINATION_TOKEN_FILE', 'DESTINATION_ENDPOINT', 'GOOGLE_APPLICATION_CREDENTIALS', 'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY', 'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI', 'AWS_CONTAINER_CREDENTIALS_FULL_URI',
        'IDENTITY_ENDPOINT', 'IDENTITY_HEADER', 'MSI_ENDPOINT', 'MSI_SECRET', 'MSAL_CLIENT_SECRET', 'CONFLUENCE_CLIENT_SECRET']
    if any(os.environ.get(key) for key in forbidden) or Path('/var/run/secrets/codeengine.cloud.ibm.com/compute-resource-token/token').exists():
        raise ValueError('Do not supply source, database, model or workload credentials to the parser')
    mode = os.environ.get('PARSER_AUTH_MODE', '')
    if mode == 'shared-token':
        from invoice_parser_identity import SharedParserVerifier
        verify = SharedParserVerifier(os.environ.pop('PARSER_SHARED_TOKEN', ''))
        def authorize(headers):
            if len(headers) != 1 or not headers[0].startswith('Bearer '):
                raise PermissionError()
            verify(headers[0][7:])
    elif mode == 'private-ingress':
        # Explicitly selected only when the native hosting boundary authenticates
        # and restricts callers. An arbitrary request header is never that proof.
        def authorize(headers):
            return None
    else:
        raise ValueError('Select explicit owned parser admission')
    port = int(os.environ.get('PORT', '8080'))
    if not 1024 <= port <= 65535:
        raise ValueError('Use an owned nonprivileged parser port')
    DocumentServer(('0.0.0.0', port), installed_parser(), authorize).serve_forever(poll_interval=.2)


if __name__ == '__main__':
    main()
