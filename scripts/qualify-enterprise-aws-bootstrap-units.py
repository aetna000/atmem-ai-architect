"""Parse emitted systemd units in the owned Linux VM without installing them."""
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]


def qualify(directory,out):
    directory=directory.resolve();out=out.resolve()
    if not directory.is_relative_to(ROOT/'.local')or not out.is_relative_to(ROOT/'.local')or out.exists():raise ValueError('Use owned input and fresh evidence')
    proof=json.loads((directory/'independent-verification.json').read_text())
    if not proof['passed']or proof['cloudOperations']:raise ValueError('Require independent output verification')
    for name,digest in proof['sourceHashes'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Independent verifier source drift')
    for name,digest in proof['inputHashes'].items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=digest:raise ValueError('Independent verifier input drift')
    events=[json.loads(line)for line in (directory/'mock-plans.log').read_text().splitlines()]
    plan=next(value['test_plan']for value in events if value.get('@testrun')=='private_document_substrate'and value.get('test_plan'))
    launch=next(row['change']['after']for row in plan['resource_changes']if row['type']=='aws_launch_template')
    cloud=base64.b64decode(launch['user_data'],validate=True).decode();assert cloud.startswith('#cloud-config\n')
    cloud=json.loads(cloud.split('\n',1)[1]);files={row['path']:row['content']for row in cloud['write_files']if row['path'].startswith('/etc/systemd/system/')}
    owned={name.removeprefix('/etc/systemd/system/'):raw for name,raw in files.items()}
    assert set(owned)=={'atmem-document-guard.service','ecs.service.d/atmem-document.conf'}
    # Native syntax/dependency verification uses explicit platform-service stubs;
    # this is not a check of the actual Amazon AMI's units or startup behavior.
    owned.update({'ecs.service':'[Unit]\nRequires=docker.service\nAfter=docker.service cloud-final.service\n[Service]\nExecStart=/bin/true\n',
                  'docker.service':'[Service]\nExecStart=/bin/true\n',
                  'cloud-final.service':'[Service]\nType=oneshot\nExecStart=/bin/true\n'})
    payload=base64.b64encode(json.dumps(owned).encode()).decode()
    code='''import base64,json,os,shutil,subprocess,tempfile
from pathlib import Path
value=json.loads(base64.b64decode(PAYLOAD,validate=True));assert shutil.which('systemd-analyze')
with tempfile.TemporaryDirectory(prefix='atmem-native-units-')as folder:
 root=Path(folder)
 for name,text in value.items():
  target=root/name;assert target.is_relative_to(root)
  target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
 result=subprocess.run(['systemd-analyze','verify','--man=no',*[str(root/name)for name in ['ecs.service','docker.service','cloud-final.service','atmem-document-guard.service']]],
  env={**os.environ,'SYSTEMD_UNIT_PATH':folder+':/usr/lib/systemd/system:/lib/systemd/system'},stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
 if result.returncode:
  print(result.stderr.decode()[:8192]);raise SystemExit(result.returncode)
 print(json.dumps({'passed':True,'nativeSystemdVerify':True,'installedUnits':False,'platformServicesAreStubs':True}))
'''.replace('PAYLOAD',repr(payload))
    out.mkdir(parents=True)
    result=subprocess.run(['colima','ssh','--profile','architect-qualification','--','python3','-I','-c',code],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=40)
    (out/'native.stdout').write_bytes(result.stdout);(out/'native.stderr').write_bytes(result.stderr)
    passed=result.returncode==0 and json.loads(result.stdout).get('passed')is True
    receipt={'recordedAt':datetime.now(timezone.utc).isoformat(),'passed':passed,'cloudOperations':False,
             'sourceHashes':{str(Path(__file__).relative_to(ROOT)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
             'inputHashes':{str((directory/name).relative_to(ROOT)):hashlib.sha256((directory/name).read_bytes()).hexdigest()for name in ['independent-verification.json','mock-plans.log','receipt.json']},
             'scope':'Native systemd-analyze verifies emitted guard/drop-in syntax/dependencies with explicit Docker/ECS/cloud-final stubs in a temporary directory in the owned Linux VM. No units installed or services changed; not actual AMI or host startup qualification.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if not passed:raise ValueError('Native unit verification failed')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();qualify(args.directory,args.out)
