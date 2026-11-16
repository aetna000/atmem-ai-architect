"""Prepare and optionally submit the owned, digest-pinned native worker image."""
import argparse,hashlib,json,shlex,shutil,subprocess,tarfile,tempfile,re
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--project',required=True);parser.add_argument('--apply',action='store_true');parser.add_argument('--base-image',help='Reuse a previously built owned immutable runtime, only with identical dependency locks and runtime pins');parser.add_argument('--refresh-python-lock',action='store_true',help='Explicitly synchronize a changed hashed Python lock in the pinned base');parser.add_argument('--refresh-node-lock',action='store_true',help='Explicitly install the candidate JavaScript lock without executing package scripts');args=parser.parse_args()
if (args.refresh_python_lock or args.refresh_node_lock) and not args.base_image:parser.error('A dependency refresh needs the owned pinned base')
if args.base_image and not re.fullmatch(r'us-central1-docker\.pkg\.dev/'+re.escape(args.project)+r'/architect/native-worker@sha256:[a-f0-9]{64}',args.base_image):parser.error('Reuse only an owned digest-pinned runtime')
root=Path(__file__).resolve().parents[2];pins=json.loads((root/'hosted/deploy/runtime-images.json').read_text())
output=root/'.local/worker-build';output.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='architect-native-build-') as temporary:
 context=Path(temporary)
 allowed={'.py','.mjs','.jsx','.js','.json','.md','.css','.txt','.ts','.toml','.yaml','.yml','.svg','.lock'}
 inputs=[]
 for directory in ['hosted','server','src','scripts','agent-skills','knowledge']:
  for source in sorted((root/directory).rglob('*')):
   relative=source.relative_to(root)
   if any(part.startswith('.') or part=='__pycache__' for part in relative.parts):continue
   if source.is_symlink():raise RuntimeError('Build inputs cannot be symbolic links')
   if not source.is_file() or source.suffix not in allowed:continue
   # No paid/operator smoke programs or browser identity fixtures enter the image.
   if source.name in {'atbots_native_smoke.py','stripe_checkout_testmode.py','native_browser_server.py'}:continue
   target=context/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
   inputs.append({'path':relative.as_posix(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
 # Native prompts load the governing product text at process startup.
 for name in ['package.json','package-lock.json','CONSTITUTION.md']:
  shutil.copyfile(root/name,context/name);inputs.append({'path':name,'sha256':hashlib.sha256((root/name).read_bytes()).hexdigest()})
 # Preserve the exact evidence needed to admit reviewed engineering practices.
 # Import only explicitly pinned receipts, never the full specification history.
 practices=json.loads((root/'knowledge/engineering-practices.json').read_text())
 for row in practices['records']:
  if row.get('evidenceLevel')!='locally-tested':continue
  proof=row['localVerification'];relative=Path(proof['receipt']);source=root/relative
  if relative.is_absolute() or '..' in relative.parts or relative.parts[0]!='specs' or any((root/Path(*relative.parts[:i])).is_symlink() for i in range(1,len(relative.parts)+1)):
   raise RuntimeError('Engineering evidence must be an owned repository receipt')
  digest=hashlib.sha256(source.read_bytes()).hexdigest()
  if digest!=proof['sha256']:raise RuntimeError('Engineering evidence changed; review the pinned practice first')
  target=context/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
  if not any(item['path']==relative.as_posix() for item in inputs):inputs.append({'path':relative.as_posix(),'sha256':digest})
 source_sha=hashlib.sha256(json.dumps({'files':inputs,'baseImage':args.base_image},sort_keys=True,separators=(',',':')).encode()).hexdigest()
 image=f'us-central1-docker.pkg.dev/{args.project}/architect/native-worker:source-{source_sha[:20]}'
 manifest={'kind':'Owned native Architect worker source','sourceSha256':source_sha,'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'files':inputs,'runtimeImages':pins,'baseImage':args.base_image}
 (context/'worker-source.json').write_text(json.dumps(manifest,indent=2)+'\n')
 dockerfile=f'''FROM {pins['uv']['image']} AS uv
FROM {pins['node']['image']} AS node
FROM {pins['docker']['image']} AS dockercli
FROM {pins['terraform']['image']} AS terraform
FROM {pins['playwright']['image']}
USER root
COPY --from=uv /uv /usr/local/bin/uv
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=terraform /bin/terraform /usr/local/bin/terraform
ENV UV_PYTHON_INSTALL_DIR=/opt/python UV_NO_CACHE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYDANTIC_AI_NO_BANNER=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN ln -sf ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && uv python install {pins['pythonVersion']} && uv venv --python {pins['pythonVersion']} /opt/architect/venv
WORKDIR /opt/architect
COPY hosted/worker-requirements.lock /opt/architect/hosted/worker-requirements.lock
RUN uv pip sync --python /opt/architect/venv/bin/python --require-hashes /opt/architect/hosted/worker-requirements.lock && uv pip check --python /opt/architect/venv/bin/python
ENV PATH=/opt/architect/venv/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin ATMEM_ARCHITECT_PROVIDER_CACHE=/opt/architect/provider-mirror ATMEM_ARCHITECT_TERRAFORM_BIN=/usr/local/bin/terraform
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY . /opt/architect/
RUN if [ ! -x /opt/architect/emulator/bin/python ]; then uv venv --python /opt/architect/venv/bin/python /opt/architect/emulator; fi && uv pip sync --python /opt/architect/emulator/bin/python --require-hashes /opt/architect/server/terraform-emulator-requirements.lock && /opt/architect/emulator/bin/python -I -m ensurepip --default-pip && /opt/architect/emulator/bin/python -I -c 'import moto,flask,boto3;assert moto.__version__=="5.2.5"'
RUN /opt/architect/emulator/bin/python -I /opt/architect/hosted/deploy/prepare-emulator-wheels.py
RUN python -m unittest hosted.tests.test_model_metering hosted.tests.test_native_model_broker hosted.tests.test_native_worker_process hosted.tests.test_native_host server.tests.test_atbots_engineering_backend -v
RUN node hosted/deploy/mirror-providers.mjs && python hosted/deploy/unpack-provider-mirror.py
RUN node -e "import('./src/terraform.mjs').then(m=>{{if(typeof m.terraformSketch!=='function')process.exit(1)}})" && python -c "import atmem;import importlib.metadata as m;assert m.version('atmem')=='2.3.14'" && terraform version -json > /opt/architect/terraform-runtime.json
RUN groupadd --gid 10001 architect && useradd --uid 10001 --gid 10001 --create-home architect && mkdir -p /var/lib/architect && chown 10001:10001 /var/lib/architect
USER architect
CMD ["python","-m","hosted.worker_main"]
'''
 if args.base_image:
  names=['hosted/deploy/runtime-images.json']+([] if args.refresh_node_lock else ['package-lock.json'])+([] if args.refresh_python_lock else ['hosted/worker-requirements.lock'])
  expected={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}
  verify="from pathlib import Path;import hashlib;expected="+repr(expected)+";assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest for name,digest in expected.items()),'Runtime/dependency inputs changed: perform a full build'"
  clean="from pathlib import Path;import json;root=Path('/opt/architect');rows=json.loads((root/'worker-source.json').read_text())['files'];paths=[root/row['path'] for row in rows];assert all(path.resolve().is_relative_to(root) and not path.is_symlink() for path in paths);[path.unlink() for path in paths]"
  refresh='COPY hosted/worker-requirements.lock /tmp/architect-worker.lock\nRUN uv pip sync --python /opt/architect/venv/bin/python --require-hashes /tmp/architect-worker.lock && uv pip check --python /opt/architect/venv/bin/python\n' if args.refresh_python_lock else ''
  dockerfile=f'''FROM {args.base_image}
USER root
WORKDIR /opt/architect
RUN python -c {shlex.quote(verify)}
{refresh}RUN python -c {shlex.quote(clean)}
COPY . /opt/architect/
RUN if [ ! -x /opt/architect/emulator/bin/python ]; then uv venv --python /opt/architect/venv/bin/python /opt/architect/emulator; fi && uv pip sync --python /opt/architect/emulator/bin/python --require-hashes /opt/architect/server/terraform-emulator-requirements.lock && /opt/architect/emulator/bin/python -I -m ensurepip --default-pip && /opt/architect/emulator/bin/python -I -c 'import moto,flask,boto3;assert moto.__version__=="5.2.5"'
{'RUN npm ci --ignore-scripts' if args.refresh_node_lock else ''}
RUN /opt/architect/emulator/bin/python -I /opt/architect/hosted/deploy/prepare-emulator-wheels.py
RUN python -m unittest hosted.tests.test_model_metering hosted.tests.test_native_model_broker hosted.tests.test_native_worker_process hosted.tests.test_native_host hosted.tests.test_native_snapshot_protocol hosted.tests.test_firestore_read_recovery server.tests.test_atbots_engineering_backend server.tests.test_local_validation server.tests.test_engineering_handoff -v
USER architect
CMD ["python","-m","hosted.worker_main"]
'''
 (context/'Dockerfile').write_text(dockerfile)
 config={'steps':[{'name':'gcr.io/cloud-builders/docker','args':['build','--platform','linux/amd64','-t',image,'.']}],'images':[image],'options':{'logging':'CLOUD_LOGGING_ONLY'},'timeout':'1800s'}
 (context/'cloudbuild.json').write_text(json.dumps(config,indent=2)+'\n')
 shutil.copyfile(context/'Dockerfile',output/'Dockerfile');shutil.copyfile(context/'worker-source.json',output/'worker-source.json');shutil.copyfile(context/'cloudbuild.json',output/'cloudbuild.json')
 plan={'image':image,'sourceSha256':source_sha,'sourceFileCount':len(inputs),'platform':'linux/amd64','providerKeysIncluded':False,'productionModelRequestsInBuild':False,'vmCreated':False}
 (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(plan,indent=2),flush=True)
 if args.apply:
  command=['gcloud','builds','submit',str(context),'--project',args.project,'--region','us-central1','--config',str(context/'cloudbuild.json'),'--service-account',f'projects/{args.project}/serviceAccounts/architect-build@{args.project}.iam.gserviceaccount.com','--gcs-source-staging-dir',f'gs://{args.project}-architect-build-source/native-worker','--async','--format=json','--quiet']
  result=subprocess.run(command,check=True,capture_output=True,text=True);receipt=json.loads(result.stdout)
  (output/'submission.json').write_text(json.dumps(receipt,indent=2)+'\n')
  print(json.dumps({'buildId':receipt.get('id'),'status':receipt.get('status'),'image':image}),flush=True)
