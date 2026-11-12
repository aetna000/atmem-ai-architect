"""Exact installed AWS controller with owned SQL fixtures and abrupt process death."""
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[1]


def qualify(args):
    out=args.out.resolve();receipt=args.core_receipt.resolve()
    if out.exists()or not out.is_relative_to(ROOT/'.local')or not receipt.is_relative_to(ROOT/'.local'):raise ValueError('Use fresh owned local evidence and image receipt')
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket():raise ValueError('Use the owned Docker VM')
    core=json.loads(receipt.read_text())
    if not core.get('passed')or core.get('provider')!='aws':raise ValueError('Require the qualified AWS image')
    for name,digest in core['sourceHashes'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Qualified image source changed')
    names=['tests/runtime/'+name for name in ['enterprise_aws_document_postgres.py','enterprise_aws_execution_contract.py','enterprise_aws_jobs_contract.py',
        'enterprise_google_jobs_acceptance.py','enterprise_deployment_fixture.py','enterprise_oauth_acceptance.py','durable_postgres_acceptance.py','durable_fixture_tasks.py']]
    names+=['src/runtime/durable_workflow.py','src/runtime/workflow_contract.py',
        'tests/fixtures/providers/aws-ecs-2014-11-13-botocore-1.43.123.json.gz','tests/fixtures/providers/aws-ecs-2014-11-13-botocore-1.43.123.json.provenance.json']
    hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()for name in names}
    hashes[str(Path(__file__).resolve().relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    payload={name:base64.b64encode((ROOT/name).read_bytes()).decode()for name in names}
    out.mkdir(parents=True);checks=[];passed=False
    env={'PATH':os.environ.get('PATH',''),'HOME':str(out),'DOCKER_HOST':args.docker_host,'DOCKER_CONFIG':str(ROOT/'.local/qualification-docker-config')}
    def run(label,command,data=None):
        done=subprocess.run(['docker',*command],env=env,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
        (out/(label+'.stdout')).write_bytes(done.stdout);(out/(label+'.stderr')).write_bytes(done.stderr)
        checks.append({'check':label,'passed':done.returncode==0,'exitCode':done.returncode})
        if done.returncode:raise RuntimeError('AWS installed recovery qualification failed: '+label)
        return done.stdout+done.stderr
    loader='''import base64,json,os,runpy,sys
from pathlib import Path,PurePosixPath
root=Path('/tmp/workspace');root.mkdir()
for name,raw in json.load(sys.stdin).items():
 path=PurePosixPath(name);assert not path.is_absolute()and '..'not in path.parts
 target=root.joinpath(*path.parts);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(raw,validate=True));target.chmod(0o400)
os.chdir(root);sys.path[:0]=['/app',str(root/'tests/runtime'),str(root/'src/runtime')]
entry=root/'tests/runtime/enterprise_aws_document_postgres.py';sys.argv=[str(entry),'-v'];runpy.run_path(str(entry),run_name='__main__')
'''
    try:
        observed=run('image',['image','inspect','--format','{{.Id}}',core['imageId']]).decode().strip()
        if observed!=core['imageId']:raise ValueError('Installed image identity changed')
        for version in [17,18]:
            original=json.loads((ROOT/'.local/durable-postgres'/('fixture.json'if version==17 else'fixture-pg18.json')).read_text())
            name='atmem-durable-qualification'+('-pg18'if version==18 else'')
            template='{"Id":{{json .Id}},"Name":{{json .Name}},"NetworkSettings":{"Ports":{{json .NetworkSettings.Ports}}}}'
            observed=json.loads(run('pg'+str(version)+'-container',['container','inspect','--format',template,name]))
            if (original['name']!=name or observed['Name']!='/'+name or
                not any(v['HostIp']=='127.0.0.1'and int(v['HostPort'])==original['port']for v in observed['NetworkSettings']['Ports']['5432/tcp'])):raise ValueError('Owned fixture identity changed')
            private={**payload,'fixture.json':base64.b64encode(json.dumps({**original,'port':5432}).encode()).decode()}
            output=run('pg'+str(version)+'-recovery',['run','--rm','--platform','linux/amd64','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=64m',
                '--memory','512m','--pids-limit','96','--cap-drop','ALL','--security-opt','no-new-privileges','--network','container:'+observed['Id'],
                '--env','ATMEM_WORKFLOW_TEST_CONFIG=/tmp/workspace/fixture.json','-i',core['imageId'],'python','-I','-c',loader],json.dumps(private).encode())
            if not re.search(rb'Ran 11 tests in [^\n]+\n\nOK\s*$',output):raise ValueError('Unexpected AWS recovery inventory')
        if any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest for name,digest in hashes.items()):raise ValueError('Recovery qualification sources changed')
        passed=True
    finally:
        (out/'receipt.json').write_text(json.dumps({'recordedAt':datetime.now(timezone.utc).isoformat(),'passed':passed,'checks':checks,'sourceHashes':hashes,
            'imageId':core['imageId'],'cloudOperations':False,'testsPerPostgresVersion':11,'nativeSqlRecoveryTestsPerVersion':3,'additionalOfflineContractTestsPerVersion':8,
            'scope':'Installed Linux AWS controller with real owned PostgreSQL17/18 and abrupt child process death. ECS/S3/host-policy HTTP are fixtures. Not native account behavior, host hardening or complete project acceptance.'},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--docker-host',required=True);parser.add_argument('--core-receipt',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);qualify(parser.parse_args())
