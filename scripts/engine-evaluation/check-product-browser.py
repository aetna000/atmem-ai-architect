#!/usr/bin/env python3
"""Independent captured-package browser journey with explicit local vendor emulation."""
import argparse,base64,hashlib,json,os,subprocess,sys,tempfile,threading,time,uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import parse_qs,urlsplit,urlencode
from cryptography.hazmat.primitives.asymmetric import rsa,padding
from cryptography.hazmat.primitives import hashes
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec

APP=r'''
import json,os,sys,time,zipfile,http.server
os.environ.update(AWS_REGION='ap-southeast-2',MODEL_ID='amazon.nova-lite-v1:0',COGNITO_ISSUER='LOCAL-EMULATED-ISSUER',CLIENT_ID='local-review-client',COGNITO_DOMAIN=ORIGIN)
with zipfile.ZipFile('/work/source/build/support-review.zip') as z:z.extractall('/tmp/app')
sys.path.insert(0,'/tmp/app');import handler
class Model:
 def converse(self,**kw):
  ticket=kw['messages'][0]['content'][0]['text']
  if ticket=='model-timeout':raise TimeoutError('PRIVATE-SYNTHETIC')
  if ticket=='slow-clear':time.sleep(2)
  value={'summary':'Synthetic reviewed suggestion.','topic':'technical','urgency':'normal','uncertainty':{'level':'high','reason':'Local emulated model; human review required.'}}
  if ticket=='unsafe-output':value['extra']='rejected'
  return {'stopReason':'end_turn','output':{'message':{'role':'assistant','content':[{'text':json.dumps(value)}]}}}
handler._bedrock=lambda:Model()
class Adapter(http.server.BaseHTTPRequestHandler):
 def do_POST(self):
  event=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  result=handler.handler(event,None);body=json.dumps(result).encode()
  self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass
http.server.ThreadingHTTPServer(('127.0.0.1',8091),Adapter).serve_forever()
'''
RELAY="""import base64,http.client,json,sys
payload=base64.b64decode(sys.argv[1]);c=http.client.HTTPConnection('127.0.0.1',8091,timeout=10);c.request('POST','/',payload,{'Content-Type':'application/json'});r=c.getresponse();assert r.status==200;print(r.read().decode());c.close()
"""

def b64(data):return base64.urlsafe_b64encode(data).decode().rstrip('=')
def unb64(value):return base64.urlsafe_b64decode(value+'='*(-len(value)%4))
parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--output',type=Path);args=parser.parse_args();run=args.run.resolve();out=args.output.resolve() if args.output else run/'browser-journey';out.mkdir(exist_ok=False)
manifest=json.loads((run/'artifact.json').read_text());archive=(run/'artifact.zip').read_bytes();assert hashlib.sha256(archive).hexdigest()==manifest['sha256']
key=rsa.generate_private_key(public_exponent=65537,key_size=2048);codes={};counts={'authorize':0,'token':0,'verified':0,'denied':0};lock=threading.Lock();execution=str(uuid.uuid4());cancel=threading.Event();result={}
endpoint='unix://'+str(Path.home()/'.colima/architect-qualification/docker.sock');name='atmem-validator-'+uuid.UUID(execution).hex
control=tempfile.TemporaryDirectory(prefix='atmem-browser-relay-');config=Path(control.name)/'docker';config.mkdir();(config/'config.json').write_text('{}')
env={'PATH':os.environ.get('PATH',''),'HOME':control.name,'DOCKER_CONFIG':str(config),'DOCKER_HOST':endpoint}
prefix=['docker','--host',endpoint,'--config',str(config),'exec','--user','65532:65532',name,'/var/lang/bin/python3.12','-I','-c',RELAY]
def relay(event):
 response=subprocess.run([*prefix,base64.b64encode(json.dumps(event).encode()).decode()],env=env,capture_output=True,text=True,timeout=15)
 if response.returncode:raise RuntimeError('Isolated application bridge unavailable')
 return json.loads(response.stdout)
def token(role='Reviewers',expiry=None):
 value={'iss':'LOCAL-EMULATED-ISSUER','client_id':'local-review-client','token_use':'access','sub':'local-staff','exp':expiry or time.time()+300,'cognito:groups':[role]}
 data=b64(b'{"alg":"RS256","typ":"JWT"}')+'.'+b64(json.dumps(value).encode());return data+'.'+b64(key.sign(data.encode(),padding.PKCS1v15(),hashes.SHA256()))
def verify(value):
 head,body,signature=value.split('.');assert json.loads(unb64(head))=={'alg':'RS256','typ':'JWT'}
 key.public_key().verify(unb64(signature),(head+'.'+body).encode(),padding.PKCS1v15(),hashes.SHA256())
 claims=json.loads(unb64(body));assert claims['iss']=='LOCAL-EMULATED-ISSUER' and claims['client_id']=='local-review-client' and claims['exp']>time.time() and claims['token_use']=='access';return claims
