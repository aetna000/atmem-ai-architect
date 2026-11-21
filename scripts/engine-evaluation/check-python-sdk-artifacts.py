"""Qualify selected SDK services from pinned wheels in actual isolated runtimes.

Evaluator-only assembly/oracle; not a generated client implementation. Public
dependency source hashes/licenses are retained. No cloud account calls occur.
"""
import argparse,dataclasses,hashlib,io,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.dependency_mirror import inspect_mirror
from server.local_validation import DockerValidationWorker
from server.validation_jobs import registered_validators
ORACLE=r'''
import datetime,hashlib,http.server,json,os,pathlib,sys,threading,zipfile
sys.dont_write_bytecode=True
root=pathlib.Path('/work/source');catalog=json.loads((root/'index.json').read_text());target=pathlib.Path('/tmp/qualified-sdk');target.mkdir()
included=[]
for artifact in catalog['artifacts']:
 content=(root/artifact['file']).read_bytes();assert hashlib.sha256(content).hexdigest()==artifact['sha256']
 with zipfile.ZipFile(root/artifact['file']) as wheel:
  for item in wheel.infolist():
   if item.is_dir():continue
   path=pathlib.PurePosixPath(item.filename);assert not path.is_absolute() and '..' not in path.parts
   if path.parts[:2]==('botocore','data') and len(path.parts)>3 and path.parts[2] not in {'bedrock','bedrock-runtime'}:continue
   destination=target.joinpath(*path.parts);assert not destination.exists();destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(wheel.read(item));included.append(str(path))
sys.path.insert(0,str(target))
import boto3,botocore
from botocore.config import Config
from botocore.exceptions import ClientError,ReadTimeoutError
assert boto3.__version__==botocore.__version__=='1.43.123'
config=Config(region_name='ap-southeast-2',connect_timeout=.2,read_timeout=.2,retries={'total_max_attempts':1,'mode':'standard'})
credentials={'aws_access_key_id':'SYNTHETIC-ONLY','aws_secret_access_key':'SYNTHETIC-ONLY'}
regional=boto3.client('bedrock',config=config,**credentials);assert regional.meta.endpoint_url=='https://bedrock.ap-southeast-2.amazonaws.com'
shape=regional.meta.service_model.operation_model('GetAccountDataRetention');assert shape.http['method']=='GET' and shape.http['requestUri']=='/data-retention' and (shape.input_shape is None or not shape.input_shape.members)
assert set(shape.output_shape.members)=={'mode','updatedAt'}
runtime=boto3.client('bedrock-runtime',config=config,**credentials);assert runtime.meta.endpoint_url=='https://bedrock-runtime.ap-southeast-2.amazonaws.com';assert 'Converse' in runtime.meta.service_model.operation_names
calls=[];mode='none'
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  assert self.path=='/data-retention';assert self.headers.get('Content-Length','0')=='0';assert '/ap-southeast-2/bedrock/aws4_request' in self.headers['Authorization'];calls.append(mode)
  if mode=='timeout':
   import time;time.sleep(.4)
  code,body=(403,{'__type':'AccessDeniedException','message':'Synthetic denied'}) if mode=='denied' else (429,{'__type':'ThrottlingException','message':'Synthetic throttle'}) if mode=='throttle' else (500,{'__type':'InternalServerException','message':'Synthetic unavailable'}) if mode=='internal' else (200,{'mode':mode,'updatedAt':'2026-11-11T00:00:00Z'})
  raw=json.dumps(body).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers()
  try:self.wfile.write(raw)
  except BrokenPipeError:pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();client=boto3.client('bedrock',endpoint_url='http://127.0.0.1:'+str(server.server_port),config=config,**credentials);checks=4
try:
 for value in ['none','default','inherit','aws_review','provider_data_share']:
  mode=value;before=len(calls);reply=client.get_account_data_retention();assert reply['mode']==value and isinstance(reply['updatedAt'],datetime.datetime) and len(calls)==before+1;checks+=1
 for value,expected in [('denied','AccessDeniedException'),('throttle','ThrottlingException'),('internal','InternalServerException')]:
  mode=value;before=len(calls)
  try:client.get_account_data_retention()
  except ClientError as error:assert error.response['Error']['Code']==expected and len(calls)==before+1;checks+=1
  else:raise AssertionError('Expected SDK denial/failure')
 mode='timeout';before=len(calls)
 try:client.get_account_data_retention()
 except ReadTimeoutError:assert len(calls)==before+1;checks+=1
 else:raise AssertionError('Expected SDK timeout')
finally:server.shutdown();server.server_close();thread.join()
assert all(not item.startswith(('numpy/','awscrt/'))for item in included)
print(json.dumps({'marker':'PINNED_SDK_ARTIFACTS_PASSED','checks':checks,'boto3':boto3.__version__,'botocore':botocore.__version__,'getAccountDataRetentionAvailable':True,'converseAvailable':True,'sourceFiles':len(included),'assembledBytes':sum(path.stat().st_size for path in target.rglob('*')if path.is_file()),'services':['bedrock','bedrock-runtime'],'cloudRequests':0}))
'''
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mirror',type=Path,required=True);parser.add_argument('--validators',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--endpoint',required=True);args=parser.parse_args()
checked=inspect_mirror(args.mirror);data=io.BytesIO()
with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED)as archive:
 for file in sorted(args.mirror.iterdir()):archive.writestr(file.name,file.read_bytes())
content=data.getvalue();sha=hashlib.sha256(content).hexdigest();worker=DockerValidationWorker(args.endpoint);validators=registered_validators(json.loads(args.validators.read_text()));out=args.output.resolve();out.mkdir(parents=True,exist_ok=False);results=[]
for ident in ['lambda-python312-tests','python-tests']:
 spec=validators[ident].spec;spec=dataclasses.replace(spec,name='pinned-sdk-artifacts',command=(spec.command[0],'-I','-c',ORACLE),timeout_seconds=60)
 result=worker.run(content,sha,spec);(out/(ident+'.json')).write_text(json.dumps(result,indent=2)+'\n');results.append({'runtime':ident,'status':result['status'],'imageId':spec.image,'platform':spec.platform});print(ident,result['status'],result['output'][-1500:],flush=True)
 assert result['status']=='passed' and 'PINNED_SDK_ARTIFACTS_PASSED' in result['output'],result
(out/'receipt.json').write_text(json.dumps({'passed':True,'catalogSha256':checked['sha256'],'artifactSha256':sha,'oracleSha256':hashlib.sha256(ORACLE.encode()).hexdigest(),'results':results,'cloudOperations':False,'scope':'Pinned pure-Python wheel dependency closure with explicit selected botocore service data, actual Lambda Python3.12 ARM64 and Python3.13 AMD64 execution. SDK operation/model/endpoints and local signed GET/mode/timestamp/denial/throttle/failure/one-attempt timeout contracts. This is SDK artifact qualification, not generated application safety gates, cloud account state, deployment or all-SDK service compatibility.'},indent=2)+'\n');(out/'oracle.py').write_text(ORACLE)
