"""Reproduce original archive receiving build without host runtime substitution."""
import argparse,hashlib,json,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
archive=ROOT/'.local/engine-product/20261111-native-azure-primary/artifact.zip'
digest=hashlib.sha256(archive.read_bytes()).hexdigest();assert digest=='bea50c6b0677d3d20b74a6916780edf79a0fe7c4e8208901a42f561d985afdad'
with zipfile.ZipFile(archive)as z:files={i.filename:z.read(i).decode('utf8')for i in z.infolist()if not i.is_dir()}
oracle=Path(__file__).with_name('check-receiving.mjs').read_bytes()
result=subprocess.run(['docker','--host','unix:///Users/javadtaghia/.avm/c/engine/docker.sock','run','--rm','-i','--pull','never','--platform','linux/amd64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','256m','--cpus','1','--pids-limit','64','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,mode=1777','--entrypoint','node','sha256:00486a3f6db3ac32d3f9fb0ccb3819944f17c54933e83adbee7a77fec9d678e1','--input-type=module','-e',oracle.decode()],input=json.dumps(files).encode(),capture_output=True,timeout=60)
(out/'stdout').write_bytes(result.stdout);(out/'stderr').write_bytes(result.stderr)
if result.returncode:raise RuntimeError('Receiving build failed; retained stdout/stderr')
d=json.loads(result.stdout);d.update(sourceArtifactSha256=digest,oracleSha256=hashlib.sha256(oracle).hexdigest());(out/'receipt.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
