import{v,r,l}from'./invoice-builder.mjs';

// IBM 2.9 supports JobDefinition, not a Terraform cron subscription resource.
// Keep job delivery separate from scheduling/alert acceptance under qualification.
export function ibmInvoiceOperations(b,n,{projectId,pull}){
 const{add}=b;
 b.variable.operations_enabled={type:'bool',default:false,description:'Create the three fixed SQL operating tasks after reviewed immutable image publication. Scheduling and alert acceptance are separate.'};
 b.examples.operations_enabled=false;b.testExpressions.operations_enabled='true';
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
 b.output.operator_jobs={value:{account:v('account_id'),region:b.region,projectId,operatorSecret:l('operator_secret_name'),names:Object.fromEntries(['initialize','maintain','monitor'].map(action=>[action,l('name')+'-'+action]))}};
 b.files['scripts/run-operator.py']=IBM_OPERATOR_RUNNER;
 b.files['OPERATING_JOBS.md']=IBM_OPERATING_JOBS;
 b.assertions.push(`run "operator_before_applications" {
 command = plan
 variables { applications_enabled = false }
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
 }
 expect_failures = [var.runtime_image]
}
`);
}

const IBM_OPERATING_JOBS=`# IBM fixed invoice operating tasks

This slice delivers initialize, maintain and monitor task definitions. It does not
yet deliver scheduled subscriptions or Cloud Logs alerts. Do not count it as full
operating acceptance or release the application on this evidence alone.

Foundation uses applications_enabled=false and operations_enabled=false. Publish
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

Each task uses one array index, no automatic retries and a 960-second platform
limit; the application enforces its own 900-second work deadline. Private SQL TLS,
actual native login privileges, task outcome, schedules and alert delivery still
need separately authorized destination checks. Provider schema/mocks are not
deployment, SQL runtime or scheduling evidence.
`;

const IBM_OPERATOR_RUNNER=`"""Preview or explicitly execute a fixed owned IBM Code Engine task."""
import argparse
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
    if not isinstance(value,dict)or set(value)!={'account','region','projectId','operatorSecret','names'}:raise ValueError('Use the owned operator_jobs output')
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

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['initialize','maintain','monitor']);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    plan=commands(configuration(),args.action)
    if not args.execute:
        print(json.dumps({'execute':False,'commands':plan,'cloudOperations':False}));return
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
        env={**os.environ,'IBMCLOUD_HOME':str(home),'IBMCLOUD_TRACE':'false'}
        for index,command in enumerate(plan):subprocess.run(command,cwd=ROOT,env=env,check=True,timeout=1100 if index==2 else 120)

if __name__=='__main__':main()
`;
