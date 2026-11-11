#!/usr/bin/env python3
"""Exercise the exported offline helper with real installed tools, no model code."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.engineering_delivery import seed_delivery
OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-uncoached-product-run/portable-helper'
OUT.mkdir(parents=True,exist_ok=True)
config=json.loads((ROOT/'.local/engineering-preview/operator-toolchain.json').read_text())
receipt={'passed':False,'cloudOperations':False,'downloads':False}
with tempfile.TemporaryDirectory(prefix='atmem-portable-receiver-') as folder:
    root=Path(folder);pinned=seed_delivery(root)
    env={'PATH':os.environ.get('PATH',''),'HOME':folder,'CHECKPOINT_DISABLE':'1','PYTHONDONTWRITEBYTECODE':'1'}
    command=[sys.executable,str(root/'atmem-tools/prepare.py'),'--python',config['tools']['python'],
        '--node',config['tools']['node'],'--terraform',config['tools']['terraform'],'--provider-mirror',config['tools']['providerMirror'],
        '--require','python','--require','node','--require','terraform','--require','providerMirror']
    setup=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=15)
    assert setup.returncode==0,setup.stderr
    result=json.loads(setup.stdout);assert not result['downloads'] and not result['cloudAccess']
    env.update(OPENSSL_CONF=str(root/'.worker-tmp/openssl.cnf'),TF_CLI_CONFIG_FILE=str(root/'.worker-tmp/terraform.rc'))
    checks=[]
    for name,args in [('python',[str(root/'.tools/python'),'--version']),('node',[str(root/'.tools/node'),'--version']),
                      ('terraform',[str(root/'.tools/terraform'),'version','-json'])]:
        tested=subprocess.run(args,cwd=root,env=env,capture_output=True,text=True,timeout=15)
        assert tested.returncode==0,(name,tested.stderr)
        checks.append({'tool':name,'exitCode':tested.returncode,'versionOutput':tested.stdout.strip()})
    for name,digest in pinned.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
    second=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=15);assert second.returncode==0
    receipt.update(passed=True,checks=checks,inputDigests=pinned,idempotentSetup=True,
        boundary='Backend-owned public helper copied into a fresh receiving project with no .tools/.worker-tmp. Actual installed Python/Node/Terraform aliases execute version commands; an explicit existing offline provider mirror is configured. No generated client code, dependency download, account lookup or deployment is executed. This is tooling closure, not project runtime correctness.')
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('Passed fresh receiving-project offline tool setup, real executable aliases and idempotent input preservation.')
