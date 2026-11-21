"""Worker-only private HTTPS parser contract. Endpoint/auth are operator-owned."""
import json
import re
import time
from urllib.parse import urlsplit
import requests
from invoice_document import DocumentError
from invoice_extraction import document_evidence
from invoice_object_store import digest_pdf
from structured_output import _object
from workflow_errors import TemporaryWork

class ParserClient:
    def __init__(self,endpoint,authorization=None,*,session=None):
        try:target=urlsplit(endpoint)
        except(ValueError,TypeError):raise ValueError('Use the exact private parser endpoint')from None
        if(not isinstance(endpoint,str)or len(endpoint)>2000 or target.scheme!='https'or not target.hostname or target.path!='/extract'
           or target.query or target.fragment or target.username or target.password or any(ord(c)<33 or ord(c)>126 for c in endpoint)):raise ValueError('Use the owned private HTTPS /extract endpoint')
        try:port=target.port
        except ValueError:raise ValueError('Use the owned private parser port')from None
        if port is not None and not 1<=port<=65535:raise ValueError('Use the owned private parser port')
        if authorization is not None and not callable(authorization):raise ValueError('Use owned native caller authorization')
        self.endpoint=endpoint;self.authorization=authorization;self.session=session or requests.Session();self.session.trust_env=False
    def __call__(self,raw):
        digest=digest_pdf(raw);headers={'Content-Type':'application/pdf'}
        try:
            if self.authorization is not None:
                token=self.authorization()
                if not isinstance(token,str)or not token.startswith('Bearer ')or not 8<=len(token)<=20000 or any(ord(c)<33 or ord(c)>126 for c in token[7:]):raise ValueError('Invalid parser caller identity')
                headers['Authorization']=token
            deadline=time.monotonic()+125
            with self.session.post(self.endpoint,data=raw,headers=headers,timeout=(2,115),allow_redirects=False,stream=True)as response:
                if response.status_code in {408,429,500,502,503,504}:raise TemporaryWork('PDF parsing is temporarily unavailable')
                if response.status_code==422:raise DocumentError('unreadable_pdf')
                if response.status_code!=200:raise TemporaryWork('Private parser admission is unavailable')
                content=bytearray()
                for chunk in response.iter_content(1):
                    content.extend(chunk)
                    if len(content)>120500 or time.monotonic()>deadline:raise ValueError('Parser response exceeds its boundary')
            value=json.loads(content,object_pairs_hook=_object,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite parser output')))
            if not isinstance(value,dict)or set(value)!={'status','document'}or value['status']!='ok':raise ValueError('Invalid parser response')
            document=value['document'];document_evidence(document)
            if document['sha256']!=digest:raise ValueError('Parser original digest differs')
            return document
        except(DocumentError,TemporaryWork):raise
        except Exception:raise TemporaryWork('Private parser could not confirm extraction')from None

def google_parser_authorization(audience,session=None):
    if not isinstance(audience,str)or not re.fullmatch(r'https://[a-z0-9-]+(?:\.[a-z0-9-]+)?\.run\.app',audience):raise ValueError('Use the owned Cloud Run parser audience')
    session=session or requests.Session();session.trust_env=False
    def read():
        deadline=time.monotonic()+4
        with session.get('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity',params={'audience':audience,'format':'full'},headers={'Metadata-Flavor':'Google'},allow_redirects=False,timeout=(1,2),stream=True)as response:
            if response.status_code!=200 or response.headers.get('Metadata-Flavor')!='Google':raise TemporaryWork('Parser workload identity unavailable')
            raw=bytearray()
            for chunk in response.iter_content(1):
                raw.extend(chunk)
                if len(raw)>16384 or time.monotonic()>deadline:raise TemporaryWork('Parser workload identity unavailable')
        value=raw.decode('ascii')
        if not value or any(ord(c)<33 or ord(c)>126 for c in value):raise TemporaryWork('Parser workload identity unavailable')
        return'Bearer '+value
    return read
