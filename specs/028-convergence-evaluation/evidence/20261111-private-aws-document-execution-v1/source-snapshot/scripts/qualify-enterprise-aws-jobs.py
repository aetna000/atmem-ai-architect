"""Run the emitted ECS stages locally; S3/ECS account operations are not used."""
import argparse
import base64
from datetime import datetime,timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'tests/runtime'),str(ROOT/'.local/aws-web-runtime-sdk')]
from enterprise_aws_jobs import task_definition
from enterprise_aws_jobs_contract import config,native_check
from enterprise_document_job import request,result
from botocore.model import ServiceModel


def qualify(args):
    out=args.out.resolve()
    if out.exists()or not out.is_relative_to(ROOT/'.local'):raise ValueError('Use a fresh owned evidence directory')
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket():raise ValueError('Use the existing owned Docker socket')
    receipts=[]
    for path in [args.core_receipt,args.parser_receipt]:
        path=path.resolve()
        if not path.is_relative_to(ROOT/'.local'):raise ValueError('Use owned exact image receipts')
        value=json.loads(path.read_text())
        if not value.get('passed',value.get('allChecksPassed')):raise ValueError('Require qualified images')
        for name,digest in value['sourceHashes'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Qualified source changed: '+name)
        receipts.append(value)
    if receipts[0].get('provider')!='aws'or receipts[0].get('awsDocumentContractTests')!=25:raise ValueError('Require the AWS image and native contract checks')
    out.mkdir(parents=True);checks=[];success=False
    env={'PATH':os.environ.get('PATH',''),'HOME':str(out),'DOCKER_HOST':args.docker_host,'DOCKER_CONFIG':str(ROOT/'.local/qualification-docker-config')}
    paths=[Path(__file__).resolve(),ROOT/'tests/runtime/enterprise_aws_jobs_contract.py',
           *[ROOT/'src/runtime'/name for name in ['enterprise_aws_jobs.py','enterprise_aws_objects.py','enterprise_aws_transfer.py','enterprise_document_job.py','enterprise_document_contract.py']],
           ROOT/'tests/fixtures/providers/aws-ecs-2014-11-13-botocore-1.43.123.json.gz']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
    schema=paths[-1];provenance=json.loads(schema.with_suffix('.provenance.json').read_text())
    if hashlib.sha256(schema.read_bytes()).hexdigest()!=provenance['sha256']:raise ValueError('Native ECS schema drift')
    model=ServiceModel(json.loads(gzip.decompress(schema.read_bytes())),service_name='ecs')
    def run(label,command,data=None):
        done=subprocess.run(['docker',*command],env=env,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=160)
        (out/(label+'.stdout')).write_bytes(done.stdout);(out/(label+'.stderr')).write_bytes(done.stderr)
        checks.append({'check':label,'passed':done.returncode==0,'exitCode':done.returncode})
        if done.returncode:raise RuntimeError('AWS local stage qualification failed: '+label)
        return done.stdout
    wrapper='''import base64,hashlib,io,json,os,runpy,sys
sys.path.insert(0,'/app')
import boto3
fixture=json.load(sys.stdin);value=json.loads(os.environ['DOCUMENT_JOB'])
class Native:
 def owner(self,options):
  assert options['Bucket']==value['bucket']and options['ExpectedBucketOwner']==value['accountId']
 def get_bucket_location(self,**options):self.owner(options);return {'LocationConstraint':value['region']}
 def get_bucket_versioning(self,**options):self.owner(options);return {}
 def get_object(self,**options):
  self.owner(options);assert options['Key']=='document-jobs/'+value['request']['requestId']+'/input'
  assert options['IfMatch']==value['inputETag']
  raw=base64.b64decode(fixture['raw'],validate=True)
  return {'Body':io.BytesIO(raw),'ContentLength':len(raw),'ETag':value['inputETag'],'ServerSideEncryption':'AES256'}
 def put_object(self,**options):
  self.owner(options);assert options['Key']=='document-jobs/'+value['request']['requestId']+'/result'
  assert options['IfNoneMatch']=='*'and options['ServerSideEncryption']=='AES256'
  raw=options['Body'];assert options['ChecksumSHA256']==base64.b64encode(hashlib.sha256(raw).digest()).decode()
  print(json.dumps({'uploadedSha256':hashlib.sha256(raw).hexdigest(),'uploadedBytes':len(raw)}))
  return {'ETag':'"'+'f'*32+'"','ServerSideEncryption':'AES256'}
class Session:
 def client(self,name,**options):
  assert name=='s3'and options['region_name']==value['region']
  assert options['endpoint_url']=='https://s3.'+value['region']+'.amazonaws.com'
  return Native()
boto3.Session=Session
sys.argv=['enterprise_aws_transfer.py',fixture['mode']]
runpy.run_path('/app/enterprise_aws_transfer.py',run_name='__main__')
'''
    try:
        images=[value['imageId']for value in receipts]
        for side,image in zip(['transfer','parser'],images):
            info=json.loads(run(side+'-image',['image','inspect',image]))[0]
            if (info['Os'],info['Architecture'],info['Config']['User'])!=('linux','amd64','10001:10001'):raise ValueError('Unexpected exact image identity')
        owned=config()
        for key,image in zip(['transferImage','parserImage'],images):owned[key]=owned[key].split('@')[0]+'@'+image
        mapping={owned['transferImage']:images[0],owned['parserImage']:images[1]}
        for filename,mime,content in [('policy.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document','twenty days'),('invoice-scan.pdf','application/pdf','42.50')]:
            path=ROOT/'benchmarks/convergence/fixtures'/('invoices'if filename.endswith('.pdf')else'enterprise-documents')/filename
            raw=path.read_bytes();hashes[str(path.relative_to(ROOT))]=hashlib.sha256(raw).hexdigest()
            identifier=uuid.uuid4().hex+uuid.uuid4().hex;spec=task_definition(owned,request(raw,mime,identifier),'"'+'d'*32+'"')
            native_check(spec,model.operation_model('RegisterTaskDefinition').input_shape)
            (out/(filename+'-ecs-request.json')).write_text(json.dumps(spec,indent=2)+'\n')
            volumes={};uploaded=None
            try:
                for side in ['input','output']:
                    name='atmem-aws-job-qualification-'+identifier+'-'+side
                    run(filename+'-'+side+'-volume',['volume','create',name]);volumes[side]=name
                for stage,container in enumerate(spec['containerDefinitions']):
                    command=['run','--rm','--platform','linux/amd64','--network','none','--read-only','--log-driver','none',
                             '--user',container['user'],'--memory',str(container['memory'])+'m','--cpu-shares',str(container['cpu']),
                             '--pids-limit','128','--cap-drop','ALL','--security-opt','no-new-privileges']
                    for cap in container['linuxParameters']['capabilities'].get('add',[]):command+=['--cap-add',cap]
                    for temporary in container['linuxParameters'].get('tmpfs',[]):command+=['--tmpfs',temporary['containerPath']+':'+','.join(temporary['mountOptions'])+',size='+str(temporary['size'])+'m']
                    for mount in container['mountPoints']:command+=['--mount','type=volume,source='+volumes[mount['sourceVolume']]+',target='+mount['containerPath']+(',readonly'if mount['readOnly']else'')]
                    for item in container.get('environment',[]):command+=['--env',item['name']+'='+item['value']]
                    image=mapping[container['image']]
                    if stage==1:
                        logged=run(filename+'-parse',command+[image,*container['entryPoint'],*container['command']])
                        if json.loads(logged)!={'status':'ok'}:raise ValueError('Parser emitted more than a status receipt')
                    else:
                        mode='download'if stage==0 else'upload'
                        logged=run(filename+'-'+mode,command+['-i',image,'python','-I','-c',wrapper],json.dumps({'mode':mode,'raw':base64.b64encode(raw).decode()}).encode())
                        if stage==2:uploaded=json.loads(logged)
                read="import os,sys;sys.path.insert(0,'/app');from enterprise_document_job import read_file,MAX_ENVELOPE;fd=os.open('/output',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);sys.stdout.buffer.write(read_file(fd,'result.json',MAX_ENVELOPE));os.close(fd)"
                encoded=run(filename+'-collect',['run','--rm','--platform','linux/amd64','--network','none','--read-only','--log-driver','none','--cap-drop','ALL',
                    '--mount','type=volume,source='+volumes['output']+',target=/output,readonly',images[0],'python','-I','-c',read])
                document=result(raw,mime,identifier,encoded)
                if content not in document['text']or uploaded!={'uploadedSha256':hashlib.sha256(encoded).hexdigest(),'uploadedBytes':len(encoded)}:raise ValueError('Actual transfer/parser/consumer binding changed')
                checks.append({'check':filename+'-three-stage-byte-bound-answer','passed':True})
            finally:
                for side,name in volumes.items():run(filename+'-'+side+'-cleanup',['volume','rm',name])
        if any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest for name,digest in hashes.items()):raise ValueError('Qualification source drift')
        success=True
    finally:
        (out/'receipt.json').write_text(json.dumps({'recordedAt':datetime.now(timezone.utc).isoformat(),'passed':success,'checks':checks,'sourceHashes':hashes,
            'coreImageId':receipts[0]['imageId'],'parserImageId':receipts[1]['imageId'],'cloudOperations':False,
            'scope':'Actual ECS-plan transfer CLI, root/CHOWN handoff, two separate task-like POSIX volumes, parser and Office/scanned-PDF consumer in restricted owned Linux. S3 is an explicit SDK fixture. Local network/logging/PID restrictions do not prove native host policy, ECS scheduling, identity, termination, recovery or whole-project acceptance.'},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--docker-host',required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--core-receipt',type=Path,required=True);parser.add_argument('--parser-receipt',type=Path,required=True);qualify(parser.parse_args())
