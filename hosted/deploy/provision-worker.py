"""Provision the single native worker; no Hosting publication or model spending.

Default prints the concrete plan. --apply creates only the dedicated resources.
The persistent state disk is never reformatted or deleted by this operator tool.
"""
import argparse,base64,json,re,subprocess,hashlib
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--project',required=True)
parser.add_argument('--admin-x-id',required=True)
parser.add_argument('--image',required=True)
parser.add_argument('--os-image',required=True)
parser.add_argument('--apply',action='store_true')
parser.add_argument('--enable-browser-checks',action='store_true',help='Register the reviewed browser validator after actual host qualification')
args=parser.parse_args()
if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]',args.project):parser.error('Use the explicit project ID')
if not re.fullmatch(r'[1-9][0-9]{0,19}',args.admin_x_id):parser.error('Use the verified administrator X subject')
if not re.fullmatch(r'us-central1-docker\.pkg\.dev/'+re.escape(args.project)+r'/architect/native-worker@sha256:[a-f0-9]{64}',args.image):parser.error('Pin the owned worker image by digest')
if not re.fullmatch(r'cos-stable-[0-9-]+',args.os_image):parser.error('Pin an immutable COS stable image')
root=Path(__file__).resolve().parents[2];out=root/'.local/worker-deployment';out.mkdir(parents=True,exist_ok=True)
project=args.project;region='us-central1';zone=region+'-a';name='architect-native-worker';account='architect-worker@'+project+'.iam.gserviceaccount.com'
environment={'ARCHITECT_DATA_ENVIRONMENT':'production','ARCHITECT_GOOGLE_PROJECT':project,
 'ARCHITECT_FIRESTORE_DATABASE':'architect','ARCHITECT_FIREBASE_STORAGE_BUCKET':project+'-architect-projects',
 'ARCHITECT_ADMIN_X_IDS':args.admin_x_id,'ARCHITECT_WORKER_STATE':'/var/lib/architect/runtime',
 'ARCHITECT_BYOK_KEYRING_VERSION':f'projects/{project}/secrets/architect-byok-keyring/versions/1',
 'ARCHITECT_OPENROUTER_KEY_VERSION':f'projects/{project}/secrets/architect-openrouter-api-key/versions/1',
 'ATMEM_ARCHITECT_ENGINEERING_TOOL_ROOTS':json.dumps(['/opt/architect','/opt/python','/usr/local/bin']),
 'ATMEM_ARCHITECT_ENGINEERING_TOOLCHAIN':json.dumps({'python':'/opt/architect/venv/bin/python','node':'/usr/local/bin/node','terraform':'/usr/local/bin/terraform','providerMirror':'/opt/architect/provider-mirror'}),
 'ATMEM_ARCHITECT_ENGINEERING_VALIDATOR_ENDPOINT':'unix:///var/run/docker.sock'}
