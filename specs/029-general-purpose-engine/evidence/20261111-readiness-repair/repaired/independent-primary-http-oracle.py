
import concurrent.futures,contextlib,http.client,http.server,io,json,os,sys,threading,time,zipfile
with zipfile.ZipFile('/work/source/dist/function.zip') as archive:
 assert all(not item.filename.startswith('/') and '..' not in item.filename.split('/') for item in archive.infolist())
 archive.extractall('/tmp/delivery')
sys.path.insert(0,'/tmp/delivery')
from app import handler
os.environ.update(CLIENT_ID='independentclient',ISSUER='independent-local-issuer',AUTH_ORIGIN='https://independent.auth.ap-southeast-2.amazoncognito.com',ALLOWED_SUBS='["approved-staff"]',INFERENCE_ENABLED='true',RETENTION_VERIFIED_UNTIL=str(int(time.time())+1800))
local=threading.local();calls=[];unhandled=[];lock=threading.Lock();checks=0
class Control:
 def get_model_invocation_logging_configuration(self):
  mode=getattr(local,'mode','valid')
  if mode=='logging-denied':raise PermissionError('PRIVATE-SYNTHETIC')
  if mode=='logging-enabled':return {'loggingConfig':{'textDataDeliveryEnabled':True}}
  if mode=='logging-unknown':return {'loggingConfig':{}}
  return {}
class Model:
 def converse(self,**kw):
  text=kw['messages'][0]['content'][0]['text']
  assert kw['modelId']=='amazon.nova-lite-v1:0' and kw['messages'][0]['role']=='user'
  with lock:calls.append(text)
  mode=getattr(local,'mode','valid')
  if mode=='timeout':raise TimeoutError('PRIVATE-SYNTHETIC '+text)
  value={'summary':'Fixture: '+text[:60],'topic':'technical','urgency':'normal','uncertainty':{'level':'high','reason':'Independent synthetic model; human review required.'}}
  if mode=='extra':value['action']='write-customer'
  if mode=='missing':del value['uncertainty']
  if mode=='bad-topic':value['topic']=['technical']
  output='not JSON' if mode=='invalid' else json.dumps(value)
  return {'stopReason':'max_tokens' if mode=='truncated' else 'guardrail_intervened' if mode=='refused' else 'end_turn','output':{'message':{'content':[{'text':output}]}}}
class Adapter(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):self.dispatch()
 def do_POST(self):self.dispatch()
 def dispatch(self):
  local.mode=self.headers.get('X-Oracle-Outcome','valid')
  token=self.headers.get('Authorization','');claims={}
  if token.startswith('Bearer fixture-'):
   claims={'sub':'approved-staff','token_use':'access','client_id':'independentclient','iss':'independent-local-issuer'}
   variant=token.removeprefix('Bearer fixture-')
   if variant=='unapproved':claims['sub']='other-staff'
   if variant=='issuer':claims['iss']='wrong-issuer'
   if variant=='client':claims['client_id']='wrong-client'
   if variant=='id-token':claims['token_use']='id'
  event={'rawPath':self.path,'headers':dict(self.headers),'body':self.rfile.read(int(self.headers.get('Content-Length','0'))).decode(),'requestContext':{'http':{'method':self.command},'authorizer':{'jwt':{'claims':claims}}}}
  try:result=handler.handler(event,None,clients_factory=lambda:(Control(),Model()))
  except Exception as error:
   with lock:unhandled.append(type(error).__name__)
   result={'statusCode':500,'headers':{'Content-Type':'application/json'},'body':'{"error":"independent-adapter-observed-unhandled-exception"}'}
  raw=result['body'].encode();self.send_response(result['statusCode'])
  for key,value in result['headers'].items():self.send_header(key,value)
  self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Adapter);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
def send(body=None,token='Bearer fixture-valid',mode='valid',content_type='application/json',method='POST',path='/suggest'):
 client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5);headers={'Content-Type':content_type,'X-Oracle-Outcome':mode}
 if token:headers['Authorization']=token
 client.request(method,path,body,headers);response=client.getresponse();result=(response.status,dict(response.getheaders()),response.read());client.close();return result
def success(text):
 global checks
 result=send(json.dumps({'text':text}));assert result[0]==200,result
 assert 'no-store' in result[1]['Cache-Control'];value=json.loads(result[2]);assert set(value)=={'summary','topic','urgency','uncertainty'} and value['summary']=='Fixture: '+text[:60]
 assert value['uncertainty']['level']=='high';checks+=1
captured=io.StringIO()
try:
 with contextlib.redirect_stdout(captured),contextlib.redirect_stderr(captured):
  result=send(method='GET',path='/',token=None);assert result[0]==200 and b'Human review' in result[2];checks+=1
  success('INDEPENDENT-NO-LOG-CANARY: redacted ticket')
  for token in [None,'Bearer fixture-unapproved','Bearer fixture-issuer','Bearer fixture-client','Bearer fixture-id-token']:
   count=len(calls);result=send(json.dumps({'text':'denied'}),token=token);assert result[0]==403 and len(calls)==count,result;checks+=1
  for body in ['not-json','{"text":"a","text":"b"}',json.dumps({'text':3}),json.dumps({'text':'a','extra':True}),json.dumps({'text':' '}),json.dumps({'text':'x'*20481}),json.dumps({'text':'é'*10241})]:
   count=len(calls);result=send(body);assert result[0]==400 and len(calls)==count,result;checks+=1
  success('x'*20480);success('é'*10240)
  count=len(calls);result=send(json.dumps({'text':'wrong media'}),content_type='text/plain');assert result[0]==400 and len(calls)==count;checks+=1
  result=send(json.dumps({'text':'never write customer records'}),path='/helpdesk/update');assert result[0]==404 and len(calls)==count;checks+=1
  for mode in ['timeout','extra','missing','bad-topic','invalid','truncated','refused','logging-enabled','logging-denied','logging-unknown']:
   count=len(calls);result=send(json.dumps({'text':'INDEPENDENT-NO-LOG-CANARY'}),mode=mode)
   assert result[0]==503 and len(calls)==count+(0 if mode.startswith('logging-') else 1),result
   assert 'summary' not in json.loads(result[2]) and b'PRIVATE-SYNTHETIC' not in result[2] and b'INDEPENDENT-NO-LOG-CANARY' not in result[2];checks+=1
  success('recovered')
  with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:list(pool.map(lambda i:success('concurrent-isolation-'+str(i)),range(5)))
  count=len(calls);result=send('{"text":'+'['*1500+'0'+']'*1500+'}')
  assert result[0]==400 and len(calls)==count,('deep malformed input did not return controlled 400',result,unhandled);checks+=1
 assert not unhandled,unhandled
 assert 'INDEPENDENT-NO-LOG-CANARY' not in captured.getvalue();checks+=1
finally:server.shutdown();server.server_close();thread.join()
print('INDEPENDENT_PRIMARY_HTTP_PASSED',checks)
