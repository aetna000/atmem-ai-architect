"""Synthetic loopback TLS service enforcing the declared idempotency contract."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import time
import shutil

class TlsDestinationFixture:
    def __init__(self):
        self.folder=tempfile.TemporaryDirectory(prefix='atmem-workflow-tls-');root=Path(self.folder.name);self.calls=[];self.effects={};self.lock=threading.Lock();self.mode='completed';self.token='synthetic-fixture-token'
        certificate=root/'fixture.crt';key=root/'fixture.key'
        openssl=shutil.which('openssl')
        if Path('/opt/homebrew/opt/openssl@3/bin/openssl').is_file():openssl='/opt/homebrew/opt/openssl@3/bin/openssl'
        if not openssl:raise RuntimeError('Install OpenSSL with req -addext support for the local TLS fixture')
        subprocess.run([openssl,'req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(key),'-out',str(certificate)],check=True,capture_output=True)
        key.chmod(0o600);owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=70000:self.send_error(413);return
                raw=self.rfile.read(length)
                if self.headers.get('Authorization')!='Bearer '+owner.token:self.send_error(401);return
                body=json.loads(raw);key=self.headers.get('Idempotency-Key')
                if self.path!='/actions'or key!=body.get('operation_id'):self.send_error(400);return
                with owner.lock:
                    owner.calls.append({'key':key,'body':body})
                    if key in owner.effects and owner.effects[key]['payload_sha256']!=body['payload_sha256']:self.send_error(409);return
                    receipt=owner.effects.setdefault(key,{'operation_id':key,'payload_sha256':body['payload_sha256'],'external_id':'synthetic-'+str(len(owner.effects)+1),'status':'completed'})
                    if owner.mode=='pending':receipt={**receipt,'status':'pending'}
                    if owner.mode=='wrong-receipt':receipt={**receipt,'operation_id':'different-operation'}
                    data=json.dumps(receipt).encode()
                self.send_response(202 if owner.mode=='pending'else 200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers()
                if owner.mode=='slow-receipt':
                    try:
                        for byte in data:self.wfile.write(bytes([byte]));self.wfile.flush();time.sleep(.05)
                    except(OSError,ssl.SSLError):pass
                else:self.wfile.write(data)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.daemon_threads=True
        server_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);server_context.load_cert_chain(certificate,key);self.server.socket=server_context.wrap_socket(self.server.socket,server_side=True)
        self.url='https://localhost:'+str(self.server.server_port)+'/actions';self.ca_file=certificate
        self.context=ssl.create_default_context(cafile=str(certificate));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=2);self.folder.cleanup()
