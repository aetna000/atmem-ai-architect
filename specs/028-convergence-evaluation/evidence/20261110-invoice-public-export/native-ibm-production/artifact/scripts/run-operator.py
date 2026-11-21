"""Preview or explicitly execute a fixed owned IBM Code Engine task."""
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
