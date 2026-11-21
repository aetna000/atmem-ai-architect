"""Independent connected receiving fixture. Real separate containers, no cloud/host ports.

Only disposable resources labelled with this attempt UUID are cleaned up.
"""
from pathlib import Path
import argparse,concurrent.futures,datetime,hashlib,json,os,secrets,subprocess,time,traceback,uuid
import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--attempt',required=True);args=parser.parse_args();assert args.attempt.isalnum()
BULK=ROOT/'.local/external-artifacts/native-amd64-runtime/v1'/('connected-'+args.attempt);BULK.mkdir()
IMAGE=(ROOT/'.local/external-artifacts/native-amd64-runtime/v1/receiving-build-v1/image-id.txt').read_text().strip();PG='sha256:996e9dc583ba9f0265a2c75547a9c95fb22c251e394749cab205a0a00e1856a1';ENDPOINT='unix:///Users/javadtaghia/.avm/c/amd64/validator.sock'
ident=uuid.uuid4().hex;prefix='atmem-recv-'+ident[:10];network=prefix+'-net';volume=prefix+'-data';names={role:prefix+'-'+role for role in ['db','control','api','worker']};created=[];checks=[];app_inputs={}
receipt={'format':'atmem.independent-connected-receiver','version':1,'attempt':args.attempt,'fixtureId':ident,'imageId':IMAGE,'postgresImage':PG,'artifactSha256':'69bdacf7d6813bfdd977b007abe7c94d8c3308cb2e09f9fd09c6cb39cf61031d','checks':checks,'evaluatorSources':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()for name in ['run.py','control.py','destination.py']},'cloudOperations':False,'nativeGoogleIdentityOrAccountAcceptance':False,'ownerProjectWrites':0,'fullAcceptance':False,'resourcesCleaned':False}
def docker(*arguments,input=None,check=True):
 result=subprocess.run(['docker','--host',ENDPOINT,*arguments],input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if check and result.returncode:raise RuntimeError('Docker '+arguments[0]+' failed: '+result.stderr.decode(errors='replace')[-2000:])
 return result

def checkpoint(name,**values):
 checks.append({'name':name,'passed':True,'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),**values});(BULK/'checkpoint.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Verified '+name,flush=True)
def write_files(container,files):
 code="import json,pathlib,sys;files=json.loads(sys.stdin.buffer.read(1000000));[(pathlib.Path('/runtime',name).write_text(value),pathlib.Path('/runtime',name).chmod(0o600))for name,value in files.items()]"
 docker('exec','-i',container,'/usr/local/bin/python3','-I','-c',code,input=json.dumps(files).encode())
def rpc(value):
 r=docker('exec','-i',names['control'],'/usr/local/bin/python3','-I','/runtime/control.py',input=json.dumps(value,ensure_ascii=True,allow_nan=False).encode());return json.loads(r.stdout)
def sql(query,params=(),role='admin',rollback=False):return rpc({'action':'sql','query':query,'params':list(params),'role':role,'rollback':rollback})
def events():return rpc({'action':'events'})['events']
def wait_until(operation,timeout=120):
 end=time.monotonic()+timeout;last=None
 while time.monotonic()<end:
  try:
   last=operation()
   if last:return last
  except (RuntimeError,ConnectionError)as error:last=str(error)[-2200:]
  time.sleep(.25)
 raise AssertionError('Receiving observation deadline, no acceptance: '+str(last))
account=str(uuid.uuid4());foreign=str(uuid.uuid4());number='908070605040';service='independent-sample-receiver';origin='https://independent-staff.example.test';issuer='https://cloud.google.com/iap';audience=f'/projects/{number}/locations/australia-southeast1/services/{service}'
key=ec.generate_private_key(ec.SECP256R1());jwk=json.loads(jwt.algorithms.ECAlgorithm.to_jwk(key.public_key()));jwk.update(kid='independent-es256',use='sig',alg='ES256')
def token(subject='staff',claims=None,signer=None):
 now=int(time.time());value={'iss':issuer,'aud':audience,'iat':now,'exp':now+300,'sub':subject,'email':subject+'@independent.example.test','roles':['reviewer'],'groups':['ignored']};value.update(claims or {});return jwt.encode(value,signer or key,algorithm='ES256',headers={'kid':'independent-es256'})
def request(method,path,body=None,subject='staff',assertion=None,dedup=None,raw=None,extra_headers=None):
 headers={'x-goog-iap-jwt-assertion':assertion or token(subject),'Origin':origin}
 if body is not None or raw is not None:headers['Content-Type']='application/json'
 if dedup:headers['Idempotency-Key']=dedup
 headers.update(extra_headers or {});call={'action':'http','method':method,'path':path,'headers':headers}
 if body is not None:call['body']=body
 if raw is not None:call['raw']=raw
 return rpc(call)
def expect(response,status):
 assert response['status']==status and isinstance(response['body'],dict),(status,response)
 assert {k.lower():v for k,v in response['headers'].items()}.get('cache-control')=='no-store',response['headers']
 return response['body']
def submit(value,key=None,subject='staff'):
 return expect(request('POST','/api/operations',value,subject=subject,dedup=key or uuid.uuid4().hex),202)['operation']['id']
def operation(operation_id,state='review'):
 def read():
  value=expect(request('GET','/api/operations/'+operation_id,subject='reviewer'),200)['operation']
  assert value['state']!='dead',value
  return value if value['state']==state else None
 return wait_until(read)
def inspect(operation_id):return expect(request('POST','/api/operations/'+operation_id+'/inspect',{},subject='reviewer'),200)
def approve(operation_id,inspection):return expect(request('POST','/api/operations/'+operation_id+'/approve',{'revision':inspection['operation']['revision'],'payloadSha256':inspection['payloadSha256']},subject='reviewer'),200)
fixtures={'roles':{'api':'receiving_api','worker':'receiving_worker'},'passwords':{role:secrets.token_hex(24)for role in ['admin','api','worker']},'destinationToken':secrets.token_hex(24)}
fixtures['dsns']={role:'host=db port=5432 dbname=samples user='+({'admin':'receiving_operator'}.get(role,fixtures['roles'].get(role)))+' password='+fixtures['passwords'][role]for role in ['admin','api','worker']}
tls_key=ec.generate_private_key(ec.SECP256R1());now=datetime.datetime.now(datetime.timezone.utc);name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'independent local recipient')]);cert=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(tls_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1)).not_valid_after(now+datetime.timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName('destination.test')]),False).sign(tls_key,hashes.SHA256());ca=cert.public_bytes(serialization.Encoding.PEM).decode();private=tls_key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode()
GATE="import os,pathlib,sys,time;deadline=time.monotonic()+180\nwhile not pathlib.Path('/runtime/ready').exists():\n if time.monotonic()>deadline:raise RuntimeError('Fixture injection deadline')\n time.sleep(.05)\nos.execv(sys.executable,[sys.executable,'-I','/app/sample_entry.py',*sys.argv[1:]])"
def container(role,image,extra,command):
 result=docker('run','--pull','never','-d','--name',names[role],'--label','atmem.receiver='+ident,'--network',network,'--network-alias',role,'--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','96'if role=='db'else'64','--memory','384m'if role=='db'else'256m','--cpus','1',*extra,image,*command);created.append(names[role]);return result.stdout.decode().strip()
