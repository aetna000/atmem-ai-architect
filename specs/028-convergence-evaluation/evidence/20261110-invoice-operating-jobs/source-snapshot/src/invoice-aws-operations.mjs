import{v,r,l}from'./invoice-builder.mjs';

// Fixed native jobs, not Terraform provisioners or API/model-accessible tools.
export function awsInvoiceOperations(b,n,{account,region,privateSubnets,trust}){
 const{add,input}=b;
 for(const key of ['operations_enabled','maintenance_enabled']){b.variable[key]={type:'bool',default:false,description:key==='operations_enabled'?'Publish the reviewed runtime image, then create fixed operator task definitions before application release.':'Enable only after successful owned SQL bootstrap and membership admission. Starts daily cleanup/hourly monitoring.'};b.examples[key]=false;b.testExpressions[key]='true';}
 const alert=input('operator_alert_topic_arn','Existing reviewed same-account regional SNS alert topic. Its owner must authorize CloudWatch publishing and verify an actual subscribed on-call route; this package does not modify that existing policy.','arn:aws:sns:'+b.examples.region+':123456789012:reviewed-operations','^arn:aws:sns:[a-z0-9-]+:[0-9]{12}:[A-Za-z0-9_-]{1,256}$');
 b.resource.terraform_data.review_gate.lifecycle.precondition.push({condition:'${!var.maintenance_enabled || var.operations_enabled}',error_message:'Maintenance requires the separate operator tasks.'},{condition:'${!var.applications_enabled || (var.operations_enabled && var.maintenance_enabled)}',error_message:'Bootstrap owned SQL and staff access, then enable the operating jobs before application release.'},{condition:'${startswith(var.operator_alert_topic_arn,format("arn:aws:sns:%s:%s:",var.region,var.account_id))}',error_message:'Use the reviewed existing alert route in this account and region.'});
 b.locals.operator_deployment=b.output.operator_deployment.value;
 add('aws_security_group',n+'_operator',{name_prefix:l('name')+'-operator-',description:'Separate fixed operator jobs: private SQL and native image/secret/log transport',vpc_id:r('aws_vpc',n,'id')});
 add('aws_vpc_security_group_ingress_rule',n+'_database_from_operator',{security_group_id:r('aws_security_group',n+'_database','id'),ip_protocol:'tcp',from_port:5432,to_port:5432,referenced_security_group_id:r('aws_security_group',n+'_operator','id')});
 for(const [suffix,port,target]of[['sql',5432,{referenced_security_group_id:r('aws_security_group',n+'_database','id')}],['native_https',443,{cidr_ipv4:'0.0.0.0/0'}]])add('aws_vpc_security_group_egress_rule',n+'_operator_'+suffix,{security_group_id:r('aws_security_group',n+'_operator','id'),ip_protocol:'tcp',from_port:port,to_port:port,...target});
 add('aws_cloudwatch_log_group',n+'_operator',{name:'/ecs/'+l('name')+'/operator',retention_in_days:7});
 add('aws_iam_role',n+'_operator_execution',{name:l('name')+'-operator-execution',assume_role_policy:trust});
 const secret=r('aws_db_instance',n,'master_user_secret[0].secret_arn');
 add('aws_iam_role_policy',n+'_operator_execution',{role:r('aws_iam_role',n+'_operator_execution','id'),policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Action:['ecr:GetAuthorizationToken'],Resource:'*'},{Effect:'Allow',Action:['ecr:BatchGetImage','ecr:GetDownloadUrlForLayer','ecr:BatchCheckLayerAvailability'],Resource:r('aws_ecr_repository',n+'_runtime','arn')},{Effect:'Allow',Action:['logs:CreateLogStream','logs:PutLogEvents'],Resource:r('aws_cloudwatch_log_group',n+'_operator','arn')+':*'},{Effect:'Allow',Action:['secretsmanager:GetSecretValue'],Resource:secret}]})});
 const settings={REGION:region,DATABASE_NAME:'invoice',DATABASE_HOST:r('aws_db_instance',n,'address'),DATABASE_USER:'invoice_operator',DATABASE_CA_FILE:'/app/rds-global-ca.pem',OPERATOR_DEPLOYMENT_BASE64:'${base64encode(jsonencode(local.operator_deployment))}'};
 for(const action of ['initialize','maintain','monitor']){
  const init={name:'prepare-tmp',image:v('runtime_image'),essential:false,user:'0:0',readonlyRootFilesystem:true,command:['python','-I','-c','import os;os.chmod("/runtime-tmp",0o1777)'],mountPoints:[{sourceVolume:'runtime-tmp',containerPath:'/runtime-tmp',readOnly:false}]};
  const container={name:'operator',image:v('runtime_image'),essential:true,readonlyRootFilesystem:true,command:['python','-I','/app/invoice_operator_job.py',action,'--execute'],environment:Object.entries(settings).map(([name,value])=>({name,value})),secrets:[{name:'DATABASE_PASSWORD',valueFrom:secret+':password::'}],mountPoints:[{sourceVolume:'runtime-tmp',containerPath:'/tmp',readOnly:false}],dependsOn:[{containerName:'prepare-tmp',condition:'SUCCESS'}],logConfiguration:{logDriver:'awslogs',options:{'awslogs-group':r('aws_cloudwatch_log_group',n+'_operator','name'),'awslogs-region':region,'awslogs-stream-prefix':action}}};
  add('aws_ecs_task_definition',n+'_operator_'+action,{count:'${var.operations_enabled ? 1 : 0}',family:l('name')+'-'+action,network_mode:'awsvpc',requires_compatibilities:['FARGATE'],cpu:'512',memory:'1024',execution_role_arn:r('aws_iam_role',n+'_operator_execution','arn'),volume:{name:'runtime-tmp'},runtime_platform:{operating_system_family:'LINUX',cpu_architecture:'X86_64'},container_definitions:JSON.stringify([init,container]),depends_on:['aws_iam_role_policy.'+n+'_operator_execution']});
 }
 add('aws_sqs_queue',n+'_operator_failures',{name:l('name')+'-operator-failures',sqs_managed_sse_enabled:true,message_retention_seconds:604800,visibility_timeout_seconds:60,lifecycle:{prevent_destroy:true}});
 add('aws_scheduler_schedule_group',n+'_operator',{name:l('name')+'-operator'});
 add('aws_iam_role',n+'_operator_scheduler',{count:'${var.operations_enabled ? 1 : 0}',name:l('name')+'-operator-scheduler',assume_role_policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Principal:{Service:'scheduler.amazonaws.com'},Action:'sts:AssumeRole',Condition:{StringEquals:{'aws:SourceAccount':account},ArnEquals:{'aws:SourceArn':r('aws_scheduler_schedule_group',n+'_operator','arn')}}}]})});
 add('aws_iam_role_policy',n+'_operator_scheduler',{count:'${var.operations_enabled ? 1 : 0}',role:r('aws_iam_role',n+'_operator_scheduler[0]','id'),policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Action:['ecs:RunTask'],Resource:['maintain','monitor'].map(action=>r('aws_ecs_task_definition',n+'_operator_'+action+'[0]','arn')),Condition:{ArnEquals:{'ecs:cluster':r('aws_ecs_cluster',n,'arn')}}},{Effect:'Allow',Action:['iam:PassRole'],Resource:r('aws_iam_role',n+'_operator_execution','arn'),Condition:{StringEquals:{'iam:PassedToService':'ecs-tasks.amazonaws.com'}}},{Effect:'Allow',Action:['sqs:SendMessage'],Resource:r('aws_sqs_queue',n+'_operator_failures','arn')}]})});
 for(const[action,expression]of[['maintain','cron(17 2 * * ? *)'],['monitor','rate(1 hour)']]){
  add('aws_scheduler_schedule',n+'_'+action,{count:'${var.operations_enabled ? 1 : 0}',name:l('name')+'-'+action,group_name:r('aws_scheduler_schedule_group',n+'_operator','name'),state:'${var.maintenance_enabled ? "ENABLED" : "DISABLED"}',schedule_expression:expression,schedule_expression_timezone:'UTC',flexible_time_window:{mode:'OFF'},target:{arn:r('aws_ecs_cluster',n,'arn'),role_arn:r('aws_iam_role',n+'_operator_scheduler[0]','arn'),ecs_parameters:{task_definition_arn:r('aws_ecs_task_definition',n+'_operator_'+action+'[0]','arn'),launch_type:'FARGATE',platform_version:'1.4.0',task_count:1,enable_execute_command:false,network_configuration:{subnets:privateSubnets,security_groups:[r('aws_security_group',n+'_operator','id')],assign_public_ip:false}},dead_letter_config:{arn:r('aws_sqs_queue',n+'_operator_failures','arn')},retry_policy:{maximum_event_age_in_seconds:3600,maximum_retry_attempts:2}},depends_on:['aws_iam_role_policy.'+n+'_operator_scheduler','aws_route_table_association.'+n+'_private_0','aws_route_table_association.'+n+'_private_1']});
  add('aws_cloudwatch_log_metric_filter',n+'_'+action+'_success',{name:l('name')+'-'+action+'-success',log_group_name:r('aws_cloudwatch_log_group',n+'_operator','name'),pattern:'{ $.format = "invoice-operator-v1" && $.action = "'+action+'" && $.status = "ok" }',metric_transformation:{name:l('name')+'-'+action+'-success',namespace:'AtMem/InvoiceOperations',value:'1',default_value:0,unit:'Count'}});
  add('aws_cloudwatch_metric_alarm',n+'_'+action+'_missing',{alarm_name:l('name')+'-'+action+'-missing',alarm_description:'No successful '+action+' receipt in two operating periods. Inspect owned operator task logs and failed-job queue; no payload is in the count-only receipt.',namespace:'AtMem/InvoiceOperations',metric_name:l('name')+'-'+action+'-success',statistic:'Sum',period:action==='maintain'?86400:3600,evaluation_periods:2,datapoints_to_alarm:2,threshold:1,comparison_operator:'LessThanThreshold',treat_missing_data:'breaching',actions_enabled:v('maintenance_enabled'),alarm_actions:[alert],ok_actions:[alert]});
 }
 const taskArns=['initialize','maintain','monitor'].map(action=>r('aws_ecs_task_definition',n+'_operator_'+action+'[0]','arn'));
 add('aws_cloudwatch_event_rule',n+'_operator_stopped',{count:'${var.operations_enabled ? 1 : 0}',name:l('name')+'-operator-stopped',event_pattern:JSON.stringify({source:['aws.ecs'],'detail-type':['ECS Task State Change'],detail:{clusterArn:[r('aws_ecs_cluster',n,'arn')],taskDefinitionArn:taskArns,lastStatus:['STOPPED'],$or:[{stopCode:['TaskFailedToStart']},{containers:{name:['operator'],exitCode:[{'anything-but':0}]}}]}})});
 add('aws_sqs_queue_policy',n+'_operator_failures',{count:'${var.operations_enabled ? 1 : 0}',queue_url:r('aws_sqs_queue',n+'_operator_failures','id'),policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Principal:{Service:'events.amazonaws.com'},Action:'sqs:SendMessage',Resource:r('aws_sqs_queue',n+'_operator_failures','arn'),Condition:{ArnEquals:{'aws:SourceArn':r('aws_cloudwatch_event_rule',n+'_operator_stopped[0]','arn')},StringEquals:{'aws:SourceAccount':account}}}]})});
 add('aws_cloudwatch_event_target',n+'_operator_stopped',{count:'${var.operations_enabled ? 1 : 0}',rule:r('aws_cloudwatch_event_rule',n+'_operator_stopped[0]','name'),arn:r('aws_sqs_queue',n+'_operator_failures','arn'),input:JSON.stringify({format:'invoice-operator-v1',status:'failed',code:'operator_task_stopped'}),depends_on:['aws_sqs_queue_policy.'+n+'_operator_failures']});
 add('aws_cloudwatch_metric_alarm',n+'_operator_failures',{alarm_name:l('name')+'-operator-failed',alarm_description:'Operator task or schedule invocation failed. Inspect task logs and the private failed-job queue before retrying.',namespace:'AWS/SQS',metric_name:'ApproximateNumberOfMessagesVisible',dimensions:{QueueName:r('aws_sqs_queue',n+'_operator_failures','name')},statistic:'Maximum',period:300,evaluation_periods:1,threshold:0,comparison_operator:'GreaterThanThreshold',treat_missing_data:'notBreaching',actions_enabled:v('operations_enabled'),alarm_actions:[alert]});
 b.output.operator_jobs={value:{cluster:r('aws_ecs_cluster',n,'arn'),privateSubnets,securityGroups:[r('aws_security_group',n+'_operator','id')],taskDefinitions:Object.fromEntries(['initialize','maintain','monitor'].map(action=>[action,'${try(aws_ecs_task_definition.'+n+'_operator_'+action+'[0].arn,null)}'])),failedJobQueue:r('aws_sqs_queue',n+'_operator_failures','id'),alertTopic:alert}};
 b.output.operator_bootstrap_request={value:{cluster:r('aws_ecs_cluster',n,'arn'),taskDefinition:'${try(aws_ecs_task_definition.'+n+'_operator_initialize[0].arn,null)}',launchType:'FARGATE',platformVersion:'1.4.0',count:1,enableExecuteCommand:false,networkConfiguration:{awsvpcConfiguration:{subnets:privateSubnets,securityGroups:[r('aws_security_group',n+'_operator','id')],assignPublicIp:'DISABLED'}}}};
 b.files['OPERATING_JOBS.md']=AWS_OPERATING_JOBS;
 b.assertions.push(`run "operator_before_applications" {
 command = plan
 variables {
 applications_enabled = false
 maintenance_enabled = false
 }
 assert {
 condition = length(aws_ecs_task_definition.${n}_operator_initialize) == 1 && length(aws_ecs_service.${n}_api) == 0 && aws_scheduler_schedule.${n}_maintain[0].state == "DISABLED" && aws_ecs_task_definition.${n}_operator_monitor[0].task_role_arn == null
 error_message = "Fixed bootstrap tasks precede application release; schedules remain stopped and no task role is conferred."
 }
}

run "operating_jobs_required" {
 command = plan
 variables {
 operations_enabled = false
 maintenance_enabled = false
 }
 expect_failures = [terraform_data.review_gate]
}
run "operator_mutable_image_rejected" {
 command = plan
 variables {
 applications_enabled = false
 maintenance_enabled = false
 runtime_image = "unreviewed:latest"
 }
 expect_failures = [var.runtime_image]
}
`);
}

