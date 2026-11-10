import test from'node:test';
import assert from'node:assert/strict';
import {invoiceApplicationFiles}from'../src/invoice-application.mjs';
import {invoiceDependencies}from'../src/invoice-dependencies.mjs';
import {pythonContainer}from'../src/python-container.mjs';
import {createHash}from'node:crypto';
import {awsInvoiceTerraform}from'../src/invoice-aws.mjs';
import {azureInvoiceTerraform}from'../src/invoice-azure.mjs';
import {gcpInvoiceTerraform}from'../src/invoice-gcp.mjs';
import {ibmInvoiceTerraform}from'../src/invoice-ibm.mjs';

test('every emitted invoice application contains its local runtime import closure and private parser source',()=>{
 for(const provider of ['aws','azure','gcp','ibm']){
  const root='applications/block_696e766f696365/',files=invoiceApplicationFiles(provider,'block_696e766f696365');
  assert.equal(JSON.parse(files[root+'invoice-deployment.json']).provider,provider);
  for(const[name,source]of Object.entries(files))if(name.startsWith(root)&&name.endsWith('.py')){
   const folder=name.slice(0,name.lastIndexOf('/')+1);
   for(const match of source.matchAll(/^from ([a-z_][a-z_0-9]*) import /gm))if(/^(?:invoice_|workflow_|durable_workflow$|approved_http_destination$|structured_|policy_review$|aws_json_model$|azure_structured$|gcp_structured$|ibm_structured$)/.test(match[1]))assert.ok(files[folder+match[1]+'.py'],'Missing '+match[1]+' imported by '+name);
  }
  assert.ok(files[root+'workflow_schema.sql']);assert.ok(files[root+'invoice_runtime_secrets.py']);assert.match(files[root+'Dockerfile'],/"--limit-concurrency", "32"/);assert.doesNotMatch(files[root+'Dockerfile'],/COPY web\//);
  assert.ok(files[root+'parser/invoice_parser_service.py']);assert.match(files[root+'parser/Dockerfile'],/USER 10001:10001/);
 }
});
test('invoice dependency unions retain strict pins, hashes and explicit IBM compatibility decision',()=>{
 for(const provider of ['aws','azure','gcp','ibm']){
  const lock=invoiceDependencies(provider),testing=invoiceDependencies(provider,{tests:true});assert.match(lock.requirements,/psycopg==3\.3\.8/);assert.match(lock.requirements,/procrastinate==3\.10\.0/);assert.match(testing.requirements,/httpx==0\.28\.1/);
  assert.ok(lock.sources.every(source=>source.metadataSha256));assert.equal(lock.resolutions.length,provider==='ibm'?1:0);
  if(provider==='ibm'){assert.match(lock.requirements,/python-dateutil==3\.0\.0/);assert.doesNotMatch(lock.requirements,/boto3==/);}else assert.match(lock.requirements,/python-dateutil==2\.9\.0\.post0/);
 }
 assert.doesNotMatch(invoiceDependencies('aws').requirements,/mangum==/);
});
test('invoice emission rejects foreign provider/address rather than falling back',()=>{
 for(const provider of ['tools','other',''])assert.throws(()=>invoiceApplicationFiles(provider,'block_696e766f696365'));
 for(const address of ['../private','block_hello','${local.other}'])assert.throws(()=>invoiceApplicationFiles('aws',address));
});
test('shared container helper keeps existing defaults and rejects path/capacity overrides',()=>{
 const standard=pythonContainer('public_faq_app',['public_faq_app.py'],['faq-deployment.json']);assert.match(standard,/COPY output-contract.json/);assert.match(standard,/COPY web\//);assert.match(standard,/"--limit-concurrency", "16"/);
 for(const options of [{assets:['../secret.pem']},{assets:['private.key']},{concurrency:0},{concurrency:101},{web:'false'},{unknown:true}])assert.throws(()=>pythonContainer('invoice_native',['invoice_native.py'],[],options));
});
test('AWS invoice export contains the exact trusted database CA and functional operator source',()=>{
 const root='applications/block_696e766f696365/',files=invoiceApplicationFiles('aws','block_696e766f696365'),receipt=JSON.parse(files[root+'rds-ca-source.json']);
 assert.equal(createHash('sha256').update(files[root+'rds-global-ca.pem']).digest('hex'),receipt.sha256);assert.equal((files[root+'rds-global-ca.pem'].match(/BEGIN CERTIFICATE/g)||[]).length,receipt.certificates);
 assert.match(files[root+'Dockerfile'],/COPY .*rds-global-ca.pem/);assert.ok(files[root+'invoice_operator.py']);assert.ok(files[root+'invoice_operator_core.py']);assert.match(files[root+'Dockerfile'],/invoice_operator_core\.py/);assert.ok(files[root+'invoice_operations.py']);assert.ok(files[root+'invoice_retention.py']);
 for(const provider of['azure','gcp','ibm'])assert.equal(invoiceApplicationFiles(provider,'block_696e766f696365')[root+'rds-global-ca.pem'],undefined);
});
test('AWS infrastructure keeps parser authority, workload identities, immutable releases and existing DNS separate',()=>{
 const files=awsInvoiceTerraform({id:'11111111-1111-4111-8111-111111111111',revision:1,nodes:[],edges:[]},{id:'invoice',address:'block_696e766f696365',provider:'aws',region:'ap-southeast-2'}),config=JSON.parse(files['main.tf.json']),n='block_696e766f696365';
 assert.equal(config.resource.aws_db_instance[n].publicly_accessible,false);assert.equal(config.resource.aws_db_instance[n].iam_database_authentication_enabled,true);
 assert.equal(config.resource.aws_ecs_task_definition[n+'_parser'].task_role_arn,undefined);assert.notEqual(config.resource.aws_ecs_task_definition[n+'_api'].task_role_arn,config.resource.aws_ecs_task_definition[n+'_worker'].task_role_arn);
 assert.deepEqual(config.resource.aws_ecs_task_definition[n+'_parser'].depends_on,['terraform_data.review_gate','aws_iam_role_policy.'+n+'_parser_execution']);
 const parser=JSON.parse(config.resource.aws_ecs_task_definition[n+'_parser'].container_definitions).find(container=>container.name==='parser');assert.deepEqual(parser.environment,[{name:'PORT',value:'8080'}]);assert.equal(parser.secrets,undefined);
 assert.ok(Object.values(config.resource.aws_vpc_security_group_egress_rule).every(rule=>rule.security_group_id!=='${aws_security_group.'+n+'_parser.id}'));
 assert.equal(config.data.aws_route53_zone.destination.private_zone,false);assert.equal(Object.keys(config.resource.aws_route53_zone).length,1);assert.ok(config.output.operator_deployment);
 assert.match(files['OPERATIONS.md'],/quarantine-restore/);assert.match(files['tests/invoice.tftest.hcl'],/foreign_image_rejected/);assert.match(files['tests/invoice.tftest.hcl'],/mutable_image_rejected/);
 assert.equal(config.variable.applications_enabled.default,false);assert.ok(config.resource.terraform_data.review_gate.lifecycle.precondition.some(rule=>rule.error_message.includes('ECR')));
});
test('Azure invoice compiler isolates parser identity, data and native secrets without provider substitution',()=>{
 const n='block_696e766f696365',project={id:'11111111-1111-4111-8111-111111111111',revision:1,nodes:[],edges:[]},row={id:'invoice',address:n,provider:'azure',region:'australiaeast'},files=azureInvoiceTerraform(project,row),config=JSON.parse(files['main.tf.json']);
 assert.deepEqual(Object.keys(config.terraform.required_providers).sort(),['azapi','azuread','azurerm']);assert.equal(config.terraform.required_providers.azapi.version,'2.13.0');assert.ok(Object.keys(config.resource).every(type=>!/^aws_|^google_|^ibm_/.test(type)));
 const parser=config.resource.azapi_resource[n+'_parser'],api=config.resource.azapi_resource[n+'_api'],worker=config.resource.azapi_resource[n+'_worker'];
 assert.deepEqual(parser.identity.identity_ids,['${azurerm_user_assigned_identity.'+n+'_pull.id}']);assert.deepEqual(parser.body.properties.configuration.identitySettings,[{identity:'${azurerm_user_assigned_identity.'+n+'_pull.id}',lifecycle:'None'}]);
 const env=container=>Object.fromEntries(container.env.map(entry=>[entry.name,entry.value]));
 const parserEnv=env(parser.body.properties.template.containers[0]);assert.equal(parserEnv.PARSER_AUTH_MODE,'entra-workload');assert.equal(parserEnv.PARSER_WORKER_PRINCIPAL_ID,'${azurerm_user_assigned_identity.'+n+'_worker.principal_id}');assert.equal(parser.body.properties.configuration.ingress.external,false);
 assert.ok(Object.keys(parserEnv).every(key=>key==='PORT'||key.startsWith('PARSER_')));
 const apiEnv=env(api.body.properties.template.containers[0]);assert.equal(apiEnv.MODEL_RESOURCE_ID,undefined);assert.equal(apiEnv.DESTINATION_TOKEN,undefined);
 const workerContainer=worker.body.properties.template.containers[0];assert.deepEqual(workerContainer.env.find(entry=>entry.name==='DESTINATION_TOKEN'),{name:'DESTINATION_TOKEN',secretRef:'accounting-token'});assert.equal(worker.body.properties.configuration.secrets[0].value,undefined);assert.equal(config.resource.azurerm_key_vault_secret,undefined);
 assert.equal(config.resource.azurerm_postgresql_flexible_server[n].authentication.password_auth_enabled,false);assert.equal(config.resource.azurerm_storage_account[n].public_network_access_enabled,false);assert.equal(config.resource.azuread_application_app_role[n+'_parser'].value,'Parser.Invoke');
 assert.ok(config.resource.terraform_data.review_gate.lifecycle.precondition.every(rule=>!rule.condition.includes('azurerm_container_registry.')),'Review gate must not depend on resources that depend on the review gate');
 assert.throws(()=>azureInvoiceTerraform(project,{...row,provider:'gcp'}));
});
test('AWS fixed operating jobs have separate private admin authority and monitored schedules',()=>{
 const n='block_696e766f696365',files=awsInvoiceTerraform({id:'11111111-1111-4111-8111-111111111111',revision:1,nodes:[],edges:[]},{id:'invoice',address:n,provider:'aws',region:'ap-southeast-2'}),config=JSON.parse(files['main.tf.json']),resources=config.resource;
 for(const action of ['initialize','maintain','monitor']){
  const task=resources.aws_ecs_task_definition[n+'_operator_'+action],container=JSON.parse(task.container_definitions).find(row=>row.name==='operator');
  assert.equal(task.task_role_arn,undefined);assert.equal(task.network_mode,'awsvpc');assert.equal(container.readonlyRootFilesystem,true);assert.deepEqual(container.command,['python','-I','/app/invoice_operator_job.py',action,'--execute']);
  assert.ok(container.environment.every(row=>!row.name.startsWith('MODEL_')&&!row.name.startsWith('DESTINATION_')&&!row.name.startsWith('PARSER_')));assert.deepEqual(container.secrets.map(row=>row.name),['DATABASE_PASSWORD']);assert.match(container.secrets[0].valueFrom,/master_user_secret\[0\]\.secret_arn.*:password::$/);
 }
 const policy=JSON.parse(resources.aws_iam_role_policy[n+'_operator_execution'].policy),secretGrant=policy.Statement.find(row=>row.Action.includes('secretsmanager:GetSecretValue'));
 assert.match(secretGrant.Resource,/master_user_secret/);assert.ok(policy.Statement.every(row=>!row.Action.some(action=>/^(s3:|bedrock:|rds-db:)/.test(action))));
 const scheduler=JSON.parse(resources.aws_iam_role_policy[n+'_operator_scheduler'].policy),run=scheduler.Statement.find(row=>row.Action.includes('ecs:RunTask'));assert.equal(run.Resource.length,2);assert.ok(run.Resource.every(value=>!value.includes('_initialize')));assert.ok(run.Condition.ArnEquals['ecs:cluster']);
 const trust=JSON.parse(resources.aws_iam_role[n+'_operator_scheduler'].assume_role_policy);assert.match(trust.Statement[0].Condition.ArnEquals['aws:SourceArn'],/aws_scheduler_schedule_group/);
 for(const action of ['maintain','monitor']){const schedule=resources.aws_scheduler_schedule[n+'_'+action];assert.equal(schedule.target.ecs_parameters.network_configuration.assign_public_ip,false);assert.equal(schedule.target.ecs_parameters.enable_execute_command,false);assert.equal(schedule.target.retry_policy.maximum_retry_attempts,2);assert.ok(schedule.target.dead_letter_config.arn);assert.equal(resources.aws_cloudwatch_metric_alarm[n+'_'+action+'_missing'].treat_missing_data,'breaching');}
 assert.equal(resources.aws_scheduler_schedule[n+'_initialize'],undefined);assert.equal(resources.aws_sqs_queue[n+'_operator_failures'].sqs_managed_sse_enabled,true);
 assert.equal(resources.aws_cloudwatch_event_target[n+'_operator_stopped'].input,JSON.stringify({format:'invoice-operator-v1',status:'failed',code:'operator_task_stopped'}));
 const root='applications/'+n+'/';for(const name of ['invoice_operator_job.py','invoice_maintenance.py','invoice_configuration.py']){assert.ok(files[root+name]);assert.ok(files[root+'Dockerfile'].includes(name));}
});
test('AWS operating examples follow the selected region instead of retaining Sydney',()=>{
 const files=awsInvoiceTerraform({id:'11111111-1111-4111-8111-111111111111',revision:1,nodes:[],edges:[]},{id:'invoice',address:'block_696e766f696365',provider:'aws',region:'us-west-2'}),examples=JSON.parse(files['deployment.tfvars.json.example']);
 assert.equal(examples.region,'us-west-2');assert.ok(examples.operator_alert_topic_arn.startsWith('arn:aws:sns:us-west-2:'));
});
test('Azure operating jobs separate administrator identity and use explicit current diagnostic routing',()=>{
 const n='block_696e766f696365',files=azureInvoiceTerraform({id:'11111111-1111-4111-8111-111111111111',revision:1,nodes:[],edges:[]},{id:'invoice',address:n,provider:'azure',region:'australiaeast'}),config=JSON.parse(files['main.tf.json']),resources=config.resource;
 assert.equal(resources.azurerm_container_app_environment[n].logs_destination,'azure-monitor');const diagnostic=resources.azurerm_monitor_diagnostic_setting[n+'_environment'];assert.equal(diagnostic.log_analytics_destination_type,'Dedicated');assert.deepEqual(diagnostic.enabled_log.map(row=>row.category).sort(),['ContainerAppConsoleLogs','ContainerAppSystemLogs']);
 for(const action of ['initialize','maintain','monitor']){
  const job=resources.azapi_resource[n+'_operator_'+action],container=job.body.properties.template.containers[0];assert.equal(job.type,'Microsoft.App/jobs@2025-07-01');assert.deepEqual(job.identity.identity_ids,['${azurerm_user_assigned_identity.'+n+'_pull.id}','${azurerm_user_assigned_identity.'+n+'_operator.id}']);assert.deepEqual(container.command,['python','-I','/app/invoice_operator_job.py',action,'--execute']);
  assert.ok(container.env.every(row=>!row.secretRef&&!row.name.startsWith('MODEL_')&&!row.name.startsWith('DESTINATION_')&&!row.name.startsWith('DOCUMENT_')));
  assert.equal(container.env.find(row=>row.name==='WORKLOAD_IDENTITY_CLIENT_ID').value,'${azurerm_user_assigned_identity.'+n+'_operator.client_id}');assert.equal(job.body.properties.configuration.secrets,undefined);
 }
 assert.deepEqual(resources.azapi_resource[n+'_operator_initialize'].body.properties.configuration.identitySettings,[{identity:'${azurerm_user_assigned_identity.'+n+'_pull.id}',lifecycle:'None'},{identity:'${azurerm_user_assigned_identity.'+n+'_operator.id}',lifecycle:'Main'}]);
 assert.ok(Object.values(resources.azurerm_role_assignment).every(row=>!String(row.role_definition_name).includes('Container Apps')));
 for(const name of ['monitor-missing','maintain-missing','initialize-failed']){assert.ok(files['monitoring/'+name+'.kql'].includes('ContainerAppConsoleLogs'));assert.ok(!files['monitoring/'+name+'.kql'].includes('_CL'));}
 assert.match(files['monitoring/initialize-failed.kql'],/ContainerAppSystemLogs/);assert.match(files['OPERATING_JOBS.md'],/override image\/command\/env/);assert.match(files['tests/invoice.tftest.hcl'],/scheduled_jobs_and_log_validation/);
 assert.ok(config.output.operator_bootstrap_url.value.endsWith('-initialize/start?api-version=2025-07-01'));assert.ok(files['OPERATING_JOBS.md'].includes('terraform output -raw operator_bootstrap_url'));
});

test('Google invoice compiler binds private SQL proxy, CPU allocation and separate workload authorities',()=>{
 const n='block_696e766f696365',project={id:'11111111-1111-4111-8111-111111111111',revision:1,nodes:[],edges:[]},row={id:'invoice',address:n,provider:'gcp',region:'australia-southeast1'},files=gcpInvoiceTerraform(project,row),config=JSON.parse(files['main.tf.json']);
 const dependencyReview=JSON.parse(files['CLOUD_SQL_PROXY_SECURITY_REVIEW.json']);assert.equal(dependencyReview.platform,'linux/amd64');assert.equal(dependencyReview.status,'reviewed-not-affected-by-listed-findings');assert.equal(dependencyReview.findings.length,3);
 assert.deepEqual(Object.keys(config.terraform.required_providers).sort(),['google','google-beta']);assert.ok(Object.keys(config.resource).every(type=>!/^aws_|^azurerm_|^ibm_/.test(type)));
 const services=config.resource.google_cloud_run_v2_service,api=services[n+'_api'],worker=services[n+'_worker'],parser=services[n+'_parser'];
 assert.equal(api.iap_enabled,true);assert.equal(api.invoker_iam_disabled,false);assert.notEqual(api.template.service_account,worker.template.service_account);assert.notEqual(worker.template.service_account,parser.template.service_account);
 assert.equal(parser.template.containers.length,1);assert.deepEqual(parser.template.containers[0].env,[]);assert.equal(parser.template.vpc_access,undefined);
 for(const service of [api,worker]){
  const [app,proxy]=service.template.containers,env=Object.fromEntries(app.env.map(entry=>[entry.name,entry.value]));
  assert.equal(env.DATABASE_TRANSPORT,'cloudsql-private-proxy');assert.equal(env.DATABASE_SERVICE_ACCOUNT,service.template.service_account);assert.equal(app.resources.cpu_idle,false);assert.equal(service.template.scaling.min_instance_count,1);assert.deepEqual(app.depends_on,['cloud-sql-proxy']);assert.match(proxy.image,/@sha256:[0-9a-f]{64}$/);assert.equal(proxy.image,dependencyReview.imageIndex);assert.deepEqual(proxy.args.slice(0,4),['--private-ip','--address=127.0.0.1','--port=5432','--structured-logs']);
 }
 assert.ok(api.template.containers[0].env.every(entry=>!entry.value_source));assert.equal(worker.template.containers[0].env.filter(entry=>entry.value_source).length,1);
 assert.deepEqual(config.resource.google_sql_user[n+'_api'].database_roles,[]);assert.deepEqual(config.resource.google_sql_user[n+'_worker'].database_roles,[]);assert.deepEqual(config.resource.google_sql_user[n+'_ops'].database_roles,['cloudsqlsuperuser']);assert.equal(config.resource.google_sql_database_instance[n].settings.ip_configuration.ipv4_enabled,false);
 assert.equal(config.resource.google_cloud_run_v2_service_iam_member[n+'_parser'].member,'serviceAccount:${google_service_account.'+n+'_worker.email}');assert.throws(()=>gcpInvoiceTerraform(project,{...row,provider:'azure'}));
});

test('invoice deployments have stable environment-separated physical identities and matching image fixtures',()=>{
 const project={id:'11111111-1111-4111-8111-111111111111',revision:1,nodes:[],edges:[]},address='block_696e766f696365';
 for(const [provider,adapter,region]of [['aws',awsInvoiceTerraform,'ap-southeast-2'],['azure',azureInvoiceTerraform,'australiaeast'],['gcp',gcpInvoiceTerraform,'australia-southeast1']]){
  const row={id:'invoice',address,provider,region},stage=adapter(project,row,'staging'),production=adapter(project,row,'production'),config=JSON.parse(stage['main.tf.json']),prod=JSON.parse(production['main.tf.json']);
  assert.notEqual(config.locals.name,prod.locals.name);assert.notEqual(config.locals.api_db_user,prod.locals.api_db_user);assert.equal(adapter(project,row,'staging')['main.tf.json'],stage['main.tf.json']);
  const seed='https://atmem.ai/workspaces/'+project.id+'/'+address+'/staging';assert.ok(config.locals.name.includes(seed));assert.ok(stage['tests/invoice.tftest.hcl'].includes(seed));assert.equal(config.resource.terraform_data.review_gate.input.environment,'staging');assert.equal(prod.resource.terraform_data.review_gate.input.environment,'production');
  assert.throws(()=>adapter(project,row,'prodution'),/environment/);
 }
});

test('IBM invoice compiler preserves private SQL and parser isolation, secret references and native ownership',()=>{
 const n='block_696e766f696365',project={id:'11111111-1111-4111-8111-111111111111',revision:1,nodes:[],edges:[]},row={id:'invoice',address:n,provider:'ibm',region:'au-syd'},files=ibmInvoiceTerraform(project,row),config=JSON.parse(files['main.tf.json']),resources=config.resource;
 assert.deepEqual(Object.keys(config.terraform.required_providers),['ibm']);assert.equal(config.terraform.required_providers.ibm.version,'2.9.0');assert.ok(Object.keys(resources).every(type=>!/^aws_|^google_|^azurerm_/.test(type)));
 assert.equal(resources.ibm_database[n].service_endpoints,'private');assert.equal(resources.ibm_database[n].adminpassword,undefined);assert.equal(resources.ibm_database[n].users,undefined);assert.equal(resources.ibm_code_engine_secret,undefined);assert.equal(resources.ibm_resource_key,undefined);
 const api=resources.ibm_code_engine_app[n+'_api'],worker=resources.ibm_code_engine_app[n+'_worker'],parser=resources.ibm_code_engine_app[n+'_parser'];assert.equal(parser.managed_domain_mappings,'local_private');assert.equal(parser.run_compute_resource_token_enabled,false);assert.equal(parser.run_service_account,'none');
 assert.deepEqual(parser.run_env_variables.map(entry=>entry.name),['PARSER_AUTH_MODE','PARSER_SHARED_TOKEN']);assert.equal(parser.run_env_variables.find(entry=>entry.name==='PARSER_SHARED_TOKEN').type,'secret_key_reference');
 assert.ok(api.run_env_variables.every(entry=>!['DESTINATION_TOKEN','PARSER_SHARED_TOKEN','MODEL_ID'].includes(entry.name)));assert.equal(api.run_env_variables.find(entry=>entry.name==='PUBLIC_ORIGIN_MODE').value,'code-engine-default');assert.ok(!api.run_env_variables.some(entry=>entry.name==='PUBLIC_ORIGIN'));
 assert.deepEqual(worker.run_env_variables.filter(entry=>entry.type==='secret_key_reference').map(entry=>entry.name).sort(),['DATABASE_PASSWORD','DESTINATION_TOKEN','PARSER_SHARED_TOKEN']);assert.equal(worker.scale_min_instances,1);assert.equal(worker.scale_max_instances,1);assert.notEqual(resources.ibm_iam_trusted_profile_policy[n+'_api_documents'].iam_id,resources.ibm_iam_trusted_profile_policy[n+'_worker_documents'].iam_id);
 assert.ok(api.image_reference==='${var.runtime_image}');assert.match(files['tests/invoice.tftest.hcl'],/au\.icr\.io/);assert.match(files['CODE_ENGINE_INPUTS.md'],/No request/);assert.ok(config.output.operator_deployment);assert.throws(()=>ibmInvoiceTerraform(project,{...row,provider:'gcp'}));
});
