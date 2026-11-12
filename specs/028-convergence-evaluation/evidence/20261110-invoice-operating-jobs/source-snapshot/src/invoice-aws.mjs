import {invoiceBuilder,v,r,l}from'./invoice-builder.mjs';
import {awsInvoiceOperations}from'./invoice-aws-operations.mjs';
import {CLOUD_PROVIDER_LOCKS}from'./cloud-provider-locks.mjs';

// Isolated adapter under qualification. Not registered as a complete invoice
// capability until application, operations and whole-export checks pass.
export function awsInvoiceTerraform(project,row,environment='staging'){
 if(row.provider!=='aws')throw Error('AWS invoice adapter cannot substitute another provider');
 const b=invoiceBuilder(project,row,environment),{input,add,region}=b,n=row.address;
 const account=input('account_id','Expected commercial AWS account, using an approved operator identity.','123456789012','^[0-9]{12}$');
 const zone=input('public_zone_id','Existing owned public Route53 zone. Referenced, never recreated or imported.','Z0123456789EXAMPLE','^[A-Z0-9]{5,40}$');
 const model=input('model_id','Reviewed direct regional Bedrock foundation model ID. Verify regional availability, quotas, terms and retention-none policy.','anthropic.reviewed-model-v1:0','^[a-z0-9][a-z0-9.-]*:[0-9]+$');
 const endpoint=input('accounting_endpoint','Existing accounting HTTPS adapter endpoint; no vendor or replacement system is provisioned.','https://accounting.example.test/actions','^https://[A-Za-z0-9.-]+(:[0-9]{1,5})?(/[^?#@ ]*)?$');
 const scope=input('accounting_scope','Reviewed opaque destination account/scope, bound into every approval.','owned-account','^[A-Za-z0-9_.:/-]{1,200}$');
 const seed=b.seed;
 for(const key of ['runtime_image','parser_image']){
  input(key,'Published, reviewed immutable image in the emitted ECR repository. Empty during foundation setup.',key==='runtime_image'?'123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/reviewed-runtime@sha256:'+'a'.repeat(64):'123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/reviewed-parser@sha256:'+'b'.repeat(64));
  b.variable[key].default='';b.variable[key].validation={condition:'${!('+(key==='runtime_image'?'var.applications_enabled || var.operations_enabled':'var.applications_enabled')+') || (can(regex("@sha256:[0-9a-f]{64}$",var.'+key+')) && !endswith(var.'+key+',"@sha256:'+ '0'.repeat(64)+'"))}',error_message:'Application release requires a reviewed immutable image digest.'};
  b.testExpressions[key]='format("123456789012.dkr.ecr.'+(row.region||'ap-southeast-2')+'.amazonaws.com/invoice-%s-'+(key==='runtime_image'?'runtime':'parser')+'@sha256:'+(key==='runtime_image'?'a':'b').repeat(64)+'",substr(sha256('+JSON.stringify(seed)+'),0,12))';
  b.resource.terraform_data.review_gate.lifecycle.precondition.push({condition:'${!('+(key==='runtime_image'?'var.applications_enabled || var.operations_enabled':'var.applications_enabled')+') || startswith(var.'+key+',format("%s.dkr.ecr.%s.amazonaws.com/%s-'+(key==='runtime_image'?'runtime':'parser')+'@sha256:",var.account_id,var.region,local.name))}',error_message:'Use the package-owned regional ECR repository; a digest from another repository is not an admitted release.'});
 }
 b.variable.replay_review_base64={type:'string',default:'',description:'Scoped expiring operator receipt for the real endpoint idempotency contract. Empty disables automatic replay of uncertain deliveries.'};b.examples.replay_review_base64='';
 b.data.aws_caller_identity={destination:{}};b.data.aws_availability_zones={destination:{state:'available',filter:{name:'zone-type',values:['availability-zone']}}};b.data.aws_route53_zone={destination:{zone_id:zone,private_zone:false}};
 b.resource.terraform_data.review_gate.lifecycle.precondition.push({condition:'${data.aws_caller_identity.destination.account_id == var.account_id && !data.aws_route53_zone.destination.private_zone && length(data.aws_availability_zones.destination.names) >= 2}',error_message:'Use the reviewed account, owned public DNS zone and at least two regional availability zones.'});
 Object.assign(b.locals,{api_hostname:'${format("%s.%s",local.name,trimsuffix(data.aws_route53_zone.destination.name,"."))}',parser_zone:'${format("%s.internal.%s",local.name,trimsuffix(data.aws_route53_zone.destination.name,"."))}',parser_hostname:'${format("parse.%s",local.parser_zone)}',public_origin:'${format("https://%s",local.api_hostname)}',parser_endpoint:'${format("https://%s/extract",local.parser_hostname)}',destination_contract:{id:'normalized-action-v1',endpointSha256:'${sha256(var.accounting_endpoint)}',scope,mappingVersion:1},destination_contract_base64:'${base64encode(jsonencode(local.destination_contract))}'});
 add('aws_vpc',n,{cidr_block:'10.82.0.0/16',enable_dns_support:true,enable_dns_hostnames:true,tags:{Name:l('name')}});
 add('aws_internet_gateway',n,{vpc_id:r('aws_vpc',n,'id')});
 for(let i=0;i<2;i++){
  add('aws_subnet',n+'_public_'+i,{vpc_id:r('aws_vpc',n,'id'),availability_zone:'${data.aws_availability_zones.destination.names['+i+']}',cidr_block:'10.82.'+i+'.0/24',map_public_ip_on_launch:false});
  add('aws_subnet',n+'_private_'+i,{vpc_id:r('aws_vpc',n,'id'),availability_zone:'${data.aws_availability_zones.destination.names['+i+']}',cidr_block:'10.82.'+(16+i)+'.0/24',map_public_ip_on_launch:false});
 }
 add('aws_eip',n,{domain:'vpc'});add('aws_nat_gateway',n,{allocation_id:r('aws_eip',n,'id'),subnet_id:r('aws_subnet',n+'_public_0','id'),depends_on:['aws_internet_gateway.'+n]});
 add('aws_route_table',n+'_public',{vpc_id:r('aws_vpc',n,'id')});
 add('aws_route',n+'_public',{route_table_id:r('aws_route_table',n+'_public','id'),destination_cidr_block:'0.0.0.0/0',gateway_id:r('aws_internet_gateway',n,'id')});
 add('aws_route_table',n+'_private',{vpc_id:r('aws_vpc',n,'id')});
 add('aws_route',n+'_private',{route_table_id:r('aws_route_table',n+'_private','id'),destination_cidr_block:'0.0.0.0/0',nat_gateway_id:r('aws_nat_gateway',n,'id')});
 const publicSubnets=[],privateSubnets=[];
 for(let i=0;i<2;i++){publicSubnets.push(r('aws_subnet',n+'_public_'+i,'id'));privateSubnets.push(r('aws_subnet',n+'_private_'+i,'id'));for(const kind of ['public','private'])add('aws_route_table_association',n+'_'+kind+'_'+i,{subnet_id:r('aws_subnet',n+'_'+kind+'_'+i,'id'),route_table_id:r('aws_route_table',n+'_'+kind,'id')});}
 for(const purpose of ['api_lb','api','worker','parser_lb','parser','database'])add('aws_security_group',n+'_'+purpose,{name_prefix:l('name')+'-'+purpose+'-',description:'Owned invoice '+purpose+' boundary',vpc_id:r('aws_vpc',n,'id')});
 const ingress=(name,target,port,source)=>add('aws_vpc_security_group_ingress_rule',n+'_'+name,{security_group_id:r('aws_security_group',n+'_'+target,'id'),ip_protocol:'tcp',from_port:port,to_port:port,...(source==='public'?{cidr_ipv4:'0.0.0.0/0'}:{referenced_security_group_id:r('aws_security_group',n+'_'+source,'id')})});
 const egress=(name,source,port,target)=>add('aws_vpc_security_group_egress_rule',n+'_'+name,{security_group_id:r('aws_security_group',n+'_'+source,'id'),ip_protocol:'tcp',from_port:port,to_port:port,...(target==='internet'?{cidr_ipv4:'0.0.0.0/0'}:{referenced_security_group_id:r('aws_security_group',n+'_'+target,'id')})});
 ingress('public_https','api_lb',443,'public');ingress('api_from_lb','api',8080,'api_lb');egress('lb_to_api','api_lb',8080,'api');
 ingress('parser_from_worker','parser_lb',443,'worker');ingress('parser_from_lb','parser',8080,'parser_lb');egress('lb_to_parser','parser_lb',8080,'parser');
 for(const purpose of ['api','worker']){ingress('database_from_'+purpose,'database',5432,purpose);egress(purpose+'_database',purpose,5432,'database');egress(purpose+'_https',purpose,443,'internet');}
 add('aws_db_subnet_group',n,{name:l('name'),subnet_ids:privateSubnets});
 add('aws_db_parameter_group',n,{name:l('name'),family:'postgres17',parameter:[{name:'rds.force_ssl',value:'1'},{name:'log_statement',value:'none'},{name:'log_min_error_statement',value:'panic'},{name:'log_parameter_max_length_on_error',value:'0'}]});
 add('aws_db_instance',n,{identifier:l('name'),engine:'postgres',engine_version:'17.11',instance_class:'db.t4g.small',allocated_storage:20,max_allocated_storage:100,storage_type:'gp3',storage_encrypted:true,db_name:'invoice',username:'invoice_operator',manage_master_user_password:true,iam_database_authentication_enabled:true,port:5432,publicly_accessible:false,multi_az:true,db_subnet_group_name:r('aws_db_subnet_group',n,'name'),vpc_security_group_ids:[r('aws_security_group',n+'_database','id')],parameter_group_name:r('aws_db_parameter_group',n,'name'),backup_retention_period:7,copy_tags_to_snapshot:true,deletion_protection:true,skip_final_snapshot:false,final_snapshot_identifier:l('name')+'-final',delete_automated_backups:false,auto_minor_version_upgrade:true,allow_major_version_upgrade:false,ca_cert_identifier:'rds-ca-rsa2048-g1',lifecycle:{prevent_destroy:true}});
 add('aws_s3_bucket',n,{bucket:account+'-'+l('name')+'-invoices',force_destroy:false,lifecycle:{prevent_destroy:true}});const bucket=r('aws_s3_bucket',n,'id'),bucketArn=r('aws_s3_bucket',n,'arn'),objects=bucketArn+'/accounts/'+l('account_uuid')+'/invoices/*';
 add('aws_s3_bucket_public_access_block',n,{bucket,block_public_acls:true,block_public_policy:true,ignore_public_acls:true,restrict_public_buckets:true});add('aws_s3_bucket_ownership_controls',n,{bucket,rule:{object_ownership:'BucketOwnerEnforced'}});add('aws_s3_bucket_server_side_encryption_configuration',n,{bucket,rule:{apply_server_side_encryption_by_default:{sse_algorithm:'AES256'}}});add('aws_s3_bucket_versioning',n,{bucket,versioning_configuration:{status:'Enabled'}});
 add('aws_s3_bucket_lifecycle_configuration',n,{bucket,rule:[{id:'invoice-retention',status:'Enabled',filter:{prefix:'accounts/'},expiration:{days:90},noncurrent_version_expiration:{noncurrent_days:1},abort_incomplete_multipart_upload:{days_after_initiation:1}}],depends_on:['aws_s3_bucket_versioning.'+n]});
 add('aws_s3_bucket_policy',n,{bucket,policy:JSON.stringify({Version:'2012-10-17',Statement:[{Sid:'TLSOnly',Effect:'Deny',Principal:'*',Action:'s3:*',Resource:[bucketArn,bucketArn+'/*'],Condition:{Bool:{'aws:SecureTransport':'false','aws:PrincipalIsAWSService':'false'}}}]})});
 add('aws_secretsmanager_secret',n+'_destination',{name:l('name')+'/accounting-token',recovery_window_in_days:30,lifecycle:{prevent_destroy:true}});
 add('aws_cognito_user_pool',n,{name:l('name'),username_attributes:['email'],auto_verified_attributes:['email'],admin_create_user_config:{allow_admin_create_user_only:true},mfa_configuration:'ON',software_token_mfa_configuration:{enabled:true},password_policy:{minimum_length:14,require_lowercase:true,require_uppercase:true,require_numbers:true,require_symbols:true,temporary_password_validity_days:3},account_recovery_setting:{recovery_mechanism:{name:'admin_only',priority:1}},lifecycle:{prevent_destroy:true}});
 add('aws_cognito_resource_server',n,{identifier:l('name'),name:'Invoice processing',user_pool_id:r('aws_cognito_user_pool',n,'id'),scope:{scope_name:'process',scope_description:'Signed-in invoice workspace access; approval roles are checked independently in SQL.'}});
 add('aws_cognito_user_pool_client',n,{name:l('name')+'-browser',user_pool_id:r('aws_cognito_user_pool',n,'id'),generate_secret:false,allowed_oauth_flows_user_pool_client:true,allowed_oauth_flows:['code'],allowed_oauth_scopes:['openid',l('name')+'/process'],callback_urls:[l('public_origin')+'/'],logout_urls:[l('public_origin')+'/'],supported_identity_providers:['COGNITO'],prevent_user_existence_errors:'ENABLED',enable_token_revocation:true,access_token_validity:30,id_token_validity:30,refresh_token_validity:1,token_validity_units:{access_token:'minutes',id_token:'minutes',refresh_token:'days'},depends_on:['aws_cognito_resource_server.'+n]});
 add('aws_cognito_user_pool_domain',n,{domain:account+'-'+l('name'),user_pool_id:r('aws_cognito_user_pool',n,'id')});
 for(const purpose of ['runtime','parser'])add('aws_ecr_repository',n+'_'+purpose,{name:l('name')+'-'+purpose,image_tag_mutability:'IMMUTABLE',image_scanning_configuration:{scan_on_push:true},encryption_configuration:{encryption_type:'AES256'},force_delete:false,lifecycle:{prevent_destroy:true}});
 const trust=JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Principal:{Service:'ecs-tasks.amazonaws.com'},Action:'sts:AssumeRole',Condition:{StringEquals:{'aws:SourceAccount':account},ArnLike:{'aws:SourceArn':'arn:aws:ecs:'+region+':'+account+':*'}}}]});
 for(const purpose of ['api','worker','parser']){
  add('aws_cloudwatch_log_group',n+'_'+purpose,{name:'/ecs/'+l('name')+'/'+purpose,retention_in_days:7});add('aws_iam_role',n+'_'+purpose+'_execution',{name:l('name')+'-'+purpose+'-execution',assume_role_policy:trust});
  const repo=r('aws_ecr_repository',n+'_'+(purpose==='parser'?'parser':'runtime'),'arn');
  add('aws_iam_role_policy',n+'_'+purpose+'_execution',{role:r('aws_iam_role',n+'_'+purpose+'_execution','id'),policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Action:['ecr:GetAuthorizationToken'],Resource:'*'},{Effect:'Allow',Action:['ecr:BatchGetImage','ecr:GetDownloadUrlForLayer','ecr:BatchCheckLayerAvailability'],Resource:repo},{Effect:'Allow',Action:['logs:CreateLogStream','logs:PutLogEvents'],Resource:r('aws_cloudwatch_log_group',n+'_'+purpose,'arn')+':*'},...(purpose==='worker'?[{Effect:'Allow',Action:['secretsmanager:GetSecretValue'],Resource:r('aws_secretsmanager_secret',n+'_destination','arn')}]:[])]})});
  if(purpose!=='parser'){
   add('aws_iam_role',n+'_'+purpose,{name:l('name')+'-'+purpose,assume_role_policy:trust});
   add('aws_iam_role_policy',n+'_'+purpose,{role:r('aws_iam_role',n+'_'+purpose,'id'),policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Action:purpose==='api'?['s3:PutObject','s3:GetObject','s3:GetObjectVersion']:['s3:GetObject','s3:GetObjectVersion'],Resource:objects},{Effect:'Allow',Action:['rds-db:connect'],Resource:'arn:aws:rds-db:'+region+':'+account+':dbuser:'+r('aws_db_instance',n,'resource_id')+'/'+l(purpose+'_db_user')},...(purpose==='worker'?[{Effect:'Allow',Action:['bedrock:InvokeModel'],Resource:'arn:aws:bedrock:'+region+'::foundation-model/'+model},{Effect:'Allow',Action:['bedrock:GetAccountDataRetention','bedrock:GetModelInvocationLoggingConfiguration'],Resource:'*',Condition:{StringEquals:{'aws:RequestedRegion':region}}}]:[])]})});
  }
 }
 add('aws_acm_certificate',n,{domain_name:l('api_hostname'),subject_alternative_names:[l('parser_hostname')],validation_method:'DNS',lifecycle:{create_before_destroy:true}});
 add('aws_route53_record',n+'_certificate',{for_each:{api:l('api_hostname'),parser:l('parser_hostname')},zone_id:zone,...Object.fromEntries([['name','resource_record_name'],['type','resource_record_type']].map(([key,attribute])=>[key,'${one([for dvo in aws_acm_certificate.'+n+'.domain_validation_options : dvo.'+attribute+' if dvo.domain_name == each.value])}'])),records:['${one([for dvo in aws_acm_certificate.'+n+'.domain_validation_options : dvo.resource_record_value if dvo.domain_name == each.value])}'],ttl:60,allow_overwrite:false});
 add('aws_acm_certificate_validation',n,{certificate_arn:r('aws_acm_certificate',n,'arn'),validation_record_fqdns:'${[for record in aws_route53_record.'+n+'_certificate : record.fqdn]}'});
 add('aws_route53_zone',n+'_parser',{name:l('parser_zone'),vpc:{vpc_id:r('aws_vpc',n,'id')}});
 for(const purpose of ['api','parser']){
  add('aws_lb',n+'_'+purpose,{name:l('name')+'-'+purpose,internal:purpose==='parser',load_balancer_type:'application',security_groups:[r('aws_security_group',n+'_'+purpose+'_lb','id')],subnets:purpose==='api'?publicSubnets:privateSubnets,idle_timeout:150,drop_invalid_header_fields:true,enable_deletion_protection:true});
  add('aws_lb_target_group',n+'_'+purpose,{name:l('name')+'-'+purpose,port:8080,protocol:'HTTP',target_type:'ip',vpc_id:r('aws_vpc',n,'id'),deregistration_delay:120,health_check:{enabled:true,path:'/healthz',protocol:'HTTP',port:'traffic-port',matcher:'200',interval:30,timeout:5,healthy_threshold:2,unhealthy_threshold:3}});
  add('aws_lb_listener',n+'_'+purpose,{load_balancer_arn:r('aws_lb',n+'_'+purpose,'arn'),port:443,protocol:'HTTPS',ssl_policy:'ELBSecurityPolicy-TLS13-1-2-2021-06',certificate_arn:r('aws_acm_certificate_validation',n,'certificate_arn'),default_action:{type:'forward',target_group_arn:r('aws_lb_target_group',n+'_'+purpose,'arn')}});
  add('aws_route53_record',n+'_'+purpose,{zone_id:purpose==='api'?zone:r('aws_route53_zone',n+'_parser','zone_id'),name:l(purpose==='api'?'api_hostname':'parser_hostname'),type:'A',alias:{name:r('aws_lb',n+'_'+purpose,'dns_name'),zone_id:r('aws_lb',n+'_'+purpose,'zone_id'),evaluate_target_health:true}});
 }
 add('aws_ecs_cluster',n,{name:l('name'),setting:{name:'containerInsights',value:'enabled'}});
 const common={REGION:region,ACCOUNT_ID:l('account_uuid'),WORKFLOW_NAMESPACE:'invoice',DATABASE_NAME:'invoice',DATABASE_HOST:r('aws_db_instance',n,'address'),DATABASE_CA_FILE:'/app/rds-global-ca.pem',DOCUMENT_BUCKET:bucket,AWS_ACCOUNT_ID:account,DESTINATION_CONTRACT_BASE64:l('destination_contract_base64')};
 for(const purpose of ['api','worker','parser']){
  const image=purpose==='parser'?v('parser_image'):v('runtime_image'),settings=purpose==='parser'?{PORT:'8080'}:purpose==='api'?{...common,DATABASE_USER:l('api_db_user'),PUBLIC_ORIGIN:l('public_origin'),POOL_ID:r('aws_cognito_user_pool',n,'id'),CLIENT_ID:r('aws_cognito_user_pool_client',n,'id'),AUTH_ORIGIN:'https://'+r('aws_cognito_user_pool_domain',n,'domain')+'.auth.'+region+'.amazoncognito.com',AUTH_SCOPE:l('name')+'/process'}:{...common,DATABASE_USER:l('worker_db_user'),PARSER_ENDPOINT:l('parser_endpoint'),MODEL_ID:model,MAX_OUTPUT_TOKENS:'2048',DESTINATION_ENDPOINT:endpoint,DESTINATION_SCOPE:scope,DESTINATION_REPLAY_REVIEW_BASE64:v('replay_review_base64')};
  const container={name:purpose,image,essential:true,readonlyRootFilesystem:true,portMappings:[{containerPort:8080,protocol:'tcp'}],environment:Object.entries(settings).map(([name,value])=>({name,value})),mountPoints:[{sourceVolume:'runtime-tmp',containerPath:'/tmp',readOnly:false}],dependsOn:[{containerName:'prepare-tmp',condition:'SUCCESS'}],logConfiguration:{logDriver:'awslogs',options:{'awslogs-group':r('aws_cloudwatch_log_group',n+'_'+purpose,'name'),'awslogs-region':region,'awslogs-stream-prefix':purpose}},...(purpose==='api'?{}:{command:['python','-I','/app/'+(purpose==='worker'?'invoice_worker.py':'invoice_parser_service.py')]}),...(purpose==='worker'?{secrets:[{name:'DESTINATION_TOKEN',valueFrom:r('aws_secretsmanager_secret',n+'_destination','arn')}]}:{})};
  const init={name:'prepare-tmp',image,essential:false,user:'0:0',readonlyRootFilesystem:true,command:['python','-I','-c','import os;os.chmod("/runtime-tmp",0o1777)'],mountPoints:[{sourceVolume:'runtime-tmp',containerPath:'/runtime-tmp',readOnly:false}]};
  add('aws_ecs_task_definition',n+'_'+purpose,{count:'${var.applications_enabled ? 1 : 0}',family:l('name')+'-'+purpose,network_mode:'awsvpc',requires_compatibilities:['FARGATE'],cpu:purpose==='parser'?'1024':'512',memory:purpose==='parser'?'2048':'1024',execution_role_arn:r('aws_iam_role',n+'_'+purpose+'_execution','arn'),...(purpose!=='parser'?{task_role_arn:r('aws_iam_role',n+'_'+purpose,'arn')}:{}),volume:{name:'runtime-tmp'},runtime_platform:{operating_system_family:'LINUX',cpu_architecture:'X86_64'},container_definitions:JSON.stringify([init,container]),depends_on:['aws_iam_role_policy.'+n+'_'+purpose+'_execution',...(purpose!=='parser'?['aws_iam_role_policy.'+n+'_'+purpose]:[])]});
  add('aws_ecs_service',n+'_'+purpose,{count:'${var.applications_enabled ? 1 : 0}',name:l('name')+'-'+purpose,cluster:r('aws_ecs_cluster',n,'id'),task_definition:r('aws_ecs_task_definition',n+'_'+purpose+'[0]','arn'),desired_count:1,launch_type:'FARGATE',platform_version:'1.4.0',deployment_circuit_breaker:{enable:true,rollback:true},network_configuration:{subnets:privateSubnets,security_groups:[r('aws_security_group',n+'_'+purpose,'id')],assign_public_ip:false},...(purpose!=='worker'?{load_balancer:{target_group_arn:r('aws_lb_target_group',n+'_'+purpose,'arn'),container_name:purpose,container_port:8080},health_check_grace_period_seconds:90}:{}),depends_on:['aws_lb_listener.'+n+'_api','aws_lb_listener.'+n+'_parser','aws_route_table_association.'+n+'_private_0','aws_route_table_association.'+n+'_private_1']});
 }
 b.output.application_url={value:l('public_origin')};b.output.runtime_repository={value:r('aws_ecr_repository',n+'_runtime','repository_url')};b.output.parser_repository={value:r('aws_ecr_repository',n+'_parser','repository_url')};b.output.account_identity={value:l('account_uuid')};
 b.output.operator_deployment={value:{provider:'aws',deploymentId:l('account_uuid'),accountId:l('account_uuid'),namespace:'invoice',tenantId:null,bindings:Object.fromEntries(['api','worker'].map(purpose=>[purpose,{name:l(purpose+'_db_user'),principal:r('aws_iam_role',n+'_'+purpose,'arn')}]))}};
 awsInvoiceOperations(b,n,{account,region,privateSubnets,trust});
 b.output.database_bootstrap={value:{host:r('aws_db_instance',n,'address'),database:'invoice',adminSecretArn:r('aws_db_instance',n,'master_user_secret[0].secret_arn'),apiRole:l('api_db_user'),workerRole:l('worker_db_user'),apiPrincipal:r('aws_iam_role',n+'_api','arn'),workerPrincipal:r('aws_iam_role',n+'_worker','arn'),destinationSecretArn:r('aws_secretsmanager_secret',n+'_destination','arn')}};
 b.assertions.push(`run "private_database_and_parser" {\n command = plan\n assert {\n condition = aws_db_instance.${n}.publicly_accessible == false && aws_db_instance.${n}.iam_database_authentication_enabled && aws_db_instance.${n}.storage_encrypted && aws_lb.${n}_parser.internal\n error_message = "Database and parser must retain their private, encrypted and IAM boundaries."\n }\n assert {\n condition = aws_ecs_task_definition.${n}_parser[0].task_role_arn == null\n error_message = "Parser must not inherit application data/model authority."\n }\n}\nrun "foundation_only" {\n command = plan\n variables {\n applications_enabled = false\n operations_enabled = false\n maintenance_enabled = false\n }\n assert {\n condition = length(aws_ecs_service.${n}_api) == 0 && length(aws_ecs_service.${n}_worker) == 0 && length(aws_ecs_service.${n}_parser) == 0\n error_message = "Bootstrap and publication must precede application release."\n }\n}`);
 b.assertions.push(`run "foreign_image_rejected" {\n command = plan\n variables { runtime_image = "123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/foreign@sha256:${'a'.repeat(64)}" }\n expect_failures = [terraform_data.review_gate]\n}\nrun "mutable_image_rejected" {\n command = plan\n variables { runtime_image = "unreviewed:latest" }\n expect_failures = [var.runtime_image]\n}\nrun "foreign_account_rejected" {\n command = plan\n variables {\n account_id = "999999999999"\n applications_enabled = false\n operations_enabled = false\n maintenance_enabled = false\n }\n expect_failures = [terraform_data.review_gate]\n}\n`);
 const mock='mock_provider "aws" {\n override_during = plan\n mock_resource "aws_iam_role" { defaults = { arn="arn:aws:iam::123456789012:role/owned-fixture" } }\n override_resource {\n target = aws_iam_role.'+n+'_api\n values = { arn="arn:aws:iam::123456789012:role/owned-api-fixture" }\n }\n override_resource {\n target = aws_iam_role.'+n+'_worker\n values = { arn="arn:aws:iam::123456789012:role/owned-worker-fixture" }\n }\n mock_resource "aws_s3_bucket" { defaults = { id="fixture-invoices",arn="arn:aws:s3:::fixture-invoices" } }\n mock_resource "aws_secretsmanager_secret" { defaults = { arn="arn:aws:secretsmanager:ap-southeast-2:123456789012:secret:owned-destination-fixture" } }\n mock_resource "aws_db_instance" { defaults = { address = "fixture.abcdef.ap-southeast-2.rds.amazonaws.com", master_user_secret = [{secret_arn="arn:aws:secretsmanager:ap-southeast-2:123456789012:secret:owned-operator-fixture",kms_key_id="owned-native-key",secret_status="active"}] } }\n mock_resource "aws_cognito_user_pool" { defaults = { id = "ap-southeast-2_Fixture" } }\n mock_resource "aws_cognito_user_pool_client" { defaults = { id = "fixtureclient123" } }\n mock_data "aws_caller_identity" { defaults = { account_id = "123456789012" } }\n mock_data "aws_availability_zones" { defaults = { names = ["ap-southeast-2a","ap-southeast-2b"] } }\n mock_data "aws_route53_zone" { defaults = { name = "example.test.",private_zone = false } }\n}\n';
 return b.finish({aws:{region,allowed_account_ids:[account]}},{aws:{source:'hashicorp/aws',version:'6.72.0'}},CLOUD_PROVIDER_LOCKS.aws,mock,AWS_INVOICE_GUIDE);
}

