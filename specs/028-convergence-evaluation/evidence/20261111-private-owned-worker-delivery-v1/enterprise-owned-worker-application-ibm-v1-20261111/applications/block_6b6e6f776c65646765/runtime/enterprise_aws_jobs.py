"""Owned EC2/ECS per-file controller, not a complete production composition.

The parser requires per-container network disabling, unavailable on Fargate.
Host-policy verification/provisioning and complete export integration are required;
this module does not register a capability or change existing cloud resources.
"""
import json
import copy
import re
import hashlib
import threading
import time
import uuid
from pathlib import Path
from types import MappingProxyType
from enterprise_aws_objects import S3DocumentObjects
from enterprise_document_job import request,result
from enterprise_document_jobs import DocumentJobLedger
from enterprise_sources import SourceUnavailable
from enterprise_aws_hosts import EcsHostPolicy,VerifiedHosts


def configuration(value):
    fields={'format','accountId','region','bucket','clusterArn','hostPolicySha256','hostDocumentArn','hostDocumentHash','hostDocumentVersion','workerRoleArn',
            'transferRoleArn','executionRoleArn','parserImage','transferImage','taskDefinitionArn'}
    if not isinstance(value,dict)or set(value)!=fields or value['format']!='enterprise-aws-document-job-v2':
        raise ValueError('Use the exact owned AWS document-job configuration')
    patterns={'accountId':r'[0-9]{12}','region':r'(?:af|ap|ca|eu|il|me|mx|sa|us)-(?:east|west|south|north|central|southeast|southwest|northeast|northwest)-[1-9]',
              'bucket':r'[a-z0-9][a-z0-9-]{1,61}[a-z0-9]'}
    for key,pattern in patterns.items():
        if not isinstance(value[key],str)or not re.fullmatch(pattern,value[key]):raise ValueError('Invalid owned AWS destination')
    if not isinstance(value['hostPolicySha256'],str)or not re.fullmatch('[0-9a-f]{64}',value['hostPolicySha256']):
        raise ValueError('Use the reviewed dedicated-host policy fingerprint')
    account,region=value['accountId'],value['region']
    prefix='arn:aws:'
    if (not isinstance(value['hostDocumentArn'],str)or not re.fullmatch(re.escape(prefix+'ssm:'+region+':'+account+':document/')+r'[A-Za-z0-9_.-]{3,128}',value['hostDocumentArn'])or
        not isinstance(value['hostDocumentHash'],str)or not re.fullmatch('[0-9a-f]{64}',value['hostDocumentHash'])or
        not isinstance(value['hostDocumentVersion'],str)or not re.fullmatch('[1-9][0-9]{0,8}',value['hostDocumentVersion'])):
        raise ValueError('Use the exact owned version/hash-bound host document')
    for key in ['workerRoleArn','transferRoleArn','executionRoleArn']:
        if not isinstance(value[key],str)or not re.fullmatch(re.escape(prefix+'iam::'+account+':role/')+r'[A-Za-z0-9_+=,.@/-]{1,128}',value[key]):
            raise ValueError('Use explicit same-account owned roles')
    if len({value[key]for key in ['workerRoleArn','transferRoleArn','executionRoleArn']})!=3:
        raise ValueError('Worker, storage transfer and image execution authority must be distinct')
    if not isinstance(value['clusterArn'],str)or not re.fullmatch(re.escape(prefix+'ecs:'+region+':'+account+':cluster/')+r'[A-Za-z0-9_-]{1,255}',value['clusterArn']):
        raise ValueError('Use the owned regional ECS cluster')
    if (not isinstance(value['taskDefinitionArn'],str)or not re.fullmatch(re.escape(prefix+'ecs:'+region+':'+account+':task-definition/document-')+r'[A-Za-z0-9_-]{1,200}:[1-9][0-9]{0,8}',value['taskDefinitionArn'])):
        raise ValueError('Use the exact operator-owned regional task-definition revision')
    for key in ['parserImage','transferImage']:
        if not isinstance(value[key],str)or not re.fullmatch(re.escape(account+'.dkr.ecr.'+region+'.amazonaws.com/')+r'[a-z0-9]+(?:[._/-][a-z0-9]+)*@sha256:[0-9a-f]{64}',value[key]):
            raise ValueError('Use immutable owned regional ECR images')
    if value['parserImage']==value['transferImage']:raise ValueError('Keep the parser and trusted transfer artifacts separate')
    return dict(value)