def app(role):
 container(role,IMAGE,['--tmpfs','/runtime:rw,noexec,nosuid,nodev,size=2m,uid=10001,gid=10001,mode=0700','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=8m,uid=10001,gid=10001,mode=0700','--env','PORT=8080','--env','LISTEN_HOST=0.0.0.0','--entrypoint','/usr/local/bin/python3'],['-I','-c',GATE,role,'/runtime/config.json',*(['/runtime/destination-token']if role=='worker'else[])])
 config={'mode':'local-fixture','accountId':account,'projectNumber':number,'serviceName':service,'publicOrigin':origin,'destination':'https://destination.test:8443/route','destinationScope':'independent-receiver','destinationCaSha256':hashlib.sha256(ca.encode()).hexdigest(),'fixtureJwks':{'keys':[jwk]},'fixtureDsnFile':'/runtime/database.dsn','fixtureCaFile':'/runtime/ca.pem'}
 files={'config.json':json.dumps(config),'database.dsn':fixtures['dsns'][role]}
 if role=='worker':files.update({'ca.pem':ca,'destination-token':fixtures['destinationToken']})
 files['ready']='go';app_inputs[role]=dict(files);write_files(names[role],files)
 if role=='worker':write_files(names['control'],{'application-config.json':json.dumps(config)})
