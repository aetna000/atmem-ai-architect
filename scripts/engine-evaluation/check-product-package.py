#!/usr/bin/env python3
"""Independent packaged HTTP diagnostic for one observed product artifact.

Evaluation-only interface adapter; not production selection or an export repair.
Gateway claims and Bedrock are explicit fixtures; actual packaged code/HTTP are used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec

ORACLE=r'''
import concurrent.futures,contextlib,http.client,http.server,io,json,os,pathlib,sys,threading,time,zipfile
with zipfile.ZipFile('/work/source/build/support-review.zip') as archive:
 for item in archive.infolist():
  path=pathlib.PurePosixPath(item.filename)
  assert not path.is_absolute() and '..' not in path.parts
 assert sum(item.file_size for item in archive.infolist())<2000000
 archive.extractall('/tmp/delivery')
sys.path.insert(0,'/tmp/delivery')
import handler
os.environ.update(AWS_REGION='ap-southeast-2',MODEL_ID='amazon.nova-lite-v1:0',CLIENT_ID='independent-client',COGNITO_ISSUER='https://cognito-idp.ap-southeast-2.amazonaws.com/ap-southeast-2_Independent',COGNITO_DOMAIN='https://independent.auth.ap-southeast-2.amazoncognito.com')
local=threading.local();calls=[];lock=threading.Lock();checks=0
class Fixture:
 def converse(self,**kwargs):
  assert kwargs['modelId']=='amazon.nova-lite-v1:0'
  assert kwargs['messages'][0]['role']=='user'
  ticket=kwargs['messages'][0]['content'][0]['text']
  with lock:calls.append(ticket)
  mode=getattr(local,'mode','valid')
  if mode=='timeout':raise TimeoutError('PRIVATE-SYNTHETIC-PROVIDER-DETAIL '+ticket)
  value={'summary':'Synthetic fixture: '+ticket[:60],'topic':'other','urgency':'normal','uncertainty':{'level':'high','reason':'Synthetic transport; no model quality claim.'}}
  if mode=='extra':value['action']='send-reply'
  if mode=='missing':del value['uncertainty']
  if mode=='bad-topic':value['topic']=['other']
  text='not JSON' if mode=='invalid' else json.dumps(value)
  return {'stopReason':'max_tokens' if mode=='truncated' else 'guardrail_intervened' if mode=='refused' else 'end_turn','output':{'message':{'role':'assistant','content':[{'text':text}]}}}
handler._bedrock=lambda:Fixture()
class Adapter(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):self.dispatch()
 def do_POST(self):self.dispatch()
 def dispatch(self):
  identity=self.headers.get('Authorization','');claims={}
  if identity.startswith('Bearer fixture-'):
   claims={'iss':os.environ['COGNITO_ISSUER'],'client_id':os.environ['CLIENT_ID'],'sub':'synthetic-staff','token_use':'access','exp':time.time()+60,'cognito:groups':['Reviewers']}
   variant=identity.removeprefix('Bearer fixture-')
   if variant=='expired':claims['exp']=time.time()-60
   if variant=='issuer':claims['iss']='https://wrong.example'
   if variant=='client':claims['client_id']='wrong-client'
   if variant=='id-token':claims['token_use']='id'
   if variant=='group':claims['cognito:groups']=['OtherGroup']
  local.mode=self.headers.get('X-Oracle-Outcome','valid')
  body=self.rfile.read(int(self.headers.get('Content-Length','0'))).decode('utf8')
  result=handler.handler({'rawPath':self.path,'headers':dict(self.headers),'body':body,'requestContext':{'http':{'method':self.command},'authorizer':{'jwt':{'claims':claims}}}},None)
  data=result['body'].encode('utf8');self.send_response(result['statusCode'])
  for key,value in result['headers'].items():self.send_header(key,value)
  self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Adapter);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
def send(body=None,token='Bearer fixture-valid',mode='valid',content_type='application/json',method='POST',path='/api/suggest'):
 client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
 headers={'Content-Type':content_type,'X-Oracle-Outcome':mode}
 if token:headers['Authorization']=token
 client.request(method,path,body,headers);response=client.getresponse();result=(response.status,dict(response.getheaders()),response.read());client.close();return result
def success(ticket):
 global checks
 result=send(json.dumps({'ticket':ticket}));assert result[0]==200,result
 assert 'no-store' in result[1]['cache-control']
 value=json.loads(result[2]);assert set(value)=={'summary','topic','urgency','uncertainty'}
 assert value['summary']=='Synthetic fixture: '+ticket[:60]
 assert value['uncertainty']['level']=='high';checks+=1;return value
captured=io.StringIO()
try:
 with contextlib.redirect_stdout(captured),contextlib.redirect_stderr(captured):
  result=send(method='GET',path='/',token=None);assert result[0]==200 and b'human review' in result[2].lower();checks+=1
  success('INDEPENDENT-NO-LOG-CANARY: redacted ticket')
  for token in [None,'Bearer fixture-group','Bearer fixture-expired','Bearer fixture-issuer','Bearer fixture-client','Bearer fixture-id-token']:
   count=len(calls);result=send(json.dumps({'ticket':'denied'}),token=token)
   assert result[0]==403 and len(calls)==count,result;checks+=1
  for body in ['not-json','{"ticket":"a","ticket":"b"}',json.dumps({'ticket':3}),json.dumps({'ticket':'a','extra':True}),json.dumps({'ticket':'  '}),json.dumps({'ticket':'x'*20481}),json.dumps({'ticket':'é'*10241})]:
   count=len(calls);result=send(body);assert result[0]==400 and len(calls)==count,result;checks+=1
  success('x'*20000);success('x'*20480)
  count=len(calls);result=send(json.dumps({'ticket':'bad content'}),content_type='text/plain');assert result[0]==400 and len(calls)==count;checks+=1
  result=send(json.dumps({'ticket':'never write customer records'}),path='/helpdesk/update');assert result[0]==404 and len(calls)==count;checks+=1
  for mode in ['timeout','extra','missing','bad-topic','invalid','truncated','refused']:
   count=len(calls);result=send(json.dumps({'ticket':'INDEPENDENT-NO-LOG-CANARY'}),mode=mode)
   assert result[0]==503 and len(calls)==count+1,result
   assert 'summary' not in json.loads(result[2]) and b'PRIVATE-SYNTHETIC' not in result[2] and b'INDEPENDENT-NO-LOG-CANARY' not in result[2];checks+=1
  success('recovery succeeds')
  with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:list(pool.map(lambda i:success('isolated-concurrent-'+str(i)),range(5)))
 assert 'INDEPENDENT-NO-LOG-CANARY' not in captured.getvalue();checks+=1
finally:server.shutdown();server.server_close();thread.join()
print('INDEPENDENT_PACKAGED_HTTP_PASSED',checks)
'''

parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);args=parser.parse_args();run=args.run.resolve()
manifest=json.loads((run/'artifact.json').read_text());content=(run/'artifact.zip').read_bytes();assert hashlib.sha256(content).hexdigest()==manifest['sha256']
worker=DockerValidationWorker('unix://'+str(Path.home()/'.colima/architect-qualification/docker.sock'))
spec=ValidationSpec('independent-packaged-http','sha256:48d884813cf44e927cf64c5529dd630dd3b18338c6dc727991eef9b71e934a20',('/usr/local/bin/python3','-c',ORACLE))
result=worker.run(content,manifest['sha256'],spec)
result.update(oracleSha256=hashlib.sha256(ORACLE.encode()).hexdigest(),
    semanticBoundary='Independent actual packaged-code/static-asset/HTTP/input/role/expiry/failure/recovery/concurrency/no-stdout-leak checks. API Gateway JWT claims and Bedrock are explicit fixtures, not cryptographic identity, actual model, browser OAuth, vendor integration or whole-system acceptance.')
(run/'independent-http-oracle.py').write_text(ORACLE)
(run/'independent-http.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'],result['output'])
assert result['status']=='passed' and 'INDEPENDENT_PACKAGED_HTTP_PASSED 33' in result['output'],result
