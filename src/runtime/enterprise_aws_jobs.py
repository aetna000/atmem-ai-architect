"""Owned EC2/ECS per-file controller, not a complete production composition.

The parser requires per-container network disabling, unavailable on Fargate.
Host-policy verification/provisioning and complete export integration are required;
this module does not register a capability or change existing cloud resources.
"""
import json
import re
import hashlib
import threading
import time
import uuid
from types import MappingProxyType
from enterprise_aws_objects import S3DocumentObjects
from enterprise_document_job import request,result
from enterprise_document_jobs import DocumentJobLedger
from enterprise_sources import SourceUnavailable


def configuration(value):
    fields={'format','accountId','region','bucket','clusterArn','hostPolicySha256','workerRoleArn',
            'transferRoleArn','executionRoleArn','parserImage','transferImage'}
    if not isinstance(value,dict)or set(value)!=fields or value['format']!='enterprise-aws-document-job-v1':
        raise ValueError('Use the exact owned AWS document-job configuration')
    patterns={'accountId':r'[0-9]{12}','region':r'(?:af|ap|ca|eu|il|me|mx|sa|us)-(?:east|west|south|north|central|southeast|southwest|northeast|northwest)-[1-9]',
              'bucket':r'[a-z0-9][a-z0-9-]{1,61}[a-z0-9]'}
    for key,pattern in patterns.items():
        if not isinstance(value[key],str)or not re.fullmatch(pattern,value[key]):raise ValueError('Invalid owned AWS destination')
    if not isinstance(value['hostPolicySha256'],str)or not re.fullmatch('[0-9a-f]{64}',value['hostPolicySha256']):
        raise ValueError('Use the reviewed dedicated-host policy fingerprint')
    account,region=value['accountId'],value['region']
    prefix='arn:aws:'
    for key in ['workerRoleArn','transferRoleArn','executionRoleArn']:
        if not isinstance(value[key],str)or not re.fullmatch(re.escape(prefix+'iam::'+account+':role/')+r'[A-Za-z0-9_+=,.@/-]{1,128}',value[key]):
            raise ValueError('Use explicit same-account owned roles')
    if len({value[key]for key in ['workerRoleArn','transferRoleArn','executionRoleArn']})!=3:
        raise ValueError('Worker, storage transfer and image execution authority must be distinct')
    if not isinstance(value['clusterArn'],str)or not re.fullmatch(re.escape(prefix+'ecs:'+region+':'+account+':cluster/')+r'[A-Za-z0-9_-]{1,255}',value['clusterArn']):
        raise ValueError('Use the owned regional ECS cluster')
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


def task_definition(config,metadata,etag):
    owned=configuration(config);transfer=transfer_metadata(owned,metadata,etag)
    def mount(name,path,readonly):return {'sourceVolume':name,'containerPath':path,'readOnly':readonly}
    def common(name,image,user,essential):
        return {'name':name,'image':image,'user':user,'essential':essential,
                'cpu':128,'memory':256,'readonlyRootFilesystem':True,'privileged':False,
                'dockerSecurityOptions':['no-new-privileges'],
                'linuxParameters':{'capabilities':{'drop':['ALL']},'initProcessEnabled':True,'maxSwap':0},
                # ECS does not accept Docker's 'none' log driver in this API.
                # Omission inherits the dedicated host daemon's required 'none'
                # default. Host policy verification/provisioning is still needed.
                'stopTimeout':5,
                'ulimits':[{'name':'nofile','softLimit':256,'hardLimit':256}]}
    def bridge(mode):
        value=common(mode,owned['transferImage'],'0:0'if mode=='download'else'10001:10001',mode=='upload')
        value.update(entryPoint=['python'],command=['-I','/app/enterprise_aws_transfer.py',mode],
                     environment=[{'name':'DOCUMENT_JOB','value':json.dumps(transfer,separators=(',',':'))}],
                     mountPoints=[mount('input','/work/input',mode!='download'),mount('output','/work/output',mode!='download')])
        if mode=='download':value['linuxParameters']['capabilities']['add']=['CHOWN']
        else:value['dependsOn']=[{'containerName':'parser','condition':'SUCCESS'}];value['startTimeout']=120
        return value
    parser=common('parser',owned['parserImage'],'10001:10001',False)
    parser.update(cpu=1792,memory=2048,disableNetworking=True,entryPoint=['python'],
                  command=['-I','/app/enterprise_document_cli.py','--job'],
                  dependsOn=[{'containerName':'download','condition':'SUCCESS'}],startTimeout=60,
                  mountPoints=[mount('input','/input',True),mount('output','/output',False)])
    parser['linuxParameters']['tmpfs']=[{'containerPath':'/tmp','size':128,'mountOptions':['rw','noexec','nosuid','nodev']}]
    return {'family':'document-'+metadata['requestId'],'networkMode':'bridge','requiresCompatibilities':['EC2'],
            'runtimePlatform':{'cpuArchitecture':'X86_64','operatingSystemFamily':'LINUX'},
            'placementConstraints':[{'type':'memberOf','expression':'attribute:atmem-document-policy == '+owned['hostPolicySha256']}],
            'taskRoleArn':owned['transferRoleArn'],'executionRoleArn':owned['executionRoleArn'],
            'containerDefinitions':[bridge('download'),parser,bridge('upload')],
            'volumes':[{'name':name,'dockerVolumeConfiguration':{'scope':'task','driver':'local'}}for name in ['input','output']],
            'tags':[{'key':'atmem-workload','value':'document-parser'}]}


