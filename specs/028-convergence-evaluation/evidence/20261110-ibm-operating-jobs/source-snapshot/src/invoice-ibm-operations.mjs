import{v,r,l,UUID}from'./invoice-builder.mjs';

// IBM 2.9 supports JobDefinition, not a Terraform cron subscription resource.
// Keep job delivery separate from scheduling/alert acceptance under qualification.
export function ibmInvoiceOperations(b,n,{projectId,pull}){
 const{add}=b;
 b.variable.operations_enabled={type:'bool',default:false,description:'Create the three fixed SQL operating tasks after reviewed immutable image publication. Scheduling and alert acceptance are separate.'};
 b.examples.operations_enabled=false;b.testExpressions.operations_enabled='true';
 b.variable.maintenance_enabled={type:'bool',default:false,description:'Enable operating alerts after bootstrap; separately install the owned cron sources and verify successful runs before application release.'};b.examples.maintenance_enabled=false;b.testExpressions.maintenance_enabled='true';
 const logs=b.input('operator_logs_instance_id','Existing reviewed same-region Cloud Logs instance receiving this region\'s Code Engine platform logs. Existing account routing is preserved.','88888888-8888-4888-8888-888888888888',UUID);
 const webhook=b.input('operator_notification_integration_id','Existing verified Cloud Logs outgoing integration numeric ID; verify intended on-call recipients/delivery without exposing its endpoint or credentials.','12345','^[1-9][0-9]{0,9}$');
 b.variable.operator_notification_integration_id.validation.condition='${can(regex("^[1-9][0-9]{0,9}$",var.operator_notification_integration_id)) && try(tonumber(var.operator_notification_integration_id),0) <= 4294967295}';
 b.resource.terraform_data.review_gate.lifecycle.precondition.push({condition:'${!var.maintenance_enabled || var.operations_enabled}',error_message:'Operating alerts and schedules require fixed operator tasks.'},{condition:'${!var.applications_enabled || (var.operations_enabled && var.maintenance_enabled)}',error_message:'Initialize SQL and verify operating schedules, log routing and notifications before application release.'});
 b.locals.operator_deployment=b.output.operator_deployment.value;
 b.locals.operator_secret_name=l('name')+'-operator-sql';
 const literal=(name,value)=>({name,value,type:'literal'});
 const reference=(name,type,key,reference)=>({name,type,key,reference});
 for(const action of ['initialize','maintain','monitor']){
  const env=[literal('DATABASE_NAME','ibmclouddb'),literal('OPERATOR_DEPLOYMENT_BASE64','${base64encode(jsonencode(local.operator_deployment))}'),...Object.entries({DATABASE_HOST:'host',DATABASE_PORT:'port',DATABASE_CA_PEM:'ca_pem',DATABASE_USER:'operator_user'}).map(([name,key])=>reference(name,'config_map_key_reference',key,l('database_config_name'))),reference('DATABASE_PASSWORD','secret_key_reference','password',l('operator_secret_name'))];
  // Bootstrap needs the two runtime passwords, never the worker's accounting token.
  if(action==='initialize')for(const purpose of ['api','worker'])env.push(reference(purpose.toUpperCase()+'_DATABASE_PASSWORD','secret_key_reference','password',l(purpose==='api'?'api_secret_name':'worker_secret_name')));
  add('ibm_code_engine_job',n+'_operator_'+action,{count:'${var.operations_enabled ? 1 : 0}',project_id:projectId,name:l('name')+'-'+action,image_reference:v('runtime_image'),image_secret:pull,run_commands:['python','-I','/app/invoice_operator_job.py'],run_arguments:[action,'--execute'],run_mode:'task',run_as_user:10001,run_service_account:'none',run_compute_resource_token_enabled:false,scale_array_spec:'0',scale_cpu_limit:'1',scale_memory_limit:'1G',scale_max_execution_time:960,scale_retry_limit:0,run_env_variables:env,depends_on:['ibm_database.'+n]});
 }
 const owned='app:"codeengine" AND codeengine.projectGuid:"'+projectId+'" AND codeengine.region:"'+b.region+'"';
 const query=(action,status)=>owned+' AND codeengine.component:"'+l('name')+'-'+action+'" AND message:"invoice-operator-v1" AND message:"'+status+'"';
 const failures=owned+' AND ('+['initialize','maintain','monitor'].map(action=>'codeengine.component:"'+l('name')+'-'+action+'"').join(' OR ')+') AND ((message:"invoice-operator-v1" AND (message:"failed" OR message:"attention" OR message:"backlog")) OR level:"error" OR level:"fatal")';
 const definitions=[['failed',failures,'more_than_or_unspecified',0,'minutes_5_or_unspecified'],['monitor_missing',query('monitor','ok'),'less_than',1,'hours_2'],['maintenance_missing',query('maintain','ok'),'less_than',1,'hours_36']];
 b.output.operator_log_queries={value:Object.fromEntries(definitions.map(([purpose,filter])=>[purpose,filter]))};
 for(const[purpose,filter,condition,threshold,window]of definitions){
  add('ibm_logs_alert_definition',n+'_'+purpose,{instance_id:logs,region:b.region,name:l('name')+'-'+purpose,description:'Owned SQL operator '+purpose+'. Verify native log samples, alert evaluation and existing on-call delivery before release; no customer invoice data in notifications.',enabled:v('maintenance_enabled'),phantom_mode:false,priority:'p2',type:'logs_threshold',logs_threshold:{condition_type:condition,evaluation_delay_ms:60000,notification_payload_filter:[],logs_filter:{simple_filter:{lucene_query:filter}},rules:[{condition:{threshold,time_window:{logs_time_window_specific_value:window}},override:{priority:'p2'}}],undetected_values_management:{auto_retire_timeframe:'never_or_unspecified',trigger_undetected_values:condition==='less_than'}},notification_group:{webhooks:[{minutes:1,notify_on:'triggered_and_resolved',integration:{integration_id:'${tonumber(var.operator_notification_integration_id)}'}}]},incidents_settings:{minutes:10,notify_on:'triggered_and_resolved'}});
  b.files['monitoring/'+purpose+'.lucene']=filter+'\n';
 }
 b.output.operator_jobs={value:{account:v('account_id'),region:b.region,projectId,maintenanceEnabled:v('maintenance_enabled'),operatorSecret:l('operator_secret_name'),names:Object.fromEntries(['initialize','maintain','monitor'].map(action=>[action,l('name')+'-'+action]))}};
 b.files['scripts/run-operator.py']=IBM_OPERATOR_RUNNER;
 b.files['OPERATING_JOBS.md']=IBM_OPERATING_JOBS;
 b.assertions.push(`run "operator_before_applications" {
 command = plan
 variables {
 applications_enabled = false
 maintenance_enabled = false
 }
 assert {
 condition = length(ibm_code_engine_job.${n}_operator_initialize) == 1 && length(ibm_code_engine_app.${n}_api) == 0 && ibm_code_engine_job.${n}_operator_monitor[0].run_service_account == "none" && !ibm_code_engine_job.${n}_operator_monitor[0].run_compute_resource_token_enabled && ibm_code_engine_job.${n}_operator_monitor[0].scale_retry_limit == 0
 error_message = "Bootstrap is separate, bounded and without application/cloud authority."
 }
}
run "operator_mutable_image_rejected" {
 command = plan
 variables {
 applications_enabled = false
 runtime_image = "unreviewed:latest"
 maintenance_enabled = false
 }
 expect_failures = [var.runtime_image]
}
run "operating_jobs_required" {
 command = plan
 variables {
 operations_enabled = false
 maintenance_enabled = false
 }
 expect_failures = [terraform_data.review_gate]
}
run "maintenance_without_jobs_rejected" {
 command = plan
 variables {
 applications_enabled = false
 operations_enabled = false
 }
 expect_failures = [terraform_data.review_gate]
}
run "notification_id_overflow_rejected" {
 command = plan
 variables { operator_notification_integration_id = "4294967296" }
 expect_failures = [var.operator_notification_integration_id]
}
`);
}

