"""Independent oracle running inside the unchanged generated application image.

Only synthetic native JWT keys, local PostgreSQL connections and a private TLS CA
are injected. All application modules and production dependencies come from /app.
"""
import asyncio,datetime,hashlib,importlib.metadata,json,os,secrets,ssl,sys,tempfile,threading,time,uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch,Mock
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path.insert(0,'/app')
import psycopg,jwt,uvicorn
from psycopg import sql
from psycopg.conninfo import make_conninfo
from cryptography import x509
from cryptography.hazmat.primitives import serialization,hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import equipment_api,equipment_worker,workflow_identity,workflow_application
from workflow_database import initialize_database,grant_runtime_roles
from workflow_bindings import write_binding,load_bound_profile
from workflow_contract import normalized_contract
from workflow_application import membership_key

class Sink:
    def __init__(self,root):
        self.calls=[];self.mode='completed';self.token=secrets.token_urlsafe(24)
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')]);now=datetime.datetime.now(datetime.timezone.utc)
        cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1)).not_valid_after(now+datetime.timedelta(hours=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]),critical=False).sign(key,hashes.SHA256()))
        self.ca=root/'ca.pem';self.ca.write_bytes(cert.public_bytes(serialization.Encoding.PEM));private=root/'tls.key';private.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));private.chmod(0o600);owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                if self.headers.get('Authorization')!='Bearer '+owner.token:self.send_error(401);return
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path!='/actions' or self.headers.get('Idempotency-Key')!=body['operation_id']:self.send_error(400);return
                owner.calls.append(body);result={'operation_id':body['operation_id'],'payload_sha256':body['payload_sha256'],'external_id':'synthetic-'+str(len(owner.calls)),'status':owner.mode};raw=json.dumps(result).encode()
                self.send_response(202 if owner.mode=='pending'else 200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.daemon_threads=True;context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(self.ca,private);self.server.socket=context.wrap_socket(self.server.socket,server_side=True)
        self.url='https://localhost:'+str(self.server.server_port)+'/actions';self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)

