"""Consume actual native mock-plan output, not compiler success metadata.

Checks native IAM action/resource/condition shapes, runtime definition and host
bootstrap bindings. Not an account IAM simulation or cloud/AMI qualification.
"""
import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'tests/runtime'),str(ROOT/'.local/aws-web-runtime-sdk')]
from enterprise_aws_jobs import configuration,task_definition,verify_definition
from enterprise_aws_hosts import command_document
from enterprise_aws_jobs_contract import AwsDocumentTaskContract,native_check


def match(pattern,value):
    expression='';start=0
    for field in re.finditer(r'\$\{([^}]+)\}',pattern):
        expression+=re.escape(pattern[start:field.start()])
        expression+=('.+'if not pattern.startswith('arn:')or field[1]in {'ObjectName','RoleNameWithPath','RepositoryName'}else'[^:/]+')
        start=field.end()
    expression+=re.escape(pattern[start:])
    return re.fullmatch(expression,value)is not None


def catalogs():
    result={}
    for service in ['ecs','ssm','ssmmessages','s3','ecr','iam']:
        path=ROOT/'tests/fixtures/providers'/('aws-'+service+'-authorization-20261111.json')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=json.loads(path.with_suffix('.provenance.json').read_text())['sha256']:raise ValueError('Authorization metadata drift')
        raw=json.loads(path.read_text());result[service]=(raw,{row['Name']:row for row in raw['Actions']},{row['Name']:row for row in raw['Resources']})
    return result


def policy_shape(policy,metadata):
    observations=[]
    for statement in policy['Statement']:
        if statement['Effect']!='Allow':raise ValueError('Inspect additive allow policies separately')
        actions=statement['Action'];actions=[actions]if isinstance(actions,str)else actions
        resources=statement['Resource'];resources=[resources]if isinstance(resources,str)else resources
        for action in actions:
            service,separator,name=action.partition(':')
            if not separator or service not in metadata:raise ValueError('Unknown native IAM service')
            _,native,types=metadata[service]
            if name not in native:raise ValueError('Unknown native IAM action: '+action)
            declared=native[name];available=declared.get('Resources',[])
            keys=set(declared.get('ActionConditionKeys',[]))
            for resource in resources:
                if resource=='*':
                    for item in available:keys.update(item.get('ConditionKeys',[]));keys.update(types[item['Name']].get('ConditionKeys',[]))
                    continue
                matched=[item for item in available if any(match(pattern,resource)for pattern in types[item['Name']]['ARNFormats'])]
                if not matched:raise ValueError('Unsupported resource for '+action+': '+resource)
                for item in matched:keys.update(item.get('ConditionKeys',[]));keys.update(types[item['Name']].get('ConditionKeys',[]))
            for conditions in statement.get('Condition',{}).values():
                for key in conditions:
                    if key.startswith('aws:'):continue
                    if not any(match(pattern,key)for pattern in keys):raise ValueError('Unsupported native condition for '+action+': '+key)
            observations.append(action)
    return observations


