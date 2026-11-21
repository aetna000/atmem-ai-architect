"""Repeat the reviewed offline receiving build on the isolated AMD64 Docker endpoint."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[4];package=ROOT/'.local/external-artifacts/native-gcp-water/v1/native-run/unpacked';out=Path(sys.argv[1]).resolve();out.mkdir();endpoint='unix:///Users/javadtaghia/.avm/c/amd64/validator.sock';base='sha256:48d884813cf44e927cf64c5529dd630dd3b18338c6dc727991eef9b71e934a20'
observed=json.loads(subprocess.check_output(['docker','--host',endpoint,'image','inspect',base],text=True))[0];assert observed['Id']==base and observed['Os']=='linux'and observed['Architecture']=='amd64'
command=['docker','--host',endpoint,'build','--no-cache','--network=none','--pull=false','--platform=linux/amd64','--build-arg','PYTHON_BASE='+base,'--iidfile',str(out/'image-id.txt'),str(package)]
with(out/'build.log').open('wb')as target:r=subprocess.run(command,env={**os.environ,'DOCKER_BUILDKIT':'0'},stdout=target,stderr=subprocess.STDOUT)
receipt={'passed':r.returncode==0,'command':command,'environmentOverride':{'DOCKER_BUILDKIT':'0'},'baseImageId':base,'dockerfileSha256':hashlib.sha256((package/'Dockerfile').read_bytes()).hexdigest(),'dockerignoreSha256':hashlib.sha256((package/'.dockerignore').read_bytes()).hexdigest(),'runtimeLockSha256':hashlib.sha256((package/'application/test-requirements.lock').read_bytes()).hexdigest(),'imageId':(out/'image-id.txt').read_text().strip()if r.returncode==0 else None,'cloudOperations':False,'sourceChanged':False}
(out/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));assert r.returncode==0