const AWS_OPERATING_JOBS=`# Fixed AWS invoice operating jobs

These are generated definitions and commands, not evidence of a deployed service.
Obtain destination authorization before apply, publication or RunTask. Keep an
existing reviewed same-account regional SNS topic in operator_alert_topic_arn.
Its owner must authorize CloudWatch publishing and verify an actual subscribed
on-call route. If encrypted, the topic must use a compatible customer-managed KMS
key whose policy admits CloudWatch; the default alias/aws/sns key is not sufficient. This package does not adopt or modify the existing topic/policy.

1. Foundation: applications_enabled=false, operations_enabled=false,
   maintenance_enabled=false. Review/apply only when authorized; publish the
   scanned immutable runtime and parser images to the emitted ECR repositories.
2. Bootstrap definitions: operations_enabled=true, applications_enabled=false,
   maintenance_enabled=false, runtime_image set to the owned immutable digest.
   This creates fixed tasks and disabled schedules; it does not execute SQL.
3. From the authorized foundation state, write the nonsecret bootstrap request:

       terraform output -json operator_bootstrap_request > .local/bootstrap.json
       aws ecs run-task --cli-input-json file://.local/bootstrap.json

   Use the same reviewed AWS account/region. Retain the returned task ARN, wait
   for STOPPED and check operator exitCode=0 plus an initialized:true receipt in
   the initialize log stream. A successful RunTask response alone only admits
   scheduling; it does not prove SQL initialization. Failed start/nonzero exit
   events reach the private operator-failures queue. No task role, accounting
   credential, model or object authority is conferred on the operator container.
   The execution role resolves only the managed RDS admin password field, image
   and logs. The connection verifies the regional RDS CA/hostname. SQL transactions
   and an advisory lock protect owned retries; existing passwords are preserved.
4. Invite verified Cognito users and admit explicit application roles through
   invoice_operator.py membership as described in OPERATIONS.md. No invitation
   or sign-in silently grants reviewer/owner authority. Populate the accounting
   secret outside Terraform/source. Retain native membership/denial checks.
5. Release: applications_enabled=true, operations_enabled=true,
   maintenance_enabled=true. The review gate refuses application release without
   the operating definitions/schedules enabled. This flag does not prove step 3
   or 4 ran: retain their actual destination receipts before approving release.

Daily maintenance runs at 02:17 UTC. It removes at most twenty batches of 500
expired SQL operations, with separate transactions and exact account/namespace
ownership. Live execution jobs/leases refuse deletion. Table locks serialize
concurrent submissions, preserving new/young operations. Remaining backlog returns
nonzero; retry after inspecting count-only logs. Object lifecycle expiry remains
independent and asynchronous. No scheduler IAM role can launch the bootstrap task.

Hourly monitoring uses a read-only SQL transaction and emits scoped state counts.
Pending/approved work unchanged for two hours, expired execution leases, dead or
unknown outcomes and records overdue for cleanup by two days need attention.
These are operational starting thresholds, not a promised throughput/latency SLA.
Both jobs have a 15-minute process deadline; SQL waits/statements are bounded.

Scheduler invocation failures go to the encrypted seven-day failure queue with
bounded retries. Task failed-to-start/nonzero operator exits also reach that queue;
this matters because RunTask acceptance is not application success. Queue alarms
and missing-success-receipt alarms publish to the reviewed existing SNS topic.
Daily/hourly heartbeat alarms breach after two missing periods. Bootstrap failures
alarm as well; no bootstrap is scheduled. Operator logs retain seven days and do
not include document data, subjects, amounts or SQL/password exception text.

Test alert delivery, stopped-task routing, missed schedules, private SQL/TLS,
native secret rotation and effective IAM in an authorized destination. Cloud
availability, notification delivery and managed restore remain unverified by local
schema/mocks. Keep restore/quarantine/reconciliation isolated and explicitly paused;
daily cleanup does not authorize replaying uncertain external accounting effects.
`;
