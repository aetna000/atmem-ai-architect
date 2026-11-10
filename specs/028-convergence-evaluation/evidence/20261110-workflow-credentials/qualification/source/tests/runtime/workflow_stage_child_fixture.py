"""Trusted test child; never emitted as a production processor."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

mode=sys.argv[1]
if mode=='marker':
    time.sleep(1);Path(sys.argv[2]).write_text('escaped');sys.exit(0)
request=json.load(sys.stdin)
if mode=='tls':
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src/runtime'))
    import ssl
    from approved_http_destination import ApprovedHttpDestination
    destination=ApprovedHttpDestination(os.environ['DESTINATION_ENDPOINT'],lambda:os.environ['DESTINATION_TOKEN'],destination_scope='synthetic-account',tls_context=ssl.create_default_context(cafile=os.environ['DESTINATION_CA']))
    result=destination(request['operation'],**request['identity']);print(json.dumps({'status':'ok','result':result}));sys.exit(0)
if mode=='hang':time.sleep(60)
if mode=='flood':
    while True:os.write(1,b'x'*8192)
if mode=='descendant':
    subprocess.Popen([sys.executable,'-I',__file__,'marker',sys.argv[2]],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(60)
if mode=='invalid':os.write(1,b'{"status":"ok","status":"ok","result":{}}');sys.exit(0)
if mode=='crash':os.write(2,b'PRIVATE_PROVIDER_RESPONSE');sys.exit(2)
if mode=='receipt':
    # Represents the point after an external acceptance, before acknowledgement.
    Path(sys.argv[2]).write_text('accepted');time.sleep(60)
result={'operation':request['operation'],'identity':request['identity'],'inherited_secret':os.getenv('ATMEM_TEST_PARENT_SECRET')}
print(json.dumps({'status':'ok','result':result}))