class EcsDocumentApi:
    def __init__(self,region,*,client=None):
        if not isinstance(region,str)or not re.fullmatch(r'[a-z]{2}-[a-z]+-[1-9]',region):raise ValueError('Use a reviewed commercial AWS region')
        self.region,self.client=region,client;self._lock=threading.Lock()

    def call(self,operation,**values):
        allowed={'register_task_definition','run_task','describe_tasks','list_tasks','stop_task',
                 'list_task_definitions','deregister_task_definition','delete_task_definitions'}
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
    def __init__(self,config,*,host_check,api=None,objects=None,ledger=None,deadline=140,poll_seconds=1):
        self.config=MappingProxyType(configuration(config))
        if not callable(host_check):raise ValueError('Supply the owned dedicated-host verifier')
        if type(deadline)is not int or not 1<=deadline<=140 or type(poll_seconds)not in {int,float}or not .01<=poll_seconds<=2:
            raise ValueError('Use bounded document deadlines')
        self.host_check=host_check;self.api=api or EcsDocumentApi(self.config['region'])
        self.objects=objects or S3DocumentObjects(self.config['bucket'],self.config['region'],self.config['accountId'])
        self.ledger=ledger;self.deadline,self.poll_seconds=deadline,poll_seconds
        self.cluster=self.config['clusterArn'];self.prefix='arn:aws:ecs:'+self.config['region']+':'+self.config['accountId']+':'
        self.target=hashlib.sha256(json.dumps({key:self.config[key]for key in ['accountId','region','bucket','clusterArn']},sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def __call__(self,raw,mime):raise SourceUnavailable('source_validation_required')

    def bind_runtime(self,provider,environment):
        if (provider!='aws'or environment.get('REGION')!=self.config['region']or
            environment.get('AWS_ACCOUNT_ID')!=self.config['accountId']or environment.get('WORKER_ROLE_ARN')!=self.config['workerRoleArn']):
            raise ValueError('Document execution must match the selected AWS destination and worker identity')

    def attach_runtime(self,auth,account_id):
        if self.ledger is None:self.ledger=DocumentJobLedger(auth,account_id,self.target)
        elif (not isinstance(self.ledger,DocumentJobLedger)or self.ledger.auth is not auth or self.ledger.account_id!=account_id or self.ledger.target!=self.target):
            raise ValueError('Use the owned persistent cleanup ledger')

    def definition(self,identifier,arn):
        if not isinstance(arn,str)or not re.fullmatch(re.escape(self.prefix+'task-definition/document-'+identifier+':')+'[1-9][0-9]{0,8}',arn):
            raise SourceUnavailable('document_job_unavailable')
        return arn

    def task(self,identifier,value,definition=None):
        arn=value.get('taskArn');cluster_name=self.cluster.rsplit('/',1)[1]
        if (not isinstance(arn,str)or not re.fullmatch(re.escape(self.prefix+'task/'+cluster_name+'/')+'[0-9a-f]{32}',arn)or
            value.get('clusterArn')!=self.cluster or value.get('startedBy')!=identifier):raise SourceUnavailable('document_job_unavailable')
        owned=self.definition(identifier,value.get('taskDefinitionArn'))
        if definition is not None and owned!=definition:raise SourceUnavailable('document_job_unavailable')
        return arn

    def from_source(self,raw,mime,guard):
        if not callable(guard):raise ValueError('Supply the live source/company/job check')
        identifier=uuid.uuid4().hex+uuid.uuid4().hex;metadata=request(raw,mime,identifier)
        guard()
        if self.ledger is None:raise SourceUnavailable('document_job_recovery_required')
        self.host_check(dict(self.config));guard()
        lease=self.ledger.allocate(identifier);known=None;definition=None;started=time.monotonic()
        def check():self.ledger.guard(lease);guard();self.ledger.guard(lease)
        try:
            check();condition=self.objects.put(identifier,'input',raw)
            self.ledger.advance(lease,'job_pending');check()
            registered=self.api.call('register_task_definition',**task_definition(dict(self.config),metadata,condition))
            definition=self.definition(identifier,registered.get('taskDefinition',{}).get('taskDefinitionArn'));check()
            launched=self.api.call('run_task',cluster=self.cluster,taskDefinition=definition,launchType='EC2',count=1,
                clientToken=identifier,startedBy=identifier,enableExecuteCommand=False,enableECSManagedTags=False)
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
            try:self.cleanup(identifier,known=known,definition=definition)
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

    def cleanup(self,identifier,*,known=None,definition=None):
        if not isinstance(identifier,str)or not re.fullmatch('[0-9a-f]{64}',identifier):raise ValueError('Use the owned cleanup identity')
        tasks=[];failure=False;deadline=time.monotonic()+70
        def call(operation,**values):
            if time.monotonic()>deadline:raise SourceUnavailable('document_cleanup_unavailable')
            return self.api.call(operation,**values)
        try:
            for status in ['RUNNING','STOPPED']:
                tasks+=self.listed('list_tasks','taskArns',_deadline=deadline,cluster=self.cluster,family='document-'+identifier,desiredStatus=status,maxResults=100)
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
            definitions=[]
            for status in ['ACTIVE','INACTIVE']:
                definitions+=self.listed('list_task_definitions','taskDefinitionArns',_deadline=deadline,familyPrefix='document-'+identifier,status=status,maxResults=100)
            if definition is not None:definitions.append(definition)
            for arn in dict.fromkeys(definitions):
                self.definition(identifier,arn)
                call('deregister_task_definition',taskDefinition=arn)
                reply=call('delete_task_definitions',taskDefinitions=[arn])
                if reply.get('failures'):raise SourceUnavailable('document_cleanup_unavailable')
        except Exception:failure=True
        # Even a native task/definition cleanup failure still attempts both owned
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
