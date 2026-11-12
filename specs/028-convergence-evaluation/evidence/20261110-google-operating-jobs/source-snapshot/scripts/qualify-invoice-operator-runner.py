"""Execute the actual emitted Google CLI helper against explicit local fake CLIs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native',required=True);parser.add_argument('--out',required=True);args=parser.parse_args();native=Path(args.native).resolve();out=Path(args.out).resolve()
    if any(not path.is_relative_to(ROOT/'.local')for path in [native,out])or out.exists():raise ValueError('Use a qualified local artifact and fresh local output')
    qualification=json.loads((native/'qualification.json').read_text());source=native/'scripts/run-operator.py';sha=hashlib.sha256(source.read_bytes()).hexdigest();assert qualification['passed']and qualification['provider']=='gcp'and qualification['sourceHashes']['scripts/run-operator.py']==sha
    out.mkdir();bin=out/'fake-bin';bin.mkdir();config=out/'synthetic-outputs.json';calls=out/'fake-gcloud-calls.json'
    header='#!'+sys.executable+'\n'
    (bin/'terraform').write_text(header+"import os,sys\nfrom pathlib import Path\nassert sys.argv[1:]==['output','-json','operator_jobs']\nprint(Path(os.environ['OWNED_SYNTHETIC_OUTPUTS']).read_text())\n")
    (bin/'gcloud').write_text(header+"import os,sys,json\nfrom pathlib import Path\np=Path(os.environ['OWNED_SYNTHETIC_CALLS']);calls=json.loads(p.read_text())if p.exists()else[];calls.append(sys.argv[1:]);p.write_text(json.dumps(calls));print(json.dumps({'fixture':'fake-gcloud-completed'}))\n")
    for file in bin.iterdir():file.chmod(0o700)
    env={'PATH':str(bin)+os.pathsep+os.defpath,'OWNED_SYNTHETIC_OUTPUTS':str(config),'OWNED_SYNTHETIC_CALLS':str(calls)}
    value={'project':'reviewed-project','region':'australia-southeast1','names':{action:'invoice-fixture-'+action for action in ['initialize','maintain','monitor']}}
    config.write_text(json.dumps(value));checks=[]
    def run(name,arguments):
        result=subprocess.run([sys.executable,'-I',str(source),*arguments],env=env,cwd=native,capture_output=True,timeout=10);(out/(name+'.stdout.log')).write_bytes(result.stdout);(out/(name+'.stderr.log')).write_bytes(result.stderr);return result
    preview=run('preview',['initialize']);assert preview.returncode==0 and json.loads(preview.stdout)['willWrite']is False and not calls.exists();checks.append('preview-no-gcloud-write')
    execute=run('execute',['monitor','--execute']);assert execute.returncode==0
    actual=json.loads(calls.read_text());assert actual==[['run','jobs','execute','invoice-fixture-monitor','--project','reviewed-project','--region','australia-southeast1','--wait','--format=json']];checks.append('explicit-execute-fixed-argument-list-and-completion-wait')
    for name,body in [('foreign-job',json.dumps({**value,'names':{**value['names'],'monitor':'--args=untrusted'}})),('foreign-project',json.dumps({**value,'project':'--impersonate-service-account=foreign'})),('duplicate-fields','{"project":"reviewed-project","project":"foreign-project"}')]:
        config.write_text(body);result=run(name,['monitor','--execute']);assert result.returncode==1 and json.loads(calls.read_text())==actual;checks.append(name+'-refused-before-gcloud')
    receipt={'kind':'actual-emitted-Google-operator-runner-local-fake-CLI','passed':len(checks)==5 and hashlib.sha256(source.read_bytes()).hexdigest()==sha,'checks':checks,'sourceSha256':sha,'nativeReceiptSha256':hashlib.sha256((native/'qualification.json').read_bytes()).hexdigest(),'cloudOperations':False,'boundary':'Actual emitted Python command helper and separate explicit fake Terraform/gcloud executable processes. No real CLI authentication, native job execution or deployment.'};(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));sys.exit(0 if receipt['passed']else 1)
