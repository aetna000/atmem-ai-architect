"""Independent native-verifier crypto probe; no Google request or app acceptance."""
import hashlib, io, json, sys, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec
source=ROOT/'.local/external-artifacts/frozen-provider-eval/c11fdbc/src/runtime'
bulk=ROOT/'.local/external-artifacts/native-gcp-water/v1'
files={p.name:p.read_bytes()for p in source.iterdir()if p.suffix in {'.py','.sql'}}
stream=io.BytesIO()
with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED)as archive:
    for name,raw in files.items():archive.writestr(name,raw)
code=r'''
import json,sys,time
from types import SimpleNamespace
sys.path.insert(0,'/work/source')
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from gcp_structured import IapVerifier,AccessDenied
key=ec.generate_private_key(ec.SECP256R1());foreign=ec.generate_private_key(ec.SECP256R1())
class Keys:
 def get_signing_key_from_jwt(self,token):
  assert jwt.get_unverified_header(token)['kid']=='synthetic-iap'
  return SimpleNamespace(key=key.public_key())
config={'PROJECT_NUMBER':'123456789001','REGION':'australia-southeast1','SERVICE_NAME':'sample-routing'}
verify=IapVerifier(config,jwks=Keys());now=int(time.time())
claims={'iss':'https://cloud.google.com/iap','aud':'/projects/123456789001/locations/australia-southeast1/services/sample-routing',
 'iat':now-1,'exp':now+599,'sub':'accounts.google.com:independent-staff','email':'staff@synthetic.invalid'}
def token(changes=None,remove=None,signing=key,kid='synthetic-iap'):
 value={**claims,**(changes or {})}
 if remove:value.pop(remove)
 return jwt.encode(value,signing,algorithm='ES256',headers={'kid':kid})
assert verify(token())==claims['sub']
cases=[('issuer',token({'iss':'https://foreign.invalid'})),
 ('audience',token({'aud':'/projects/123456789002/locations/australia-southeast1/services/sample-routing'})),
 ('multiple-audiences',token({'aud':[claims['aud'],'foreign']})),
 ('expired',token({'iat':now-630,'exp':now-31})),('future-issued',token({'iat':now+120,'exp':now+600})),
 ('oversize-lifetime',token({'exp':now+1000})),('missing-email',token(remove='email')),
 ('empty-subject',token({'sub':''})),('machine-identity',token({'email':'robot@synthetic.iam.gserviceaccount.com'})),
 ('wrong-signature',token(signing=foreign)),('unknown-key',token(kid='unknown')),
 ('forged','not.a.signed.token'),('oversize','x'*16385)]
for name,value in cases:
 try:verify(value)
 except AccessDenied:pass
 else:raise AssertionError('Accepted invalid IAP assertion: '+name)
print(json.dumps({'passed':True,'validSignedES256':1,'denied':[name for name,_ in cases],
 'audience':claims['aud'],'cloudOperations':False,'googleNetworkRequests':0,
 'boundary':'Frozen shared verifier and real ES256 signatures in pinned GCP dependency image, injected synthetic JWKS only; no native IAP login, application role, group enforcement, account or whole-project acceptance.'}))
'''
entry=json.loads((bulk/'validators-observed.json').read_text())[0];raw=stream.getvalue()
spec=ValidationSpec('iap-crypto-probe',entry['image'],('/usr/local/bin/python3','-I','-c',code),platform='linux/amd64',timeout_seconds=30)
result=DockerValidationWorker('unix:///Users/javadtaghia/.avm/c/engine/docker.sock').run(raw,hashlib.sha256(raw).hexdigest(),spec)
with(bulk/'iap-probe-v1.json').open('x')as target:target.write(json.dumps(result,indent=2)+'\n')
assert result['status']=='passed',result
print(result['output'])
