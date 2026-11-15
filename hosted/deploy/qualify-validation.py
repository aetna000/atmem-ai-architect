"""Actual VM/container canaries, executed by the operator inside the private worker.

Positive runtime cases plus deliberate failures; no model or cloud account plans.
"""
import argparse,hashlib,io,json,os,sys,zipfile
from pathlib import Path
sys.path.insert(0,'/opt/architect')
from server.local_validation import DockerValidationWorker,ValidationSpec
parser=argparse.ArgumentParser();parser.add_argument('--image',required=True);args=parser.parse_args()
policy='/etc/architect/browser-seccomp.json';profiles={'chromium-userns-v1':{'path':policy,'sha256':DockerValidationWorker.REVIEWED_PROFILES['chromium-userns-v1']}}
worker=DockerValidationWorker('unix:///var/run/docker.sock',isolation_profiles=profiles)
python='''import os,pathlib,socket,unittest
class Isolation(unittest.TestCase):
 def test_outer_guards(self):
  self.assertEqual((os.getuid(),os.getgid(),os.getgroups()),(65532,65532,[]))
  status=pathlib.Path('/proc/self/status').read_text()
  self.assertEqual(int(next(line.split()[1] for line in status.splitlines() if line.startswith('CapEff:')),16),0)
  self.assertIn('NoNewPrivs:\\t1'.replace('\\t','\t'),status)
  for path in ['/var/run/docker.sock','/mnt/disks/architect-state','/var/lib/architect/runtime']:
   self.assertFalse(pathlib.Path(path).exists())
  for key in ['GOOGLE_APPLICATION_CREDENTIALS','ARCHITECT_OPENROUTER_KEY_VERSION','OPENROUTER_API_KEY']:
   self.assertNotIn(key,os.environ)
  with self.assertRaises(PermissionError):pathlib.Path('test_guards.py').write_text('changed')
  with self.assertRaises(PermissionError):os.chroot('/tmp')
  for address in [('169.254.169.254',80),('10.91.0.2',22),('192.0.2.1',80)]:
   with socket.socket() as connection:
    connection.settimeout(1)
    with self.assertRaises(OSError):connection.connect(address)
'''
browser='''import test from 'node:test';import assert from 'node:assert/strict';
const {chromium}=await import(process.env.ATMEM_PLAYWRIGHT_MODULE);
test('actual sandboxed Chromium interaction',async()=>{
 const browser=await chromium.launch({headless:true,chromiumSandbox:true});
 try{const page=await browser.newPage();await page.setContent('<button>Reserve</button><output>0</output><script>document.querySelector("button").onclick=()=>document.querySelector("output").textContent="1"</script>');await page.getByRole('button',{name:'Reserve'}).click();assert.equal(await page.locator('output').textContent(),'1');}finally{await browser.close();}
});'''
cases=[('python-guards',{'test_guards.py':python},('/opt/architect/venv/bin/python','-m','unittest','discover','-v'),'passed','standard-v1',False),
 ('python-negative',{'test_negative.py':'import unittest\nclass Negative(unittest.TestCase):\n def test_failure(self):self.fail("deliberate counterexample")\n'},('/opt/architect/venv/bin/python','-m','unittest','discover','-v'),'failed','standard-v1',False),
 ('node-positive',{'app.test.mjs':"import test from 'node:test';import assert from 'node:assert/strict';test('sum',()=>assert.equal(2+3,5));"},('/usr/local/bin/node','--test','--test-reporter=tap'),'passed','standard-v1',False),
 ('browser-positive',{'browser.test.mjs':browser},('/usr/local/bin/node','--test','--test-reporter=tap','--test-concurrency=1'),'passed','chromium-userns-v1',False),
 ('terraform-positive',{'main.tf':'terraform {\n required_providers {\n  null = { source = "hashicorp/null" }\n }\n}\nresource "null_resource" "fixture" {}\n'},('/opt/architect/venv/bin/python','-I','/opt/architect/hosted/deploy/check-terraform.py'),'passed','standard-v1',True)]
results=[]
for name,files,command,expected,profile,scratch in cases:
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
  for path,content in files.items():archive.writestr(path,content)
 raw=stream.getvalue();environment=(('ATMEM_PLAYWRIGHT_MODULE','/opt/architect/node_modules/playwright-core/index.mjs'),('PLAYWRIGHT_BROWSERS_PATH','/ms-playwright')) if profile=='chromium-userns-v1' else ()
 spec=ValidationSpec(name,args.image,command,bootstrap_python='/opt/architect/venv/bin/python',timeout_seconds=180,isolation_profile=profile,runtime_environment=environment,executable_scratch=scratch)
 result=worker.run(raw,hashlib.sha256(raw).hexdigest(),spec)
 results.append({'name':name,'expected':expected,'observed':result['status'],'testsReported':result['testsReported'],'output':result['output'][-5000:]})
 print(json.dumps(results[-1]),flush=True)
receipt={'kind':'Actual Google VM isolated container runtime canaries','imageConfigId':args.image,'passed':all(row['observed']==row['expected'] for row in results),'checks':results,'cloudDeploymentByTests':False,'modelCalls':False}
print(json.dumps(receipt),flush=True)
if not receipt['passed']:raise SystemExit(1)