class Bridge(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,status,body='',headers=None):
  if isinstance(body,dict):body=json.dumps(body);headers={'content-type':'application/json',**(headers or {})}
  raw=body.encode();self.send_response(status)
  for k,v in {'cache-control':'no-store',**(headers or {}),'content-length':str(len(raw))}.items():self.send_header(k,v)
  self.end_headers()
  try:self.wfile.write(raw)
  except BrokenPipeError:pass
 def do_GET(self):self.dispatch()
 def do_POST(self):self.dispatch()
 def dispatch(self):
  url=urlsplit(self.path);query=parse_qs(url.query);body=self.rfile.read(int(self.headers.get('content-length',0))).decode()
  if url.path=='/oauth2/authorize':
   assert query['client_id']==['local-review-client'] and query['response_type']==['code'] and query['scope']==['openid'] and query['code_challenge_method']==['S256'] and query['redirect_uri']==[origin+'/auth/callback']
   code=uuid.uuid4().hex;codes[code]={'challenge':query['code_challenge'][0],'redirect':query['redirect_uri'][0]};counts['authorize']+=1
   return self.send(302,headers={'location':origin+'/auth/callback?'+urlencode({'code':code,'state':query['state'][0]})})
  if url.path=='/oauth2/token':
   values=parse_qs(body);counts['token']+=1;pending=codes.pop(values.get('code',[''])[0],None)
   if not pending or values.get('client_id')!=['local-review-client'] or values.get('grant_type')!=['authorization_code'] or values.get('redirect_uri')!=[pending['redirect']] or b64(hashlib.sha256(values.get('code_verifier',[''])[0].encode()).digest())!=pending['challenge']:return self.send(400,{'error':'invalid_grant'})
   return self.send(200,{'access_token':token(),'token_type':'Bearer','expires_in':300})
  if url.path=='/logout':return self.send(302,headers={'location':origin+'/'})
  event={'rawPath':url.path,'headers':dict(self.headers),'body':body,'requestContext':{'http':{'method':self.command}}}
  if url.path=='/api/suggest':
   try:claims=verify(self.headers.get('authorization','').removeprefix('Bearer '));event['requestContext']['authorizer']={'jwt':{'claims':claims}};counts['verified']+=1
   except Exception:counts['denied']+=1;return self.send(401,{'error':'invalid_token'})
  try:value=relay(event);return self.send(value['statusCode'],value['body'],value.get('headers'))
  except Exception:return self.send(502,{'error':'local_bridge_unavailable'})
server=ThreadingHTTPServer(('127.0.0.1',0),Bridge);origin='http://127.0.0.1:'+str(server.server_port)
worker=DockerValidationWorker(endpoint);script=APP.replace('COGNITO_DOMAIN=ORIGIN','COGNITO_DOMAIN='+repr(origin))
spec=ValidationSpec('independent-browser-app','sha256:cdb746c1eb56b61de56e1b5e78f6194392eb00494a1bb257a592852e72d8314b',('/var/lang/bin/python3.12','-c',script),platform='linux/arm64',timeout_seconds=180,bootstrap_python='/var/lang/bin/python3.12')
def execute():result.update(worker.run(archive,manifest['sha256'],spec,execution_id=execution,cancel_event=cancel))
thread=threading.Thread(target=execute);thread.start();serving=threading.Thread(target=server.serve_forever);serving.start()
try:
 for attempt in range(80):
  try:
   if relay({'rawPath':'/config.json','requestContext':{'http':{'method':'GET'}}})['statusCode']==200:break
  except Exception:time.sleep(.15)
 else:raise RuntimeError('Isolated captured application did not start')
 browser_env=dict(os.environ,ATMEM_PRODUCT_BROWSER_ORIGIN=origin,ATMEM_PRODUCT_BROWSER_OUTPUT=str(out),ATMEM_PRODUCT_BROWSER_ROLE_TOKEN=token('Other'),ATMEM_PRODUCT_BROWSER_EXPIRED_TOKEN=token(expiry=time.time()-10))
 browser=subprocess.run(['node',str(Path(__file__).with_name('product-browser-oracle.mjs'))],env=browser_env,capture_output=True,text=True,timeout=120)
 (out/'browser.log').write_text(browser.stdout+browser.stderr)
 assert browser.returncode==0,browser.stderr
finally:
 cancel.set();thread.join(timeout=25);server.shutdown();server.server_close();serving.join();control.cleanup()
 (out/'executor.json').write_text(json.dumps(result,indent=2)+'\n')
 receipt={'artifactSha256':manifest['sha256'],'passed':browser.returncode==0 if 'browser' in locals() else False,'vendorCounts':counts,'cloudOperations':False,'boundary':'Actual captured packaged frontend Chromium to isolated Python 3.12 ARM64 handler through a local HTTP relay. Explicit independent authorization-code/PKCE and RSA JWT verification gateway emulators plus synthetic model transport. Real Cognito login/MFA/JWKS lifecycle, AWS Gateway behavior, model quality and deployment are not established. Container cancellation after browser work is expected; executor alone is not the journey verdict.'}
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