def transfer_metadata(config,metadata,etag):
    # Preserve the shared byte contract's exact fields and canonical media type.
    if not isinstance(metadata,dict)or set(metadata)!={'format','requestId','sha256','mediaType'}:
        raise ValueError('Use the exact document request')
    if (metadata['format']!='enterprise-document-job-v1' or
        not isinstance(metadata['requestId'],str)or not re.fullmatch('[0-9a-f]{64}',metadata['requestId'])or
        not isinstance(metadata['sha256'],str)or not re.fullmatch('[0-9a-f]{64}',metadata['sha256'])):
        raise ValueError('Use the owned byte-bound request')
    from enterprise_document_contract import media_type
    if media_type(metadata['mediaType'])!=metadata['mediaType']:raise ValueError('Use canonical document MIME')
    # Opaque ETag is a conditional read token, never treated as an input digest.
    if not isinstance(etag,str)or not re.fullmatch(r'"[0-9a-f]{32}(?:-[1-9][0-9]{0,4})?"',etag):
        raise ValueError('Use the acknowledged native input ETag')
    return {'format':'enterprise-aws-document-transfer-v1','accountId':config['accountId'],
            'region':config['region'],'bucket':config['bucket'],'request':dict(metadata),'inputETag':etag}


def task_family(config):
    return config['taskDefinitionArn'].rsplit('/',1)[1].rsplit(':',1)[0]


def task_definition(config):
    """Immutable operator-owned shape, shared with the Terraform compiler.

    No file identity, bytes, ETag, user prompt or model authority belongs here.
    """
    owned=configuration(config)
    replacements={'__FAMILY__':task_family(owned),'__POLICY_SHA256__':owned['hostPolicySha256'],
                  '__TRANSFER_ROLE_ARN__':owned['transferRoleArn'],'__EXECUTION_ROLE_ARN__':owned['executionRoleArn'],
                  '__TRANSFER_IMAGE__':owned['transferImage'],'__PARSER_IMAGE__':owned['parserImage']}
    def resolve(value):
        if isinstance(value,dict):return {key:resolve(item)for key,item in value.items()}
        if isinstance(value,list):return [resolve(item)for item in value]
        if isinstance(value,str):
            for key,replacement in replacements.items():value=value.replace(key,replacement)
        return value
    return resolve(json.loads(Path(__file__).with_name('enterprise-aws-task-template.json').read_text()))


def task_overrides(config,metadata,etag):
    encoded=json.dumps(transfer_metadata(configuration(config),metadata,etag),separators=(',',':'))
    return {'containerOverrides':[{'name':name,'environment':[{'name':'DOCUMENT_JOB','value':encoded}]}for name in ['download','upload']]}


