import {awsHostVerificationTerraform}from'./enterprise-aws-host-infrastructure.mjs';
import template from'./runtime/enterprise-aws-task-template.json'with{type:'json'};
import probe from'./runtime/enterprise-aws-host-probe-source.json'with{type:'json'};
import bootstrap from'./runtime/enterprise-aws-host-bootstrap-source.json'with{type:'json'};
import {awsDocumentInfrastructureTests}from'./enterprise-aws-infrastructure-tests.mjs';
import {enterpriseApplicationFiles}from'./enterprise-application.mjs';

// Parser execution substrate. Full private API/worker/SQL/source/model composition
// and destination qualification remain separate mandatory work, not implied here.
export function awsDocumentJobTerraform(project,row,environment='staging'){
 const host=awsHostVerificationTerraform(project,row,environment),child=JSON.parse(host['main.tf.json']);
 delete child.provider; // Inherit the root provider, including native test mocks.
 const regionInput=structuredClone(child.variable.region);
 const files={'modules/host-verification/main.tf.json':JSON.stringify(child,null,2)+'\n'};
 const n=row.address,v=key=>'${var.'+key+'}',r=(type,suffix,field)=>'${'+type+'.'+n+suffix+'.'+field+'}',l=key=>'${local.'+key+'}';
 const literal=value=>value.replace(/\$\{/g,()=>'$${').replace(/%\{/g,()=>'%%{');
 const seed='https://atmem.ai/workspaces/'+encodeURIComponent(project.id)+'/'+n+'/'+environment;
 const variable={account_id:child.variable.account_id,region:regionInput,worker_role_arn:child.variable.worker_role_arn,
  review_approved:{type:'bool',default:false,nullable:false,description:'Review destination, ownership, endpoint/host costs, data retention and operating responsibilities before apply.'},
  images_ready:{type:'bool',default:false,nullable:false,description:'Create the task revision only after both real immutable owned artifacts pass their checks.'},
  hosts_enabled:{type:'bool',default:false,nullable:false,description:'Launch new dedicated instances only after the actual AMI and bootstrap have been reviewed.'},
  host_count:{type:'number',default:2,nullable:false,description:'Standing capacity proposal, not autoscaling or a throughput guarantee. Review costs and load evidence.',validation:{condition:'${var.host_count == floor(var.host_count) && var.host_count >= 1 && var.host_count <= 4}',error_message:'Use one to four reviewed dedicated hosts.'}},
  availability_zones:{type:'list(string)',nullable:false,description:'Two distinct destination availability zones in the selected region.',validation:{condition:'${length(var.availability_zones) == 2 && length(distinct(var.availability_zones)) == 2 && alltrue([for zone in var.availability_zones : can(regex("^'+row.region+'[a-z]$",zone))])}',error_message:'Supply two distinct availability zones in the selected region.'}},
  host_ami_id:{type:'string',default:'',nullable:false,description:'Pin the reviewed actual Amazon ECS-optimized AL2023 x86_64 AMI. Recommended metadata is discovery, not approval.',validation:{condition:'${!var.hosts_enabled || can(regex("^ami-[0-9a-f]{17}$",var.host_ami_id))}',error_message:'Pin the actual reviewed AMI before launching hosts.'}},
  parser_revision:{type:'string',default:'',nullable:false,description:'Actual independently qualified parser artifact revision.',validation:{condition:'${!var.images_ready || can(regex("^[0-9a-f]{64}$",var.parser_revision))}',error_message:'Supply the actual qualified parser revision.'}}};
 const examples={review_approved:false,images_ready:false,hosts_enabled:false,account_id:'123456789012',region:row.region,worker_role_arn:'arn:aws:iam::123456789012:role/question-worker',availability_zones:[row.region+'a',row.region+'b'],host_ami_id:'',host_count:2,parser_revision:''};
 for(const purpose of ['parser','transfer']){
  variable[purpose+'_image']={type:'string',default:'',nullable:false,description:'Actual owned regional ECR '+purpose+' image pinned by SHA256.',validation:{condition:'${!var.images_ready || can(regex("^[a-z0-9./_-]+@sha256:[0-9a-f]{64}$",var.'+purpose+'_image))}',error_message:'Use the actual immutable '+purpose+' image.'}};
  examples[purpose+'_image']='';
 }
 const locals={name:'${format("doc-%s",substr(sha256('+JSON.stringify(seed)+'),0,12))}',
  cluster_arn:r('aws_ecs_cluster','','arn'),host_policy:'${module.host_verification.host_verification.hostPolicySha256}',
  expected:{format:'enterprise-aws-host-policy-v1',clusterArn:l('cluster_arn'),policySha256:l('host_policy')}};
 const resource={},data={aws_iam_role:{[n+'_worker']:{name:'${basename(var.worker_role_arn)}'}},
  aws_ssm_parameter:{[n+'_recommended_ami']:{name:'/aws/service/ecs/optimized-ami/amazon-linux-2023/recommended/image_id',with_decryption:false}},
  aws_ami:{[n+'_host']:{count:'${var.hosts_enabled ? 1 : 0}',owners:['amazon'],filter:[{name:'image-id',values:[v('host_ami_id')]},{name:'architecture',values:['x86_64']},{name:'virtualization-type',values:['hvm']},{name:'root-device-type',values:['ebs']},{name:'name',values:['al2023-ami-ecs-hvm-2023.*-x86_64']} ]}}};
 const checks=[{condition:v('review_approved'),error_message:'Review this concrete component plan, destination and costs before apply.'},
  {condition:'${startswith(var.worker_role_arn,format("arn:aws:iam::%s:role/",var.account_id)) && data.aws_iam_role.'+n+'_worker.arn == var.worker_role_arn}',error_message:'The existing worker must match the full same-account ARN, including its path.'}];
 for(const purpose of ['parser','transfer'])checks.push({condition:'${!var.images_ready || startswith(var.'+purpose+'_image,format("%s.dkr.ecr.%s.amazonaws.com/%s/'+purpose+'@sha256:",var.account_id,var.region,local.name))}',error_message:'Keep '+purpose+' in its owned regional repository.'});
 resource.terraform_data={[n+'_review']:{input:{source_component:literal(row.id),design_revision:project.revision,environment,requested_worker_arn:v('worker_role_arn'),resolved_worker_arn:'${data.aws_iam_role.'+n+'_worker.arn}'},lifecycle:{precondition:checks}}};
 const add=(type,suffix,body)=>((resource[type]??={})[n+suffix]={...body,depends_on:['terraform_data.'+n+'_review',...(body.depends_on||[])]});
 add('aws_ecs_cluster','',{name:l('name'),setting:[{name:'containerInsights',value:'disabled'}],configuration:{execute_command_configuration:{logging:'NONE'}}});
 const module={host_verification:{source:'./modules/host-verification',providers:{aws:'aws'},account_id:v('account_id'),region:v('region'),review_approved:v('review_approved'),cluster_arn:l('cluster_arn'),worker_role_arn:v('worker_role_arn')}};
 add('aws_vpc','',{cidr_block:'10.88.0.0/16',enable_dns_support:true,enable_dns_hostnames:true,tags:{Name:l('name')},lifecycle:{prevent_destroy:true}});
 for(let i=0;i<2;i++){
  add('aws_subnet','_'+i,{vpc_id:r('aws_vpc','','id'),cidr_block:'10.88.'+i+'.0/24',availability_zone:'${var.availability_zones['+i+']}',map_public_ip_on_launch:false});
  add('aws_route_table','_'+i,{vpc_id:r('aws_vpc','','id')});
  add('aws_route_table_association','_'+i,{subnet_id:r('aws_subnet','_'+i,'id'),route_table_id:r('aws_route_table','_'+i,'id')});
 }
 for(const suffix of ['_host','_endpoint'])add('aws_security_group',suffix,{name:l('name')+suffix.replace('_','-'),description:'Private document '+suffix.slice(1)+' boundary; rules managed separately',vpc_id:r('aws_vpc','','id')});
 add('aws_vpc_security_group_ingress_rule','_endpoint',{security_group_id:r('aws_security_group','_endpoint','id'),referenced_security_group_id:r('aws_security_group','_host','id'),ip_protocol:'tcp',from_port:443,to_port:443});
 add('aws_vpc_security_group_egress_rule','_api',{security_group_id:r('aws_security_group','_host','id'),referenced_security_group_id:r('aws_security_group','_endpoint','id'),ip_protocol:'tcp',from_port:443,to_port:443});
 const subnets=[r('aws_subnet','_0','id'),r('aws_subnet','_1','id')];
 // Modern SSM Agent uses ssmmessages; obsolete ec2messages is unavailable in
 // newer regions. No public endpoint fallback exists in this isolated VPC.
 for(const service of ['ecs','ecs-agent','ecs-telemetry','ecr.api','ecr.dkr','ssm','ssmmessages'])add('aws_vpc_endpoint','_'+service.replace(/[.-]/g,'_'),{vpc_id:r('aws_vpc','','id'),service_name:'${format("com.amazonaws.%s.'+service+'",var.region)}',vpc_endpoint_type:'Interface',private_dns_enabled:true,subnet_ids:subnets,security_group_ids:[r('aws_security_group','_endpoint','id')]});
 add('aws_vpc_endpoint','_s3',{vpc_id:r('aws_vpc','','id'),service_name:'${format("com.amazonaws.%s.s3",var.region)}',vpc_endpoint_type:'Gateway',route_table_ids:[r('aws_route_table','_0','id'),r('aws_route_table','_1','id')],
  policy:'${jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Principal="*",Action=["s3:GetObject","s3:PutObject","s3:GetBucketLocation","s3:GetBucketVersioning"],Resource=[aws_s3_bucket.'+n+'.arn,format("%s/document-jobs/*",aws_s3_bucket.'+n+'.arn),format("arn:aws:s3:::prod-%s-starport-layer-bucket/*",var.region)]}]})}'});
 add('aws_vpc_security_group_egress_rule','_s3',{security_group_id:r('aws_security_group','_host','id'),prefix_list_id:r('aws_vpc_endpoint','_s3','prefix_list_id'),ip_protocol:'tcp',from_port:443,to_port:443});
 add('aws_s3_bucket','',{bucket:'${format("atmem-doc-%s",substr(sha256(format("%s:%s",var.account_id,local.name)),0,20))}',force_destroy:false,lifecycle:{prevent_destroy:true}});
 add('aws_s3_bucket_public_access_block','',{bucket:r('aws_s3_bucket','','id'),block_public_acls:true,block_public_policy:true,ignore_public_acls:true,restrict_public_buckets:true});
 add('aws_s3_bucket_ownership_controls','',{bucket:r('aws_s3_bucket','','id'),rule:{object_ownership:'BucketOwnerEnforced'}});
 add('aws_s3_bucket_server_side_encryption_configuration','',{bucket:r('aws_s3_bucket','','id'),rule:{apply_server_side_encryption_by_default:{sse_algorithm:'AES256'}}});
 // A new bucket has no history; never suspend/adopt an existing versioned bucket.
 add('aws_s3_bucket_versioning','',{bucket:r('aws_s3_bucket','','id'),versioning_configuration:{status:'Disabled'}});
 add('aws_s3_bucket_lifecycle_configuration','',{bucket:r('aws_s3_bucket','','id'),rule:[{id:'orphan-fallback',status:'Enabled',filter:{prefix:'document-jobs/'},expiration:{days:1},abort_incomplete_multipart_upload:{days_after_initiation:1}}]});
 const bucket=r('aws_s3_bucket','','arn'),objects='${format("%s/document-jobs/*",aws_s3_bucket.'+n+'.arn)}';
 locals.bucket_policy={Version:'2012-10-17',Statement:[
  {Sid:'RequireTLS',Effect:'Deny',Principal:'*',Action:'s3:*',Resource:[bucket,'${format("%s/*",aws_s3_bucket.'+n+'.arn)}'],Condition:{Bool:{'aws:SecureTransport':'false'}}},
  {Sid:'RequireExplicitEncryption',Effect:'Deny',Principal:'*',Action:'s3:PutObject',Resource:objects,Condition:{StringNotEquals:{'s3:x-amz-server-side-encryption':'AES256'}}},
  {Sid:'RequireCreateOnly',Effect:'Deny',Principal:'*',Action:'s3:PutObject',Resource:objects,Condition:{StringNotEquals:{'s3:if-none-match':'*'}}}]};
 add('aws_s3_bucket_policy','',{bucket:r('aws_s3_bucket','','id'),policy:'${jsonencode(local.bucket_policy)}',depends_on:['aws_s3_bucket_public_access_block.'+n]});
 for(const purpose of ['parser','transfer'])add('aws_ecr_repository','_'+purpose,{name:l('name')+'/'+purpose,image_tag_mutability:'IMMUTABLE',force_delete:false,encryption_configuration:{encryption_type:'AES256'},image_scanning_configuration:{scan_on_push:true},lifecycle:{prevent_destroy:true}});
 locals.task_trust={Version:'2012-10-17',Statement:[{Effect:'Allow',Principal:{Service:'ecs-tasks.amazonaws.com'},Action:'sts:AssumeRole',Condition:{StringEquals:{'aws:SourceAccount':v('account_id')},ArnLike:{'aws:SourceArn':'${format("arn:aws:ecs:%s:%s:*",var.region,var.account_id)}'}}}]};
 const trust=service=>service==='ecs-tasks.amazonaws.com'?'${jsonencode(local.task_trust)}':JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Principal:{Service:service},Action:'sts:AssumeRole'}]});
 for(const purpose of ['host','execution','transfer'])add('aws_iam_role','_'+purpose,{name:l('name')+'-'+purpose,assume_role_policy:trust(purpose==='host'?'ec2.amazonaws.com':'ecs-tasks.amazonaws.com')});
 const policy=suffix=>add('aws_iam_role_policy',suffix,{name:l('name')+suffix.replace('_','-'),role:r('aws_iam_role',suffix,'name'),policy:'${jsonencode(local.'+suffix.slice(1)+'_policy)}'}),allow=(Sid,Action,Resource,Condition)=>({Sid,Effect:'Allow',Action,Resource,...(Condition?{Condition}:{} )});
 locals.transfer_policy={Version:'2012-10-17',Statement:[allow('TemporaryBytesOnly',['s3:GetObject','s3:PutObject'],objects),allow('CheckOwnedStore',['s3:GetBucketLocation','s3:GetBucketVersioning'],bucket)]};policy('_transfer');
 locals.execution_policy={Version:'2012-10-17',Statement:[allow('EcrLogin',['ecr:GetAuthorizationToken'],'*'),allow('OwnedImagesOnly',['ecr:BatchGetImage','ecr:GetDownloadUrlForLayer','ecr:BatchCheckLayerAvailability'],[r('aws_ecr_repository','_parser','arn'),r('aws_ecr_repository','_transfer','arn')])]};policy('_execution');
 const ci='${format("arn:aws:ecs:%s:%s:container-instance/%s/*",var.region,var.account_id,local.name)}',tasks='${format("arn:aws:ecs:%s:%s:task/%s/*",var.region,var.account_id,local.name)}';
 locals.host_policy_document={Version:'2012-10-17',Statement:[allow('RegisterInOwnedCluster',['ecs:RegisterContainerInstance','ecs:DeregisterContainerInstance','ecs:SubmitAttachmentStateChanges','ecs:SubmitContainerStateChange','ecs:SubmitTaskStateChange'],l('cluster_arn')),
  allow('OwnedAgentLifecycle',['ecs:Poll','ecs:StartTelemetrySession','ecs:UpdateContainerInstancesState'],ci,{ArnEquals:{'ecs:cluster':l('cluster_arn')}}),
  allow('DiscoverAgentEndpoint',['ecs:DiscoverPollEndpoint'],'*'),allow('OwnedAgentTags',['ecs:ListTagsForResource'],[ci,tasks]),
  allow('AgentRegistrationTags',['ecs:TagResource'],ci,{StringEquals:{'ecs:CreateAction':'RegisterContainerInstance'}}),
  allow('SsmTransport',['ssm:UpdateInstanceInformation','ssmmessages:CreateControlChannel','ssmmessages:CreateDataChannel','ssmmessages:OpenControlChannel','ssmmessages:OpenDataChannel'],'*'),
  allow('FixedSsmDocument',['ssm:GetDocument','ssm:DescribeDocument'],'${module.host_verification.host_verification.hostDocumentArn}')]};
 add('aws_iam_role_policy','_host',{name:l('name')+'-host',role:r('aws_iam_role','_host','name'),policy:'${jsonencode(local.host_policy_document)}'});
 add('aws_iam_instance_profile','',{name:l('name')+'-host',role:r('aws_iam_role','_host','name')});
 // Resolve only owned static placeholders; no request or client source is evaluated.
 const replacements={'__FAMILY__':l('name')+'-parser','__POLICY_SHA256__':l('host_policy'),'__TRANSFER_ROLE_ARN__':r('aws_iam_role','_transfer','arn'),'__EXECUTION_ROLE_ARN__':r('aws_iam_role','_execution','arn'),'__PARSER_IMAGE__':v('parser_image'),'__TRANSFER_IMAGE__':v('transfer_image')};
 function resolve(value){if(Array.isArray(value))return value.map(resolve);if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([key,item])=>[key,resolve(item)]));if(typeof value==='string')for(const[key,item]of Object.entries(replacements))value=value.replaceAll(key,item);return value;}
 locals.task_definition=resolve(template);
 // Runtime family is deliberately prefixed document-, independent of display names.
 locals.task_definition.family='${format("document-%s-parser",local.name)}';
 add('aws_ecs_task_definition','',{count:'${var.images_ready ? 1 : 0}',family:'${local.task_definition.family}',network_mode:'bridge',requires_compatibilities:['EC2'],task_role_arn:r('aws_iam_role','_transfer','arn'),execution_role_arn:r('aws_iam_role','_execution','arn'),
  container_definitions:'${jsonencode(local.task_definition.containerDefinitions)}',runtime_platform:{cpu_architecture:'X86_64',operating_system_family:'LINUX'},placement_constraints:[{type:'memberOf',expression:'${local.task_definition.placementConstraints[0].expression}'}],
  volume:['input','output'].map(name=>({name,docker_volume_configuration:{scope:'task',driver:'local',autoprovision:false}})),tags:{'atmem-workload':'document-parser'}});
 locals.worker_policy={Version:'2012-10-17',Statement:[allow('InspectDefinition',['ecs:DescribeTaskDefinition'],'*'),allow('RunPinnedDefinition',['ecs:RunTask'],'${var.images_ready ? aws_ecs_task_definition.'+n+'[0].arn : null}',{ArnEquals:{'ecs:cluster':l('cluster_arn')},Bool:{'ecs:enable-execute-command':'false'}}),
  allow('OwnedTaskLifecycle',['ecs:DescribeTasks','ecs:StopTask'],tasks,{ArnEquals:{'ecs:cluster':l('cluster_arn')}}),allow('DiscoverOwnedRuns',['ecs:ListTasks'],ci,{ArnEquals:{'ecs:cluster':l('cluster_arn')}}),
  allow('PassOnlyTransferAndPull',['iam:PassRole'],[r('aws_iam_role','_transfer','arn'),r('aws_iam_role','_execution','arn')],{StringEquals:{'iam:PassedToService':'ecs-tasks.amazonaws.com'}}),
  allow('OwnedTemporaryBytes',['s3:GetObject','s3:PutObject','s3:DeleteObject'],objects),allow('CheckOwnedStore',['s3:GetBucketLocation','s3:GetBucketVersioning'],bucket)]};
 // Conditional local prevents evaluating [0] while images are not ready.
 locals.enabled_worker_policy='${var.images_ready ? jsonencode(local.worker_policy) : null}';
 add('aws_iam_role_policy','_worker',{count:'${var.images_ready ? 1 : 0}',name:l('name')+'-worker',role:'${data.aws_iam_role.'+n+'_worker.name}',policy:l('enabled_worker_policy')});
 const encode=text=>btoa(Array.from(new TextEncoder().encode(text),byte=>String.fromCharCode(byte)).join(''));
 locals.expected_b64='${base64encode(jsonencode(local.expected))}';
 const guardUnit='[Unit]\nDescription=AtMem private parser host guard\nRequires=docker.service\nAfter=docker.service\nBindsTo=docker.service\nPartOf=docker.service\n\n[Service]\nType=oneshot\nRemainAfterExit=yes\nTimeoutStartSec=60\nExecStart=/usr/bin/python3 -I /opt/atmem/enterprise_aws_host_bootstrap.py guard ${local.expected_b64}\n';
 const ecsDropin='[Unit]\nRequires=atmem-document-guard.service\nAfter=atmem-document-guard.service\nBindsTo=atmem-document-guard.service\nPartOf=docker.service\n';
 locals.cloud_init={package_update:false,package_upgrade:false,bootcmd:[['systemctl','mask','--runtime','--now','ecs.service']],write_files:[
  {path:'/opt/atmem/enterprise_aws_host_probe.py',owner:'root:root',permissions:'0600',encoding:'b64',content:encode(probe)},
  {path:'/opt/atmem/enterprise_aws_host_bootstrap.py',owner:'root:root',permissions:'0600',encoding:'b64',content:encode(bootstrap)},
  {path:'/etc/systemd/system/atmem-document-guard.service',owner:'root:root',permissions:'0644',content:guardUnit},
  {path:'/etc/systemd/system/ecs.service.d/atmem-document.conf',owner:'root:root',permissions:'0644',content:ecsDropin}],
  runcmd:[['/bin/bash','-euo','pipefail','-c','/usr/bin/python3 -I /opt/atmem/enterprise_aws_host_bootstrap.py prepare ${local.expected_b64}\n/usr/bin/systemctl daemon-reload\n/usr/bin/systemctl restart docker.service\n/usr/bin/systemctl start atmem-document-guard.service\n/usr/bin/systemctl unmask --runtime ecs.service\n/usr/bin/systemctl enable --now --no-block ecs.service']]};
 locals.cloud_init_text=['#cloud-config','${jsonencode(local.cloud_init)}'].join(String.fromCharCode(10));
 add('aws_launch_template','',{count:'${var.hosts_enabled ? 1 : 0}',name_prefix:l('name')+'-',image_id:'${data.aws_ami.'+n+'_host[0].id}',instance_type:'m6i.large',update_default_version:false,
  iam_instance_profile:{arn:r('aws_iam_instance_profile','','arn')},network_interfaces:[{associate_public_ip_address:false,security_groups:[r('aws_security_group','_host','id')]}],
  metadata_options:{http_endpoint:'enabled',http_tokens:'required',http_put_response_hop_limit:1,http_protocol_ipv6:'disabled',instance_metadata_tags:'disabled'},
  block_device_mappings:[{device_name:'${data.aws_ami.'+n+'_host[0].root_device_name}',ebs:{encrypted:true,delete_on_termination:true,volume_size:40,volume_type:'gp3'}}],
  user_data:'${base64encode(local.cloud_init_text)}',
  tag_specifications:[{resource_type:'instance',tags:{'atmem-document-policy':l('host_policy'),Name:l('name')}},{resource_type:'volume',tags:{Name:l('name')}}],lifecycle:{create_before_destroy:true}});
 add('aws_autoscaling_group','',{count:'${var.hosts_enabled ? 1 : 0}',name:l('name'),min_size:v('host_count'),max_size:v('host_count'),desired_capacity:v('host_count'),vpc_zone_identifier:subnets,health_check_type:'EC2',
  launch_template:{id:'${aws_launch_template.'+n+'[0].id}',version:'${tostring(aws_launch_template.'+n+'[0].latest_version)}'},
  tag:[{key:'atmem-document-policy',value:l('host_policy'),propagate_at_launch:true}],
  depends_on:['aws_iam_role_policy.'+n+'_host',...Object.keys(resource.aws_vpc_endpoint).map(name=>'aws_vpc_endpoint.'+name),'aws_vpc_security_group_egress_rule.'+n+'_api','aws_vpc_security_group_egress_rule.'+n+'_s3']});
 locals.document_job_configuration={format:'enterprise-aws-document-job-v2',accountId:v('account_id'),region:v('region'),bucket:r('aws_s3_bucket','','id'),clusterArn:l('cluster_arn'),
  hostPolicySha256:l('host_policy'),hostDocumentArn:'${module.host_verification.host_verification.hostDocumentArn}',hostDocumentHash:'${module.host_verification.host_verification.hostDocumentHash}',hostDocumentVersion:'${module.host_verification.host_verification.hostDocumentVersion}',
  workerRoleArn:v('worker_role_arn'),transferRoleArn:r('aws_iam_role','_transfer','arn'),executionRoleArn:r('aws_iam_role','_execution','arn'),parserImage:v('parser_image'),transferImage:v('transfer_image'),taskDefinitionArn:'${var.images_ready ? aws_ecs_task_definition.'+n+'[0].arn : null}'};
 locals.document_executor_configuration={format:'enterprise-document-executor-v1',provider:'aws',parserRevision:v('parser_revision'),configuration:l('document_job_configuration')};
 const output={document_job_configuration:{value:'${var.images_ready && var.hosts_enabled ? local.document_job_configuration : null}',description:'Runtime config only; requires complete worker/export and destination checks.',depends_on:['aws_autoscaling_group.'+n,'aws_iam_role_policy.'+n+'_worker']},
  artifacts:{value:{parserRepository:r('aws_ecr_repository','_parser','repository_url'),transferRepository:r('aws_ecr_repository','_transfer','repository_url'),parserRevision:v('parser_revision'),recommendedAmi:'${nonsensitive(data.aws_ssm_parameter.'+n+'_recommended_ami.value)}',hostAmi:v('host_ami_id')}},
  host_verification:{value:'${module.host_verification.host_verification}'},document_executor_configuration:{value:'${var.images_ready && var.hosts_enabled ? local.document_executor_configuration : null}',description:'Owned worker input envelope, bound to the approved parser revision; full application hosting/export acceptance is separate.'}};
 const main={terraform:child.terraform,provider:{aws:{region:v('region'),allowed_account_ids:[v('account_id')]}},variable,locals,data,module,resource,output};
 return {...enterpriseApplicationFiles('aws',n),...files,'main.tf.json':JSON.stringify(main,null,2)+'\n','.terraform.lock.hcl':host['.terraform.lock.hcl'],'deployment.tfvars.json.example':JSON.stringify(examples,null,2)+'\n',
  'tests/document-infrastructure.tftest.hcl':awsDocumentInfrastructureTests(n,seed,row.region),
  'document-job-boundary.json':JSON.stringify({provider:'aws',region:row.region,component:row.id,scope:'Private parser execution substrate; complete application/export is unfinished.',cloudOperations:false,wholeProjectQualified:false},null,2)+'\n',
  'README.md':'# AWS private parser substrate\n\nCreates a new dedicated private VPC, two subnets, API/ECR/SSM endpoints, temporary no-history S3 store, separate host/transfer/image-pull roles, immutable repositories, fixed host verifier and optional EC2 pool/static task revision. Existing worker identity is referenced by its full ARN and receives additive named policies. No existing pool, database, document source or website is adopted.\n\nReview costs before foundation apply: endpoints incur standing charges even with hosts disabled. Hosts are a fixed bounded standing pool, not automatically scaled or performance-qualified. Supply actual reviewed AMI and independently qualified immutable images; discovery metadata does not approve them. Runtime output remains null until both switches are enabled.\n\nNo NAT, internet gateway, public IP or SSH ingress is created. Trusted transfer stages can reach the named private APIs and the S3 gateway prefix list; the parser has networking disabled. Physical erasure, native host/agent/SSM/IAM behavior, strict retention and throughput require destination qualification. One-day lifecycle is an asynchronous fallback, not a deadline.\n\nTask definitions belong to Terraform, not the worker. Upgrade by publishing a new reviewed revision and draining active work before replacing hosts; automatic rolling host replacement/draining is not implemented. Keep the old cleanup target available when changing family/bucket/destination. Never destroy populated stores or terminate active hosts without a reviewed drain.\n\nComplete API/worker/SQL/model/source hosting, enrollment, secrets, recovery and Spec Kit/export composition remain unfinished. No whole-project, security, cloud-plan or deployment acceptance is implied.\n'};
}