async def main(inputs):
    checks=[];before={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('/app').glob('*.py')};assert before==inputs['applicationHashes'],'Application image source differs from captured package';assert os.getuid()==10001
    auxiliary={name:hashlib.sha256(Path(path).read_bytes()).hexdigest()for name,path in [('workflow_schema.sql','/app/workflow_schema.sql'),('requirements.lock','/build/requirements.lock')]};assert auxiliary==inputs['auxiliaryHashes']
    versions={name:importlib.metadata.version(name)for name in inputs['runtimePins']};assert versions==inputs['runtimePins'],'Installed image dependencies differ from the exact runtime lock'
    checks.append('exact image SQL schema/runtime lock and every installed runtime dependency match captured package')
    with psycopg.connect(inputs['adminDsn'])as c:
        assert int(c.execute('SHOW server_version_num').fetchone()[0])//10000==17
        initialize_database(c)
        roles=[]
        for suffix in ['api','worker']:
            name='image_'+suffix;password=secrets.token_urlsafe(24);roles.append((name,password));c.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(name),sql.Literal(password)))
        grant_runtime_roles(c,*[r[0]for r in roles])
    api_dsn,worker_dsn=[make_conninfo(inputs['adminDsn'],user=n,password=p)for n,p in roles]
    for dsn in [api_dsn,worker_dsn]:
        with psycopg.connect(dsn)as c:
            try:c.execute('DELETE FROM workflow.events')
            except psycopg.errors.InsufficientPrivilege:pass
            else:raise AssertionError('Runtime role can erase audit events')
    checks.append('actual image bytes/UID and separate restricted PostgreSQL17 roles')
    with tempfile.TemporaryDirectory(prefix='image-journey-')as folder:
        root=Path(folder);sink=Sink(root);server=None;worker_task=None;api_task=None
        try:
            account=json.loads(Path('/app/application-template.json').read_text())['accountId'];staff,other,reviewer=[str(uuid.uuid4())for _ in range(3)]
            settings={'POOL_ID':'ap-southeast-2_ImageFixture','CLIENT_ID':'imagefixtureclient','AUTH_ORIGIN':'https://image-fixture.auth.ap-southeast-2.amazoncognito.com','AUTH_SCOPE':'equipment/process'}
            # Uvicorn port is reserved before constructing the bound public origin.
            import socket
            listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(128);origin='http://127.0.0.1:'+str(listener.getsockname()[1]);listener.setblocking(False)
            values=[('api','publicOrigin',origin),* [('identity',k,v)for k,v in settings.items()],('destination','endpointSha256',normalized_contract(sink.url,'image-journey')['endpointSha256']),('destination','scope','image-journey')]
            ledger={'version':1,'outputs':[{'componentId':'work:'+o,'provider':'aws','environment':'qualification','name':n,'value':v,'sensitive':False,'sourceSha256':'b'*64}for o,n,v in values]};ledger_path=root/'outputs.json';ledger_path.write_text(json.dumps(ledger));binding=root/'binding';write_binding('/app/application-template.json',ledger_path,binding);profile=load_bound_profile('/app/application-template.json',binding)
            credential=root/'destination.token';credential.write_text(sink.token);credential.chmod(0o600)
            env={'BINDING_DIRECTORY':str(binding),'APPLICATION_TEMPLATE':'/app/application-template.json','DESTINATION_ENDPOINT':sink.url,'DESTINATION_CREDENTIAL_FILE':str(credential)}
            with psycopg.connect(inputs['adminDsn'])as c:
                c.execute('INSERT INTO workflow.accounts(id)VALUES(%s)',(account,))
                for subject,roles_for_subject in [(staff,['user']),(other,['user']),(reviewer,['reviewer'])]:c.execute('INSERT INTO workflow.memberships(account_id,subject,roles)VALUES(%s,%s,%s)',(account,membership_key(profile,subject),roles_for_subject))
            key=rsa.generate_private_key(public_exponent=65537,key_size=2048);jwks=Mock();jwks.get_signing_key_from_jwt.return_value=SimpleNamespace(key=key.public_key());native=workflow_identity.native_staff_identity
            with patch.dict(os.environ,env,clear=True),patch('workflow_application.native_database',return_value=api_dsn),patch('workflow_identity.native_staff_identity',side_effect=lambda p,c,**kw:native(p,c,jwks=jwks)):
                app=equipment_api.app()
            with patch('workflow_application.native_database',return_value=worker_dsn):worker=equipment_worker.build(env)
            worker.deliver.stage.environment['SSL_CERT_FILE']=str(sink.ca)
            server=uvicorn.Server(uvicorn.Config(app,log_level='critical',access_log=False,proxy_headers=False));api_task=asyncio.create_task(server.serve(sockets=[listener]));worker_task=asyncio.create_task(worker.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=2))
            for _ in range(200):
                if server.started:break
                if api_task.done():await api_task
                await asyncio.sleep(.025)
            assert server.started,'Actual HTTP listener did not start'
            def request(method,path,data,who,idem=None,forged=False):
                now=int(time.time());claims={'iat':now-1,'exp':now+300,'sub':who,'iss':'https://cognito-idp.ap-southeast-2.amazonaws.com/'+settings['POOL_ID'],'client_id':settings['CLIENT_ID'],'token_use':'access','scope':'openid '+settings['AUTH_SCOPE'],'username':'image-fixture'}
                token='forged'if forged else jwt.encode(claims,key,algorithm='RS256',headers={'kid':'synthetic-image-key'})
                headers={'Authorization':'Bearer '+token,'Origin':origin,'Content-Type':'application/json','Idempotency-Key':idem or str(uuid.uuid4())}
                try:
                    with urlopen(Request(origin+path,data=None if data is None else json.dumps(data).encode(),headers=headers,method=method),timeout=5)as r:return r.status,json.load(r)
                except HTTPError as r:return r.code,json.load(r)
            async def http(method,path,data=None,who=staff,**kwargs):return await asyncio.to_thread(request,method,path,data,who,**kwargs)
            async def until(op,expected):
                for _ in range(300):
                    if worker_task.done():await worker_task
                    with psycopg.connect(inputs['adminDsn'])as c:state=c.execute('SELECT state FROM workflow.operations WHERE id=%s',(op,)).fetchone()[0]
                    if state==expected:return
                    await asyncio.sleep(.05)
                raise AssertionError('Operation failed to reach '+expected+'; observed '+state)
            checks.append('actual image API/worker factories and real Uvicorn HTTP listener; synthetic native keys/SQL/CA disclosed')
            source={'itemId':'image-camera','memberId':'member-1','requestedDays':30,'fragile':False};idem=str(uuid.uuid4());status,result=await http('POST','/api/operations',{'source':source},idem=idem);assert status==202,(status,result);op=result['operation']['id']
            status,result=await http('POST','/api/operations',{'source':source},idem=idem);assert status==202 and result['operation']['id']==op;await until(op,'review')
            status,result=await http('GET','/api/operations/'+op);assert status==200 and result['operation']['result']=={'loanDays':14,'inspectionRequired':False}
            checks.append('HTTP submit/replay, real durable queue and actual bounded process child apply14-day policy')
            for who in [other]:assert (await http('GET','/api/operations/'+op,who=who))[0]in {403,404}
            assert not(await http('GET','/api/operations',who=other))[1]['operations'];assert(await http('POST','/api/operations/'+op+'/approve',{'revision':1}))[0]==403
            assert(await http('GET','/api/operations/'+op,forged=True))[0]==403
            checks.append('own-read/list and reviewer-only approval with real native JWT cryptography; forged token denied')
            for bad in [{'source':source,'accountId':str(uuid.uuid4())},{'source':{**source,'requestedDays':True}}]:assert(await http('POST','/api/operations',bad))[0]==400
            checks.append('account override and boolean integer input denied over real HTTP')
            assert(await http('POST','/api/operations/'+op+'/approve',{'revision':1},who=reviewer))[0]==200;await until(op,'sent');assert len(sink.calls)==1 and sink.calls[0]['result']=={'itemId':'image-camera','memberId':'member-1','loanDays':14,'inspectionRequired':False}
            checks.append('reviewer approval and actual delivery child publish exact payload once through verified loopback TLS')
            fragile={**source,'itemId':'glassware','fragile':True};status,result=await http('POST','/api/operations',{'source':fragile});assert status==202;second=result['operation']['id'];await until(second,'review')
            assert(await http('POST','/api/operations/'+second+'/review',{'revision':1,'result':{'loanDays':4,'inspectionRequired':True}},who=reviewer))[0]in {400,409}
            status,result=await http('POST','/api/operations/'+second+'/review',{'revision':1,'result':{'loanDays':2,'inspectionRequired':True}},who=reviewer);assert status==200;revision=result['operation']['revision'];assert revision==2
            assert(await http('POST','/api/operations/'+second+'/approve',{'revision':1},who=reviewer))[0]==409
            checks.append('fragile3-day policy, valid edit and stale approval revision enforced through HTTP')
            sink.mode='pending';assert(await http('POST','/api/operations/'+second+'/approve',{'revision':revision},who=reviewer))[0]==200;await until(second,'unknown');assert len(sink.calls)==2
            with psycopg.connect(inputs['adminDsn'])as c:jobs=c.execute("SELECT count(*) FROM workflow.procrastinate_jobs WHERE args->>'operation_id'=%s",(second,)).fetchone()[0]
            assert(await http('POST','/api/operations/'+second+'/approve',{'revision':revision},who=reviewer))[0]in {200,409};await asyncio.sleep(.3)
            with psycopg.connect(inputs['adminDsn'])as c:assert c.execute("SELECT count(*) FROM workflow.procrastinate_jobs WHERE args->>'operation_id'=%s",(second,)).fetchone()[0]==jobs
            assert len(sink.calls)==2;checks.append('uncertain TLS outcome remains unknown with no second job or effect on repeat approval')
            with psycopg.connect(inputs['adminDsn'])as c:c.execute('UPDATE workflow.memberships SET active=false WHERE account_id=%s AND subject=%s',(account,membership_key(profile,staff)))
            assert(await http('GET','/api/operations/'+op))[0]==403;checks.append('live membership revocation overrides an unexpired signed token')
            after={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('/app').glob('*.py')};assert before==after
            print(json.dumps({'passed':True,'checks':checks,'applicationHashes':before,'auxiliaryHashes':auxiliary,'dependencyVersions':versions,'applicationSourceUnchanged':True,'uid':os.getuid(),'httpTransport':'real loopback TCP/Uvicorn','database':'private PostgreSQL17 TCP, separate nonadmin API/worker roles','destination':'real loopback TLS with synthetic CA','cloudOperations':False,'boundary':'Actual unchanged emitted image source/dependencies/factories and process children. Synthetic native keys, SQL role injection, public output ledger and CA; no AWS resource/IAM/native DB authentication or full-project acceptance.'}))
        finally:
            if server is not None:server.should_exit=True
            if worker_task is not None:worker_task.cancel()
            await asyncio.gather(*[t for t in [api_task,worker_task]if t is not None],return_exceptions=True)
            sink.close()

asyncio.run(main(json.load(sys.stdin)))
