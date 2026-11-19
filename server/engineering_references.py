"""Public architecture research. No project-supplied URLs, queries or headers."""
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from . import modeling_catalog
import re
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

REFERENCES = {
    'c4-views': ('Architecture views', 'C4 model', 'https://c4model.com/diagrams'),
    'asyncapi-3': ('Async messages and correlation', 'AsyncAPI 3.0.0',
                   'https://raw.githubusercontent.com/asyncapi/spec/v3.0.0/spec/asyncapi.md'),
    'otel-logs': ('Structured logs and trace correlation', 'OpenTelemetry',
                  'https://opentelemetry.io/docs/specs/otel/logs/data-model/index.md'),
    'warehouse-flow': ('Equipment acknowledgement, reconnect and replay', 'SAP EWM 9.0',
                       'https://help.sap.com/saphelp_ewm900/helpdata/en/46/2d2354fe2e2502e10000000a1553f7/content.htm?no_cache=true'),
    'nist-ot-r3': ('Operational technology security and safety boundaries', 'NIST SP 800-82 Rev. 3',
                   'https://csrc.nist.gov/pubs/sp/800/82/r3/final'),
    'transactional-outbox': ('Reliable publication after a database transaction', 'AWS Prescriptive Guidance',
                             'https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html'),
}
PAGE = 5000
MAX_BYTES = 1_500_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.suppressed = set()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'noscript', 'svg'}:
            self.suppressed.add(tag)

    def handle_endtag(self, tag):
        self.suppressed.discard(tag)

    def handle_data(self, data):
        if not self.suppressed and data.strip():
            self.parts.append(data.strip())


def catalog():
    return [{'id': key, 'title': title, 'publisher': publisher, 'url': url}
            for key, (title, publisher, url) in REFERENCES.items()]+modeling_catalog.catalog()


def read_reference(reference, offset=0, expected_digest=None):
    if isinstance(reference,str) and reference.startswith('modeling-'):
        return modeling_catalog.read(reference,offset,expected_digest)
    if not isinstance(reference, str) or reference not in REFERENCES or type(offset) is not int or offset < 0:
        raise ValueError('Select a public reference ID and a valid page offset.')
    if expected_digest is not None and (not isinstance(expected_digest,str) or not re.fullmatch(r'[a-f0-9]{64}',expected_digest)):
        raise ValueError('Use the exact digest returned by the reference tool.')
    if offset and not expected_digest:
        raise ValueError('An evidence digest is required for subsequent pages.')
    title, publisher, url = REFERENCES[reference]
    try:
        request = Request(url, headers={'Accept': 'text/plain, text/markdown, text/html',
                                        'User-Agent': 'AtMem Architect public references'})
        # A fixed HTTPS destination, no ambient proxy, cookies, redirects or project inputs.
        with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=6) as response:
            raw = response.read(MAX_BYTES + 1)
            kind = response.headers.get_content_type()
        if not raw or len(raw) > MAX_BYTES or kind not in {'text/plain', 'text/markdown', 'text/html'}:
            raise ValueError('The public source exceeded the supported content boundary.')
        text = raw.decode('utf-8')
        if kind == 'text/html':
            parser = VisibleText()
            parser.feed(text)
            text = '\n'.join(parser.parts)
        if not text.strip():
            raise ValueError('The public endpoint did not provide readable evidence.')
        digest = sha256(raw).hexdigest()
        if expected_digest and digest != expected_digest:
            raise ValueError('The source changed. Request its first page again.')
        if offset >= len(text):
            raise ValueError('The requested evidence page is past the end.')
    except (URLError, TimeoutError, OSError, UnicodeError) as error:
        raise ValueError('The reviewed public reference is currently unavailable.') from error
    return {'id': reference, 'title': title, 'publisher': publisher, 'url': url, 'sha256': digest,
            'retrievedAt': datetime.now(timezone.utc).isoformat(), 'characters': len(text),
            'offset': offset, 'nextOffset': offset + PAGE if offset + PAGE < len(text) else None,
            'text': text[offset:offset+PAGE], 'evidenceLevel': 'public_reference_snapshot'}