policy=(root/'hosted/deploy/browser-seccomp.json').read_bytes()
if hashlib.sha256(policy).hexdigest()!='e53c15d248f57bceec0a3a16fad1b4ab0d05a7bddb455f86a60e2dba5612cdf7':raise RuntimeError('Browser isolation policy changed; independent review is required')
environment['ATMEM_ARCHITECT_ENGINEERING_ISOLATION_PROFILES']=json.dumps({'chromium-userns-v1':{'path':'/etc/architect/browser-seccomp.json','sha256':hashlib.sha256(policy).hexdigest()}})
envlines='\n'.join(key+'='+value for key,value in environment.items())+'\n'
# Trusted startup contains no API keys. A public image digest and Secret Manager
# resource names are configuration, not credentials. Private native state is bound
# separately from the disposable image and retained when the instance is replaced.
startup='''#!/bin/bash
set -euo pipefail
umask 077
for required in blkid wipefs mkfs.ext4 mount mountpoint docker stat; do command -v "$required" >/dev/null; done
DEVICE=/dev/disk/by-id/google-architect-state
STATE=/mnt/disks/architect-state
for attempt in $(seq 1 60); do test -b "$DEVICE" && break; sleep 1; done
test -b "$DEVICE"
TYPE=$(blkid -s TYPE -o value "$DEVICE" || true)
if test -z "$TYPE"; then
  # Only the dedicated newly-created blank state disk is initialized.
  test -z "$(wipefs -n --noheadings -o TYPE "$DEVICE")"
  mkfs.ext4 -F -m 0 "$DEVICE"
elif test "$TYPE" != ext4; then
  echo 'Unexpected state filesystem; refusing to modify it' >&2; exit 1
fi
mkdir -p "$STATE"
mountpoint -q "$STATE" || mount -o nodev,nosuid "$DEVICE" "$STATE"
mkdir -p "$STATE/runtime" "$STATE/config" /var/lib/architect/docker-auth
chmod 755 "$STATE/config"
chown 10001:10001 "$STATE/runtime"
chmod 700 "$STATE/runtime"
printf '%s' '__POLICY__' | base64 -d > "$STATE/config/browser-seccomp.json"
chmod 444 "$STATE/config/browser-seccomp.json"
export HOME=/var/lib/architect/docker-auth
export DOCKER_CONFIG="$HOME/.docker"
/usr/bin/docker-credential-gcr configure-docker --registries=us-central1-docker.pkg.dev
IMAGE=__IMAGE__
docker pull "$IMAGE"
# The validation controller runs a trusted root bootstrap, then drops to 65532
# before executing source. Never run the long-lived native worker as root.
printf 'FROM %s\\nUSER 0:0\\n' "$IMAGE" | docker build --pull=false --network=none -t architect-native-validator:operator-pinned -
IMAGE_ID=$(docker image inspect architect-native-validator:operator-pinned --format '{{.Id}}')
cat > "$STATE/config/worker.env" <<'ARCHITECT_ENV'
__ENV__ARCHITECT_ENV
# Start with only checks whose immutable runtime contracts are registered here.
# Browser checks are added after the exact host/user-namespace policy is qualified.
printf 'ATMEM_ARCHITECT_ENGINEERING_VALIDATORS=[{"id":"python-tests","label":"Python application tests","image":"%s","command":["/opt/architect/venv/bin/python","-m","unittest","discover","-v"],"bootstrapPython":"/opt/architect/venv/bin/python","timeoutSeconds":180,"applicability":{"anyOf":["**/test_*.py","**/*_test.py"]}},{"id":"node-tests","label":"Node application tests","image":"%s","command":["/usr/local/bin/node","--test","--test-reporter=tap","--test-concurrency=1"],"bootstrapPython":"/opt/architect/venv/bin/python","timeoutSeconds":180,"applicability":{"anyOf":["**/*.test.mjs","**/*.test.js"]}}]\n' "$IMAGE_ID" "$IMAGE_ID" >> "$STATE/config/worker.env"
printf 'ATMEM_ARCHITECT_TERRAFORM_EMULATOR_IMAGE=%s\\n' "$IMAGE_ID" >> "$STATE/config/worker.env"
chmod 600 "$STATE/config/worker.env"
SOCKET_GROUP=$(stat -c '%g' /var/run/docker.sock)
cat > /etc/systemd/system/architect-native-worker.service <<ARCHITECT_UNIT
[Unit]
Description=AtMem AI Architect private native worker
Requires=docker.service
After=docker.service network-online.target
[Service]
Environment=HOME=/var/lib/architect/docker-auth
Environment=DOCKER_CONFIG=/var/lib/architect/docker-auth/.docker
ExecStartPre=-/usr/bin/docker rm -f architect-native-worker
ExecStart=/usr/bin/docker run --rm --name architect-native-worker --init --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 512 --memory 3g --cpus 2 --group-add $SOCKET_GROUP --tmpfs /tmp:rw,noexec,nosuid,nodev,size=256m,mode=1777 --mount type=bind,src=$STATE/runtime,dst=/var/lib/architect/runtime --mount type=bind,src=$STATE/config,dst=/etc/architect,readonly --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock --env-file $STATE/config/worker.env --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 $IMAGE
ExecStop=/usr/bin/docker stop -t 45 architect-native-worker
Restart=on-failure
RestartSec=10
TimeoutStopSec=60
[Install]
WantedBy=multi-user.target
ARCHITECT_UNIT
systemctl daemon-reload
systemctl enable architect-native-worker.service
systemctl restart architect-native-worker.service
'''.replace('__IMAGE__',args.image).replace('__ENV__',envlines).replace('__POLICY__',base64.b64encode(policy).decode())
# Registrations use the config ID of the locally derived trusted bootstrap image.
extra=[{'id':'terraform-schema','label':'Offline Terraform schema validation','image':'__CONFIG_ID__','command':['/opt/architect/venv/bin/python','-I','/opt/architect/hosted/deploy/check-terraform.py'],'bootstrapPython':'/opt/architect/venv/bin/python','timeoutSeconds':180,'executableScratch':True,'applicability':{'anyOf':['**/*.tf','**/*.tf.json']}}]
if args.enable_browser_checks:
 extra.append({'id':'node-browser-tests','label':'Sandboxed browser and Node tests','image':'__CONFIG_ID__','command':['/usr/local/bin/node','--test','--test-reporter=tap','--test-concurrency=1'],'bootstrapPython':'/opt/architect/venv/bin/python','timeoutSeconds':180,'isolationProfile':'chromium-userns-v1','runtimeEnvironment':{'ATMEM_PLAYWRIGHT_MODULE':'/opt/architect/node_modules/playwright-core/index.mjs','PLAYWRIGHT_BROWSERS_PATH':'/ms-playwright'},'applicability':{'anyOf':['**/browser.test.mjs','**/*.browser.test.mjs']}})