def verify_definition(config,reply):
    """Reject drift before storing bytes; tolerate only inert native defaults.

    Native describe metadata is not a runtime override or deployment proof.
    Unknown nonempty configuration fails closed rather than being projected away.
    """
    desired=task_definition(config);desired.pop('tags')
    if not isinstance(reply,dict)or not isinstance(reply.get('taskDefinition'),dict):raise SourceUnavailable('document_definition_unavailable')
    actual=copy.deepcopy(reply['taskDefinition'])
    if (actual.pop('taskDefinitionArn',None)!=config['taskDefinitionArn']or
        type(actual.get('revision'))is not int or actual.pop('revision')!=int(config['taskDefinitionArn'].rsplit(':',1)[1])or
        actual.pop('status',None)!='ACTIVE'):
        raise SourceUnavailable('document_definition_unavailable')
    for field in ['registeredAt','registeredBy','compatibilities','requiresAttributes']:
        actual.pop(field,None)
    if actual.get('enableFaultInjection')is False:actual.pop('enableFaultInjection')
    if not isinstance(actual.get('containerDefinitions'),list):raise SourceUnavailable('document_definition_unavailable')
    for container in actual['containerDefinitions']:
        if not isinstance(container,dict):raise SourceUnavailable('document_definition_unavailable')
        if container.get('disableNetworking')is False:container.pop('disableNetworking')
        if container.get('versionConsistency')=='enabled':container.pop('versionConsistency')
    def canonical(value):
        if isinstance(value,dict):return {key:canonical(item)for key,item in value.items()if item!=[]and item!={}}
        if isinstance(value,list):return [canonical(item)for item in value]
        return value
    if json.dumps(canonical(actual),sort_keys=True)!=json.dumps(canonical(desired),sort_keys=True):raise SourceUnavailable('document_definition_unavailable')
    return config['taskDefinitionArn']


class EcsDocumentApi:
    def __init__(self,region,*,client=None):
        if not isinstance(region,str)or not re.fullmatch(r'[a-z]{2}-[a-z]+-[1-9]',region):raise ValueError('Use a reviewed commercial AWS region')
        self.region,self.client=region,client;self._lock=threading.Lock()

    def call(self,operation,**values):
        allowed={'describe_task_definition','run_task','describe_tasks','list_tasks','stop_task'}
        if operation not in allowed:raise ValueError('Use the owned document lifecycle')
        try:
            if self.client is None:
                with self._lock:
                    if self.client is None:
                        import boto3
                        from botocore.config import Config
                        self.client=boto3.Session().client('ecs',region_name=self.region,
                            endpoint_url='https://ecs.'+self.region+'.amazonaws.com',
                            config=Config(proxies={},connect_timeout=2,read_timeout=8,retries={'total_max_attempts':1}))
            value=getattr(self.client,operation)(**values)
            if not isinstance(value,dict):raise ValueError()
            return value
        except Exception:raise SourceUnavailable('document_job_unavailable')from None


