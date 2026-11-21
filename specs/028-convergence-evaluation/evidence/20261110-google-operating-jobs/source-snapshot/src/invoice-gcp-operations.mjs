import{v,r,l}from'./invoice-builder.mjs';

export function gcpInvoiceOperations(b,n,{destination,region,sa,member,proxy}){
 const{add,input}=b;
 for(const key of ['operations_enabled','maintenance_enabled']){b.variable[key]={type:'bool',default:false,description:key==='operations_enabled'?'After immutable image publication, create fixed private SQL operator jobs before application release.':'Enable daily cleanup/hourly monitor after owned SQL bootstrap. Verify live telemetry/notification acceptance before application release.'};b.examples[key]=false;b.testExpressions[key]='true';}
 const channel=input('operator_notification_channel','Existing verified on-call Cloud Monitoring channel in this project, referenced without modification.','projects/'+b.examples.project_id+'/notificationChannels/123456789012','^projects/[a-z][a-z0-9-]{4,28}[a-z0-9]/notificationChannels/[0-9]+$');
 b.resource.terraform_data.review_gate.lifecycle.precondition.push({condition:'${!var.maintenance_enabled || var.operations_enabled}',error_message:'Scheduled maintenance requires separate operator jobs.'},{condition:'${!var.applications_enabled || (var.operations_enabled && var.maintenance_enabled)}',error_message:'Complete owned SQL, membership and operating telemetry acceptance before application release.'},{condition:'${startswith(var.operator_notification_channel,format("projects/%s/notificationChannels/",var.project_id))}',error_message:'Use the reviewed notification channel in this destination project.'});
 b.locals.operator_deployment=b.output.operator_deployment.value;
 for(const[purpose,service]of[['scheduler','cloudscheduler.googleapis.com'],['logging','logging.googleapis.com'],['monitoring','monitoring.googleapis.com']])add('google_project_service',n+'_'+purpose,{project:destination,service,disable_on_destroy:false});
 add('google_project_service_identity',n+'_scheduler',{provider:'google-beta',project:destination,service:'cloudscheduler.googleapis.com',depends_on:['google_project_service.'+n+'_scheduler']});
 add('google_project_iam_member',n+'_scheduler_service_agent',{project:destination,role:'roles/cloudscheduler.serviceAgent',member:r('google_project_service_identity',n+'_scheduler','member')});
 add('google_service_account',n+'_scheduler',{project:destination,account_id:l('name')+'-scheduler',display_name:'Only invoke owned maintenance/monitor jobs; no SQL/data/bootstrap/override authority',depends_on:['google_project_service.'+n+'_identity']});
 const settings={DATABASE_NAME:'invoice',DATABASE_CONNECTION_NAME:r('google_sql_database_instance',n,'connection_name'),DATABASE_TRANSPORT:'cloudsql-private-proxy',DATABASE_SERVICE_ACCOUNT:sa('ops','email'),OPERATOR_PROXY_SHUTDOWN:'cloudsql-private-proxy',OPERATOR_DEPLOYMENT_BASE64:'${base64encode(jsonencode(local.operator_deployment))}'};
 for(const action of ['initialize','maintain','monitor']){
  const operator={name:'operator',image:v('runtime_image'),command:['python','-I','/app/invoice_operator_job.py',action,'--execute'],resources:{limits:{cpu:'1',memory:'1Gi'}},env:Object.entries(settings).map(([name,value])=>({name,value}))};
  // Stable concurrent startup; the operator waits on /startup itself and always
  // POSTs /quitquitquit, so a completed/failed task cannot leave this sidecar alive.
  const sidecar={name:'cloud-sql-proxy',image:proxy.image,args:['--private-ip','--address=127.0.0.1','--port=5432','--structured-logs','--lazy-refresh','--health-check','--http-address=127.0.0.1','--http-port=9090','--quitquitquit','--admin-port=9091','--exit-zero-on-sigterm',r('google_sql_database_instance',n,'connection_name')],resources:{limits:{cpu:'1',memory:'256Mi'}}};
  add('google_cloud_run_v2_job',n+'_operator_'+action,{count:'${var.operations_enabled ? 1 : 0}',project:destination,name:l('name')+'-'+action,location:region,deletion_protection:true,launch_stage:'GA',template:{parallelism:1,task_count:1,template:{service_account:sa('ops','email'),execution_environment:'EXECUTION_ENVIRONMENT_GEN2',timeout:'960s',max_retries:0,containers:[operator,sidecar],vpc_access:{egress:'PRIVATE_RANGES_ONLY',network_interfaces:{network:r('google_compute_network',n,'name'),subnetwork:r('google_compute_subnetwork',n,'name')}}}},depends_on:['google_project_service.'+n+'_run','google_artifact_registry_repository_iam_member.'+n,'google_sql_database.'+n,'google_sql_user.'+n+'_ops','google_sql_user.'+n+'_api','google_sql_user.'+n+'_worker','google_project_iam_member.'+n+'_ops_connect','google_project_iam_member.'+n+'_ops_login']});
  if(action==='initialize')continue;
  add('google_cloud_run_v2_job_iam_member',n+'_operator_'+action,{count:'${var.operations_enabled ? 1 : 0}',project:destination,location:region,name:r('google_cloud_run_v2_job',n+'_operator_'+action+'[0]','name'),role:'roles/run.invoker',member:'serviceAccount:'+r('google_service_account',n+'_scheduler','email')});
  add('google_cloud_scheduler_job',n+'_'+action,{count:'${var.operations_enabled ? 1 : 0}',project:destination,region,name:l('name')+'-'+action,schedule:action==='maintain'?'17 2 * * *':'7 * * * *',time_zone:'Etc/UTC',paused:'${!var.maintenance_enabled}',attempt_deadline:'180s',retry_config:{retry_count:2,min_backoff_duration:'10s',max_backoff_duration:'60s',max_retry_duration:'300s'},http_target:{http_method:'POST',uri:'https://run.googleapis.com/v2/projects/'+destination+'/locations/'+region+'/jobs/'+l('name')+'-'+action+':run',body:'${base64encode("{}")}',headers:{'Content-Type':'application/json'},oauth_token:{service_account_email:r('google_service_account',n+'_scheduler','email'),scope:'https://www.googleapis.com/auth/cloud-platform'}},depends_on:['google_project_service.'+n+'_scheduler','google_project_iam_member.'+n+'_scheduler_service_agent','google_cloud_run_v2_job_iam_member.'+n+'_operator_'+action]});
 }
 const jobNames=['initialize','maintain','monitor'].map(action=>'resource.labels.job_name="'+l('name')+'-'+action+'"').join(' OR ');
 const failures='resource.type="cloud_run_job" AND resource.labels.location="'+region+'" AND ('+jobNames+') AND ((jsonPayload.format="invoice-operator-v1" AND (jsonPayload.status="failed" OR jsonPayload.status="attention" OR jsonPayload.status="backlog")) OR severity>=ERROR)';
 const schedulerFailures='resource.type="cloud_scheduler_job" AND resource.labels.location="'+region+'" AND (resource.labels.job_id="'+l('name')+'-maintain" OR resource.labels.job_id="'+l('name')+'-monitor") AND severity>=ERROR';
 const success='resource.type="cloud_run_job" AND resource.labels.location="'+region+'" AND resource.labels.job_name="'+l('name')+'-monitor" AND jsonPayload.format="invoice-operator-v1" AND jsonPayload.action="monitor" AND jsonPayload.status="ok"';
 for(const[purpose,filter]of[['failed',failures],['scheduler_failed',schedulerFailures],['monitor_success',success]]){
  add('google_logging_metric',n+'_'+purpose,{project:destination,name:l('name')+'-'+purpose,filter,metric_descriptor:{metric_kind:'DELTA',value_type:'INT64',unit:'1'},depends_on:['google_project_service.'+n+'_logging']});
  b.files['monitoring/'+purpose+'.filter']=filter+'\n';
 }
 for(const[purpose,resourceType]of[['failed','cloud_run_job'],['scheduler_failed','cloud_scheduler_job']])add('google_monitoring_alert_policy',n+'_'+purpose,{project:destination,display_name:l('name')+'-'+purpose,combiner:'OR',enabled:v('operations_enabled'),notification_channels:[channel],conditions:[{display_name:'Owned operator or scheduler failure',condition_threshold:{filter:'resource.type="'+resourceType+'" AND metric.type="logging.googleapis.com/user/'+l('name')+'-'+purpose+'"',comparison:'COMPARISON_GT',threshold_value:0,duration:'0s',aggregations:[{alignment_period:'600s',per_series_aligner:'ALIGN_SUM'}],trigger:{count:1}}}],alert_strategy:{auto_close:'1800s'},documentation:{mime_type:'text/markdown',content:'Inspect the owned operator execution/logs and private SQL path. A RunJob acceptance response does not prove task success. Never replay uncertain accounting effects.'},depends_on:['google_project_service.'+n+'_monitoring','google_logging_metric.'+n+'_'+purpose]});
 // Google absence has a <24h trigger ceiling and requires an initial sample.
 // Hourly monitoring checks SQL's 92-day overdue invariant instead of emitting
 // an invalid 48-hour metric-absence rule for a once-daily maintenance job.
 add('google_monitoring_alert_policy',n+'_monitor_missing',{project:destination,display_name:l('name')+'-monitor-missing',combiner:'OR',enabled:v('maintenance_enabled'),notification_channels:[channel],conditions:[{display_name:'No successful hourly SQL monitor',condition_absent:{filter:'resource.type="cloud_run_job" AND metric.type="logging.googleapis.com/user/'+l('name')+'-monitor_success"',duration:'7200s',aggregations:[{alignment_period:'600s',per_series_aligner:'ALIGN_SUM'}],trigger:{count:1}}}],alert_strategy:{auto_close:'1800s'},documentation:{mime_type:'text/markdown',content:'This absence rule needs an actual successful measurement after policy installation/modification. Run monitor and verify its metric before release. Hourly SQL monitoring reports overdue retention; a never-started metric is not an armed heartbeat.'},depends_on:['google_project_service.'+n+'_monitoring','google_logging_metric.'+n+'_monitor_success']});
 b.output.operator_start_urls={value:Object.fromEntries(['initialize','maintain','monitor'].map(action=>[action,'https://run.googleapis.com/v2/projects/'+destination+'/locations/'+region+'/jobs/'+l('name')+'-'+action+':run']))};
 b.output.operator_bootstrap_url={value:'https://run.googleapis.com/v2/projects/'+destination+'/locations/'+region+'/jobs/'+l('name')+'-initialize:run',description:'Use only after reviewed operating-job resources have actually been applied.'};
 b.output.operator_jobs={value:{project:destination,region,serviceAccount:sa('ops','email'),schedulerServiceAccount:r('google_service_account',n+'_scheduler','email'),notificationChannel:channel,names:Object.fromEntries(['initialize','maintain','monitor'].map(action=>[action,l('name')+'-'+action]))}};
 b.files['OPERATING_JOBS.md']=GCP_OPERATING_JOBS;
 b.files['scripts/run-operator.py']=GCP_OPERATOR_RUNNER;
 b.assertions.push(`run "operator_before_applications" {
 command = plan
 variables {
 applications_enabled = false
 maintenance_enabled = false
 staff_principals = []
 }
 assert {
 condition = length(google_cloud_run_v2_job.${n}_operator_initialize) == 1 && google_cloud_scheduler_job.${n}_maintain[0].paused && length(google_cloud_run_v2_service.${n}_api) == 0
 error_message = "Manual bootstrap must precede scheduled maintenance and application release."
 }
}
run "operator_private_proxy_and_caller" {
 command = plan
 assert {
 condition = google_cloud_run_v2_job.${n}_operator_monitor[0].template[0].template[0].service_account == google_service_account.${n}_ops.email && google_cloud_run_v2_job.${n}_operator_monitor[0].template[0].template[0].max_retries == 0 && contains(google_cloud_run_v2_job.${n}_operator_monitor[0].template[0].template[0].containers[1].args,"--quitquitquit") && google_cloud_run_v2_job_iam_member.${n}_operator_maintain[0].member == "serviceAccount:\${google_service_account.${n}_scheduler.email}"
 error_message = "Separate SQL operator, private terminating proxy and job-scoped invoker are required."
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

const GCP_OPERATING_JOBS=`# Google invoice operating jobs

Obtain authorization before account writes, apply, publication or RunJob. Fixed
operator jobs are not API/model tools. The existing project, verified staff and
notification channel are referenced, never replaced. Verify the existing channel's
actual on-call recipients and delivery. Review organization log placement/retention
and effective inherited IAM; this package does not rewrite existing logging sinks.
Operator receipts contain counts/status, not invoices, subjects or amounts.

Foundation: applications_enabled=false, operations_enabled=false,
maintenance_enabled=false. Publish reviewed immutable runtime/parser images into
the owned regional repository only when authorized. With runtime_image supplied,
set operations_enabled=true and keep maintenance/applications false. The three
fixed jobs exist; daily/hourly schedules remain paused.

As the separately authorized destination operator, preview the emitted command:

    python3 scripts/run-operator.py initialize

Then add --execute for the authorized destination. The helper reads nonsecret
Terraform outputs and invokes gcloud with exact project/region/name and --wait,
without shell interpolation, overrides or exposing OAuth tokens. Use maintain or
monitor for the other fixed jobs. Install/authenticate the reviewed Google Cloud
CLI beforehand. The exact operator_start_urls REST outputs are also available.
Do not use public invokers or application roles to launch privileged SQL work. RunJob acceptance is asynchronous: retain the actual
completed execution/exit status and initialized:true receipt before continuing.

The ops service account intentionally has separate cloudsqlsuperuser SQL authority.
API/worker IAM SQL users must already exist. Bootstrap verifies native IAM markers,
owned identities, exact schema/grants and scope, never creates a substitute native
IAM user or adopts unrelated roles. Managed Cloud SQL role mutation, native IAM and
effective privileges require destination checks; local PostgreSQL is not Cloud SQL.
Admit verified staff SQL memberships separately; IAP access alone is insufficient.
Populate the accounting secret outside Terraform/source and outside operator jobs.

Each job has one task, parallelism one, no native retry and a 960-second task limit.
Its operator waits up to 30 seconds on the pinned proxy's own loopback startup
endpoint, uses a 900-second work deadline and always calls the loopback shutdown
endpoint. Initial SQL connection transport failures retry at most three times with
fresh credentials; authentication/permission/schema errors do not. No insecure
remote connection, public SQL IP or configurable proxy URL is introduced. The
maintained proxy uses private IP/upstream TLS and a fixed instance. A failed shutdown
cannot emit an ok heartbeat; native task timeout remains the final failure bound.

Next enable maintenance_enabled=true while applications_enabled=false. Cleanup
runs 02:17 UTC daily, monitor at minute 7 hourly. The scheduler uses its own invoker
identity scoped to maintain/monitor only, OAuth, bounded retries and no bootstrap
or override/SQL authority. Its service agent has the required native role.
Manually run monitor and verify a real success metric AFTER policy installation/
modification: Google's absence policy does not arm from a never-written metric.
The two-hour monitor absence rule plus failures and hourly SQL retention-overdue
checks cover operating progress. No invalid 48-hour absence condition is emitted.
Native platform ERROR logs and count-only failed/attention/backlog receipts alert;
inspect execution history as well. Test failed scheduling/execution, first-sample,
missing runs and channel delivery before final applications_enabled=true release.

Daily cleanup is bounded to twenty 500-record transactions and refuses live jobs/
leases; younger/concurrent work is preserved. Original-object expiry is separate
and asynchronous. Restore/quarantine/reconciliation remain isolated and paused.
Local schemas/mocks and fixture SQL do not prove Cloud SQL IAM/TLS, scheduling,
metric/log ingestion, notification delivery or managed restore. Retain those actual
destination acceptance receipts; no production readiness is inferred from a URL.
`;

const GCP_OPERATOR_RUNNER=String.raw`"""Preview or explicitly execute one owned Google operator job from Terraform outputs."""
import argparse
import json
import re
import subprocess
import sys

def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate output field')
        result[key]=value
    return result

def command(action,configuration):
    if action not in {'initialize','maintain','monitor'}or not isinstance(configuration,dict):raise ValueError('Use an owned fixed operator action')
    project=configuration.get('project');region=configuration.get('region');names=configuration.get('names')
    if not isinstance(project,str)or not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]',project)or not isinstance(region,str)or not re.fullmatch(r'[a-z]+-[a-z]+[1-9][0-9]?',region):raise ValueError('Use the emitted destination')
    if not isinstance(names,dict)or set(names)!={'initialize','maintain','monitor'}or any(not isinstance(name,str)or not re.fullmatch(r'[a-z][a-z0-9-]{1,61}[a-z0-9]',name)for name in names.values())or len(set(names.values()))!=3:raise ValueError('Use distinct owned job names')
    return ['gcloud','run','jobs','execute',names[action],'--project',project,'--region',region,'--wait','--format=json']

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['initialize','maintain','monitor']);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    result=subprocess.run(['terraform','output','-json','operator_jobs'],capture_output=True,check=True,timeout=30)
    selected=command(args.action,json.loads(result.stdout,object_pairs_hook=unique))
    if not args.execute:
        print(json.dumps({'willWrite':False,'command':selected}));return 0
    return subprocess.run(selected,timeout=1200).returncode

if __name__=='__main__':
    try:sys.exit(main())
    except Exception:
        print('Operator invocation failed. Check the owned Terraform state, authenticated destination and job execution receipt.',file=sys.stderr);sys.exit(1)
`;