import shlex
# Generate the complete validator line with the image-local Python interpreter.
registration_code='\n'.join([
 'import json,os','from pathlib import Path',"p=Path('/config/worker.env')","key='ATMEM_ARCHITECT_ENGINEERING_VALIDATORS='",
 'extra=json.loads('+repr(json.dumps(extra))+')',"[row.update(image=os.environ['CONFIG_ID']) for row in extra]",'result=[]',
 'for line in p.read_text().splitlines():',
 ' if line.startswith(key):',
 '  entries=json.loads(line[len(key):])',
 '  if '+repr(args.enable_browser_checks)+':',
 "   [row['applicability'].update(noneOf=['**/browser.test.mjs','**/*.browser.test.mjs']) for row in entries if row['id']=='node-tests']",
 "  line=key+json.dumps(entries+extra,separators=(',',':'))",' result.append(line)',"p.write_text('\\n'.join(result)+'\\n')"])
registration='docker run --rm --network=none --read-only --user 0:0 --env CONFIG_ID="$IMAGE_ID" --mount type=bind,src="$STATE/config",dst=/config --entrypoint python "$IMAGE" -c '+shlex.quote(registration_code)+'\n'
registration_anchor = 'printf \'ATMEM_ARCHITECT_TERRAFORM_EMULATOR_IMAGE=%s\\n\' "$IMAGE_ID" >> "$STATE/config/worker.env"\nchmod 600 "$STATE/config/worker.env"'
startup=startup.replace(registration_anchor,registration+registration_anchor)
(out/'startup.sh').write_text(startup)
plan={'instance':name,'project':project,'zone':zone,'machineType':'e2-medium','osImage':'cos-cloud/'+args.os_image,
 'workerImage':args.image,'stateDisk':name+'-state','stateDiskGiB':30,'stateDiskAutoDelete':False,
 'bootDiskGiB':30,'singleWorkerOnly':True,'serviceAccount':account,'network':'architect-workers',
 'inbound':'SSH only through IAP; no application port','snapshotRetentionDays':7,
 'modelSpendingChanged':False,'hostingPublished':False,'startupSha256':hashlib.sha256(startup.encode()).hexdigest(),
 'costBoundary':'One e2-medium, 60 GiB standard disks, ephemeral IPv4, daily state snapshots; approximately USD31/month before snapshots/API/model/network usage.'}
(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(plan,indent=2),flush=True)
if not args.apply:raise SystemExit(0)
def command(*parts,check=True):
 result=subprocess.run(['gcloud',*parts,'--project',project,'--quiet'],capture_output=True,text=True)
 if check and result.returncode:raise RuntimeError(result.stderr[-5000:])
 return result
