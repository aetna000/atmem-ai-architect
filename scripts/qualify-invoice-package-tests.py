"""Execute the delivered portable test suite in its exact Linux test image."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
PROBE=r'''
import hashlib,importlib.metadata,json,os,re,subprocess,sys
from pathlib import Path
packet=json.load(sys.stdin)
for name,digest in packet['files'].items():assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest()==digest
versions={}
for name,version in re.findall(r'^([a-zA-Z0-9_.-]+)==([^ \\\n]+)',Path('/app/test-requirements.lock').read_text(),re.M):
 actual=importlib.metadata.version(name);assert actual==version;versions[name]=actual
private=Path('/app/.local');private.chmod(0o700);fixture=private/'owned-fixture.json';fixture.write_text(json.dumps(packet['fixture']));fixture.chmod(0o600)
out=private/'portable-tests'
result=subprocess.run([sys.executable,'-I','/app/tests/run.py','--fixture',str(fixture),'--out',str(out)],capture_output=True,timeout=160)
receipt=json.loads((out/'receipt.json').read_text())if(out/'receipt.json').exists()else{'passed':False}
logs={path.name:path.read_text()for path in out.glob('*.log')}
print(json.dumps({'passed':result.returncode==0 and receipt['passed'],'receipt':receipt,'versions':versions,'stdout':result.stdout.decode(),'stderr':result.stderr.decode(),'logs':logs}))
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--image',required=True);parser.add_argument('--fixture',required=True);parser.add_argument('--docker-host',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    source=Path(args.source).resolve();fixture=Path(args.fixture).resolve();out=Path(args.out).resolve()
    if out.exists()or any(not path.is_relative_to(ROOT/'.local')for path in [source,fixture,out])or not re.fullmatch(r'sha256:[0-9a-f]{64}',args.image)or not args.docker_host.startswith('unix:///'):raise ValueError('Use exact local source/image/fixture and a fresh local output')
    config=json.loads(fixture.read_text())
    package_name='atmem-invoice-'+hashlib.sha256(str(source).encode()).hexdigest()[:12]
    existing_fixture=config.get('name')in {'atmem-durable-qualification','atmem-durable-qualification-pg18'}
    package_fixture=fixture.is_relative_to(source/'.local/durable-postgres')and config.get('name')in {package_name,package_name+'-pg18'}
    if not(existing_fixture or package_fixture)or not re.fullmatch(r'architect_qualification_[a-z0-9]{1,32}',config.get('database',''))or not re.fullmatch('[0-9a-f]{64}',config.get('marker','')):raise ValueError('Use an existing owned or exact package-local loopback fixture')
    files=[*source.glob('*.py'),*source.glob('*.sql'),*source.glob('invoice-web.*'),source/'invoice-deployment.json',source/'test-requirements.lock',*(source/'tests').glob('*.py'),*(source/'parser').glob('*.py'),*(source/'test-fixtures').glob('*')]
    hashes=lambda:{str(path.relative_to(source)):hashlib.sha256(path.read_bytes()).hexdigest()for path in sorted(files)}
    before=hashes();tool_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();out.mkdir()
    env={'PATH':os.environ['PATH'],'DOCKER_HOST':args.docker_host,'DOCKER_CONFIG':str(ROOT/'.local/qualification-docker-config')}
    command=['docker','run','--rm','--platform','linux/amd64','--network','host','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--tmpfs','/app/.local:rw,noexec,nosuid,size=128m','--memory','512m','--cpus','1','--pids-limit','64','--cap-drop','ALL','--security-opt','no-new-privileges:true','-i','--entrypoint','python',args.image,'-I','-c',PROBE]
    result=subprocess.run(command,env=env,input=json.dumps({'files':before,'fixture':config}).encode(),capture_output=True,timeout=180)
    for secret in [config['password'],config['marker']]:assert secret.encode()not in result.stdout+result.stderr
    (out/'stdout.json').write_bytes(result.stdout);(out/'stderr.log').write_bytes(result.stderr)
    try:probe=json.loads(result.stdout)
    except Exception:probe={'passed':False}
    for name,body in probe.pop('logs',{}).items():
        if Path(name).name!=name:raise ValueError('Unexpected log name')
        (out/name).write_text(body)
    passed=result.returncode==0 and probe.get('passed')and before==hashes()and tool_hash==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    receipt={'kind':'actual-emitted-portable-invoice-tests-linux-image','passed':bool(passed),'image':args.image,'sourceHashes':before,'qualifierSha256':tool_hash,'probe':probe,'cloudOperations':False,'boundary':'Actual emitted test/runtime sources and exact pinned Linux test dependencies with real owned loopback PostgreSQL. Synthetic identity/storage/model/accounting transport fixtures, not cloud authentication, actual OCR image, model quality, account plan or deployment.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':bool(passed),'checks':probe.get('receipt',{}).get('checks'),'stderr':probe.get('stderr'),'receipt':str(out/'receipt.json')}));sys.exit(0 if passed else 1)
