"""Point-in-time host inspection through one fixed, hash/version-bound SSM document."""
from dataclasses import dataclass
import base64
import json
import math
from pathlib import Path
import re
import shlex
import threading
import time
from types import MappingProxyType
from enterprise_sources import SourceUnavailable


def unique(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('Ambiguous host-inspection content')
        value[key]=item
    return value


def command_document(config):
    source=Path(__file__).with_name('enterprise_aws_host_probe.py').read_bytes()
    expected={'format':'enterprise-aws-host-policy-v1','clusterArn':config['clusterArn'],'policySha256':config['hostPolicySha256']}
    launcher='import base64;exec(compile(base64.b64decode('+repr(base64.b64encode(source).decode())+'),"owned-host-probe","exec"))'
    command='exec /usr/bin/python3 -I -c '+shlex.quote(launcher)+' '+shlex.quote(base64.b64encode(json.dumps(expected,sort_keys=True,separators=(',',':')).encode()).decode())
    return {'schemaVersion':'2.2','description':'Fixed read-only parser host inspection; no caller command or secret parameters.',
            'parameters':{},'mainSteps':[{'action':'aws:runShellScript','name':'verifyHost',
                'precondition':{'StringEquals':['platformType','Linux']},'inputs':{'timeoutSeconds':'30','runCommand':[command]}}]}


@dataclass(frozen=True)
class VerifiedHosts:
    policy_sha256:str
    members:tuple
    expires_at:float

    def placement(self,config):
        if (self.policy_sha256!=config['hostPolicySha256']or type(self.expires_at)not in {int,float}or not math.isfinite(self.expires_at)or
            not 0<self.expires_at-time.monotonic()<=121 or type(self.members)is not tuple or not 1<=len(self.members)<=10):
            raise SourceUnavailable('document_host_verification_changed')
        prefix='arn:aws:ecs:'+config['region']+':'+config['accountId']+':container-instance/'+config['clusterArn'].rsplit('/',1)[1]+'/'
        instances=[];arns=[]
        for member in self.members:
            if (type(member)is not tuple or len(member)!=2 or not isinstance(member[0],str)or
                not re.fullmatch(re.escape(prefix)+'[0-9a-f]{32}',member[0])or not isinstance(member[1],str)or not re.fullmatch('i-[0-9a-f]{17}',member[1])):
                raise SourceUnavailable('document_host_verification_changed')
            arns.append(member[0]);instances.append(member[1])
        if len(set(instances))!=len(instances)or len(set(arns))!=len(arns):raise SourceUnavailable('document_host_verification_changed')
        return [{'type':'memberOf','expression':'ec2InstanceId in ['+', '.join("'"+value+"'"for value in sorted(instances))+']'}]


class HostApi:
    def __init__(self,region,*,ecs=None,ssm=None):
        if not isinstance(region,str)or not re.fullmatch('[a-z]{2}-[a-z]+-[1-9]',region):raise ValueError('Use the owned AWS region')
        self.region=region;self.clients={'ecs':ecs,'ssm':ssm};self._lock=threading.Lock()
    def call(self,service,operation,**values):
        allowed={'ecs':{'list_container_instances','describe_container_instances'},'ssm':{'get_document','send_command','get_command_invocation'}}
        if service not in allowed or operation not in allowed[service]:raise ValueError('Use the fixed host-inspection contract')
        try:
            if self.clients[service]is None:
                with self._lock:
                    if self.clients[service]is None:
                        import boto3
                        from botocore.config import Config
                        self.clients[service]=boto3.Session().client(service,region_name=self.region,
                            endpoint_url='https://'+service+'.'+self.region+'.amazonaws.com',
                            config=Config(proxies={},connect_timeout=2,read_timeout=5,retries={'total_max_attempts':1}))
            value=getattr(self.clients[service],operation)(**values)
            if not isinstance(value,dict):raise ValueError()
            return value
        except Exception as error:
            if service=='ssm'and operation=='get_command_invocation'and getattr(error,'response',{}).get('Error',{}).get('Code')=='InvocationDoesNotExist':
                return {'Status':'Pending'}
            raise SourceUnavailable('document_host_verification_unavailable')from None


class EcsHostPolicy:
    def __init__(self,config,*,api=None,poll_seconds=1):
        from enterprise_aws_jobs import configuration
        self.config=MappingProxyType(configuration(config));self.api=api or HostApi(self.config['region'])
        if type(poll_seconds)not in {int,float}or not .01<=poll_seconds<=2:raise ValueError('Use a bounded host-inspection poll interval')
        self.poll_seconds=poll_seconds
    def __call__(self,config):
        if config!=self.config:raise ValueError('Use the exact owned host policy destination')
        try:return self.verify()
        except Exception:raise SourceUnavailable('document_host_verification_unavailable')from None
    def verify(self):
        c=self.config;started=time.monotonic();cluster=c['clusterArn']
        def call(service,operation,**values):
            if time.monotonic()-started>60:raise ValueError('Host inspection deadline')
            return self.api.call(service,operation,**values)
        listing=call('ecs','list_container_instances',cluster=cluster,status='ACTIVE',maxResults=10,
            filter='attribute:atmem-document-policy == '+c['hostPolicySha256'])
        arns=listing.get('containerInstanceArns')
        if not isinstance(arns,list)or not 1<=len(arns)<=10 or len(set(arns))!=len(arns)or listing.get('nextToken'):raise ValueError('Owned host pool unavailable')
        observed=call('ecs','describe_container_instances',cluster=cluster,containerInstances=arns)
        instances=observed.get('containerInstances')
        if observed.get('failures')or not isinstance(instances,list)or len(instances)!=len(arns):raise ValueError('Owned host pool changed')
        members=[]
        for value in instances:
            attributes=value.get('attributes',[])
            if (value.get('containerInstanceArn')not in arns or value.get('agentConnected')is not True or value.get('status')!='ACTIVE'or
                not isinstance(attributes,list)or sum(v.get('name')=='atmem-document-policy'and v.get('value')==c['hostPolicySha256']for v in attributes)!=1):
                raise ValueError('Native host selection changed')
            members.append((value['containerInstanceArn'],value.get('ec2InstanceId')))
        verified=VerifiedHosts(c['hostPolicySha256'],tuple(members),time.monotonic()+120);verified.placement(c)
        version=c['hostDocumentVersion'];document=call('ssm','get_document',Name=c['hostDocumentArn'],DocumentVersion=version,DocumentFormat='JSON')
        content=document.get('Content')
        if not isinstance(content,str)or len(content.encode())>65536 or document.get('DocumentVersion')!=version or json.loads(content,object_pairs_hook=unique)!=command_document(c):
            raise ValueError('Owned command document content changed')
        sent=call('ssm','send_command',InstanceIds=[instance for _,instance in members],DocumentName=c['hostDocumentArn'],
            DocumentVersion=version,DocumentHash=c['hostDocumentHash'],DocumentHashType='Sha256',TimeoutSeconds=30,
            CloudWatchOutputConfig={'CloudWatchOutputEnabled':False})
        command=sent.get('Command',{}).get('CommandId')
        if not isinstance(command,str)or not re.fullmatch('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',command):raise ValueError('Invalid native inspection identity')
        for _,instance in members:
            while True:
                value=call('ssm','get_command_invocation',CommandId=command,InstanceId=instance,PluginName='verifyHost')
                status=value.get('Status')
                if status=='Success':break
                if status not in {'Pending','InProgress','Delayed'}:raise ValueError('Host inspection failed')
                time.sleep(self.poll_seconds)
            if (value.get('CommandId')!=command or value.get('InstanceId')!=instance or value.get('DocumentVersion')!=version or
                value.get('DocumentName')not in {c['hostDocumentArn'],c['hostDocumentArn'].rsplit('/',1)[1]}or
                type(value.get('ResponseCode'))is not int or value['ResponseCode']!=0 or value.get('StandardErrorContent')or
                value.get('StandardOutputUrl')or value.get('StandardErrorUrl')):raise ValueError('Host inspection identity changed')
            encoded=value.get('StandardOutputContent')
            if not isinstance(encoded,str)or not 0<len(encoded.encode())<=4096:raise ValueError('Invalid host observation')
            output=json.loads(encoded,object_pairs_hook=unique)
            if (not isinstance(output,dict)or set(output)!={'format','policySha256','clusterArn','bootId'}or
                output['format']!='enterprise-aws-host-observation-v1'or output['policySha256']!=c['hostPolicySha256']or output['clusterArn']!=cluster or
                not isinstance(output['bootId'],str)or not re.fullmatch('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',output['bootId'])):
                raise ValueError('Host observation changed')
        verified.placement(c);return verified