export const AWS_INVOICE_GUIDE=`# AWS invoice workflow infrastructure

New private VPC/subnets, regional NAT, IAM-authenticated Multi-AZ PostgreSQL 17,
private versioned invoice bucket, invited/MFA Cognito users, separate API/worker
roles, a role-free isolated parser task, ECR repositories and regional TLS ingress.
The public Route53 zone and external accounting system remain existing references.

Run foundation first with applications_enabled=false. Build/scan/publish the exact
emitted runtime/parser images only after authorization. Bootstrap SQL logins/grants,
schema using the emitted fixed operator initialize task, then admit verified staff
memberships with the separate operator CLI; populate the
accounting secret outside Terraform state/source. Then review a plan enabling the
application release with operations_enabled=true and maintenance_enabled=true.
Native platform secret injection becomes a private temporary
file; credential rotation requires an explicit workload rollout. Never put secret
values in tfvars, source, build context or command arguments.

Parser ingress is private HTTPS restricted to the worker security group. TLS ends
at its internal regional ALB; the target HTTP hop is inside restricted private
security groups. The parser has no task IAM role, data/model grant, secret injection
or outbound security-group rule. A short trusted root init container prepares only
the ephemeral temporary volume; processing containers retain nonroot image users.
No Docker daemon is installed in the worker. Verify actual platform isolation and
effective inherited IAM in an authorized staging environment before production.

The storage lifecycle expires current originals after 90 days and noncurrent
versions after one additional day; physical provider deletion is asynchronous.
Application payload access expires independently of physical cleanup. The emitted
OPERATIONS.md and invoice_operator.py implement scoped audit cleanup, restored
delivery quarantine and explicit completion reconciliation. Fixed Fargate operator
tasks, daily expired-only cleanup and hourly count-only monitoring are emitted;
review their existing same-account SNS alert route and verify its subscribed
notification/publish policy before release. Scheduler delivery failures and stopped
operator failures reach a private encrypted queue; missing successful receipts also
alarm. No accounting/model/object/task IAM role is given to an operator container.
The platform execution role can fetch only the managed RDS admin secret password,
owned image and logs. Bootstrap is manual and never scheduled. Native operating
checks and alert delivery remain destination acceptance steps. Seven-day encrypted database backups may
contain older data; review the stated backup/retention policy before deployment.
No static/mock check establishes an exact deletion deadline or cloud restore.

The single NAT, ALBs, managed database and continuously running tasks have fixed
cost drivers. Review actual regional rates, service/model availability and quotas;
no invented quote, price cap, throughput/latency SLA or deployment claim is made.
Infrastructure emission remains under qualification until the complete project,
operations, native account inputs and original full business brief are checked.
`;
