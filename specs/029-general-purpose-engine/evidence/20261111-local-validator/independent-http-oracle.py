
import concurrent.futures,contextlib,http.client,http.server,importlib.util,io,json,os,sys,threading
config=json.loads(sys.argv[1]);checks=0
os.environ.update(ISSUER='synthetic-only',CLIENT_ID='synthetic-only',AUTH_DOMAIN='http://127.0.0.1',APP_URL='http://127.0.0.1/')
spec=importlib.util.spec_from_file_location('evaluated_http_adapter','scripts/local_server.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),getattr(adapter,config['handler']))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
captured=io.StringIO()
def request(body=None,authorized=True,headers=None,method='POST',path=None):
 client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
 fields={'Content-Type':'application/json',**(headers or {})}
 if authorized:fields['Authorization']=config['token']
 client.request(method,path or config['path'],body,fields);response=client.getresponse()
 result=(response.status,dict(response.getheaders()),response.read());client.close();return result
def suggestion(result):
 status,headers,body=result
 assert status==200,result
 assert 'no-store' in headers['Cache-Control']
 value=json.loads(body)
 assert set(value)=={'summary','topic','urgency','uncertainty'}
 assert all(isinstance(value[key],str) and value[key] for key in ['summary','topic','urgency'])
 assert isinstance(value['uncertainty'],dict) and set(value['uncertainty'])=={'level','reason'}
 assert all(isinstance(value['uncertainty'][key],str) and value['uncertainty'][key] for key in ['level','reason'])
 return value
try:
 with contextlib.redirect_stdout(captured),contextlib.redirect_stderr(captured):
  body=json.dumps({'ticket':'SYNTHETIC-NO-LOG-CANARY-2841: account access failure.'})
  suggestion(request(body));checks+=1
  for bad in ['not-json',json.dumps({'ticket':''}),json.dumps({'ticket':'x'*20481}),json.dumps({'ticket':'é'*10241}),'{"ticket":"a","ticket":"b"}',json.dumps({'ticket':True})]:
   result=request(bad);assert result[0]==400,result
   assert not {'summary','topic','urgency','uncertainty'}.issubset(json.loads(result[2]))
   checks+=1
  result=request(body,authorized=False);assert result[0] in (401,403),result;checks+=1
  result=request(body,headers={'Content-Type':'text/plain'});assert result[0]==400,result;checks+=1
  result=request(method='GET',path='/');assert result[0]==200 and b'<html' in result[2].lower(),result;checks+=1
  with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
   results=list(pool.map(lambda index:request(json.dumps({'ticket':'Synthetic parallel '+str(index)})),range(5)))
  for result in results:suggestion(result);checks+=1
  if config['failureMode']=='native-factory':
   original=adapter.SyntheticBedrock
   class FailedTransport:
    def converse(self,**kwargs):raise TimeoutError('SYNTHETIC-PRIVATE-PROVIDER-DIAGNOSTIC')
   adapter.SyntheticBedrock=FailedTransport
   try:result=request(body)
   finally:adapter.SyntheticBedrock=original
  else:result=request(body,headers={'X-Synthetic-Outcome':'failure'})
  assert result[0]==503,result
  assert b'SYNTHETIC-PRIVATE-PROVIDER-DIAGNOSTIC' not in result[2]
  assert 'summary' not in json.loads(result[2]);checks+=1
  suggestion(request(body));checks+=1
 assert 'SYNTHETIC-NO-LOG-CANARY-2841' not in captured.getvalue()
 checks+=1
finally:
 server.shutdown();server.server_close();thread.join()
print('INDEPENDENT_HTTP_DIAGNOSTIC_PASSED',checks)
