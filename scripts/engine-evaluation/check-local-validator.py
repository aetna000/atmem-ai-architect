#!/usr/bin/env python3
"""Real local-container controller qualification; synthetic canaries, no cloud."""
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import sys
import threading
import zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec

OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-local-validator'
OUT.mkdir(parents=True,exist_ok=True)
IMAGE='sha256:48d884813cf44e927cf64c5529dd630dd3b18338c6dc727991eef9b71e934a20'
ENDPOINT='unix://'+str(Path.home()/'.colima/architect-qualification/docker.sock')


def archive(files):
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as bundle:
        for name,content in files.items():bundle.writestr(name,content)
    return data.getvalue()


listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();port=listener.getsockname()[1]
canary='SYNTHETIC HOST-ONLY CANARY';hits=[]
def serve():
    try:
        listener.settimeout(60)
        connection,_=listener.accept();hits.append(True);connection.sendall(canary.encode());connection.close()
    except OSError:pass
thread=threading.Thread(target=serve,daemon=True);thread.start()
probe='''import http.client,http.server,os,pathlib,socket,threading,sys
assert os.getuid()==65532 and os.getgid()==65532 and os.getgroups()==[]
status=pathlib.Path('/proc/self/status').read_text()
assert 'NoNewPrivs:\\t1' in status
assert int(next(line.split()[1] for line in status.splitlines() if line.startswith('CapEff:')),16)==0
assert int(next(line.split()[1] for line in status.splitlines() if line.startswith('CapPrm:')),16)==0
try:pathlib.Path(__file__).write_text('CHANGED')
except PermissionError:pass
else:raise AssertionError('Source was writable')
assert not pathlib.Path('/var/run/docker.sock').exists()
assert not pathlib.Path('/Users').exists()
assert os.environ.get('ATMEM_SYNTHETIC_HOST_SECRET') is None
try:socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_ICMP)
except PermissionError:pass
else:raise AssertionError('Raw socket allowed')
for endpoint in [('192.0.2.1',80),('127.0.0.1',PORT)]:
 s=socket.socket();s.settimeout(1)
 try:s.connect(endpoint)
 except OSError:pass
 else:raise AssertionError('External/host connection allowed')
 finally:s.close()
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.end_headers();self.wfile.write(b'isolated-http')
 def log_message(self,*args):pass
server=http.server.HTTPServer(('127.0.0.1',0),Handler)
t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3);client.request('GET','/health')
response=client.getresponse();assert response.status==200 and response.read()==b'isolated-http'
client.close();server.shutdown();server.server_close();t.join()
print('PASS: nonroot/no-groups/no-effective-capabilities/no-new-privileges/read-only-source/no-Docker/no-host-mount/no-host-secret/no-raw-socket/no-external-or-host-network/actual-isolated-loopback-HTTP')
print('Python:',sys.version)
'''.replace('PORT',str(port))
checks=[]
prior_canary=os.environ.get('ATMEM_SYNTHETIC_HOST_SECRET')
os.environ['ATMEM_SYNTHETIC_HOST_SECRET']='SYNTHETIC-ONLY-HOST-ENV-CANARY'
try:
    worker=DockerValidationWorker(ENDPOINT)
    for name,files,command,budget,expected in [
        ('policy-http-probe',{'policy_probe.py':probe},('/usr/local/bin/python3','policy_probe.py'),60,'passed'),
        ('timeout-probe',{'wait.py':'import time;time.sleep(30)'},('/usr/local/bin/python3','wait.py'),2,'failed'),
        ('skip-probe',{'test_skip.py':'import unittest\n@unittest.skip("deliberately missing evidence")\nclass Missing(unittest.TestCase):\n def test_missing(self):pass\n'},('/usr/local/bin/python3','-m','unittest','discover','-v'),60,'incomplete'),
        ('zero-tests-probe',{'not_a_test.py':'pass'},('/usr/local/bin/python3','-m','unittest','discover','-v'),60,'failed'),
        ('zip-slip-probe',{'../escape.py':'raise RuntimeError("must never execute")'},('/usr/local/bin/python3','escape.py'),60,'failed')]:
        data=archive(files)
        result=worker.run(data,hashlib.sha256(data).hexdigest(),ValidationSpec(name,IMAGE,command,timeout_seconds=budget))
        checks.append({'expectedStatus':expected,**result})
        (OUT/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
        print(name,result['status'],result['output'][-1000:],flush=True)
    output_worker=DockerValidationWorker(ENDPOINT,max_output_bytes=1024)
    data=archive({'loud.py':'print("x"*1000000)'})
    result=output_worker.run(data,hashlib.sha256(data).hexdigest(),ValidationSpec('output-limit-probe',IMAGE,('/usr/local/bin/python3','loud.py')))
    checks.append({'expectedStatus':'failed',**result})
    (OUT/'output-limit-probe.json').write_text(json.dumps(result,indent=2)+'\n')
finally:
    if prior_canary is None:os.environ.pop('ATMEM_SYNTHETIC_HOST_SECRET',None)
    else:os.environ['ATMEM_SYNTHETIC_HOST_SECRET']=prior_canary
    listener.close()
    receipt={'passed':len(checks)==6 and all(c['status']==c['expectedStatus'] for c in checks) and not hits,
        'checks':checks,'hostCanaryConnections':len(hits),'cloudOperations':False,
        'boundary':'Actual isolated cached Linux container execution: policy/loopback success plus timeout, skipped evidence, traversal and output-limit rejection. No generated application or full-system acceptance.'}
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert receipt['passed'],receipt
