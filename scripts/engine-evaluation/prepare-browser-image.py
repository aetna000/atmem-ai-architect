"""Operator-owned offline image derivation; never processes generated Dockerfiles."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2];out=ROOT/'.local/engine-product/browser-runtime-preparation';meta=json.loads((out/'image.json').read_text());endpoint='unix:///Users/javadtaghia/.colima/architect-qualification/docker.sock'
with tempfile.TemporaryDirectory(prefix='atmem-browser-build-') as folder:
 root=Path(folder);config=root/'docker-config';config.mkdir();(config/'config.json').write_text('{}');context=root/'context';context.mkdir()
 source=ROOT/'node_modules/playwright-core';shutil.copytree(source,context/'playwright-core')
 hashes={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
 (context/'Dockerfile').write_text('FROM mcr.microsoft.com/playwright@'+meta['imageId']+'\nCOPY playwright-core /opt/atmem/playwright-core\n')
 env={'PATH':os.environ.get('PATH',''),'HOME':folder,'DOCKER_CONFIG':str(config),'DOCKER_HOST':endpoint};prefix=['docker','--host',endpoint,'--config',str(config)]
 with (out/'build.log').open('w') as log:subprocess.run([*prefix,'build','--network','none','--pull=false','--platform','linux/arm64','--tag','atmem-local/browser-qualification:1.64.1',str(context)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90,check=True)
 inspected=subprocess.run([*prefix,'image','inspect','atmem-local/browser-qualification:1.64.1'],env=env,capture_output=True,text=True,check=True)
 d=json.loads(inspected.stdout)[0];(out/'derived-image.json').write_text(json.dumps({'imageId':d['Id'],'baseImageId':meta['imageId'],'platform':'linux/arm64','moduleVersion':json.loads((source/'package.json').read_text())['version'],'moduleHashes':hashes,'dockerfile':(context/'Dockerfile').read_text(),'downloadsDuringBuild':False,'cloudOperations':False,'boundary':'Operator-reviewed derivation copies existing installed playwright-core into pinned public image. No generated source, package install, credentials or registry build step.'},indent=2)+'\n');print(d['Id'])