const IBM_OPERATING_JOBS=`# IBM fixed invoice operating tasks

This package delivers initialize/maintain/monitor task definitions, an explicit
owned cron installer/observer, and Cloud Logs alert definitions. Local tests do not
prove real native execution, log routing, notification delivery or deployment.

Foundation uses applications_enabled=false, operations_enabled=false and
maintenance_enabled=false. Publish
the reviewed immutable runtime image into the owned registry only when authorized.
Set operations_enabled=true with applications still false to create fixed tasks.
Populate the separate operator SQL secret outside Terraform. databaseConfig also
needs operator_user: the exact administrative login for this new owned database.
Only initialize receives the separate API and worker SQL password keys. No task
receives the accounting token, parser token, model or object-store authority.

The destination operator installs/authenticates IBM Cloud CLI and its reviewed Code
Engine plugin in a dedicated private CLI home. For example, set IBMCLOUD_HOME to
this package's .local/ibm-operator-cli during login/plugin setup. Keep that directory
mode 0700 and outside source control. Never copy a user's global CLI credentials.

Preview: python3 scripts/run-operator.py initialize
Authorized execution adds --execute. The helper reads this package's Terraform
output, explicitly selects its account/region/project in the isolated CLI home,
then submits the fixed task with --wait. It supplies no image, environment, command
or service-account overrides. Job-launch permission is privileged; do not grant it
to the application, worker, model or public user. Retain the actual completed job
and initialized:true/monitor/maintenance receipt, not merely submit acceptance.

After bootstrap, run maintain and monitor once and inspect actual successful
receipts in the existing Cloud Logs destination. Verify that regional Code Engine
platform logging is routed to operator_logs_instance_id through the existing
account routing. Review its region/data custody and the existing outgoing
notification integration. Do not replace account log routing or expose credentials.
Read terraform output -json operator_log_queries for resolved queries; monitoring/
files are readable Terraform expression templates, not resolved instance selectors.
The Lucene filters use documented app/codeengine.projectGuid/region/component and
message/level fields, never deprecated label.Namespace/Project/Stream fields.
Verify the actual native samples match each emitted query before enabling alerts;
account parsing/routing can change message layout. Missing SQL monitor alerts after
two hours; missing daily maintenance after 36 hours. Undetected values trigger
missing-run alerts; native zero-sample evaluation/delivery still need acceptance.
Notifications exclude payload fields; no invoice/subject/amount is emitted by jobs.

Keep applications false, set maintenance_enabled=true, apply reviewed alerts, then
preview python3 scripts/run-operator.py install-schedules. With authorized --execute,
the helper uses supported Knative PingSource and IBM JobDefinition APIs in this
project's isolated KUBECONFIG. Only maintain (02:17 UTC daily) and monitor (hourly at
minute 7) are scheduled. Initialize is never scheduled. It refuses unrelated source
ownership and uses native resourceVersion to avoid overwriting concurrent changes.
Use check-schedules --execute to observe configuration and current Ready generation.
Ready means reconciled source configuration, not successful SQL work. Retain actual
successful scheduled task/log/alert delivery evidence before application release.
Cron sources are explicitly operated resources outside Terraform because IBM 2.9
has no cron subscription resource; do not hide account writes in a provisioner.
Before rollback, identify the two exact owned PingSource names/UIDs, verify their
owner references and remove only those sources with the authorized native operator;
do not delete the namespace/project. Disable alerts during an approved maintenance
window. Installed sources persist independently of the Terraform boolean: changing
maintenance_enabled=false does not pause or delete an installed source.

Each task uses one array index, no automatic retries and a 960-second platform
limit; the application enforces its own 900-second work deadline. Private SQL TLS,
actual native login privileges, task outcome, schedules and alert delivery still
need separately authorized destination checks. Provider schema/mocks are not
deployment, SQL runtime or scheduling evidence.
`;

