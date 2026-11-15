"""Explicit operator deployment for the X account pilot; never deploys Hosting.

Print the plan without --apply. Requires a verified numeric administrator X ID.
No model inference, VM, migration, customer deletion or payment is performed.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import urllib.request
import urllib.error

parser=argparse.ArgumentParser()
parser.add_argument('--project',required=True)
parser.add_argument('--region',default='us-central1')
parser.add_argument('--admin-x-id',required=True)
parser.add_argument('--apply',action='store_true')
parser.add_argument('--x-lookup',action='store_true',help='Enable administrator-clicked X conversion using a scoped Secret Manager credential')
parser.add_argument('--native-workspace',action='store_true',help='Enable durable native workspace API after worker qualification; does not enable model spending')
args=parser.parse_args()
if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]',args.project):parser.error('Explicit Google project required')
if not re.fullmatch(r'[a-z]+-[a-z]+[0-9]',args.region):parser.error('Use a regional location')
if not re.fullmatch(r'[1-9][0-9]{0,19}',args.admin_x_id):parser.error('Verify numeric X identity before deployment')
project=args.project;region=args.region
runtime=f'architect-accounts@{project}.iam.gserviceaccount.com'
builder=f'architect-build@{project}.iam.gserviceaccount.com'
bucket=project+'-architect-projects';source=project+'-architect-build-source'
plan={'service':'architect-accounts','region':region,'database':'architect','dataBucket':bucket,'buildBucket':source,
      'runtimeIdentity':runtime,'buildIdentity':builder,'minInstances':0,'maxInstances':1,'cpu':1,'memory':'1Gi',
      'concurrency':1,'timeoutSeconds':60,'adminXId':args.admin_x_id,'modelSpendingEnabled':False,
      'costBoundary':'Request-billed scale-to-zero API; Firestore, Storage, image builds/registry and secrets billed by usage. Max instances is not a monetary cap.',
      'hostingDeployment':False,'nativeWorkspaceEnabled':args.native_workspace}
print(json.dumps(plan,indent=2),flush=True)
if not args.apply:raise SystemExit(0)

def command(*parts,input=None,check=True):
    result=subprocess.run(['gcloud',*parts,'--project',project,'--quiet'],input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if check and result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-5000:])
    return result

def exists(*parts):
    result=command(*parts,check=False)
    if result.returncode and not any(value in result.stderr.decode().lower() for value in ['not found','not_found','does not exist','404']):
        raise RuntimeError(result.stderr.decode()[-2000:])
    return result.returncode==0

def apply(label,*parts,input=None):
    print(label,flush=True);return command(*parts,input=input)

for account in ['architect-accounts','architect-build']:
    if not exists('iam','service-accounts','describe',account+'@'+project+'.iam.gserviceaccount.com'):
        apply('Creating '+account,'iam','service-accounts','create',account,'--display-name',account)
if not exists('firestore','databases','describe','--database','architect'):
    apply('Creating dedicated Firestore database','firestore','databases','create','--database','architect','--location',region,'--type','firestore-native','--delete-protection')
for name in [bucket,source]:
    if not exists('storage','buckets','describe','gs://'+name):
        apply('Creating private '+name,'storage','buckets','create','gs://'+name,'--location',region,'--uniform-bucket-level-access','--public-access-prevention')
if not exists('artifacts','repositories','describe','architect','--location',region):
    apply('Creating container repository','artifacts','repositories','create','architect','--location',region,'--repository-format','docker')
if not exists('iam','roles','describe','architectAuthVerifier'):
    apply('Creating minimal token revocation role','iam','roles','create','architectAuthVerifier','--title','Architect Firebase token verifier','--permissions','firebaseauth.users.get','--stage','GA')
apply('Granting token revocation check','projects','add-iam-policy-binding',project,'--member','serviceAccount:'+runtime,'--role','projects/'+project+'/roles/architectAuthVerifier','--condition=None')
apply('Scoping database permission','projects','add-iam-policy-binding',project,'--member','serviceAccount:'+runtime,'--role','roles/datastore.user',
      '--condition=expression=resource.name=="projects/'+project+'/databases/architect",title=architect_database_only')
apply('Scoping project object permission','storage','buckets','add-iam-policy-binding','gs://'+bucket,'--member','serviceAccount:'+runtime,'--role','roles/storage.objectUser')
apply('Scoping build source permission','storage','buckets','add-iam-policy-binding','gs://'+source,'--member','serviceAccount:'+builder,'--role','roles/storage.objectViewer')
apply('Scoping image publication','artifacts','repositories','add-iam-policy-binding','architect','--location',region,'--member','serviceAccount:'+builder,'--role','roles/artifactregistry.writer')
apply('Enabling build logs','projects','add-iam-policy-binding',project,'--member','serviceAccount:'+builder,'--role','roles/logging.logWriter','--condition=None')
secret='architect-byok-keyring'
if not exists('secrets','describe',secret):
    value=json.dumps({'activeKey':'v1','keys':{'v1':base64.b64encode(secrets.token_bytes(32)).decode()}}).encode()
    apply('Creating private key encryption secret','secrets','create',secret,'--replication-policy','automatic','--data-file=-',input=value)
apply('Scoping keyring access','secrets','add-iam-policy-binding',secret,'--member','serviceAccount:'+runtime,'--role','roles/secretmanager.secretAccessor')
root=Path(__file__).resolve().parents[2]
# Strict source allowlist: no browser, client project files, credentials or local environment.
with tempfile.TemporaryDirectory(prefix='architect-accounts-build-') as folder:
    context=Path(folder);(context/'hosted').mkdir()
    for file in (root/'hosted').glob('*.py'):shutil.copyfile(file,context/'hosted'/file.name)
    shutil.copyfile(root/'hosted/workspace-routes.json',context/'hosted/workspace-routes.json')
    shutil.copyfile(root/'hosted/requirements.lock',context/'hosted/requirements.lock')
    shutil.copyfile(root/'hosted/deploy/Dockerfile',context/'Dockerfile')
    shutil.copyfile(root/'hosted/deploy/cloudbuild.json',context/'cloudbuild.json')
    digest=hashlib.sha256()
    for file in sorted(context.rglob('*')):
        if file.is_file():digest.update(file.relative_to(context).as_posix().encode()+b'\0'+file.read_bytes())
    apply('Enabling Firebase Storage API','services','enable','firebasestorage.googleapis.com')
    token=command('auth','print-access-token').stdout.decode().strip()
    request=urllib.request.Request(f'https://firebasestorage.googleapis.com/v1alpha/projects/{project}/buckets/{bucket}:addFirebase',
        method='POST',data=b'',headers={'Authorization':'Bearer '+token,'x-goog-user-project':project})
    try:
        with urllib.request.urlopen(request,timeout=60) as response:response.read()
    except urllib.error.HTTPError as error:
        if error.code!=409:raise
    rules=root/'.local/deployments/firebase-rules.json'
    rules.parent.mkdir(parents=True,exist_ok=True)
    rules.write_text(json.dumps({'firestore':[{'database':'architect','rules':str(root/'hosted/firestore.rules')}],
                                'storage':[{'bucket':bucket,'rules':str(root/'hosted/deploy/storage.rules')}]}))
    result=subprocess.run(['firebase','deploy','--config',str(rules),'--only','firestore:architect,storage','--project',project,'--non-interactive'],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if result.returncode:raise RuntimeError(result.stderr.decode()[-3000:])
    apply('Configuring project lifecycle','storage','buckets','update','gs://'+bucket,'--lifecycle-file',str(root/'hosted/deploy/project-lifecycle.json'))
    apply('Configuring build source lifecycle','storage','buckets','update','gs://'+source,'--lifecycle-file',str(root/'hosted/deploy/build-lifecycle.json'))
    image=f'{region}-docker.pkg.dev/{project}/architect/accounts:'+digest.hexdigest()[:20]
    apply('Building immutable account image','builds','submit',folder,'--config',str(context/'cloudbuild.json'),
          '--substitutions','_IMAGE='+image,'--service-account','projects/'+project+'/serviceAccounts/'+builder,
          '--gcs-source-staging-dir','gs://'+source+'/source','--format=json')
    env={'ARCHITECT_GOOGLE_PROJECT':project,'ARCHITECT_FIRESTORE_DATABASE':'architect','ARCHITECT_DATA_ENVIRONMENT':'production',
         'ARCHITECT_ADMIN_X_IDS':args.admin_x_id,'ARCHITECT_FIREBASE_STORAGE_BUCKET':bucket,'ARCHITECT_STRIPE_MODE':'disabled'}
    if args.native_workspace:env['ARCHITECT_NATIVE_WORKSPACE_ENABLED']='1'
    envfile=context/'runtime-env.json';envfile.write_text(json.dumps(env))
    secret_bindings='ARCHITECT_BYOK_KEYRING='+secret+':1'
    if args.x_lookup:
        lookup_secret='architect-x-lookup-credentials'
        if not exists('secrets','describe',lookup_secret):raise ValueError('Configure the private X conversion credential first')
        apply('Scoping on-demand X lookup access','secrets','add-iam-policy-binding',lookup_secret,'--member','serviceAccount:'+runtime,'--role','roles/secretmanager.secretAccessor')
        secret_bindings+=',ARCHITECT_X_LOOKUP_CREDENTIALS='+lookup_secret+':latest'
    apply('Deploying account service','run','deploy','architect-accounts','--region',region,'--image',image,'--service-account',runtime,
          '--min-instances=0','--max-instances=1','--cpu=1','--memory=1Gi','--concurrency=1','--timeout=60','--port=8080',
          '--allow-unauthenticated','--cpu-throttling','--env-vars-file',str(envfile),'--set-secrets',secret_bindings)
    result=command('run','services','describe','architect-accounts','--region',region,'--format=json')
    service=json.loads(result.stdout);receipt={**plan,'image':image,'url':service['status']['url'],'revision':service['status'].get('latestReadyRevisionName')}
    evidence=root/'.local/deployments';evidence.mkdir(parents=True,exist_ok=True)
    (evidence/'accounts-service.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'deployed':True,'url':receipt['url'],'revision':receipt['revision']},indent=2))
