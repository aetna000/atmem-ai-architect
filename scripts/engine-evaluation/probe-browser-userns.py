"""Operator-only browser sandbox experiment; no product policy changes."""
from pathlib import Path
import hashlib,io,json,os,subprocess,sys,tempfile,uuid,zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));from server.local_validation import BOOTSTRAP
out=ROOT/'.local/engine-product/browser-runtime-preparation';image=json.loads((out/'derived-image.json').read_text())['imageId'];policy=out/'browser-seccomp.json';meta=json.loads((out/'browser-seccomp-source.json').read_text());assert hashlib.sha256(policy.read_bytes()).hexdigest()==meta['sha256']
script="""import {chromium} from '/opt/atmem/playwright-core/index.mjs';
import fs from 'node:fs';
if(process.getuid()!==65532||process.getgid()!==65532||process.getgroups().some(x=>x!==65532))throw Error('Unexpected identity');
if(!fs.readFileSync('/proc/self/status','utf8').includes('NoNewPrivs:\\t1'))throw Error('NoNewPrivs missing');
const status=fs.readFileSync('/proc/self/status','utf8');if(!status.includes('CapEff:\t0000000000000000'))throw Error('Effective caps present');
const browser=await chromium.launch({headless:true,chromiumSandbox:true});
try{const page=await browser.newPage();await page.route('**/*',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><button id="go">Ready</button>'}));await page.goto('https://local-test.invalid/');if(await page.locator('#go').textContent()!=='Ready')throw Error('No browser');console.log('BROWSER_USERNS_SANDBOX_EXECUTED');}finally{await browser.close();}
"""
data=io.BytesIO()
guard="""import os,pathlib,socket
assert os.getuid()==65532 and os.getgid()==65532 and os.getgroups()==[]
status=pathlib.Path('/proc/self/status').read_text()
assert 'NoNewPrivs:\t1' in status and 'CapEff:\t0000000000000000' in status
try:os.chroot('/tmp')
except PermissionError:pass
else:raise AssertionError('Outer namespace chroot allowed')
assert not pathlib.Path('/Users').exists() and not pathlib.Path('/var/run/docker.sock').exists()
try:pathlib.Path('/work/source/probe.mjs').write_text('changed')
except PermissionError:pass
else:raise AssertionError('Source writable')
try:socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_ICMP)
except PermissionError:pass
else:raise AssertionError('Raw socket allowed')
s=socket.socket();s.settimeout(1)
try:s.connect(('192.0.2.1',80))
except OSError:pass
else:raise AssertionError('External network allowed')
s.close()
print('OUTER_NAMESPACE_GUARDS_PASSED',flush=True)
os.execv('/usr/bin/node',['/usr/bin/node','probe.mjs'])
"""
with zipfile.ZipFile(data,'w') as z:
 z.writestr('probe.mjs',script);z.writestr('guard.py',guard)
content=data.getvalue();endpoint='unix:///Users/javadtaghia/.colima/architect-qualification/docker.sock';name='atmem-browser-userns-'+uuid.uuid4().hex
with tempfile.TemporaryDirectory(prefix='atmem-browser-userns-') as folder:
 root=Path(folder);(root/'config.json').write_text('{}');env={'PATH':os.environ.get('PATH',''),'HOME':folder,'DOCKER_CONFIG':folder,'DOCKER_HOST':endpoint};prefix=['docker','--host',endpoint,'--config',folder]
 args=[*prefix,'run','--pull','never','--rm','--name',name,'--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--cap-add','SETUID','--cap-add','SETGID','--security-opt','no-new-privileges','--security-opt','seccomp='+str(policy.resolve()),'--pids-limit','128','--memory','512m','--cpus','1','--tmpfs','/work:rw,noexec,nosuid,nodev,size=64m,mode=0755','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777','--env','HOME=/tmp','--env','PYTHONDONTWRITEBYTECODE=1','--entrypoint','/usr/bin/python3','-i',image,'-I','-c',BOOTSTRAP,json.dumps([hashlib.sha256(content).hexdigest(),['/usr/bin/python3','guard.py']])]
 try:
  result=subprocess.run(args,input=content,env=env,capture_output=True,timeout=60)
  receipt={'passed':result.returncode==0,'exitCode':result.returncode,'stdout':result.stdout.decode(errors='replace'),'stderr':result.stderr.decode(errors='replace'),'imageId':image,'seccompSha256':meta['sha256'],'cloudOperations':False,'boundary':'Operator-only actual nonroot cached network-none/read-only/cap-drop/no-new-privileges container plus pinned upstream user-namespace seccomp, 512MiB/128PIDs/1CPU/time bounds. Chromium sandbox requested; no host namespaces/socket/mount/credentials. Not a product validator or hosted isolation qualification.'}
  (out/'userns-probe.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2));assert receipt['passed']
 finally:subprocess.run([*prefix,'rm','-f',name],env=env,capture_output=True,timeout=15)