const IBM_OPERATOR_RUNNER=`"""Preview or explicitly execute a fixed owned IBM Code Engine task."""
import argparse
from contextlib import contextmanager
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def unique_object(pairs):
    value={}
    for key,child in pairs:
        if key in value:raise ValueError('Duplicate operator output field')
        value[key]=child
    return value

def configuration():
    result=subprocess.run(['terraform','output','-json','operator_jobs'],cwd=ROOT,check=True,capture_output=True,text=True,timeout=30)
    value=json.loads(result.stdout,object_pairs_hook=unique_object)
    if not isinstance(value,dict)or set(value)!={'account','region','projectId','maintenanceEnabled','operatorSecret','names'}or type(value['maintenanceEnabled'])is not bool:raise ValueError('Use the owned operator_jobs output')
    if not re.fullmatch(r'[0-9a-f]{32}',value['account'])or not re.fullmatch(r'[a-z]{2}-[a-z]+',value['region'])or not re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',value['projectId']):raise ValueError('Invalid native destination')
    names=value['names']
    if not isinstance(names,dict)or set(names)!={'initialize','maintain','monitor'}:raise ValueError('Use all three fixed jobs')
    prefix=None
    for action,name in names.items():
        if not isinstance(name,str)or not re.fullmatch(r'invoice-[0-9a-f]{12}-'+action,name):raise ValueError('Use a fixed owned task')
        current=name.removesuffix('-'+action)
        if prefix is not None and current!=prefix:raise ValueError('Mixed deployment jobs')
        prefix=current
    return value

def commands(value,action):
    return [['ibmcloud','target','-c',value['account'],'-r',value['region']],['ibmcloud','ce','project','select','--id',value['projectId'],'--quiet'],['ibmcloud','ce','jobrun','submit','--job',value['names'][action],'--wait','--wait-timeout','1000']]

@contextmanager
def private_context():
    home=ROOT/'.local/ibm-operator-cli'
    # Pre-existing private CLI authentication is required; do not silently adopt
    # global account context or follow a symlink to somebody else's CLI state.
    metadata=home.lstat()
    if not stat.S_ISDIR(metadata.st_mode)or metadata.st_uid!=os.geteuid()or metadata.st_mode&0o077:raise ValueError('Authenticate in the owned mode-0700 CLI directory first')
    lock=os.open(home/'operator.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(lock,'w')as stream:
        metadata=os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode)or metadata.st_uid!=os.geteuid()or metadata.st_mode&0o077:raise ValueError('Use a private owned operation lock')
        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        kube=home/'operator-kubeconfig'
        if kube.exists()or kube.is_symlink():
            metadata=kube.lstat()
            if not stat.S_ISREG(metadata.st_mode)or metadata.st_uid!=os.geteuid()or metadata.st_mode&0o077:raise ValueError('Use a private owned kubeconfig')
        env={**os.environ,'IBMCLOUD_HOME':str(home),'IBMCLOUD_TRACE':'false','KUBECONFIG':str(kube)}
        previous=os.umask(0o077)
        try:yield env
        finally:os.umask(previous)

def kubectl(env,arguments,body=None):
    result=subprocess.run(['kubectl',*arguments],cwd=ROOT,env=env,check=True,capture_output=True,text=True,input=json.dumps(body)if body is not None else None,timeout=150)
    if len(result.stdout)>1000000:raise ValueError('Unexpected native resource response')
    return result.stdout.strip()

def get_resource(env,kind,name,namespace,optional=False):
    raw=kubectl(env,['get',kind,name,'--namespace',namespace,'-o','json',*(['--ignore-not-found']if optional else[])])
    if optional and not raw:return None
    return json.loads(raw,object_pairs_hook=unique_object)

def ownership(value,job,namespace,prefix,name):
    metadata=value.get('metadata',{});references=metadata.get('ownerReferences',[])
    expected={'apiVersion':'codeengine.cloud.ibm.com/v1beta1','kind':'JobDefinition','name':job['metadata']['name'],'uid':job['metadata']['uid'],'controller':False,'blockOwnerDeletion':False}
    if value.get('apiVersion')!='sources.knative.dev/v1'or value.get('kind')!='PingSource'or metadata.get('namespace')!=namespace or metadata.get('name')!=name or metadata.get('labels',{}).get('atmem.ai/operator-package')!=prefix or expected not in references:raise ValueError('Refuse unrelated cron source ownership')
    if len(references)!=1 or not metadata.get('uid')or not metadata.get('resourceVersion'):raise ValueError('Ambiguous cron source identity')

def schedule_spec(job,action):
    return {'schedule':'17 2 * * *'if action=='maintain'else'7 * * * *','timezone':'UTC','contentType':'application/json','data':'{}','sink':{'ref':{'apiVersion':'codeengine.cloud.ibm.com/v1beta1','kind':'JobDefinition','name':job['metadata']['name']}}}

def verify_ready(value,expected):
    spec=value.get('spec',{})
    if any(spec.get(key)!=child for key,child in expected.items()):raise ValueError('Cron configuration differs from the owned task contract')
    status=value.get('status',{});generation=value['metadata'].get('generation')
    if type(generation)is not int or status.get('observedGeneration')!=generation or not any(c.get('type')=='Ready'and c.get('status')=='True'for c in status.get('conditions',[])):raise ValueError('Cron source has not reconciled this generation')

def schedules(value,env,install):
    if install and not value['maintenanceEnabled']:raise ValueError('Enable reviewed operating alerts before installing schedules')
    target=commands(value,'monitor')[:2];target[1]=[*target[1],'--kubecfg']
    for command in target:subprocess.run(command,cwd=ROOT,env=env,check=True,timeout=120)
    namespace=kubectl(env,['config','view','--minify','-o','jsonpath={.contexts[0].context.namespace}'])
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}',namespace):raise ValueError('Use the selected native project namespace')
    prefix=value['names']['monitor'].removesuffix('-monitor');result=[]
    # Observe both targets and ownership boundaries before making either write.
    pending=[]
    for action in ['maintain','monitor']:
        job=get_resource(env,'jobdefinitions.codeengine.cloud.ibm.com',value['names'][action],namespace)
        metadata=job.get('metadata',{})
        if job.get('apiVersion')!='codeengine.cloud.ibm.com/v1beta1'or job.get('kind')!='JobDefinition'or metadata.get('name')!=value['names'][action]or metadata.get('namespace')!=namespace or not metadata.get('uid'):raise ValueError('Use the actual owned IBM JobDefinition')
        name=value['names'][action]+'-timer';current=get_resource(env,'pingsources.sources.knative.dev',name,namespace,optional=True)
        if current is not None:ownership(current,job,namespace,prefix,name)
        pending.append((action,job,name,current))
    for action,job,name,current in pending:
        spec=schedule_spec(job,action)
        if install:
            if current is None:
                document={'apiVersion':'sources.knative.dev/v1','kind':'PingSource','metadata':{'name':name,'namespace':namespace,'labels':{'atmem.ai/operator-package':prefix},'ownerReferences':[{'apiVersion':'codeengine.cloud.ibm.com/v1beta1','kind':'JobDefinition','name':job['metadata']['name'],'uid':job['metadata']['uid'],'controller':False,'blockOwnerDeletion':False}]},'spec':spec}
                kubectl(env,['create','-f','-','-o','json'],document)
            elif any(current.get('spec',{}).get(key)!=child for key,child in spec.items()):
                # Retain existing metadata/UID and resourceVersion. Native API
                # conflicts fail; never --force, adopt or retry an overwrite.
                document=copy.deepcopy(current);document.pop('status',None);document['spec']=spec
                kubectl(env,['replace','-f','-','-o','json'],document)
            kubectl(env,['wait','--for=condition=Ready','pingsources.sources.knative.dev/'+name,'--namespace',namespace,'--timeout=120s'])
        actual=get_resource(env,'pingsources.sources.knative.dev',name,namespace)
        ownership(actual,job,namespace,prefix,name);verify_ready(actual,spec)
        result.append({'action':action,'name':name,'uid':actual['metadata']['uid'],'generation':actual['metadata']['generation'],'ready':True})
    print(json.dumps({'format':'invoice-ibm-schedules-v1','sources':result,'jobExecutionValidated':False}))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['initialize','maintain','monitor','install-schedules','check-schedules']);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    value=configuration();scheduling=args.action in {'install-schedules','check-schedules'}
    if not args.execute:
        plan=commands(value,'monitor')[:2]if scheduling else commands(value,args.action)
        print(json.dumps({'execute':False,'commands':plan,'cloudOperations':False,'schedules':{action:{'job':value['names'][action],'cron':'17 2 * * *'if action=='maintain'else'7 * * * *','timezone':'UTC'}for action in ['maintain','monitor']}if scheduling else None}));return
    with private_context()as env:
        if scheduling:schedules(value,env,args.action=='install-schedules')
        else:
            for index,command in enumerate(commands(value,args.action)):subprocess.run(command,cwd=ROOT,env=env,check=True,timeout=1100 if index==2 else 120)

if __name__=='__main__':main()
`;
