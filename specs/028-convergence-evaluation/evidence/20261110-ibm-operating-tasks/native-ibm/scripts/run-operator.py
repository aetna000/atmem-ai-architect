"""Preview or explicitly execute a fixed owned IBM Code Engine task."""
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
