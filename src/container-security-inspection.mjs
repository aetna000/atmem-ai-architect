// Independent supplied-image security/lifecycle contract, expressed from native
// artifact semantics. Do not import the compiler or trust schedule metadata.
const canonical=value=>JSON.stringify(normalize(value));
function normalize(value){
 if(Array.isArray(value))return value.map(normalize).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)));
 return value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,normalize(value[key])])):value;
}
const parse=value=>{try{return JSON.parse(value);}catch{return null;}};
export function inspectContainerSecurity(cloud,name,config,provider,rootRef,fail){
 const resources=config.resource||{},ref=(type,key)=>'${'+type+'.'+name+'.'+key+'}';
 const providerKeys={aws:['region','allowed_account_ids','alias'],azure:['features','subscription_id','alias'],gcp:['region','project','alias'],ibm:['region','alias']}[cloud];
 if(Object.keys(provider||{}).some(key=>!providerKeys.includes(key)))fail('The provider gained configuration outside its reviewed destination/credential-chain contract.');
 const imageGuard='${can(regex("@sha256:[0-9a-f]{64}$", var.'+name+'_image))}';
 if(config.variable?.[name+'_image']?.validation?.condition!==imageGuard)fail('The supplied-image input lost its immutable digest requirement.');
 for(const [type,entries]of Object.entries(resources))if(type!=='terraform_data')for(const item of Object.values(entries)){
  if(item.lifecycle?.prevent_destroy!==true||item.lifecycle.ignore_changes!==undefined)fail('A managed supplied-image resource lost destruction protection or hides configuration changes.');
  if(item.count!==undefined||item.for_each!==undefined)fail('A supplied-image resource changed its reviewed instance ownership.');
  if(!item.depends_on?.includes('terraform_data.review_gate'))fail('A supplied-image resource bypasses its review gate.');
  if(cloud==='gcp'&&item.project!==undefined&&item.project!=='${var.project_id}')fail('A Google resource overrides the delivery-unit project.');
 }
 if(cloud==='gcp'&&resources.google_cloud_run_v2_service?.[name]?.deletion_protection!==true)fail('Cloud Run lost its native deletion protection.');
 if(cloud!=='aws')return;
 if(canonical(provider?.allowed_account_ids)!==canonical([rootRef('account_id')]))fail('The AWS provider lost its explicit account boundary.');
 const partition=ref('data.aws_partition','partition'),lookup=config.data?.aws_partition?.[name];
 if(!lookup||Object.keys(lookup).length)fail('AWS partition metadata must come from the owned native provider without query overrides.');
 const trust={Version:'2012-10-17',Statement:[{Effect:'Allow',Principal:{Service:'ecs-tasks.amazonaws.com'},Action:'sts:AssumeRole',Condition:{StringEquals:{'aws:SourceAccount':'${var.account_id}'},ArnLike:{'aws:SourceArn':'arn:'+partition+':ecs:${var.region}:${var.account_id}:*'}}}]};
 for(const id of [name,name+'_task']){
  const role=resources.aws_iam_role?.[id];
  if(canonical(parse(role?.assume_role_policy))!==canonical(trust)||role?.managed_policy_arns!==undefined||role?.inline_policy!==undefined)fail('An ECS role gained unreviewed trust, attachments or inline application permissions.');
 }
 const policy=resources.aws_iam_role_policy?.[name];
 const expected={Version:'2012-10-17',Statement:[{Effect:'Allow',Action:['ecr:GetAuthorizationToken'],Resource:'*'},{Effect:'Allow',Action:['ecr:BatchCheckLayerAvailability','ecr:GetDownloadUrlForLayer','ecr:BatchGetImage'],Resource:'${var.'+name+'_repository_arn}'},{Effect:'Allow',Action:['logs:CreateLogStream','logs:PutLogEvents'],Resource:ref('aws_cloudwatch_log_group','arn')+':*'}]};
 if(policy?.role!==ref('aws_iam_role','id')||canonical(parse(policy?.policy))!==canonical(expected))fail('ECS execution permissions no longer match exact image-pull and owned-log-stream scope.');
 const repositoryValidation=config.variable?.[name+'_repository_arn']?.validation?.condition;
 if(repositoryValidation!=='${can(regex("^arn:(aws|aws-cn|aws-us-gov):ecr:([a-z]{2}-[a-z]+|us-gov-[a-z]+)-[0-9]{1,2}:[0-9]{12}:repository/[a-z0-9][a-z0-9._/-]{0,255}$", var.'+name+'_repository_arn))}')fail('The ECR input no longer excludes wildcard repository grants.');
 const repositoryRegion='try(split(":",var.'+name+'_repository_arn)[3],"")';
 if(!policy?.lifecycle?.precondition?.some(p=>p.condition==='${startswith(var.'+name+'_repository_arn,"arn:'+partition+':ecr:") && (startswith('+repositoryRegion+',"cn-") ? "aws-cn" : startswith('+repositoryRegion+',"us-gov-") ? "aws-us-gov" : "aws") == data.aws_partition.'+name+'.partition}'))fail('The ECR grant lost its native deployment-partition/region-family check.');
 const service=resources.aws_ecs_service?.[name],task=resources.aws_ecs_task_definition?.[name];
 if(!service?.lifecycle?.precondition?.some(p=>p.condition==='${data.aws_partition.'+name+'.partition == (startswith(var.region,"cn-") ? "aws-cn" : startswith(var.region,"us-gov-") ? "aws-us-gov" : "aws")}'))fail('The native provider partition no longer agrees with the selected supported region family.');
 if(service?.cluster!==ref('aws_ecs_cluster','id')||service?.task_definition!==ref('aws_ecs_task_definition','arn')||service?.launch_type!=='FARGATE'||service?.enable_execute_command===true)fail('The ECS service lost its owned task/cluster or gained remote execution.');
 if(task?.network_mode!=='awsvpc'||canonical(task?.requires_compatibilities)!==canonical(['FARGATE']))fail('The task lost its explicit Fargate network contract.');
 const containers=parse(task?.container_definitions);
 if(!Array.isArray(containers)||containers.length!==1)fail('The supplied-image task gained unreviewed containers.');
 else{
  const container=containers[0];
  if(container.image!=='${var.'+name+'_image}'||Object.keys(container).some(key=>!['name','image','essential','portMappings','logConfiguration'].includes(key)))fail('The task changed its image or gained unreviewed runtime inputs.');
  if(container.logConfiguration?.logDriver!=='awslogs'||container.logConfiguration.options?.['awslogs-group']!==ref('aws_cloudwatch_log_group','name')||container.logConfiguration.options?.['awslogs-region']!=='${var.region}')fail('Container logs no longer use the owned log group and region.');
 }
}