def exists(*parts):
 result=command(*parts,check=False)
 if result.returncode and not any(word in result.stderr.lower() for word in ['not found','not_found','does not exist','404']):raise RuntimeError(result.stderr[-3000:])
 return result.returncode==0
def apply(label,*parts):
 print(label,flush=True);return command(*parts)
if not exists('iam','service-accounts','describe',account):apply('Creating dedicated worker identity','iam','service-accounts','create','architect-worker','--display-name','Architect native worker')
apply('Allowing operational log writes','projects','add-iam-policy-binding',project,'--member','serviceAccount:'+account,'--role','roles/logging.logWriter','--condition=None')
apply('Granting exact named database only','projects','add-iam-policy-binding',project,'--member','serviceAccount:'+account,'--role','roles/datastore.user','--condition=expression=resource.name=="projects/'+project+'/databases/architect",title=architect_database_only')
apply('Granting private project object access','storage','buckets','add-iam-policy-binding','gs://'+project+'-architect-projects','--member','serviceAccount:'+account,'--role','roles/storage.objectUser')
apply('Granting owned image pull access','artifacts','repositories','add-iam-policy-binding','architect','--location',region,'--member','serviceAccount:'+account,'--role','roles/artifactregistry.reader')
for secret in ['architect-byok-keyring','architect-openrouter-api-key']:apply('Granting exact '+secret+' access','secrets','add-iam-policy-binding',secret,'--member','serviceAccount:'+account,'--role','roles/secretmanager.secretAccessor')
if not exists('compute','networks','describe','architect-workers'):apply('Creating isolated worker network','compute','networks','create','architect-workers','--subnet-mode=custom')
if not exists('compute','networks','subnets','describe','architect-workers','--region',region):apply('Creating worker subnet','compute','networks','subnets','create','architect-workers','--region',region,'--network','architect-workers','--range','10.91.0.0/24','--enable-private-ip-google-access')
if not exists('compute','firewall-rules','describe','architect-worker-iap-ssh'):apply('Allowing IAP SSH only','compute','firewall-rules','create','architect-worker-iap-ssh','--network','architect-workers','--allow','tcp:22','--source-ranges','35.235.240.0/20','--target-service-accounts',account)
if not exists('compute','resource-policies','describe','architect-state-daily','--region',region):apply('Creating seven-day state snapshot schedule','compute','resource-policies','create','snapshot-schedule','architect-state-daily','--region',region,'--daily-schedule','--start-time','04:00','--max-retention-days','7','--on-source-disk-delete','keep-auto-snapshots','--storage-location',region)
if not exists('compute','disks','describe',name+'-state','--zone',zone):
 apply('Creating retained private state disk','compute','disks','create',name+'-state','--zone',zone,'--type=pd-standard','--size=30GB','--labels=product=architect,purpose=native-state')
 apply('Attaching state snapshot schedule','compute','disks','add-resource-policies',name+'-state','--zone',zone,'--resource-policies','architect-state-daily')
if exists('compute','instances','describe',name,'--zone',zone):raise RuntimeError('Worker already exists. Review a stopped/single-worker update explicitly; no duplicate worker was created.')
apply('Creating bounded private worker instance','compute','instances','create',name,'--zone',zone,'--machine-type=e2-medium','--image',args.os_image,'--image-project=cos-cloud','--boot-disk-size=30GB','--boot-disk-type=pd-standard','--disk=name='+name+'-state,device-name=architect-state,mode=rw,boot=no,auto-delete=no','--subnet=architect-workers','--service-account',account,'--scopes=https://www.googleapis.com/auth/cloud-platform','--metadata=block-project-ssh-keys=TRUE,serial-port-enable=FALSE','--metadata-from-file=startup-script='+str(out/'startup.sh'),'--shielded-secure-boot','--shielded-vtpm','--shielded-integrity-monitoring','--deletion-protection','--labels=product=architect,purpose=native-worker')
description=json.loads(command('compute','instances','describe',name,'--zone',zone,'--format=json').stdout)
(out/'instance.json').write_text(json.dumps(description,indent=2)+'\n')
print(json.dumps({'created':True,'instance':name,'status':description['status'],'nativeAcceptance':False}),flush=True)