class EcsDocuments:
    def __init__(self,config,*,host_check=None,api=None,objects=None,ledger=None,deadline=140,poll_seconds=1):
        self.config=MappingProxyType(configuration(config))
        if host_check is None:host_check=EcsHostPolicy(dict(self.config))
        if not callable(host_check):raise ValueError('Supply the owned dedicated-host verifier')
        if type(deadline)is not int or not 1<=deadline<=140 or type(poll_seconds)not in {int,float}or not .01<=poll_seconds<=2:
            raise ValueError('Use bounded document deadlines')
        self.host_check=host_check;self.api=api or EcsDocumentApi(self.config['region'])
        self.objects=objects or S3DocumentObjects(self.config['bucket'],self.config['region'],self.config['accountId'])
        self.ledger=ledger;self.deadline,self.poll_seconds=deadline,poll_seconds
        self.cluster=self.config['clusterArn'];self.prefix='arn:aws:ecs:'+self.config['region']+':'+self.config['accountId']+':'
        self.target=hashlib.sha256(json.dumps({**{key:self.config[key]for key in ['accountId','region','bucket','clusterArn']},'taskFamily':task_family(self.config)},sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def __call__(self,raw,mime):raise SourceUnavailable('source_validation_required')

    def bind_runtime(self,provider,environment):
        if (provider!='aws'or environment.get('REGION')!=self.config['region']or
            environment.get('AWS_ACCOUNT_ID')!=self.config['accountId']or environment.get('WORKER_ROLE_ARN')!=self.config['workerRoleArn']):
            raise ValueError('Document execution must match the selected AWS destination and worker identity')

    def attach_runtime(self,auth,account_id):
        if self.ledger is None:self.ledger=DocumentJobLedger(auth,account_id,self.target)
        elif (not isinstance(self.ledger,DocumentJobLedger)or self.ledger.auth is not auth or self.ledger.account_id!=account_id or self.ledger.target!=self.target):
            raise ValueError('Use the owned persistent cleanup ledger')

    def definition(self,arn):
        if not isinstance(arn,str)or not re.fullmatch(re.escape(self.prefix+'task-definition/'+task_family(self.config)+':')+'[1-9][0-9]{0,8}',arn):
            raise SourceUnavailable('document_job_unavailable')
        return arn

    def task(self,identifier,value,definition=None):
        arn=value.get('taskArn');cluster_name=self.cluster.rsplit('/',1)[1]
        if (not isinstance(arn,str)or not re.fullmatch(re.escape(self.prefix+'task/'+cluster_name+'/')+'[0-9a-f]{32}',arn)or
            value.get('clusterArn')!=self.cluster or value.get('startedBy')!=identifier):raise SourceUnavailable('document_job_unavailable')
        owned=self.definition(value.get('taskDefinitionArn'))
        if definition is not None and owned!=definition:raise SourceUnavailable('document_job_unavailable')
        return arn

    def from_source(self,raw,mime,guard):
        if not callable(guard):raise ValueError('Supply the live source/company/job check')
        identifier=uuid.uuid4().hex+uuid.uuid4().hex;metadata=request(raw,mime,identifier)
        guard()
        if self.ledger is None:raise SourceUnavailable('document_job_recovery_required')
        hosts=self.host_check(dict(self.config));guard()
        if not isinstance(hosts,VerifiedHosts):raise SourceUnavailable('document_host_verification_required')
        hosts.placement(dict(self.config))
        definition=verify_definition(dict(self.config),self.api.call('describe_task_definition',taskDefinition=self.config['taskDefinitionArn']))
        guard()
        lease=self.ledger.allocate(identifier);known=None;started=time.monotonic()
        def check():self.ledger.guard(lease);guard();self.ledger.guard(lease)
        try:
            check();condition=self.objects.put(identifier,'input',raw)
            self.ledger.advance(lease,'job_pending');check()
            launched=self.api.call('run_task',cluster=self.cluster,taskDefinition=definition,launchType='EC2',count=1,
                clientToken=identifier,startedBy=identifier,enableExecuteCommand=False,enableECSManagedTags=False,
                overrides=task_overrides(dict(self.config),metadata,condition),
                placementConstraints=hosts.placement(dict(self.config)))
            if launched.get('failures')or len(launched.get('tasks',[]))!=1:raise SourceUnavailable('document_job_unavailable')
            known=self.task(identifier,launched['tasks'][0],definition);self.ledger.advance(lease,'job_running')
            while True:
                check()
                if time.monotonic()-started>self.deadline:raise SourceUnavailable('document_job_unavailable')
                observed=self.api.call('describe_tasks',cluster=self.cluster,tasks=[known])
                if observed.get('failures')or len(observed.get('tasks',[]))!=1:raise SourceUnavailable('document_job_unavailable')
                task=observed['tasks'][0]
                if self.task(identifier,task,definition)!=known:raise SourceUnavailable('document_job_unavailable')
                if task.get('lastStatus')=='STOPPED':
                    if task.get('containerInstanceArn')not in {arn for arn,_ in hosts.members}:raise SourceUnavailable('document_host_verification_changed')
                    containers=task.get('containers',[])
                    if (len(containers)!=3 or {v.get('name')for v in containers}!={'download','parser','upload'}or
                        any(v.get('lastStatus')!='STOPPED'or type(v.get('exitCode'))is not int or v['exitCode']!=0 for v in containers)):
                        raise SourceUnavailable('document_job_unavailable')
                    break
                if task.get('lastStatus')not in {'PROVISIONING','PENDING','ACTIVATING','RUNNING','DEACTIVATING','STOPPING','DEPROVISIONING'}:
                    raise SourceUnavailable('document_job_unavailable')
                time.sleep(self.poll_seconds)
            self.ledger.advance(lease,'succeeded');check()
            value=result(raw,mime,identifier,self.objects.load(identifier,'result'));check();return value
        finally:
            cleanup=self.ledger.claim_owner(lease)
            try:self.cleanup(identifier,known=known)
            except BaseException:self.ledger.failed(cleanup);raise
            else:self.ledger.completed(cleanup)

    def listed(self,operation,key,*,_deadline=None,**values):
        found=[];token=None;seen=set()
        for _ in range(5):
            if _deadline is not None and time.monotonic()>_deadline:raise SourceUnavailable('document_cleanup_unavailable')
            reply=self.api.call(operation,**values,**({'nextToken':token}if token else{}))
            items=reply.get(key)
            if not isinstance(items,list)or any(not isinstance(v,str)for v in items):raise SourceUnavailable('document_cleanup_unavailable')
            found.extend(items);token=reply.get('nextToken')
            if token is None:return list(dict.fromkeys(found))
            if not isinstance(token,str)or not 0<len(token)<=4096 or token in seen:break
            seen.add(token)
        raise SourceUnavailable('document_cleanup_unavailable')

    def cleanup(self,identifier,*,known=None):
        if not isinstance(identifier,str)or not re.fullmatch('[0-9a-f]{64}',identifier):raise ValueError('Use the owned cleanup identity')
        tasks=[];failure=False;deadline=time.monotonic()+70
        def call(operation,**values):
            if time.monotonic()>deadline:raise SourceUnavailable('document_cleanup_unavailable')
            return self.api.call(operation,**values)
        try:
            # AWS startedBy is the only filter permitted alongside cluster.
            # Default RUNNING desired status also includes pending launches.
            # Unknown terminal tasks are left to native task-volume cleanup;
            # uncertain creation keeps its durable settlement/retry window.
            tasks+=self.listed('list_tasks','taskArns',_deadline=deadline,cluster=self.cluster,startedBy=identifier,maxResults=100)
            if known is not None:tasks.append(known)
            tasks=list(dict.fromkeys(tasks))
            if len(tasks)>10:raise SourceUnavailable('document_cleanup_unavailable')
            for arn in tasks:
                observed=call('describe_tasks',cluster=self.cluster,tasks=[arn])
                if observed.get('failures')or len(observed.get('tasks',[]))!=1:raise SourceUnavailable('document_cleanup_unavailable')
                value=observed['tasks'][0]
                if self.task(identifier,value)!=arn:raise SourceUnavailable('document_cleanup_unavailable')
                if value.get('lastStatus')!='STOPPED':
                    call('stop_task',cluster=self.cluster,task=arn,reason='Owned document cleanup')
                    started=time.monotonic()
                    while True:
                        reply=call('describe_tasks',cluster=self.cluster,tasks=[arn])
                        if reply.get('failures')or len(reply.get('tasks',[]))!=1:raise SourceUnavailable('document_cleanup_unavailable')
                        current=reply['tasks'][0]
                        if self.task(identifier,current)!=arn:raise SourceUnavailable('document_cleanup_unavailable')
                        if current.get('lastStatus')=='STOPPED':break
                        if time.monotonic()-started>20:raise SourceUnavailable('document_cleanup_unavailable')
                        time.sleep(self.poll_seconds)
        except Exception:failure=True
        # Even a native task cleanup failure still attempts both owned
        # objects. Return no document text until the entire cleanup succeeds.
        for side in ['input','result']:
            try:self.objects.delete(identifier,side)
            except Exception:failure=True
        if failure:raise SourceUnavailable('document_cleanup_unavailable')

    def reconcile(self,*,limit=5):
        if self.ledger is None:raise SourceUnavailable('document_job_recovery_required')
        if type(limit)is not int or not 1<=limit<=20:raise ValueError('Use bounded cleanup batches')
        counts={'claimed':0,'retired':0,'settling':0,'failed':0}
        for _ in range(limit):
            lease=self.ledger.claim_due()
            if lease is None:break
            counts['claimed']+=1
            try:self.cleanup(lease.request_id)
            except Exception:self.ledger.failed(lease);counts['failed']+=1
            else:
                retired=self.ledger.completed(lease);counts['retired'if retired else'settling']+=1
        return counts
