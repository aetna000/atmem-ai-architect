"""Actual target imports/crypto/SQL; no application or cloud service acceptance."""
import hashlib,io,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec
out=ROOT/'.local/external-artifacts/provider-sql-validation/v1'
entries=json.loads((out/'validators-observed.json').read_text());worker=DockerValidationWorker('unix:///Users/javadtaghia/.avm/c/engine/docker.sock')
code=r'''
import importlib,importlib.util,json,os,sys
import psycopg,jwt
from cryptography.hazmat.primitives.asymmetric import rsa
modules=json.loads(sys.argv[1])
for name in ['fastapi','procrastinate','psycopg','jwt','cryptography','httpx',*modules]:importlib.import_module(name)
key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
token=jwt.encode({'sub':'local-sdk-probe','aud':'local','iss':'fixture'},key,algorithm='RS256')
assert jwt.decode(token,key.public_key(),algorithms=['RS256'],audience='local',issuer='fixture')['sub']=='local-sdk-probe'
try:jwt.decode(token,key.public_key(),algorithms=['RS256'],audience='foreign',issuer='fixture')
except jwt.InvalidAudienceError:pass
else:raise AssertionError('Foreign audience accepted')
try:jwt.decode(token,rsa.generate_private_key(public_exponent=65537,key_size=2048).public_key(),algorithms=['RS256'],audience='local',issuer='fixture')
except jwt.InvalidSignatureError:pass
else:raise AssertionError('Wrong signature accepted')
assert importlib.util.find_spec('boto3')is None
with psycopg.connect(os.environ['ATMEM_TEST_POSTGRES_DSN'])as c:version=c.execute('SHOW server_version').fetchone()[0]
print(json.dumps({'imports':modules,'coreImports':True,'signedJwtChecks':3,'postgresVersion':version,'uid':os.getuid(),'awsSdkPresent':False}))
'''
modules={'azure':['azure.core','azure.identity','msal','msal_extensions'],'gcp':['requests','jwt.algorithms'],'ibm':['ibm_cloud_sdk_core','ibm_cloud_sdk_core.authenticators','dateutil','tzdata']}
stream=io.BytesIO()
with zipfile.ZipFile(stream,'w'):pass
archive=stream.getvalue()
for entry in entries:
    provider=entry['id'].split('-')[2];target=out/provider/'sdk-import-v1.json';assert not target.exists()
    command=('/usr/local/bin/python3','-I','/opt/atmem/sql_validation.py','-c',code,json.dumps(modules[provider]))
    result=worker.run(archive,hashlib.sha256(archive).hexdigest(),ValidationSpec('sdk-import-probe',entry['image'],command,platform='linux/amd64',isolation_profile='postgresql-local-v1',timeout_seconds=60))
    target.write_text(json.dumps(result,indent=2)+'\n');assert result['status']=='passed',(provider,result)
    print('Actual AMD64 imports/crypto/SQL passed',provider,flush=True)
