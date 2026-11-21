"""Preview or explicitly execute one owned Google operator job from Terraform outputs."""
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
