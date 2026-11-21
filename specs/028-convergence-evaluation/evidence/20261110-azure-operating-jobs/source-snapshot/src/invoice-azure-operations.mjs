import{v,r,l}from'./invoice-builder.mjs';

// Separate trusted operator jobs. Job start permission is privileged because the
// native API accepts execution-template overrides; never grant it to the product.
export function azureInvoiceOperations(b,n,{rg,rgId,region,subscription,identity}){
 const{add,input}=b;
 for(const key of ['operations_enabled','maintenance_enabled']){b.variable[key]={type:'bool',default:false,description:key==='operations_enabled'?'Create manual fixed operator jobs after reviewed immutable image publication.':'After successful bootstrap/membership and log-query verification, schedule daily retention/hourly monitor and enable alerts.'};b.examples[key]=false;b.testExpressions[key]='true';}
 const actionGroup=input('operator_action_group_id','Existing reviewed same-subscription Azure Monitor action group with a verified on-call route; referenced without modifying it.','/subscriptions/'+b.examples.subscription_id+'/resourceGroups/reviewed-operations/providers/Microsoft.Insights/actionGroups/on-call','^/subscriptions/[0-9a-f-]{36}/resourceGroups/[^/]+/providers/Microsoft\\.Insights/actionGroups/[^/]+$');
 b.resource.terraform_data.review_gate.lifecycle.precondition.push({condition:'${!var.maintenance_enabled || var.operations_enabled}',error_message:'Maintenance requires its separate owned operator jobs.'},{condition:'${!var.applications_enabled || (var.operations_enabled && var.maintenance_enabled)}',error_message:'Complete owned SQL/membership bootstrap and operating-log acceptance before application release.'},{condition:'${startswith(lower(var.operator_action_group_id),format("/subscriptions/%s/",var.subscription_id))}',error_message:'Use the reviewed existing notification group in this subscription.'});
 b.locals.operator_deployment=b.output.operator_deployment.value;
 const environment=r('azurerm_container_app_environment',n,'id'),workspace=r('azurerm_log_analytics_workspace',n,'id');
 add('azurerm_log_analytics_workspace',n,{name:l('name')+'-operations',resource_group_name:rg,location:region,sku:'PerGB2018',retention_in_days:30,lifecycle:{prevent_destroy:true}});
 // Azure Monitor routing avoids the legacy HTTP Data Collector/_CL path. The
 // destination alone is insufficient: both log categories are explicitly routed.
 b.resource.azurerm_container_app_environment[n].logs_destination='azure-monitor';
 add('azurerm_monitor_diagnostic_setting',n+'_environment',{name:'invoice-operating-logs',target_resource_id:environment,log_analytics_workspace_id:workspace,log_analytics_destination_type:'Dedicated',enabled_log:[{category:'ContainerAppConsoleLogs'},{category:'ContainerAppSystemLogs'}]});
 const settings={DATABASE_NAME:'invoice',DATABASE_HOST:r('azurerm_postgresql_flexible_server',n,'fqdn'),DATABASE_USER:l('name')+'-operator',DATABASE_CA_FILE:'/usr/local/lib/python3.13/site-packages/certifi/cacert.pem',WORKLOAD_IDENTITY_CLIENT_ID:identity('operator','client_id'),OPERATOR_DEPLOYMENT_BASE64:'${base64encode(jsonencode(local.operator_deployment))}'};
 const common={replicaTimeout:900,replicaRetryLimit:0,registries:[{server:r('azurerm_container_registry',n,'login_server'),identity:identity('pull','id')}],identitySettings:[{identity:identity('pull','id'),lifecycle:'None'},{identity:identity('operator','id'),lifecycle:'Main'}]};
 for(const action of ['initialize','maintain','monitor']){
  const manual={...common,triggerType:'Manual',manualTriggerConfig:{parallelism:1,replicaCompletionCount:1}};
  const scheduled={...common,triggerType:'Schedule',scheduleTriggerConfig:{cronExpression:action==='maintain'?'17 2 * * *':'7 * * * *',parallelism:1,replicaCompletionCount:1}};
  // Decode one of two complete configurations, omitting the inactive trigger
  // rather than sending optional ARM objects as explicit null values.
  const configuration=action==='initialize'?manual:'${jsondecode(var.maintenance_enabled ? jsonencode('+JSON.stringify(scheduled)+') : jsonencode('+JSON.stringify(manual)+'))}';
  add('azapi_resource',n+'_operator_'+action,{count:'${var.operations_enabled ? 1 : 0}',type:'Microsoft.App/jobs@2025-07-01',name:l('name')+'-'+action,parent_id:rgId,location:region,identity:{type:'UserAssigned',identity_ids:[identity('pull','id'),identity('operator','id')]},body:{properties:{environmentId:environment,workloadProfileName:'Consumption',configuration,template:{containers:[{name:'operator',image:v('runtime_image'),command:['python','-I','/app/invoice_operator_job.py',action,'--execute'],resources:{cpu:0.5,memory:'1Gi'},env:Object.entries(settings).map(([name,value])=>({name,value}))}]}}},schema_validation_enabled:true,response_export_values:['properties.configuration.triggerType'],depends_on:['azurerm_role_assignment.'+n+'_pull','azurerm_postgresql_flexible_server_active_directory_administrator.'+n,'azurerm_postgresql_flexible_server_database.'+n,'azurerm_monitor_diagnostic_setting.'+n+'_environment']});
  const prefix='${local.name}-'+action;
  const owned=`| where EnvironmentName == '${l('name')}'\n| where JobName == '${prefix}' or JobName startswith '${prefix}-' or ContainerGroupName startswith '${prefix}-'`;
  if(action!=='initialize'){
   const hours=action==='maintain'?48:2;
   const query=`ContainerAppConsoleLogs\n| where TimeGenerated > ago(${hours}h)\n${owned}\n| where ContainerName == 'operator'\n| extend receipt = parse_json(Log)\n| where receipt.format == 'invoice-operator-v1' and receipt.action == '${action}' and receipt.status == 'ok'\n| summarize SuccessfulRuns=count()\n| where SuccessfulRuns < 1`;
   add('azurerm_monitor_scheduled_query_rules_alert_v2',n+'_'+action+'_missing',{name:l('name')+'-'+action+'-missing',resource_group_name:rg,location:region,scopes:[workspace],severity:2,evaluation_frequency:'PT1H',window_duration:action==='maintain'?'P2D':'PT2H',enabled:v('maintenance_enabled'),skip_query_validation:'${!var.maintenance_enabled}',auto_mitigation_enabled:true,description:'Missing count-only success receipt. Initial manual bootstrap/log ingestion precedes enabling scheduled operating jobs; verify notification delivery.',criteria:{query,time_aggregation_method:'Count',operator:'GreaterThan',threshold:0,failing_periods:{number_of_evaluation_periods:1,minimum_failing_periods_to_trigger_alert:1}},action:{action_groups:[actionGroup]},depends_on:['azurerm_monitor_diagnostic_setting.'+n+'_environment']});
   b.files['monitoring/'+action+'-missing.kql']=query+'\n';
  }
  const consoleQuery=`ContainerAppConsoleLogs\n| where TimeGenerated > ago(1h)\n${owned}\n| where ContainerName == 'operator'\n| extend receipt=parse_json(Log)\n| where receipt.format == 'invoice-operator-v1' and receipt.status in ('failed','attention','backlog')\n| project TimeGenerated`;
  // System logs use ReplicaName (not console ContainerGroupName). Include image
  // pull/scheduling warnings so failures before Python startup are not invisible.
  const systemOwned=`| where EnvironmentName == '${l('name')}'\n| where JobName == '${prefix}' or JobName startswith '${prefix}-' or ReplicaName startswith '${prefix}-'`;
  const query=`union (\n${consoleQuery}\n), (\nContainerAppSystemLogs\n| where TimeGenerated > ago(1h)\n${systemOwned}\n| where Type =~ 'Warning' or Type =~ 'Error'\n| project TimeGenerated\n)\n| summarize Failures=count()\n| where Failures > 0`;
  add('azurerm_monitor_scheduled_query_rules_alert_v2',n+'_'+action+'_failed',{name:l('name')+'-'+action+'-failed',resource_group_name:rg,location:region,scopes:[workspace],severity:2,evaluation_frequency:'PT5M',window_duration:'PT1H',enabled:v('operations_enabled'),skip_query_validation:'${!var.maintenance_enabled}',auto_mitigation_enabled:true,description:'Fixed operator failure/attention or native platform warning/error. Inspect trusted operator execution history; never replay uncertain accounting effects.',criteria:{query,time_aggregation_method:'Count',operator:'GreaterThan',threshold:0,failing_periods:{number_of_evaluation_periods:1,minimum_failing_periods_to_trigger_alert:1}},action:{action_groups:[actionGroup]},depends_on:['azurerm_monitor_diagnostic_setting.'+n+'_environment']});
  b.files['monitoring/'+action+'-failed.kql']=query+'\n';
 }
 b.output.operator_jobs={value:{resourceGroup:rg,initialize:l('name')+'-initialize',maintain:l('name')+'-maintain',monitor:l('name')+'-monitor',workspace:workspace,actionGroup:actionGroup,operatorPrincipal:identity('operator','principal_id'),operatorClientId:identity('operator','client_id'),permissionBoundary:'Only a trusted destination operator may start jobs. Native start accepts execution-template overrides; no start/RBAC permission is given to API or worker.'}};
 b.output.operator_start_urls={value:Object.fromEntries(['initialize','maintain','monitor'].map(action=>[action,rgId+'/providers/Microsoft.App/jobs/'+l('name')+'-'+action+'/start?api-version=2025-07-01']))};
 b.output.operator_bootstrap_url={value:rgId+'/providers/Microsoft.App/jobs/'+l('name')+'-initialize/start?api-version=2025-07-01',description:'Use only after the reviewed operations-enabled resources have actually been applied. A URL is not proof the job exists.'};
 b.files['OPERATING_JOBS.md']=AZURE_OPERATING_JOBS;
 b.assertions.push(`run "manual_operator_before_applications" {
 command = plan
 variables {
 applications_enabled = false
 maintenance_enabled = false
 staff_subjects = []
 }
 assert {
 condition = azapi_resource.${n}_operator_initialize[0].body.properties.configuration.triggerType == "Manual" && azapi_resource.${n}_operator_maintain[0].body.properties.configuration.triggerType == "Manual" && length(azapi_resource.${n}_api) == 0
 error_message = "Manual SQL bootstrap/log qualification must precede scheduled operations and application release."
 }
}
run "scheduled_jobs_and_log_validation" {
 command = plan
 assert {
 condition = azapi_resource.${n}_operator_initialize[0].body.properties.configuration.triggerType == "Manual" && azapi_resource.${n}_operator_maintain[0].body.properties.configuration.triggerType == "Schedule" && azapi_resource.${n}_operator_monitor[0].body.properties.configuration.replicaTimeout == 900 && !azurerm_monitor_scheduled_query_rules_alert_v2.${n}_monitor_missing.skip_query_validation && azurerm_container_app_environment.${n}.logs_destination == "azure-monitor"
 error_message = "Application release must include scheduled operations and mandatory current-table query validation."
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

const AZURE_OPERATING_JOBS=`# Azure invoice operating jobs

Obtain authorization before destination writes, publication, apply or job start.
The emitted native jobs are fixed trusted operator tools, not API/model endpoints.
Azure job start accepts an execution template that can override image/command/env.
Treat start permission as access to the job's available managed identity. Never
grant job start/contributor/operator or listSecrets rights to the product, end users,
worker, parser or an untrusted automation identity. This package assigns none.

Foundation: applications_enabled=false, operations_enabled=false,
maintenance_enabled=false. Review regional availability, model/version, identity,
costs and existing operator_action_group_id. No existing action group or its routes
are adopted or modified. Verify its actual notification recipients and delivery.
Azure Monitor and resource-specific log tables are used; diagnostic routing includes
both console and system logs. Logs retain 30 days, separate from 90-day invoices.
Provider-managed state must remain private/encrypted; do not publish workspace keys.

After authorized build/scan/publication of the immutable runtime image to owned ACR,
set operations_enabled=true with applications_enabled/maintenance_enabled=false.
All three jobs are Manual. The pull identity has lifecycle None; only the separate
PostgreSQL Entra administrator identity has lifecycle Main. There is no password,
accounting secret, model, object access or HTTP ingress on these jobs. The exact
operator identity and login bind token acquisition to the managed database.

Start initialize as the trusted destination operator:

    az rest --method post --url "$(terraform output -raw operator_bootstrap_url)" --body '{}'

The shared core maps owned API/worker principals in postgres, then initializes
the application schema/grants/account in invoice. Check completed execution status,
exit code and initialized:true log receipt; start acceptance alone proves neither.
Admit verified staff subjects/roles using the separate membership CLI/runbook.
Do not infer reviewer privileges from Entra app access. Keep accounting secret
population separate from this SQL-only operator identity.

The nonsecret operator_start_urls output gives the exact remaining start endpoints;
call them with an empty JSON body as above. Do not override image/command/template.
Start maintain and monitor manually and check count-only receipts and both native
log tables. Query files are in monitoring/. Validate their ownership filters against
actual JobName/replica fields at the destination. Alerts are initially unvalidated
while fresh tables do not yet exist. Enabling maintenance_enabled makes ARM query
validation mandatory; a missing/incorrect table/query must block release, not be
silently skipped. Log ingestion/diagnostic activation can be delayed. Verify actual
queries and an action-group test notification before enabling scheduled release.

Release with operations_enabled=true, maintenance_enabled=true and
applications_enabled=true. Bootstrap stays Manual. Maintain runs 02:17 UTC daily;
monitor at minute 7 hourly. Completion/parallelism is one, native retry is zero and
replica timeout is 900 seconds. The shared process deadline and SQL statement/lock
bounds apply as well. Scheduling does not prove native IAM/SQL/network/alerts worked.

Daily expired-only SQL cleanup is bounded to twenty 500-record transactions and
refuses live execution jobs/leases. New/young operations survive; original-object
expiry is a separate asynchronous lifecycle. Monitoring is a read-only count-only
transaction. Two hours of missing monitor receipts and 48 hours of missing cleanup
receipts alert, along with failure/attention/backlog and platform warnings/errors.
These are explicit operating defaults, not promised availability or a client SLA.
No KQL engine or Azure Monitor ingestion/notification execution is proved by local
provider schemas/mocks. Retain actual destination acceptance before production.

Restore/quarantine/reconciliation still require an isolated paused destination.
Never use daily maintenance to reset or resend unknown accounting side effects.
`;
