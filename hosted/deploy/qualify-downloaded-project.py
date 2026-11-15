"""Send the exact downloaded fixture plus an independent oracle to isolated checks."""
import hashlib,io,json,shlex,subprocess,zipfile
from pathlib import Path,PurePosixPath
root=Path(__file__).resolve().parents[2];out=root/'.local/worker-cloud-qualification';source=out/'handoff.zip'
buffer=io.BytesIO()
with zipfile.ZipFile(source) as handoff,zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as check:
 for entry in handoff.infolist():
  if not entry.filename.startswith('implementation/') or entry.is_dir():continue
  name=entry.filename[len('implementation/'):];path=PurePosixPath(name)
  if path.is_absolute() or '..' in path.parts:raise RuntimeError('Unsafe downloaded path')
  check.writestr(name,handoff.read(entry))
 check.writestr('independent.acceptance.test.mjs',(root/'scripts/engine-evaluation/hosted-room-oracle.mjs').read_bytes())
raw=buffer.getvalue();archive=out/'independent-oracle.zip';archive.write_bytes(raw);archive.chmod(0o600)
subprocess.run(['gcloud','compute','scp',str(archive),'architect-native-worker:/tmp/architect-independent-oracle.zip','--project','atmemai','--zone','us-central1-a','--tunnel-through-iap','--quiet'],check=True,capture_output=True)
code="import sys,json,hashlib;from server.local_validation import DockerValidationWorker,ValidationSpec;raw=sys.stdin.buffer.read();worker=DockerValidationWorker('unix:///var/run/docker.sock');spec=ValidationSpec('independent-rooms',sys.argv[1],('/usr/local/bin/node','--test','--test-reporter=tap','independent.acceptance.test.mjs'),bootstrap_python='/opt/architect/venv/bin/python',timeout_seconds=90);result=worker.run(raw,'"+hashlib.sha256(raw).hexdigest()+"',spec);print(json.dumps(result));sys.exit(0 if result['status']=='passed' else 1)"
command='sudo docker exec -i architect-native-worker python -c '+shlex.quote(code)+' "$(sudo docker image inspect architect-native-validator:operator-pinned --format \'{{.Id}}\')" < /tmp/architect-independent-oracle.zip'
result=subprocess.run(['gcloud','compute','ssh','architect-native-worker','--project','atmemai','--zone','us-central1-a','--tunnel-through-iap','--quiet','--command',command],capture_output=True,text=True)
(out/'independent-oracle-output.txt').write_text(result.stdout+result.stderr)
rows=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
if not rows:raise RuntimeError('The isolated oracle returned no receipt')
receipt={'kind':'Independent black-box HTTP acceptance of exact downloaded implementation','handoffSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'oracleSha256':hashlib.sha256((root/'scripts/engine-evaluation/hosted-room-oracle.mjs').read_bytes()).hexdigest(),'result':rows[-1]}
(out/'independent-oracle.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if result.returncode or receipt['result']['status']!='passed':raise SystemExit(1)
