"""Owned EC2/ECS document task definition, not a production launcher.

The parser requires per-container network disabling, unavailable on Fargate.
Native task execution, transfer CLI, recovery and provisioning remain separate
required work; this module does not register a capability or call an AWS account.
"""
import json
import re


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
    parser.update(cpu=2048,memory=2048,disableNetworking=True,entryPoint=['python'],
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
