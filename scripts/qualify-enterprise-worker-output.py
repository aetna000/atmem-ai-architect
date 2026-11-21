"""The exact installed worker loads a real native Terraform output envelope.

No cloud, source, model or SQL requests. Separate SQL tests exercise queue/recovery.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'tests/runtime'),str(ROOT/'.local/azure-runtime-sdk')]
from enterprise_deployment_fixture import metadata


def qualify(args):
    directory=args.directory.resolve();out=args.out.resolve();core_path=args.core_receipt.resolve()
    if out.exists()or any(not path.is_relative_to(ROOT/'.local')for path in [directory,out,core_path]):raise ValueError('Use owned input and fresh output')
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket():raise ValueError('Use the existing owned Docker VM')
    core=json.loads(core_path.read_text());native=json.loads((directory/'receipt.json').read_text());proof=json.loads((directory/'independent-verification.json').read_text())
    if any(not value['passed']or value['cloudOperations']for value in [core,native,proof]):raise ValueError('Require independently qualified exact artifacts')
    provider=core['provider']
    if provider not in {'aws','gcp'}or proof.get('nativeMockTests')!={'aws':10,'gcp':11}[provider]:raise ValueError('Require the full selected-provider native suite')
    verifier='scripts/'+('verify-aws-document-infrastructure.py'if provider=='aws'else'verify-google-document-configuration.py')
    if proof.get('verifierSha256',proof.get('sourceHashes',{}).get(verifier))!=hashlib.sha256((ROOT/verifier).read_bytes()).hexdigest():raise ValueError('Independent verifier version drift')
    for value in [core,native,proof]:
        for name,digest in value.get('sourceHashes',{}).items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Qualified source drift')
    for name,digest in native['emittedHashes'].items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=digest:raise ValueError('Emitted artifact drift')
    log=(directory/'mock-plans.log').read_bytes()
    if proof.get('nativeLogSha256',hashlib.sha256(log).hexdigest())!=hashlib.sha256(log).hexdigest():raise ValueError('Independent native log drift')
    for name,digest in proof.get('inputHashes',{}).items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=digest:raise ValueError('Independent native input drift')
    events=[json.loads(line)for line in log.splitlines()]
    plans=[event['test_plan']for event in events if event.get('@testrun')=='private_document_substrate'and event.get('test_plan')]
    if len(plans)!=1:raise ValueError('Require the real positive native plan')
    outputs=plans[0]['output_changes'];envelope=outputs['document_executor_configuration']['after']
    if provider not in {'aws','gcp'}or envelope['provider']!=provider or envelope['configuration']!=outputs['document_job_configuration']['after']:raise ValueError('Worker configuration disagrees with the native job target')
    artifacts=outputs['artifacts'if provider=='aws'else'document_job_artifacts']['after']
    if envelope['parserRevision']!=artifacts['parserRevision']:raise ValueError('Worker/parser artifact binding drift')
    owned=metadata('synthetic-output-qualification',provider);owned['parserRevision']=envelope['parserRevision']
    config=envelope['configuration'];environment={'ENTERPRISE_DOCUMENT_EXECUTOR_JSON':json.dumps(envelope),'REGION':config['region']}
    environment.update({'AWS_ACCOUNT_ID':config['accountId'],'WORKER_ROLE_ARN':config['workerRoleArn']}if provider=='aws'else{'PROJECT_ID':config['projectId'],'DATABASE_SERVICE_ACCOUNT':config['workerServiceAccount']})
    names=['enterprise_worker.py','enterprise_configuration.py','enterprise_native.py','enterprise_aws_jobs.py'if provider=='aws'else'enterprise_google_jobs.py']
    payload={'metadata':owned,'environment':environment,'provider':provider,'hashes':{name:core['sourceHashes']['src/runtime/'+name]for name in names}}
    code='''import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'/app')
from enterprise_worker import build_executor
value=json.load(sys.stdin)
for name,digest in value['hashes'].items():assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest()==digest
executor=build_executor(value['metadata'],value['environment'])
assert executor.artifact_revision==value['metadata']['parserRevision']
assert executor.run.ledger is None
assert type(executor.run).__name__==('EcsDocuments'if value['provider']=='aws'else'GoogleBatchDocuments')
print(json.dumps({'passed':True,'nativeConfigurationLoaded':True,'provider':value['provider'],'parserRevisionBound':True}))
'''
    out.mkdir(parents=True)
    env={'PATH':os.environ.get('PATH',''),'DOCKER_HOST':args.docker_host,'DOCKER_CONFIG':str(ROOT/'.local/qualification-docker-config'),'HOME':str(out)}
    command=['docker','run','--rm','--platform','linux/amd64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','128m','--pids-limit','32','-i',core['imageId'],'python','-I','-c',code]
    result=subprocess.run(command,env=env,input=json.dumps(payload).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    (out/'native.stdout').write_bytes(result.stdout);(out/'native.stderr').write_bytes(result.stderr)
    passed=result.returncode==0 and json.loads(result.stdout).get('passed')is True
    dependencies=[Path(__file__).resolve(),ROOT/'tests/runtime/enterprise_deployment_fixture.py']
    (out/'receipt.json').write_text(json.dumps({'recordedAt':datetime.now(timezone.utc).isoformat(),'passed':passed,'provider':provider,'imageId':core['imageId'],'cloudOperations':False,
       'sourceHashes':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in dependencies},
       'inputHashes':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in [core_path,directory/'receipt.json',directory/'independent-verification.json',directory/'mock-plans.log']},
       'scope':'Exact installed worker consumes the positive native provider-mock output and binds provider, destination, worker and parser revision without network access. Does not exercise native cloud identity, remote jobs, full application hosting or whole-project acceptance.'},indent=2)+'\n')
    if not passed:raise ValueError('Installed worker rejected native output')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--core-receipt',type=Path,required=True);parser.add_argument('--docker-host',required=True);qualify(parser.parse_args())
