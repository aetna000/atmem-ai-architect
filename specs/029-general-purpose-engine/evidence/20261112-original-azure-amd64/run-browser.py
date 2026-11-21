"""Original Azure browser journey; owned internal network, no host ports/mounts."""
import argparse,datetime,hashlib,json,os,secrets,subprocess,time,uuid
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=False)
endpoint='unix:///Users/javadtaghia/.avm/c/engine/docker.sock';config=OUT/'docker-config';config.mkdir();(config/'config.json').write_text('{"auths":{}}\n')
prefix=['docker','--host',endpoint,'--config',str(config)];environment={'PATH':os.environ['PATH'],'DOCKER_HOST':endpoint,'DOCKER_CONFIG':str(config)}
def docker(*args,timeout=30,**kwargs):return subprocess.run([*prefix,*args],env=environment,timeout=timeout,capture_output=True,**kwargs)
def checked(*args,**kwargs):
    result=docker(*args,**kwargs)
    if result.returncode:raise RuntimeError('Owned browser fixture action failed: '+args[0]+' '+result.stderr.decode(errors='replace')[-1000:])
    return result.stdout
app_image='sha256:00486a3f6db3ac32d3f9fb0ccb3819944f17c54933e83adbee7a77fec9d678e1'
browser_image='sha256:df7f71a8588253403dfa833c5c4aacc95ca340204a88d5483edd58131c7f1128'
policy=ROOT/'.local/engine-product/browser-runtime-preparation/browser-seccomp.json'
assert hashlib.sha256(policy.read_bytes()).hexdigest()=='e53c15d248f57bceec0a3a16fad1b4ab0d05a7bddb455f86a60e2dba5612cdf7'
ident='atmem-azure-browser-'+uuid.uuid4().hex[:12];network=ident+'-net';app=ident+'-app';browser=ident+'-browser'
app_process=None;app_log=None;created=[];receipt={'passed':False,'appImage':app_image,'browserImage':browser_image,'cloudOperations':False}
try:
    for image,arch in [(app_image,'amd64'),(browser_image,'arm64')]:
        observed=json.loads(checked('image','inspect',image))[0];assert observed['Architecture']==arch and observed['Os']=='linux'
    checked('network','create','--internal',network);created.append(('network',network))
    assert json.loads(checked('network','inspect',network))[0]['Internal']
    origin='https://app.test:8443';tenant='40000000-0000-4000-8000-000000000001';client='40000000-0000-4000-8000-000000000002'
    reviewers=['40000000-0000-4000-8000-'+str(i).zfill(12)for i in range(10,15)]
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048);now=datetime.datetime.now(datetime.timezone.utc);name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'app.test')])
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1)).not_valid_after(now+datetime.timedelta(hours=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName('app.test'),x509.DNSName('login.microsoftonline.com')]),critical=False).sign(key,hashes.SHA256()))
    package=ROOT/'.local/external-artifacts/original-azure-amd64/v1/receiving'
    source_hashes={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest()for p in package.rglob('*')if p.is_file()and(str(p.relative_to(package)).startswith('app/')or p.name=='package.json')}
    inputs={'managedIdentityClientId':'40000000-0000-4000-8000-000000000050','origin':origin,'tenant':tenant,'reviewers':reviewers,'sourceHashes':source_hashes,
        'tlsKey':key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode(),
        'tlsCert':cert.public_bytes(serialization.Encoding.PEM).decode(),
        'environment':{'PUBLIC_ORIGIN':origin,'TENANT_ID':tenant,'CLIENT_ID':client,'CLIENT_SECRET':secrets.token_urlsafe(24),
            'REVIEWER_IDS':','.join(reviewers),'AZURE_ACCOUNT_ID':'/subscriptions/40000000-0000-4000-8000-000000000003/resourceGroups/synthetic/providers/Microsoft.CognitiveServices/accounts/synthetic',
            'AZURE_OPENAI_ENDPOINT':'https://synthetic.openai.azure.com','AZURE_DEPLOYMENT':'synthetic','AZURE_MODEL':'synthetic-model','AZURE_MODEL_VERSION':'synthetic-version'}}
    (OUT/'fixture.json').write_text(json.dumps(inputs));(OUT/'fixture.json').chmod(0o644)
    common=['--pull','never','--network',network,'--dns','127.0.0.1','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','1','--env','HOME=/tmp']
    checked('create','-i','--name',app,'--network-alias','app.test','--network-alias','login.microsoftonline.com','--platform','linux/amd64',*common,'--memory','256m','--pids-limit','64','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,mode=1777','--entrypoint','node',app_image,'--input-type=module','-e',(HERE/'fixture-server.mjs').read_text());created.append(('container',app))
    app_log=(OUT/'app-attached.log').open('wb')
    app_process=subprocess.Popen([*prefix,'start','-ai',app],env=environment,stdin=subprocess.PIPE,stdout=app_log,stderr=app_log)
    app_process.stdin.write((json.dumps(inputs)+'\n').encode());app_process.stdin.flush();app_process.stdin.close()
    ready=False
    for _ in range(80):
        logs=checked('logs',app)
        if b'"ready":true'in logs:ready=True;break
        if not json.loads(checked('inspect',app))[0]['State']['Running']:break
        time.sleep(.2)
    (OUT/'app-startup.log').write_bytes(checked('logs',app))
    if not ready:raise RuntimeError('Original application fixture did not start')
    checked('create','-i','--name',browser,'--platform','linux/arm64',*common,'--user','65532:65532','--security-opt','seccomp='+str(policy),'--memory','512m','--pids-limit','128','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=96m,mode=1777','--env','PLAYWRIGHT_BROWSERS_PATH=/ms-playwright','--entrypoint','node',browser_image,'--input-type=module','-e',(HERE/'probe-browser.mjs').read_text());created.append(('container',browser))
    result=docker('start','-ai',browser,timeout=150,input=json.dumps(inputs).encode());(OUT/'browser.stdout').write_bytes(result.stdout);(OUT/'browser.stderr').write_bytes(result.stderr)
    status=json.loads(checked('inspect',browser))[0]['State'];assert not status['Running']
    if result.returncode or status['ExitCode']:raise RuntimeError('Independent original browser journey failed; output retained')
    observed=json.loads(next(line for line in reversed(result.stdout.decode().splitlines())if line.startswith('{')));assert observed['passed']
    app_logs=checked('logs',app);(OUT/'app-final.log').write_bytes(app_logs)
    assert b'PRIVATE-'not in app_logs and b'CONCURRENT-'not in app_logs and b'SYNTHETIC-SUCCESS'not in app_logs
    assert all(hashlib.sha256((package/name).read_bytes()).hexdigest()==digest for name,digest in source_hashes.items())
    receipt.update(passed=True,sourceArtifactSha256='bea50c6b0677d3d20b74a6916780edf79a0fe7c4e8208901a42f561d985afdad',sourceHashes=source_hashes,
        observed=observed,networkInternal=True,hostPortsPublished=False,hostMounts=False,
        fixtureServerSha256=hashlib.sha256((HERE/'fixture-server.mjs').read_bytes()).hexdigest(),browserOracleSha256=hashlib.sha256((HERE/'probe-browser.mjs').read_bytes()).hexdigest(),
        boundary='Original unchanged AMD64 image and real sandboxed ARM64 Chromium over fixture TLS/HTTP. Explicit synthetic in-process native identity/metadata/account/model transports and local certificate exception. No real cloud authentication/model/account/retention or whole-project acceptance.')
except Exception as error:
    receipt['error']=str(error);raise
finally:
    cleanup=[]
    for kind,name in reversed(created):
        if kind=='network':docker('network','rm',name)
        else:docker('rm','-f',name)
        result=docker('network','inspect',name)if kind=='network'else docker('inspect',name)
        absent=result.returncode!=0 and any(x in result.stderr.lower()for x in [b'no such',b'not found'])
        cleanup.append({'kind':kind,'resource':name,'absent':absent})
    if app_process is not None:app_process.wait(timeout=10)
    if app_log is not None:app_log.close()
    receipt['cleanup']=cleanup;receipt['cleanupConfirmed']=bool(cleanup)and all(x['absent']for x in cleanup);receipt['passed']=receipt['passed']and receipt['cleanupConfirmed']
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':receipt['passed'],'cleanupConfirmed':receipt['cleanupConfirmed'],'output':str(OUT)}))
    if not receipt['cleanupConfirmed']:raise RuntimeError('Owned fixture cleanup not confirmed')
