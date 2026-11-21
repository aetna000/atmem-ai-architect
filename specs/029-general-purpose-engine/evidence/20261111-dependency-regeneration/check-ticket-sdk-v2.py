"""Independent actual artifact SDK -> local signed HTTP -> handler qualification.

Evaluation adapter for the observed SDK-enabled ticket artifact. No exported file
is edited. Only the SDK client destination and synthetic credentials are supplied
by the fixture; original client factory/config, methods, parsing and gates execute.
"""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec
ORACLE=r'''
import concurrent.futures,http.server,json,os,sys,threading,time,zipfile
from urllib.parse import unquote
import io
sys.path.insert(0,'/work/source')
from scripts import build
output=io.BytesIO();build.build(output_stream=output);output.seek(0)
with zipfile.ZipFile(output) as archive:
 assert all(not n.startswith('/') and '..' not in n.split('/') for n in archive.namelist())
 archive.extractall('/tmp/actual-package')
output.close()
sys.path.insert(0,'/tmp/actual-package')
import handler,boto3,botocore
assert boto3.__version__==botocore.__version__=='1.43.123'
real_client=boto3.client;mode='valid';requests=[];configs=[];checks=[];guard=threading.Lock()
class Vendor(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):self.dispatch()
 def do_POST(self):self.dispatch()
 def dispatch(self):
  with guard:current=mode;requests.append((self.command,self.path));self.number=len(requests)
  assert '/ap-southeast-2/bedrock/aws4_request' in self.headers['Authorization']
  status=200
  if self.path=='/data-retention':
   assert self.command=='GET'
   if current=='retention-timeout':time.sleep(4)
   values={'retention-default':'default','retention-inherit':'inherit','retention-review':'aws_review','retention-share':'provider_data_share'}
   value={} if current=='retention-missing' else {'mode':values.get(current,'none'),'updatedAt':'2026-11-11T00:00:00Z'}
   if current in ['retention-denied','retention-throttled','retention-error']:
    status={'retention-denied':403,'retention-throttled':429,'retention-error':500}[current];value={'message':'PRIVATE-SDK-SYNTHETIC','__type':{403:'AccessDeniedException',429:'ThrottlingException',500:'InternalServerException'}[status]}
  elif self.path=='/logging/modelinvocations':
   assert self.command=='GET';value={'loggingConfig':{'textDataDeliveryEnabled':True}} if current=='logging-enabled' else {}
   if current=='logging-denied':status=403;value={'message':'PRIVATE-SDK-SYNTHETIC','__type':'AccessDeniedException'}
  else:
   assert self.command=='POST' and unquote(self.path)=='/model/amazon.nova-lite-v1:0/converse',self.path
   data=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert data['messages'][0]['role']=='user';ticket=data['messages'][0]['content'][0]['text']
   assert data['inferenceConfig']['maxTokens']>0
   if current=='model-timeout':time.sleep(19)
   result={'summary':'Fixture: '+ticket[:60],'topic':'technical','urgency':'normal','uncertainty':{'level':'high','reason':'Independent local SDK service fixture.'}}
   if current=='model-extra':result['action']='forbidden'
   value={'stopReason':'max_tokens' if current=='model-truncated' else 'end_turn','output':{'message':{'role':'assistant','content':[{'text':json.dumps(result)}]}}}
   if current in ['model-denied','model-throttled','model-error']:
    status={'model-denied':403,'model-throttled':429,'model-error':500}[current];value={'message':'PRIVATE-SDK-SYNTHETIC','__type':{403:'AccessDeniedException',429:'ThrottlingException',500:'InternalServerException'}[status]}
  encoded=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(encoded)));self.end_headers()
  try:self.wfile.write(encoded)
  except BrokenPipeError:pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Vendor);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
def client(service,**kwargs):
 assert service in ['bedrock','bedrock-runtime'] and kwargs['region_name']=='ap-southeast-2'
 config=kwargs['config'];assert config.retries['total_max_attempts']==1 and 0<config.connect_timeout<=2 and 0<config.read_timeout<=18
 configs.append({'service':service,'region':kwargs['region_name'],'readTimeout':config.read_timeout,'attempts':config.retries['total_max_attempts']})
 return real_client(service,**kwargs,endpoint_url='http://127.0.0.1:'+str(server.server_port),aws_access_key_id='synthetic-independent-key',aws_secret_access_key='synthetic-independent-secret')
boto3.client=client
claims={'sub':'synthetic-staff','token_use':'access','cognito:groups':['reviewers'],'scope':'review/suggest'}
def invoke(ticket='SDK-INDEPENDENT-TRANSIENT-CANARY'):
 event={'rawPath':'/suggest','headers':{'content-type':'application/json'},'body':json.dumps({'ticket':ticket}),'requestContext':{'http':{'method':'POST'},'authorizer':{'jwt':{'claims':claims}}}}
 return handler.handler(event,None)
try:
 for current in ['valid','retention-default','retention-inherit','retention-review','retention-share','retention-missing','retention-denied','retention-throttled','retention-error','retention-timeout','logging-enabled','logging-denied','model-denied','model-throttled','model-error','model-extra','model-truncated','model-timeout','valid']:
  mode=current;start=len(requests);t0=time.monotonic();result=invoke();elapsed=time.monotonic()-t0;calls=requests[start:]
  assert result['statusCode']==(200 if current=='valid' else 503),(current,result,calls)
  expected=1 if current.startswith('retention-') else 2 if current.startswith('logging-') else 3
  assert len(calls)==expected,(current,calls)
  assert calls[0]==('GET','/data-retention'),calls
  if expected>=2:assert calls[1]==('GET','/logging/modelinvocations')
  if current!='valid':assert 'summary' not in json.loads(result['body']) and 'PRIVATE-SDK' not in result['body'] and 'SDK-INDEPENDENT' not in result['body']
  if current=='retention-timeout':assert 2.5<=elapsed<7,elapsed
  if current=='model-timeout':assert 17<=elapsed<23,elapsed
  checks.append({'mode':current,'status':result['statusCode'],'signedRequests':len(calls),'elapsedSeconds':round(elapsed,3)})
 mode='valid'
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
  values=list(pool.map(lambda i:invoke('isolated-sdk-'+str(i)),range(5)))
 assert all(value['statusCode']==200 and json.loads(value['body'])['summary']=='Fixture: isolated-sdk-'+str(i) for i,value in enumerate(values))
 checks.append({'mode':'five-parallel-actual-sdk','passed':True})
 print('INDEPENDENT_ACTUAL_PACKAGE_SDK_PASSED',json.dumps({'checks':checks,'sdk':boto3.__version__,'configs':configs}))
finally:server.shutdown();server.server_close();thread.join()
'''
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--endpoint',required=True);args=p.parse_args();run=args.run.resolve()
archive=(run/'artifact.zip').read_bytes();manifest=json.loads((run/'artifact.json').read_text());assert hashlib.sha256(archive).hexdigest()==manifest['sha256']
spec=ValidationSpec('independent-ticket-sdk-v2','sha256:cdb746c1eb56b61de56e1b5e78f6194392eb00494a1bb257a592852e72d8314b',('/var/lang/bin/python3.12','-c',ORACLE),platform='linux/arm64',bootstrap_python='/var/lang/bin/python3.12',timeout_seconds=60)
result=DockerValidationWorker(args.endpoint).run(archive,manifest['sha256'],spec)
result.update(oracleSha256=hashlib.sha256(ORACLE.encode()).hexdigest(),boundary='Actual unmodified packaged handler/client configuration and vendored SDK1.43.123 on Lambda Python3.12 ARM64, with SDK endpoints redirected into a synthetic loopback HTTP service and explicit synthetic credentials. Actual SigV4/method/path/response/error parsing, per-request retention/logging gates, one-attempt real socket read timeouts, recovery and five concurrent requests. Gateway claims are fixture inputs. No real AWS IAM/account, retention drift atomicity, external-model quality or cloud deployment acceptance.')
(run/'independent-ticket-sdk-v2-oracle.py').write_text(ORACLE);(run/'independent-ticket-sdk-v2.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['output']);assert result['status']=='passed',result
