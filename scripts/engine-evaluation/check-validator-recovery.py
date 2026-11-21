#!/usr/bin/env python3
"""Live bounded cancellation and exact-job cleanup on the existing local VM."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec
OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-validation-jobs';OUT.mkdir(parents=True,exist_ok=True)
endpoint='unix://'+str(Path.home()/'.colima/architect-qualification/docker.sock')
worker=DockerValidationWorker(endpoint)
spec=ValidationSpec('recovery-probe','sha256:48d884813cf44e927cf64c5529dd630dd3b18338c6dc727991eef9b71e934a20',('/usr/local/bin/python3','wait.py'),timeout_seconds=60)
data=io.BytesIO()
with zipfile.ZipFile(data,'w') as archive:archive.writestr('wait.py','import time;time.sleep(90)')
content=data.getvalue();digest=hashlib.sha256(content).hexdigest()
ids=[str(uuid.uuid4()),str(uuid.uuid4())];flags=[threading.Event(),threading.Event()]
pool=ThreadPoolExecutor(max_workers=2);receipt={'passed':False,'cloudOperations':False}
try:
    with tempfile.TemporaryDirectory(prefix='atmem-validator-observer-') as folder:
        config=Path(folder)/'docker';config.mkdir();(config/'config.json').write_text('{}')
        env={'PATH':os.environ.get('PATH',''),'HOME':folder,'DOCKER_HOST':endpoint,'DOCKER_CONFIG':str(config)}
        def running(ident):
            name='atmem-validator-'+uuid.UUID(ident).hex
            result=subprocess.run(['docker','--host',endpoint,'--config',str(config),'container','inspect',name,'--format','{{.State.Running}}'],env=env,capture_output=True,text=True,timeout=10)
            return result.returncode==0 and result.stdout.strip()=='true'
        futures=[pool.submit(worker.run,content,digest,spec,execution_id=ident,cancel_event=flag) for ident,flag in zip(ids,flags)]
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            if all(running(ident) for ident in ids):break
            if any(future.done() for future in futures):raise RuntimeError('Probe ended before its container was observed running')
            time.sleep(.1)
        else:raise TimeoutError('Both probe containers were not observed running')
        flags[0].set();cancelled=futures[0].result(timeout=30)
        assert cancelled['status']=='failed' and cancelled['reason']=='cancelled',cancelled
        assert not running(ids[0]) and running(ids[1]),'Cancellation affected the wrong job'
        recovery=worker.recover(ids[1]);recovered=futures[1].result(timeout=30)
        assert recovery=={'cleanupConfirmed':True,'workReplayed':False}
        assert recovered['status']=='failed' and not running(ids[1]),recovered
        repeated=worker.recover(ids[1]);assert repeated==recovery
        receipt.update(passed=True,cancelled=cancelled,recovered=recovered,recovery=recovery,
            repeatedRecovery=repeated,peerPreservedDuringCancellation=True,
            boundary='Two actual named cached Linux containers observed running. Cancellation removed only its own job, peer remained running, exact-job recovery then removed that peer without replay; repeated recovery confirmed absence. No cloud, host mounts or other container changes.')
finally:
    for flag in flags:flag.set()
    pool.shutdown(wait=True)
    (OUT/'runtime-recovery-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert receipt['passed']
print('Passed actual validator cancellation, scoped peer preservation and repeated cleanup without replay.')
