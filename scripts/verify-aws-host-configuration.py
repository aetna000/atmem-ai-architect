"""Consume actual native mock-plan outputs independently of the JS emitter."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path
import shlex
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'tests/runtime'),str(ROOT/'.local/aws-web-runtime-sdk')]
from enterprise_aws_hosts import command_document,EcsHostPolicy
from enterprise_aws_jobs import configuration
from enterprise_aws_jobs_contract import config,native_check
from botocore.model import ServiceModel


def verify(path):
    path=path.resolve()
    if not path.is_relative_to(ROOT/'.local'):raise ValueError('Use owned native qualification evidence')
    receipt=json.loads((path/'receipt.json').read_text())
    if not receipt['passed']or receipt['cloudOperations']:raise ValueError('Require a passed credential-free native mock qualification')
    for collection in ['sourceHashes','emittedHashes']:
        for name,digest in receipt[collection].items():
            target=(ROOT if collection=='sourceHashes'else path)/name
            if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('Qualified source/artifact changed')
    events=[];summary=None
    log=(path/'mock-plans.log').read_bytes()
    for line in log.splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if event.get('test_summary'):summary=event['test_summary']
        if event.get('@testrun')=='fixed_host_verification'and event.get('test_plan'):events.append(event['test_plan'])
    if not summary or summary.get('status')!='pass'or summary.get('passed')!=6 or any(summary.get(key,0)for key in ['failed','errored','skipped'])or len(events)!=1:
        raise ValueError('Require all six native plans and the actual positive output')
    native=events[0];output=native['output_changes']['host_verification']['after']
    if json.loads((path/'runtime-configurations.json').read_text())!=[output]:raise ValueError('Output did not come from the positive native plan')
    c=configuration({**config(),**output});rows=native['resource_changes']
    documents=[row['change']['after']for row in rows if row['type']=='aws_ssm_document']
    if len(documents)!=1:raise ValueError('Unexpected command document count')
    document=json.loads(documents[0]['content']);expected=command_document(c)
    if document!=expected:raise ValueError('Resolved native command differs from the actual runtime verifier')
    if documents[0]['arn']!=output['hostDocumentArn']or documents[0]['hash']!=output['hostDocumentHash']or str(documents[0]['latest_version'])!=output['hostDocumentVersion']:
        raise ValueError('Runtime output drifted from native resource identity')
    args=shlex.split(document['mainSteps'][0]['inputs']['runCommand'][0])
    if args[:4]!=['exec','/usr/bin/python3','-I','-c']or len(args)!=6:raise ValueError('Unexpected probe invocation')
    launcher=ast.parse(args[4]);encoded=ast.literal_eval(launcher.body[1].value.args[0].args[0].args[0])
    probe=base64.b64decode(encoded,validate=True)
    if probe!=(ROOT/'src/runtime/enterprise_aws_host_probe.py').read_bytes():raise ValueError('Native command executes a different probe')
    compile(probe,'owned-host-probe','exec')
    payload=json.loads(base64.b64decode(args[5],validate=True))
    if payload!={'format':'enterprise-aws-host-policy-v1','clusterArn':c['clusterArn'],'policySha256':c['hostPolicySha256']}:raise ValueError('Native command policy payload changed')
    models={}
    for service,version in [('ecs','2014-11-13'),('ssm','2014-11-06')]:
        source=ROOT/f'tests/fixtures/providers/aws-{service}-{version}-botocore-1.43.123.json.gz'
        if hashlib.sha256(source.read_bytes()).hexdigest()!=json.loads(source.with_suffix('.provenance.json').read_text())['sha256']:raise ValueError('Native API schema drift')
        models[service]=ServiceModel(json.loads(gzip.decompress(source.read_bytes())),service_name=service)
    member='arn:aws:ecs:'+c['region']+':'+c['accountId']+':container-instance/document-parser/'+'a'*32
    instance='i-'+'a'*17;command='12345678-1234-1234-1234-123456789abc';calls=[]
    class Api:
        def call(self,service,operation,**values):
            native_check(values,models[service].operation_model(''.join(part.title()for part in operation.split('_'))).input_shape)
            calls.append((service,operation))
            if operation=='list_container_instances':return {'containerInstanceArns':[member]}
            if operation=='describe_container_instances':return {'containerInstances':[{'containerInstanceArn':member,'ec2InstanceId':instance,'agentConnected':True,'status':'ACTIVE','attributes':[{'name':'atmem-document-policy','value':c['hostPolicySha256']}]}]}
            if operation=='get_document':return {'DocumentVersion':c['hostDocumentVersion'],'Content':documents[0]['content']}
            if operation=='send_command':return {'Command':{'CommandId':command}}
            if operation=='get_command_invocation':return {'CommandId':command,'InstanceId':instance,'DocumentName':c['hostDocumentArn'],'DocumentVersion':c['hostDocumentVersion'],'Status':'Success','ResponseCode':0,'StandardErrorContent':'','StandardOutputContent':json.dumps({'format':'enterprise-aws-host-observation-v1','clusterArn':c['clusterArn'],'policySha256':c['hostPolicySha256'],'bootId':command})}
            raise ValueError('Unexpected native operation')
    proof=EcsHostPolicy(c,api=Api())(c);placement=proof.placement(c)
    return {'passed':True,'nativeMockTests':6,'runtimeDocumentMatchesNativePlan':True,'probeSourceSha256':hashlib.sha256(probe).hexdigest(),
            'nativeLogSha256':hashlib.sha256(log).hexdigest(),'verifierSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'hostPolicySha256':c['hostPolicySha256'],'calls':calls,'placement':placement,'cloudOperations':False,
            'scope':'Positive native Terraform output consumed by runtime, exact probe/argument binding and native ECS/SSM input schemas. Service responses are fixtures; no actual host/account or full-project acceptance.'}


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Supply the owned native qualification directory')
    print(json.dumps(verify(Path(sys.argv[1])),indent=2))
