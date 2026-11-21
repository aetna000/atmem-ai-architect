"""Independent synthetic HTTPS recipient; records actual bytes, never retries clients."""
import hashlib,http.server,json,pathlib,socket,ssl,threading,time
ROOT=pathlib.Path('/runtime');fixture=json.loads((ROOT/'fixture.json').read_bytes());lock=threading.Lock()
class Recipient(http.server.BaseHTTPRequestHandler):
 def do_POST(self):
  count=int(self.headers.get('Content-Length','0'));assert 0<count<100000
  raw=self.rfile.read(count);value=json.loads(raw)
  event={'body':value,'bodySha256':hashlib.sha256(raw).hexdigest(),'operationId':self.headers.get('Idempotency-Key'),'approvedHash':self.headers.get('X-Approved-Payload-SHA256'),'credentialMatched':self.headers.get('Authorization')=='Bearer '+fixture['destinationToken']}
  with lock:
   with(ROOT/'events.jsonl').open('a')as target:target.write(json.dumps(event,ensure_ascii=True)+'\n')
  mode=(ROOT/'mode').read_text()
  if mode=='ambiguous':
   try:self.connection.shutdown(socket.SHUT_RDWR)
   except OSError:pass
   self.connection.close();return
  if mode=='hold':
   until=time.monotonic()+90
   while not(ROOT/'release').exists()and time.monotonic()<until:time.sleep(.05)
  payload=json.dumps({'operation_id':event['operationId'],'payload_sha256':event['approvedHash'],'external_id':'independent/'+event['operationId'],'status':'completed'}).encode()
  try:self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
  except OSError:pass
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('0.0.0.0',8443),Recipient);context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2;context.load_cert_chain(ROOT/'tls.pem',ROOT/'tls.key');server.socket=context.wrap_socket(server.socket,server_side=True);server.serve_forever()