def verify(directory):
    directory=directory.resolve()
    if not directory.is_relative_to(ROOT/'.local'):raise ValueError('Use owned provider evidence')
    receipt=json.loads((directory/'receipt.json').read_text())
    if not receipt['passed']or receipt['cloudOperations']:raise ValueError('Require passed local provider checks')
    for name,digest in receipt['sourceHashes'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Compiler source changed')
    for name,digest in receipt['emittedHashes'].items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=digest:raise ValueError('Emitted artifact changed')
    events=[json.loads(line)for line in (directory/'mock-plans.log').read_text().splitlines()]
    summaries=[event['test_summary']for event in events if event.get('test_summary')]
    if len(summaries)!=1 or summaries[0]!={'status':'pass','passed':10,'failed':0,'errored':0,'skipped':0}:raise ValueError('Require all ten native mock plans')
    plans=[event['test_plan']for event in events if event.get('@testrun')=='private_document_substrate'and event.get('test_plan')]
    if len(plans)!=1:raise ValueError('Require the actual positive ready plan')
    plan=plans[0];config=configuration(plan['output_changes']['document_job_configuration']['after'])
    if json.loads((directory/'runtime-configurations.json').read_text())!=[config]:raise ValueError('Configuration record differs from actual plan')
    resources=plan['resource_changes']
    def all_of(kind):return [row['change']['after']for row in resources if row['type']==kind and row['change'].get('after')is not None]
    def one(kind):
        found=all_of(kind)
        if len(found)!=1:raise ValueError('Unexpected '+kind+' cardinality')
        return found[0]
    review=[row for row in all_of('terraform_data')if row['input'].get('requested_worker_arn')==config['workerRoleArn']]
    if len(review)!=2 or any(row['input']['resolved_worker_arn']!=config['workerRoleArn']or row['input']['source_component']!=receipt['sourceComponent']for row in review):raise ValueError('Full existing worker/source ownership is not bound')
    task=one('aws_ecs_task_definition');containers=json.loads(task['container_definitions'])
    # Terraform AWS6.72 omits false autoprovision for task-local scope in its
    # native expansion. Assert that exact narrow input, not a projected surprise.
    volumes=[]
    for volume in task['volume']:
        settings=volume['docker_volume_configuration']
        if len(settings)!=1 or settings[0]['scope']!='task'or settings[0]['driver']!='local'or settings[0]['autoprovision']is not False:raise ValueError('Unsafe native task volume')
        if volume.get('configure_at_launch')or settings[0].get('driver_opts')or settings[0].get('labels')or volume.get('host_path')or any(volume.get(key)for key in ['efs_volume_configuration','fsx_windows_file_server_volume_configuration','s3files_volume_configuration']):raise ValueError('Unexpected host/external volume')
        volumes.append({'name':volume['name'],'dockerVolumeConfiguration':{'scope':'task','driver':'local'}})
    native={'family':task['family'],'networkMode':task['network_mode'],'requiresCompatibilities':task['requires_compatibilities'],
            'runtimePlatform':{'cpuArchitecture':task['runtime_platform'][0]['cpu_architecture'],'operatingSystemFamily':task['runtime_platform'][0]['operating_system_family']},
            'taskRoleArn':task['task_role_arn'],'executionRoleArn':task['execution_role_arn'],'containerDefinitions':containers,'volumes':sorted(volumes,key=lambda row:row['name']),
            'placementConstraints':[{'type':row['type'],'expression':row['expression']}for row in task['placement_constraints']]}
    expected=task_definition(config);expected.pop('tags')
    if native!=expected:raise ValueError('Native Terraform task differs from actual runtime contract')
    verify_definition(config,{'taskDefinition':{**native,'taskDefinitionArn':task['arn'],'revision':task['revision'],'status':'ACTIVE'}})
    AwsDocumentTaskContract.setUpClass();native_check(native,AwsDocumentTaskContract.model.operation_model('RegisterTaskDefinition').input_shape)
    parser=next(item for item in containers if item['name']=='parser')
    if parser.get('environment')or not parser['disableNetworking']or parser['user']!='10001:10001':raise ValueError('Parser gained transport identity or network')
    metadata=catalogs();actions=[]
    policies=all_of('aws_iam_role_policy')
    for row in policies:actions+=policy_shape(json.loads(row['policy']),metadata)
    forbidden={'ecs:RegisterTaskDefinition','ecs:DeregisterTaskDefinition','ecs:DeleteTaskDefinitions','ecs:ExecuteCommand','ecs:CreateCluster','ssm:GetParameter','ssm:GetParameters','secretsmanager:GetSecretValue'}
    if forbidden.intersection(actions):raise ValueError('Parser substrate gained unrelated runtime authority')
    worker=[json.loads(row['policy'])for row in policies if row['role']=='question-worker']
    run=[statement for policy in worker for statement in policy['Statement']if statement.get('Sid')=='RunPinnedDefinition']
    if len(run)!=1 or run[0]['Resource']!=config['taskDefinitionArn']or run[0]['Condition']['ArnEquals']['ecs:cluster']!=config['clusterArn']:raise ValueError('Worker task pin/cluster policy drift')
    roles=all_of('aws_iam_role')
    if len(roles)!=3 or config['workerRoleArn']in {row['arn']for row in roles}:raise ValueError('Existing worker recreated or host identities collapsed')
    for arn in [config['transferRoleArn'],config['executionRoleArn']]:
        role=[row for row in roles if row['arn']==arn]
        if len(role)!=1:raise ValueError('Missing owned transfer/pull role')
        trust=json.loads(role[0]['assume_role_policy'])['Statement']
        if len(trust)!=1 or trust[0]['Principal']!={'Service':'ecs-tasks.amazonaws.com'}or trust[0]['Condition']!={'StringEquals':{'aws:SourceAccount':config['accountId']},'ArnLike':{'aws:SourceArn':'arn:aws:ecs:'+config['region']+':'+config['accountId']+':*'}}:raise ValueError('Task-role trust boundary drift')
    bucket=one('aws_s3_bucket')
    if bucket['id']!=config['bucket']or bucket['bucket']!=config['bucket']or bucket['arn']!='arn:aws:s3:::'+config['bucket']or bucket['force_destroy']is not False:raise ValueError('Store ownership or destructive deletion drift')
    if one('aws_s3_bucket_versioning')['versioning_configuration'][0]['status']!='Disabled':raise ValueError('Unexpected retained document history')
    public=one('aws_s3_bucket_public_access_block')
    if any(public[key]is not True for key in ['block_public_acls','block_public_policy','ignore_public_acls','restrict_public_buckets']):raise ValueError('Public temporary data access')
    if one('aws_s3_bucket_server_side_encryption_configuration')['rule'][0]['apply_server_side_encryption_by_default'][0]['sse_algorithm']!='AES256':raise ValueError('Store encryption differs from runtime')
    documents=all_of('aws_ssm_document')
    if len(documents)!=1 or json.loads(documents[0]['content'])!=command_document(config):raise ValueError('Fixed host document differs from actual runtime')
    host=one('aws_launch_template');cloud=base64.b64decode(host['user_data'],validate=True).decode()
    if not cloud.startswith('#cloud-config\n'):raise ValueError('Expected actual cloud-init input')
    cloud=json.loads(cloud[len('#cloud-config\n'):]);files={item['path']:item for item in cloud['write_files']}
    for filename in ['enterprise_aws_host_probe.py','enterprise_aws_host_bootstrap.py']:
        item=files['/opt/atmem/'+filename];raw=base64.b64decode(item['content'],validate=True)
        if item['owner']!='root:root'or item['permissions']!='0600'or raw!=(ROOT/'src/runtime'/filename).read_bytes():raise ValueError('Bootstrap program/ownership drift')
        ast.parse(raw)
    guard=files['/etc/systemd/system/atmem-document-guard.service']['content'];dropin=files['/etc/systemd/system/ecs.service.d/atmem-document.conf']['content']
    argv=shlex.split(next(line.removeprefix('ExecStart=')for line in guard.splitlines()if line.startswith('ExecStart=')))
    if argv[:4]!=['/usr/bin/python3','-I','/opt/atmem/enterprise_aws_host_bootstrap.py','guard']:raise ValueError('Unexpected guard command')
    expected_host={'format':'enterprise-aws-host-policy-v1','clusterArn':config['clusterArn'],'policySha256':config['hostPolicySha256']}
    if len(argv)!=5 or json.loads(base64.b64decode(argv[4],validate=True))!=expected_host:raise ValueError('Host policy argument not bound')
    if 'Requires=atmem-document-guard.service\n'not in dropin or 'After=atmem-document-guard.service\n'not in dropin:raise ValueError('ECS bypasses guard')
    if cloud['bootcmd']!=[['systemctl','mask','--runtime','--now','ecs.service']]or cloud['runcmd'][0][:4]!=['/bin/bash','-euo','pipefail','-c']:raise ValueError('Host bootstrap is not fail-fast')
    script=cloud['runcmd'][0][4]
    if script.splitlines()[0]!='/usr/bin/python3 -I /opt/atmem/enterprise_aws_host_bootstrap.py prepare '+argv[4]or not script.endswith('/usr/bin/systemctl enable --now --no-block ecs.service'):raise ValueError('Prepared policy/start order drift')
    # Launch-template provider fields deliberately encode tri-state native bools
    # as strings; require the explicit value, not Python string truthiness.
    if host['metadata_options'][0]['http_tokens']!='required'or host['metadata_options'][0]['http_put_response_hop_limit']!=1 or host['network_interfaces'][0]['associate_public_ip_address']!='false':raise ValueError('Host metadata/private placement drift')
    disks=host['block_device_mappings']
    if len(disks)!=1 or disks[0]['ebs'][0]['encrypted']!='true'or disks[0]['ebs'][0]['delete_on_termination']!='true':raise ValueError('Unencrypted or retained parser disk')
    if len(all_of('aws_subnet'))!=2 or len(all_of('aws_vpc_endpoint'))!=8 or any(row['type']in {'aws_nat_gateway','aws_internet_gateway','aws_eip','aws_route'}for row in resources):raise ValueError('Unexpected public network path')
    vpc=one('aws_vpc');subnets=all_of('aws_subnet')
    if not isinstance(vpc['id'],str)or len({row['id']for row in subnets})!=2 or any(not isinstance(row['id'],str)or row['vpc_id']!=vpc['id']or row['map_public_ip_on_launch']is not False for row in subnets):raise ValueError('Subnet escaped owned private network')
    for endpoint in all_of('aws_vpc_endpoint'):
        if endpoint['vpc_id']!=vpc['id']:raise ValueError('Endpoint escaped owned VPC')
        if endpoint['vpc_endpoint_type']=='Interface'and (endpoint['private_dns_enabled']is not True or set(endpoint['subnet_ids'])!={row['id']for row in subnets}):raise ValueError('Private endpoint DNS/placement drift')
    consumption={'configuration':config,'taskDefinition':{**native,'taskDefinitionArn':task['arn'],'revision':task['revision'],'status':'ACTIVE'},'document':json.loads(documents[0]['content'])}
    (directory/'native-runtime-consumption.json').write_text(json.dumps(consumption,indent=2)+'\n')
    dependencies=[Path(__file__).resolve(),*[ROOT/'tests/fixtures/providers'/('aws-'+service+'-authorization-20261111'+suffix)for service in metadata for suffix in ['.json','.provenance.json']],
                  *[ROOT/'src/runtime'/name for name in ['enterprise_aws_jobs.py','enterprise_aws_hosts.py','enterprise_aws_host_probe.py','enterprise_aws_host_bootstrap.py','enterprise-aws-task-template.json']],
                  ROOT/'tests/runtime/enterprise_aws_jobs_contract.py',ROOT/'tests/fixtures/providers/aws-ecs-2014-11-13-botocore-1.43.123.json.gz']
    result={'passed':True,'nativeMockTests':10,'nativeResources':len(resources),'nativeIamActionsChecked':len(actions),'runtimeTaskMatchesNativePlan':True,'bootstrapSourceAndPolicyMatch':True,'cloudOperations':False,
            'sourceHashes':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in dependencies},
            'inputHashes':{name:hashlib.sha256((directory/name).read_bytes()).hexdigest()for name in ['receipt.json','mock-plans.log','runtime-configurations.json']},
            'consumptionSha256':hashlib.sha256((directory/'native-runtime-consumption.json').read_bytes()).hexdigest(),
            'scope':'Actual positive Terraform mock plan, native ECS schema, fixed SSM command, pinned public IAM metadata, bootstrap bytes/arguments and private host configuration. Not destination IAM simulation, actual host/AMI behavior or whole-project qualification.'}
    (directory/'independent-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);verify(parser.parse_args().directory)
