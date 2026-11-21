"""Run the emitted IBM schedule reconciler against explicit offline CLI processes."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
FAKE_KUBECTL=r'''
import json,os,sys
from pathlib import Path
p=Path(os.environ['SYNTHETIC_STATE']);s=json.loads(p.read_text());a=sys.argv[1:]
assert os.environ['KUBECONFIG']==str(Path(os.environ['QUALIFIED_PACKAGE_ROOT'])/'.local/ibm-operator-cli/operator-kubeconfig')
def save():p.write_text(json.dumps(s))
if a==['config','view','--minify','-o','jsonpath={.contexts[0].context.namespace}']:print('fixture-project');sys.exit(0)
if a[0]=='get':
 assert a[3:7]==['--namespace','fixture-project','-o','json']
 if s.get('observationFailure'):sys.exit(7)
 if a[1]=='jobdefinitions.codeengine.cloud.ibm.com':print(json.dumps(s['jobs'][a[2]]));sys.exit(0)
 assert a[1]=='pingsources.sources.knative.dev'
 v=s['sources'].get(a[2])
 if v is None:
  assert a[7:]==['--ignore-not-found'];sys.exit(0)
 print(json.dumps(v));sys.exit(0)
if a[0]in ['create','replace']:
 assert a[1:]==['-f','-','-o','json'];v=json.load(sys.stdin);name=v['metadata']['name'];old=s['sources'].get(name)
 s['attempts'].append(a[0]);save()
 if a[0]=='create':
  if old is not None:sys.exit(8)
  v['metadata'].update(uid='source-'+name,resourceVersion='1',generation=1)
 else:
  assert old is not None and v['metadata']['resourceVersion']==old['metadata']['resourceVersion']and v['metadata']['uid']==old['metadata']['uid']
  if s.get('replaceConflict'):sys.exit(9)
  v['metadata']['resourceVersion']=str(int(old['metadata']['resourceVersion'])+1);v['metadata']['generation']+=1
 v['status']={'observedGeneration':v['metadata']['generation']-(1 if s.get('staleGeneration')else 0),'conditions':[{'type':'Ready','status':'True'}]}
 s['sources'][name]=v;save();print(json.dumps(v));sys.exit(0)
if a[0]=='wait':
 assert a[1]=='--for=condition=Ready'and a[3:]==['--namespace','fixture-project','--timeout=120s'];sys.exit(0)
raise AssertionError(a)
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    native=Path(args.native).resolve();out=Path(args.out).resolve()
    if any(not p.is_relative_to(ROOT/'.local')for p in [native,out])or out.exists():raise ValueError('Use qualified local artifact and fresh output')
    receipt=json.loads((native/'qualification.json').read_text());source=native/'scripts/run-operator.py';digest=hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt['passed']and receipt['provider']=='ibm'and receipt['sourceHashes']['scripts/run-operator.py']==digest
    out.mkdir();binary=out/'fake-bin';binary.mkdir();configuration=out/'outputs.json';state=out/'state.json';calls=out/'calls.json';checks=[]
    header='#!'+sys.executable+'\n'
    (binary/'terraform').write_text(header+"import os,sys\nfrom pathlib import Path\nassert sys.argv[1:]==['output','-json','operator_jobs']and str(Path.cwd())==os.environ['QUALIFIED_PACKAGE_ROOT']\nprint(Path(os.environ['SYNTHETIC_OUTPUT']).read_text())\n")
    (binary/'ibmcloud').write_text(header+"import os,sys,json\nfrom pathlib import Path\nassert os.environ['IBMCLOUD_HOME']==str(Path(os.environ['QUALIFIED_PACKAGE_ROOT'])/'.local/ibm-operator-cli')\np=Path(os.environ['SYNTHETIC_CALLS']);calls=json.loads(p.read_text())if p.exists()else[];calls.append(sys.argv[1:]);p.write_text(json.dumps(calls))\n")
    (binary/'kubectl').write_text(header+FAKE_KUBECTL)
    for file in binary.iterdir():file.chmod(0o700)
    home=native/'.local/ibm-operator-cli';home.mkdir(parents=True,mode=0o700,exist_ok=True)
    env={'PATH':str(binary)+os.pathsep+os.defpath,'SYNTHETIC_OUTPUT':str(configuration),'SYNTHETIC_STATE':str(state),'SYNTHETIC_CALLS':str(calls),'QUALIFIED_PACKAGE_ROOT':str(native)}
    value={'account':'a'*32,'region':'au-syd','projectId':'11111111-1111-4111-8111-111111111111','maintenanceEnabled':True,'operatorSecret':'invoice-0123456789ab-operator-sql','names':{action:'invoice-0123456789ab-'+action for action in ['initialize','maintain','monitor']}}
    configuration.write_text(json.dumps(value))
    initial={'jobs':{name:{'apiVersion':'codeengine.cloud.ibm.com/v1beta1','kind':'JobDefinition','metadata':{'name':name,'namespace':'fixture-project','uid':'job-'+action}}for action,name in value['names'].items()},'sources':{},'attempts':[]}
    def run(name,action='install-schedules',execute=True):
        result=subprocess.run([sys.executable,'-I',str(source),action,*(['--execute']if execute else[])],env=env,cwd=out,capture_output=True,timeout=10)
        (out/(name+'.stdout.log')).write_bytes(result.stdout);(out/(name+'.stderr.log')).write_bytes(result.stderr);return result
    def store(s):state.write_text(json.dumps(s))
    def load():return json.loads(state.read_text())
    store(initial);result=run('preview',execute=False);assert result.returncode==0 and not calls.exists()and load()==initial;checks.append('schedule-preview-no-native-CLI')
    result=run('create');assert result.returncode==0;created=load();assert created['attempts']==['create','create']and len(created['sources'])==2
    for action in ['maintain','monitor']:
        item=created['sources'][value['names'][action]+'-timer'];assert item['spec']['sink']['ref']['name']==value['names'][action]and item['metadata']['ownerReferences'][0]['uid']=='job-'+action
    assert json.loads(result.stdout.splitlines()[-1])['jobExecutionValidated']is False
    assert json.loads(calls.read_text())==[['target','-c','a'*32,'-r','au-syd'],['ce','project','select','--id',value['projectId'],'--quiet','--kubecfg']];checks.append('only-two-owned-UTC-job-sources-created')
    result=run('idempotent');assert result.returncode==0 and load()==created;checks.append('idempotent-no-overwrite')
    result=run('observe','check-schedules');assert result.returncode==0 and load()==created;checks.append('observe-ready-configuration-without-write')
    modified=copy.deepcopy(created);target=value['names']['maintain']+'-timer';modified['sources'][target]['spec']['schedule']='* * * * *';modified['sources'][target]['metadata']['annotations']={'existing':'preserve'};store(modified)
    result=run('repair');assert result.returncode==0;repaired=load();assert repaired['attempts']==['create','create','replace']and repaired['sources'][target]['metadata']['annotations']=={'existing':'preserve'}and repaired['sources'][target]['metadata']['generation']==2;checks.append('owned-update-preserves-metadata-and-resource-version')
    unrelated=copy.deepcopy(initial);unrelated['sources']=copy.deepcopy(created['sources']);unrelated['sources'][value['names']['monitor']+'-timer']['metadata']['labels']={};store(unrelated)
    result=run('foreign-source');assert result.returncode!=0 and load()['attempts']==[];checks.append('foreign-source-refused-before-either-write')
    unrelated=copy.deepcopy(created);unrelated['jobs'][value['names']['monitor']]['metadata']['uid']='recreated-unrelated-job';unrelated['attempts']=[];store(unrelated)
    result=run('recreated-job');assert result.returncode!=0 and load()['attempts']==[];checks.append('job-UID-replacement-refused')
    conflict=copy.deepcopy(modified);conflict['replaceConflict']=True;conflict['attempts']=[];store(conflict)
    result=run('conflict');assert result.returncode!=0 and load()['attempts']==['replace']and load()['sources']==modified['sources'];checks.append('native-conflict-not-forced-or-retried')
    failed=copy.deepcopy(initial);failed['observationFailure']=True;store(failed);result=run('observation-failed');assert result.returncode!=0 and load()['attempts']==[];checks.append('observation-error-not-treated-as-absence')
    stale=copy.deepcopy(created);stale['attempts']=[]
    for item in stale['sources'].values():item['status']['observedGeneration']=0
    store(stale);result=run('stale-ready','check-schedules');assert result.returncode!=0 and load()['attempts']==[];checks.append('stale-Ready-generation-refused')
    configuration.write_text(json.dumps({**value,'maintenanceEnabled':False}));store(initial);calls.unlink();result=run('disabled-install');assert result.returncode!=0 and not calls.exists()and load()['attempts']==[];checks.append('unreviewed-maintenance-disabled-before-native-selection')
    receipt={'kind':'actual-emitted-IBM-schedule-helper-offline-fake-CLI','passed':len(checks)==11 and hashlib.sha256(source.read_bytes()).hexdigest()==digest,'checks':checks,'sourceSha256':digest,'nativeReceiptSha256':hashlib.sha256((native/'qualification.json').read_bytes()).hexdigest(),'cloudOperations':False,'boundary':'Actual emitted helper and separate explicit fake Terraform/IBM/kubectl executables. Kubernetes objects are synthetic fixtures, not proof of IBM API acceptance, real authentication, source delivery, native task/SQL execution, logging or deployment.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));sys.exit(0 if receipt['passed']else 1)
