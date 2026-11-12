"""Qualify registered isolated Chromium checks and skip/zero/failure behavior."""
import argparse,hashlib,io,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'.local/engine-product/working-browser-validation');args=parser.parse_args();out=args.output.resolve();out.mkdir(exist_ok=False)
prepared=ROOT/'.local/engine-product/browser-runtime-preparation';image=json.loads((prepared/'derived-image.json').read_text())['imageId'];policy=prepared/'browser-seccomp.json'
profiles={'chromium-userns-v1':{'path':str(policy),'sha256':DockerValidationWorker.REVIEWED_PROFILES['chromium-userns-v1']}}
worker=DockerValidationWorker('unix://'+str(Path.home()/'.colima/architect-qualification/docker.sock'),isolation_profiles=profiles)
script=r'''
import test from 'node:test';import assert from 'node:assert/strict';import {execFileSync} from 'node:child_process';
const {chromium}=await import(process.env.ATMEM_PLAYWRIGHT_MODULE);
test('Outer container guards remain effective',()=>{
 const result=execFileSync('/usr/bin/python3',['-c',`import os,pathlib,socket
assert os.getuid()==65532 and os.getgid()==65532 and os.getgroups()==[]
s=pathlib.Path('/proc/self/status').read_text()
assert 'NoNewPrivs:\\t1'.replace('\\t','\t') in s
assert int(next(x.split()[1]for x in s.splitlines()if x.startswith('CapEff:')),16)==0
try:os.chroot('/tmp')
except PermissionError:pass
else:raise AssertionError('Outer chroot allowed')
try:pathlib.Path('/work/source/browser.test.mjs').write_text('changed')
except PermissionError:pass
else:raise AssertionError('Source writable')
assert not pathlib.Path('/Users').exists() and not pathlib.Path('/var/run/docker.sock').exists()
try:socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_ICMP)
except PermissionError:pass
else:raise AssertionError('Raw socket allowed')
sock=socket.socket();sock.settimeout(1)
try:sock.connect(('192.0.2.1',80))
except OSError:pass
else:raise AssertionError('External network allowed')
sock.close();print('OUTER_GUARDS_PASSED')`],{encoding:'utf8'});assert.match(result,/OUTER_GUARDS_PASSED/);
});
test('Actual Chromium sandbox page interaction and browser API receiver contract',async()=>{
 const browser=await chromium.launch({headless:true,chromiumSandbox:true});
 try{
  const page=await browser.newPage();await page.route('**/*',route=>route.request().url().endsWith('/config.json')?route.fulfill({contentType:'application/json',body:'{"enabled":true}'}):route.fulfill({contentType:'text/html',body:'<!doctype html><button id="clear">Clear</button><output id="value">Original</output><script>document.querySelector("#clear").onclick=()=>document.querySelector("#value").textContent=""</script>'}));
  await page.goto('https://local-test.invalid/');assert.equal(await page.locator('#value').textContent(),'Original');await page.locator('#clear').click();assert.equal(await page.locator('#value').textContent(),'');
  const result=await page.evaluate(async()=>{const wrapper={fetcher:fetch};let error;try{await wrapper.fetcher('/config.json');}catch(e){error=e.message;}return {error,status:(await (0,wrapper.fetcher)('/config.json')).status};});
  assert.match(result.error,/Illegal invocation/);assert.equal(result.status,200);
 }finally{await browser.close();}
});
'''
checks=[]
for name,files,expected in [
 ('browser-positive',{'browser.test.mjs':script},'passed'),
 ('node-skipped',{'skipped.test.mjs':"import test from 'node:test';test.skip('missing evidence',()=>{});"},'incomplete'),
 ('node-zero',{'README.txt':'No tests'},'failed'),
 ('node-failure',{'failed.test.mjs':"import test from 'node:test';import assert from 'node:assert/strict';test('counterexample',()=>assert.fail('Deliberate independent failure'));"},'failed')]:
 data=io.BytesIO()
 with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED)as z:
  for path,content in files.items():z.writestr(path,content)
 content=data.getvalue();spec=ValidationSpec(name,image,('/usr/bin/node','--test','--test-reporter=tap','--test-concurrency=1'),platform='linux/arm64',bootstrap_python='/usr/bin/python3',isolation_profile='chromium-userns-v1',runtime_environment=(('ATMEM_PLAYWRIGHT_MODULE','/opt/atmem/playwright-core/index.mjs'),))
 result=worker.run(content,hashlib.sha256(content).hexdigest(),spec);(out/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n');checks.append({'name':name,'expected':expected,'observed':result['status'],'testsReported':result['testsReported'],'skipped':result['skipped']});print(name,result['status'],result['output'][-500:],flush=True)
receipt={'passed':all(c['expected']==c['observed']for c in checks),'checks':checks,'cloudOperations':False,'imageId':image,'seccompSha256':profiles['chromium-userns-v1']['sha256'],'boundary':'Actual current validator code: nonroot/read-only/network-none cached Linux ARM64 containers, explicitly reviewed seccomp user namespaces, Chromium sandbox enabled in the positive oracle, interactive page and native browser receiver contract, denied outer chroot/raw socket/source writes/host paths/external network; Node skipped/zero/failure status preserved. No generated system/hosted tenant isolation acceptance.'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');assert receipt['passed'],receipt