try:
 docker('network','create','--internal','--label','atmem.receiver='+ident,network);docker('volume','create','--label','atmem.receiver='+ident,volume)
 # Only this new empty fixture volume is initialized. No user/host bind mounts.
 docker('run','--pull','never','--rm','--network','none','--read-only','--user','0:0','--cap-drop','ALL','--cap-add','CHOWN','--mount','type=volume,src='+volume+',dst=/var/lib/postgresql/data','--entrypoint','/bin/chown',PG,'999:999','/var/lib/postgresql/data')
 container('db',PG,['--user','999:999','--tmpfs','/var/run/postgresql:rw,nosuid,nodev,size=2m,uid=999,gid=999,mode=0700','--tmpfs','/tmp:rw,nosuid,nodev,size=8m,uid=999,gid=999,mode=0700','--mount','type=volume,src='+volume+',dst=/var/lib/postgresql/data','--env','POSTGRES_USER=receiving_operator','--env','POSTGRES_DB=samples','--env','POSTGRES_PASSWORD='+fixtures['passwords']['admin'],'--env','POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256'],['postgres','-c','shared_buffers=32MB','-c','max_connections=60','-c','fsync=on'])
 wait_until(lambda:docker('exec',names['db'],'pg_isready','-U','receiving_operator','-d','samples',check=False).returncode==0)
 container('control',IMAGE,['--network-alias','destination.test','--tmpfs','/runtime:rw,noexec,nosuid,nodev,size=4m,uid=10001,gid=10001,mode=0700','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=8m,uid=10001,gid=10001,mode=0700','--entrypoint','/usr/local/bin/python3'],['-I','-c','import time;time.sleep(1800)'])
 write_files(names['control'],{'fixture.json':json.dumps(fixtures),'admin.dsn':fixtures['dsns']['admin'],'tls.pem':ca,'tls.key':private,'control.py':(HERE/'control.py').read_text(),'destination.py':(HERE/'destination.py').read_text(),'mode':'success','sample_admin.py':(ROOT/'.local/external-artifacts/native-gcp-water/v1/native-run/unpacked/application/sample_admin.py').read_text()})
 rpc({'action':'roles'})
 cli="import pathlib,sys;sys.path.insert(0,'/app');sys.argv=['sample_admin.py',*sys.argv[1:]];exec(compile(pathlib.Path('/runtime/sample_admin.py').read_bytes(),'/runtime/sample_admin.py','exec'),{'__name__':'__main__','__file__':'/runtime/sample_admin.py'})"
 def admin(*arguments):docker('exec',names['control'],'/usr/local/bin/python3','-I','-c',cli,'--dsn-file','/runtime/admin.dsn',*arguments)
 admin('initialize','--api-role',fixtures['roles']['api'],'--worker-role',fixtures['roles']['worker'])
 for subject,acct,reviewer,revoked in [('staff',account,False,False),('other',account,False,False),('reviewer',account,True,False),('revoked',account,True,True),('foreign',foreign,True,False)]:admin('membership','--account',acct,'--iap-subject',subject,*(['--reviewer']if reviewer else[]),*(['--revoked']if revoked else[]))
 docker('exec','-d',names['control'],'/usr/local/bin/python3','-I','/runtime/destination.py')
 app('api');wait_until(lambda:rpc({'action':'http','method':'GET','path':'/readyz'})['status']==200)
 assert sql('SHOW server_version_num')['rows'][0]['server_version_num']=='170011'
 for role in ['api','worker']:
  props=sql('SELECT current_user,rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user',role=role)['rows'][0];assert props['current_user']==fixtures['roles'][role]and not any(v for k,v in props.items()if k!='current_user')
 checkpoint('clean image, separate PostgreSQL17, delivered operator CLI and restricted identities')
 cases=json.loads((ROOT/'specs/029-general-purpose-engine/evidence/20261112-native-gcp-water/requirements-cases-v1.json').read_text());first=cases['validSourceCases'][0]['source'];dedup='independent-concurrent-'+uuid.uuid4().hex
 with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:ids=list(pool.map(lambda _:submit(first,dedup),range(4)))
 assert len(set(ids))==1;initial=ids[0]
 assert sql("SELECT count(*) AS n FROM workflow.procrastinate_jobs WHERE args->>'operation_id'=%s",[initial])['rows'][0]['n']==1
 expect(request('POST','/api/operations',{**first,'readingScaled':17},dedup=dedup),409);expect(request('POST','/api/operations',first,dedup=dedup,subject='other'),409)
 checkpoint('four concurrent HTTP submissions commit one operation and initial queue job')
 app('worker');wait_until(lambda:rpc({'action':'http','host':'worker','method':'GET','path':'/healthz'})['status']==200)
 valid_ids=[]
 for i,case in enumerate(cases['validSourceCases']):
  op=initial if i==0 else submit(case['source']);row=operation(op);assert row['source']==case['source']and row['result']==case['expectedResult'],row;valid_ids.append(op)
  hist=expect(request('GET','/api/operations/'+op+'/history'),200)['history'];assert hist[0]['result']==case['expectedResult']
 assert not events();before=sql('SELECT count(*)AS n FROM workflow.operations')['rows'][0]['n']
 for case in cases['invalidSourceCases']:expect(request('POST','/api/operations',case['source'],dedup=uuid.uuid4().hex),400)
 assert sql('SELECT count(*)AS n FROM workflow.operations')['rows'][0]['n']==before
 checkpoint('frozen10 valid/25 invalid sources through actual HTTP, SQL, queue and processing children; no delivery before approval')
 for subject in ['revoked','foreign','unenrolled']:expect(request('GET','/api/session',subject=subject),403)
 for changes in [{'iss':'https://foreign.invalid'},{'aud':audience+'-foreign'},{'aud':[audience]},{'exp':int(time.time())-1},{'iat':int(time.time())+120},{'exp':int(time.time())+1000},{'email':'fake@foreign-project.iam.gserviceaccount.com'}]:expect(request('GET','/api/session',assertion=token(claims=changes)),403)
 expect(request('GET','/api/session',assertion=token(signer=ec.generate_private_key(ec.SECP256R1()))),403);expect(request('GET','/api/session',assertion='malformed'),403)
 expect(request('GET','/api/operations/'+initial,subject='other'),404);assert initial not in {x['id']for x in expect(request('GET','/api/operations',subject='other'),200)['operations']}
 expect(request('POST','/api/operations/'+initial+'/inspect',{}),403)
 checkpoint('signed IAP denials, live SQL membership and account/owner isolation ignore role/group claims')
 op=valid_ids[0];seen=inspect(op);oldrev=seen['operation']['revision'];changed=expect(request('POST','/api/operations/'+op+'/review',{'revision':oldrev,'reviewNote':''},subject='reviewer'),200)['operation'];assert changed['revision']==oldrev+1 and changed['result']['reviewNote']==''
 expect(request('POST','/api/operations/'+op+'/approve',{'revision':oldrev,'payloadSha256':seen['payloadSha256']},subject='reviewer'),409)
 fresh=inspect(op);expect(request('POST','/api/operations/'+op+'/approve',{'revision':fresh['operation']['revision'],'payloadSha256':'0'*64},subject='reviewer'),409)
 expect(request('POST','/api/operations/'+op+'/review',{'revision':changed['revision'],'reviewNote':'','readingNgPerL':1},subject='reviewer'),400)
 admin('membership','--account',account,'--iap-subject','reviewer','--reviewer','--revoked');expect(request('POST','/api/operations/'+op+'/approve',{'revision':fresh['operation']['revision'],'payloadSha256':fresh['payloadSha256']},subject='reviewer'),403);admin('membership','--account',account,'--iap-subject','reviewer','--reviewer')
 fresh=inspect(op);approve(op,fresh);operation(op,'sent');received=events();assert len(received)==1;event=received[0];source=first;expected={k:source[k]for k in ['stationCode','readingScaled','unit','sampleKind']};expected.update(cases['validSourceCases'][0]['expectedResult']);expected['reviewNote']=''
 assert event['body']==expected and event['operationId']==op and event['approvedHash']==fresh['payloadSha256']and event['credentialMatched']
 checkpoint('exact inspection, empty edit, stale/tampered/revoked denials and real TLS seven-field delivery')
 for role in ['api','worker']:
  for query in ["UPDATE workflow.memberships SET active=true","DELETE FROM workflow.results_history","UPDATE workflow.results_history SET actor='forbidden'","CREATE TABLE workflow.forbidden_test(id int)","UPDATE workflow.schema_version SET source_sha256=repeat('0',64)","SELECT rolpassword FROM pg_authid"]:
   result=sql(query,role=role,rollback=True);assert result.get('sqlstate')=='42501',{'unexpectedPermissionResult':result.get('sqlstate','query_succeeded')}
 checkpoint('runtime SQL roles cannot enroll, erase history or perform schema DDL')

 # Protocol and complete review-note checks are independent of generated tests.
 expect(request('POST','/api/operations',first,dedup=uuid.uuid4().hex,extra_headers={'Origin':'https://foreign.invalid'}),403)
 expect(request('POST','/api/operations',first,dedup=uuid.uuid4().hex,extra_headers={'Content-Type':'text/plain'}),415)
 expect(request('POST','/api/operations?accountId='+foreign,first,dedup=uuid.uuid4().hex),400)
 raw=json.dumps(first).replace('"readingScaled": 0','"readingScaled": 0, "readingScaled": 1');assert raw!=json.dumps(first);expect(request('POST','/api/operations',raw=raw,dedup=uuid.uuid4().hex),400)
 review_op=valid_ids[1]
 for note in cases['reviewCases']['invalidNotes']:
  snapshot=inspect(review_op);expect(request('POST','/api/operations/'+review_op+'/review',{'revision':snapshot['operation']['revision'],'reviewNote':note},subject='reviewer'),400)
 for note in cases['reviewCases']['validNotes']:
  snapshot=inspect(review_op);edited=expect(request('POST','/api/operations/'+review_op+'/review',{'revision':snapshot['operation']['revision'],'reviewNote':note},subject='reviewer'),200)['operation'];assert edited['revision']==snapshot['operation']['revision']+1 and edited['result']['reviewNote']==note
 snapshot=inspect(review_op);number=snapshot['operation']['result']['readingNgPerL']
 for field,value in [('readingNgPerL',number-1),('readingNgPerL',number+1),('dutyPriority','urgent')]:expect(request('POST','/api/operations/'+review_op+'/review',{'revision':snapshot['operation']['revision'],'reviewNote':'',field:value},subject='reviewer'),400)
 checkpoint('strict Origin/media/query/duplicate JSON, full note bounds and both derived-number mutation directions')
 binding_op=valid_ids[2];snapshot=inspect(binding_op);before_events=len(events())
 for field in ['endpointSha256','payloadContractSha256','applicationContractSha256']:
  sql("UPDATE workflow.operations SET destination_contract=jsonb_set(destination_contract,ARRAY[%s]::text[],to_jsonb(%s::text)) WHERE id=%s",[field,'0'*64,binding_op])
  expect(request('POST','/api/operations/'+binding_op+'/approve',{'revision':snapshot['operation']['revision'],'payloadSha256':snapshot['payloadSha256']},subject='reviewer'),409)
  sql('UPDATE workflow.operations SET destination_contract=%s::jsonb WHERE id=%s',[json.dumps(snapshot['destination']),binding_op])
 assert len(events())==before_events
 checkpoint('changed endpoint, payload and application-policy bindings cannot reuse an inspection')
 # Paused worker + controlled expiry exercises component fencing with actual role/SQL.
 docker('pause',names['worker'])
 try:
  fenced=submit(first);assert rpc({'action':'extraction-fence','operationId':fenced,'expectedResult':cases['validSourceCases'][0]['expectedResult']})['oldLeaseRejected'];operation(fenced)
  snapshot=inspect(fenced);approve(fenced,snapshot);assert rpc({'action':'dispatch-fence','operationId':fenced})['oldLeaseRejected'];operation(fenced,'unknown');assert len(events())==before_events
 finally:docker('unpause',names['worker'])
 checkpoint('real SQL expired/reclaimed extraction and dispatch leases reject stale completion; no unverified replay')

 unknown=valid_ids[-1];rpc({'action':'mode','value':'ambiguous'});inspection=inspect(unknown);approve(unknown,inspection);operation(unknown,'unknown');count=len(events());assert count==2
 approve(unknown,inspection);assert len(events())==count
 docker('restart','-t','1',names['worker']);write_files(names['worker'],app_inputs['worker']);wait_until(lambda:rpc({'action':'http','host':'worker','method':'GET','path':'/healthz'})['status']==200)
 docker('restart','-t','1',names['db']);wait_until(lambda:docker('exec',names['db'],'pg_isready','-U','receiving_operator','-d','samples',check=False).returncode==0)
 assert operation(unknown,'unknown')['source']==cases['validSourceCases'][-1]['source'];approve(unknown,inspection);time.sleep(6);assert len(events())==count;assert operation(initial,'sent')['result']['reviewNote']==''
 checkpoint('ambiguous external effect remains unknown across repeated approval and real worker/database container restarts',workerVolatileInputsRestoredIdentically=True)
 # Structural fixture receipts contain no credentials, signing key or token.
 controls=[]
 for role in ['api','worker','control','db']:
  info=json.loads(docker('inspect',names[role]).stdout)[0];assert not info['HostConfig'].get('PortBindings')and info['HostConfig']['ReadonlyRootfs']and info['HostConfig']['CapDrop']==['ALL'];assert not any(m['Type']=='bind'for m in info['Mounts']);controls.append({'role':role,'imageId':info['Image'],'user':info['Config']['User'],'network':network,'hostPorts':False,'readOnlyRoot':True,'capDropAll':True,'noHostBindMounts':True})
 assert json.loads(docker('network','inspect',network).stdout)[0]['Internal']is True
 receipt['containerControls']=controls;receipt['connectedGroupsPassed']=len(checks);receipt['fullAcceptance']=False;receipt['connectedScopePassed']=True
except BaseException as error:
 receipt['failureType']=type(error).__name__;receipt['failure']=str(error);receipt['connectedScopePassed']=False;raise
finally:
 for name in created:
  result=docker('logs',name,check=False);(BULK/(name+'.log')).write_bytes(result.stdout+result.stderr)
  info=docker('inspect',name,check=False)
  if info.returncode==0:
   assert json.loads(info.stdout)[0]['Config']['Labels'].get('atmem.receiver')==ident;docker('rm','-f',name,check=False)
 for kind,name in [('volume',volume),('network',network)]:
  info=docker(kind,'inspect',name,check=False)
  if info.returncode==0:
   assert json.loads(info.stdout)[0].get('Labels',{}).get('atmem.receiver')==ident;docker(kind,'rm',name,check=False)
 receipt['resourcesCleaned']=all(docker('inspect',name,check=False).returncode!=0 for name in created)and docker('volume','inspect',volume,check=False).returncode!=0 and docker('network','inspect',network,check=False).returncode!=0
 (BULK/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
