"""Check the actual emitted IBM helper using explicit offline CLI executables."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    native=Path(args.native).resolve();out=Path(args.out).resolve()
    if any(not p.is_relative_to(ROOT/'.local')for p in [native,out])or out.exists():raise ValueError('Use an owned native qualification and fresh local output')
    receipt=json.loads((native/'qualification.json').read_text());source=native/'scripts/run-operator.py';digest=hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt['passed']and receipt['provider']=='ibm'and receipt['sourceHashes']['scripts/run-operator.py']==digest
    out.mkdir();binary=out/'fake-bin';binary.mkdir();configuration=out/'outputs.json';calls=out/'calls.json';checks=[]
    header='#!'+sys.executable+'\n'
    (binary/'terraform').write_text(header+"import os,sys\nfrom pathlib import Path\nassert sys.argv[1:]==['output','-json','operator_jobs']\nassert str(Path.cwd())==os.environ['QUALIFIED_PACKAGE_ROOT']\nprint(Path(os.environ['SYNTHETIC_OUTPUT']).read_text())\n")
    (binary/'ibmcloud').write_text(header+"import os,sys,json\nfrom pathlib import Path\nassert os.environ['IBMCLOUD_HOME']==str(Path(os.environ['QUALIFIED_PACKAGE_ROOT'])/'.local/ibm-operator-cli')\nassert os.environ['IBMCLOUD_TRACE']=='false'\np=Path(os.environ['SYNTHETIC_CALLS']);calls=json.loads(p.read_text())if p.exists()else[];calls.append(sys.argv[1:]);p.write_text(json.dumps(calls))\nif os.environ.get('SYNTHETIC_FAIL_SELECT')and sys.argv[1:3]==['ce','project']:sys.exit(9)\n")
    for file in binary.iterdir():file.chmod(0o700)
    env={'PATH':str(binary)+os.pathsep+os.defpath,'SYNTHETIC_OUTPUT':str(configuration),'SYNTHETIC_CALLS':str(calls),'QUALIFIED_PACKAGE_ROOT':str(native),'IBMCLOUD_TRACE':'true'}
    value={'account':'a'*32,'region':'au-syd','projectId':'11111111-1111-4111-8111-111111111111','maintenanceEnabled':True,'operatorSecret':'invoice-0123456789ab-operator-sql','names':{action:'invoice-0123456789ab-'+action for action in ['initialize','maintain','monitor']}}
    configuration.write_text(json.dumps(value))
    def run(name,arguments,extra=None):
        result=subprocess.run([sys.executable,'-I',str(source),*arguments],env={**env,**(extra or{})},cwd=out,capture_output=True,timeout=10)
        (out/(name+'.stdout.log')).write_bytes(result.stdout);(out/(name+'.stderr.log')).write_bytes(result.stderr);return result
    result=run('preview',['initialize']);assert result.returncode==0 and json.loads(result.stdout)['cloudOperations']is False and not calls.exists();checks.append('preview-no-cloud-cli')
    result=run('missing-private-context',['monitor','--execute']);assert result.returncode!=0 and not calls.exists();checks.append('no-global-auth-fallback')
    home=native/'.local/ibm-operator-cli';home.mkdir(parents=True,mode=0o700)
    for action in ['initialize','maintain','monitor']:
        calls.unlink(missing_ok=True);result=run('execute-'+action,[action,'--execute']);assert result.returncode==0
        expected=[['target','-c',value['account'],'-r','au-syd'],['ce','project','select','--id',value['projectId'],'--quiet'],['ce','jobrun','submit','--job',value['names'][action],'--wait','--wait-timeout','1000']]
        assert json.loads(calls.read_text())==expected;checks.append('explicit-private-context-and-fixed-'+action)
    home.chmod(0o755);calls.unlink();result=run('public-context-refused',['monitor','--execute']);assert result.returncode!=0 and not calls.exists();checks.append('public-auth-directory-refused');home.chmod(0o700)
    with (home/'operator.lock').open('w')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);result=run('concurrent-operation',['monitor','--execute']);assert result.returncode!=0 and not calls.exists();checks.append('concurrent-context-mutation-refused')
    result=run('project-selection-failed',['monitor','--execute'],{'SYNTHETIC_FAIL_SELECT':'true'});assert result.returncode!=0 and len(json.loads(calls.read_text()))==2;checks.append('failed-project-selection-stops-before-submit');calls.unlink()
    for name,body in [('injected-account',json.dumps({**value,'account':'--apikey=foreign'})),('mixed-jobs',json.dumps({**value,'names':{**value['names'],'monitor':'invoice-ffffffffffff-monitor'}})),('duplicate-fields','{"account":"a","account":"b"}')]:
        configuration.write_text(body);result=run(name,['monitor','--execute']);assert result.returncode!=0 and not calls.exists();checks.append(name+'-refused')
    receipt={'kind':'actual-emitted-IBM-operator-runner-offline-fake-CLI','passed':len(checks)==11 and hashlib.sha256(source.read_bytes()).hexdigest()==digest,'checks':checks,'sourceSha256':digest,'nativeReceiptSha256':hashlib.sha256((native/'qualification.json').read_bytes()).hexdigest(),'cloudOperations':False,'boundary':'Actual emitted helper with separate explicitly fake Terraform/IBM CLI processes. No real CLI authentication, SQL runtime, native task execution, scheduling, alerts or deployment.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));sys.exit(0 if receipt['passed']else 1)
