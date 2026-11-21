"""Consume independently reconstructed Terraform output with the exact AWS image."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]


def qualify(args):
    directory=args.directory.resolve();out=args.out.resolve();core_path=args.core_receipt.resolve()
    if out.exists()or any(not path.is_relative_to(ROOT/'.local')for path in [directory,out,core_path]):raise ValueError('Use owned inputs and fresh output')
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket():raise ValueError('Use the existing owned Docker VM socket')
    proof=json.loads((directory/'independent-verification.json').read_text());core=json.loads(core_path.read_text())
    if not proof['passed']or not core['passed']or core['provider']!='aws'or proof['cloudOperations']or core['cloudOperations']:raise ValueError('Require independently qualified native mock output and AWS image')
    for receipt in [proof,core]:
        for name,digest in receipt['sourceHashes'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Qualified source drift')
    for name,digest in proof['inputHashes'].items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=digest:raise ValueError('Qualified native input drift')
    raw=(directory/'native-runtime-consumption.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=proof['consumptionSha256']:raise ValueError('Independent consumption payload drift')
    payload=json.loads(raw);payload['hashes']={name:core['sourceHashes']['src/runtime/'+name]for name in ['enterprise_aws_jobs.py','enterprise_aws_hosts.py','enterprise_aws_host_probe.py','enterprise-aws-task-template.json']}
    code='''import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'/app')
from enterprise_aws_jobs import configuration,verify_definition
from enterprise_aws_hosts import command_document
value=json.load(sys.stdin)
for name,digest in value['hashes'].items():assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest()==digest
owned=configuration(value['configuration'])
assert verify_definition(owned,{'taskDefinition':value['taskDefinition']})==owned['taskDefinitionArn']
assert command_document(owned)==value['document']
print(json.dumps({'passed':True,'installedDefinitionMatches':True,'installedDocumentMatches':True,'sourceHashesMatch':True}))
'''
    out.mkdir(parents=True)
    env={'PATH':os.environ.get('PATH',''),'DOCKER_HOST':args.docker_host,'DOCKER_CONFIG':str(ROOT/'.local/qualification-docker-config'),'HOME':str(out)}
    command=['docker','run','--rm','--platform','linux/amd64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','128m','--pids-limit','32','-i',core['imageId'],'python','-I','-c',code]
    result=subprocess.run(command,input=json.dumps(payload).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=30)
    (out/'native.stdout').write_bytes(result.stdout);(out/'native.stderr').write_bytes(result.stderr)
    passed=result.returncode==0 and json.loads(result.stdout).get('passed')is True
    (out/'receipt.json').write_text(json.dumps({'recordedAt':datetime.now(timezone.utc).isoformat(),'passed':passed,'imageId':core['imageId'],'cloudOperations':False,
        'sourceHashes':{str(Path(__file__).relative_to(ROOT)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        'inputHashes':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in [core_path,directory/'independent-verification.json',directory/'native-runtime-consumption.json']},
        'scope':'Exact installed AWS image consumes the independently reconstructed positive Terraform task/configuration and fixed command bytes without network access. Not ECS/SSM account execution, actual host behavior, image availability or whole-project acceptance.'},indent=2)+'\n')
    if not passed:raise ValueError('Installed image rejected native output')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--core-receipt',type=Path,required=True);parser.add_argument('--docker-host',required=True);qualify(parser.parse_args())
