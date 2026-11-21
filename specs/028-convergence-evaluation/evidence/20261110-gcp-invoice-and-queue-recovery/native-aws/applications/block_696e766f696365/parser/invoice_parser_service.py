"""Private bounded PDF RPC container; never expose as an anonymous public service.

Hosting must restrict callers to the worker, isolate this container and grant it
no document-store, database, model or destination permissions. Provider ingress
auth/network/TLS is a separate infrastructure boundary, not an HTTP header trust
claim made by this server. No request selects a URL, file, command or credential.
"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import hashlib
import json
import os
import socket
import sys
from pathlib import Path
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from invoice_document import PdfDocument,DocumentError

LIMIT=10000000

class ParserServer(ThreadingHTTPServer):
    daemon_threads=True
    request_queue_size=16
    def __init__(self,address,parser,authorize=None):
        if authorize is not None and not callable(authorize):raise ValueError('Use the owned parser authorization adapter')
        self.parser=parser;self.authorize=authorize;self.slot=threading.BoundedSemaphore(1);super().__init__(address,ParserHandler)

class ParserHandler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.0'
    def log_message(self,*args):pass
    def setup(self):
        super().setup();self.connection.settimeout(5)
    def reply(self,status,value):
        body=json.dumps(value,ensure_ascii=False,allow_nan=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.path=='/healthz':self.reply(200,{'status':'running'})
        else:self.reply(404,{'status':'rejected','reason':'invalid_request'})
    def do_POST(self):
        if self.path!='/extract':self.reply(404,{'status':'rejected','reason':'invalid_request'});return
        if self.server.authorize is not None:
            try:
                headers=self.headers.get_all('Authorization')or[]
                if len(headers)!=1 or not headers[0].startswith('Bearer '):raise PermissionError()
                self.server.authorize(headers[0][7:])
            except Exception:self.reply(403,{'status':'rejected','reason':'access_denied'});return
        # Reject ambiguous framing rather than trusting a proxy's normalization.
        lengths=self.headers.get_all('Content-Length')or[]
        if self.headers.get('Transfer-Encoding')or len(lengths)!=1 or not lengths[0].isascii()or not lengths[0].isdigit():self.reply(411,{'status':'rejected','reason':'invalid_request'});return
        if len(lengths[0])>10 or not 1<=int(lengths[0])<=LIMIT:self.reply(413,{'status':'rejected','reason':'document_too_large'});return
        if self.headers.get('Content-Type','').split(';')[0].lower()!='application/pdf':self.reply(415,{'status':'rejected','reason':'invalid_pdf'});return
        if not self.server.slot.acquire(blocking=False):self.reply(429,{'status':'rejected','reason':'busy'});return
        try:
            remaining=int(lengths[0]);body=bytearray();deadline=time.monotonic()+15
            while remaining:
                left=deadline-time.monotonic()
                if left<=0:raise TimeoutError()
                self.connection.settimeout(min(5,left));chunk=self.rfile.read1(min(remaining,65536))
                if not chunk:raise ValueError('Incomplete PDF body')
                body.extend(chunk);remaining-=len(chunk)
            raw=bytes(body);self.connection.settimeout(5)
            document=self.server.parser.extract(raw,hashlib.sha256(raw).hexdigest())
            self.reply(200,{'status':'ok','document':document})
        except DocumentError as error:self.reply(422,{'status':'rejected','reason':error.code})
        except(TimeoutError,socket.timeout):self.reply(408,{'status':'rejected','reason':'upload_timeout'})
        except ValueError:self.reply(400,{'status':'rejected','reason':'invalid_request'})
        except Exception:self.reply(503,{'status':'rejected','reason':'extraction_unavailable'})
        finally:self.server.slot.release()

def main():
    # These checks catch common accidental mounts. Infrastructure admission still
    # must prove that this separate workload has no inherited cloud authority.
    forbidden=['DATABASE_PASSWORD','DATABASE_PASSWORD_FILE','DATABASE_HOST','DATABASE_CONNECTION_NAME','DESTINATION_TOKEN_FILE','DESTINATION_ENDPOINT','GOOGLE_APPLICATION_CREDENTIALS','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_CONTAINER_CREDENTIALS_RELATIVE_URI','AWS_CONTAINER_CREDENTIALS_FULL_URI','IDENTITY_ENDPOINT','IDENTITY_HEADER','MSI_ENDPOINT','MSI_SECRET']
    if any(os.environ.get(key)for key in forbidden)or Path('/var/run/secrets/codeengine.cloud.ibm.com/compute-resource-token/token').exists():raise ValueError('Do not supply parser database, action or workload credentials')
    port=int(os.environ.get('PORT','8080'))
    if not 1024<=port<=65535:raise ValueError('Use the owned nonprivileged parser port')
    mode=os.environ.get('PARSER_AUTH_MODE','private-ingress');authorize=None
    if mode=='entra-workload':
        from invoice_parser_identity import EntraParserVerifier
        authorize=EntraParserVerifier(*[os.environ[name]for name in ['PARSER_TENANT_ID','PARSER_AUDIENCE','PARSER_WORKER_CLIENT_ID','PARSER_WORKER_PRINCIPAL_ID']])
    elif mode!='private-ingress':raise ValueError('Use the owned parser authorization mode')
    ParserServer(('0.0.0.0',port),PdfDocument(),authorize).serve_forever(poll_interval=.2)

if __name__=='__main__':main()
