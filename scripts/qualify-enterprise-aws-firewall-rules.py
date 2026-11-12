"""Check the actual owned Linux rule grammar using temporary, unlinked chains.

Never edits FORWARD, DOCKER-USER, existing rules, or a cloud account.
"""
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def qualify(out):
    out=out.resolve()
    if out.exists()or not out.is_relative_to(ROOT/'.local'):raise ValueError('Use fresh owned local evidence')
    source=ROOT/'src/runtime/enterprise_aws_host_probe.py';digest=hashlib.sha256(source.read_bytes()).hexdigest()
    # Import only this reviewed stdlib-only module inside the existing owned VM.
    # No host/container configuration is prepared by this grammar check.
    script='''import base64,json,shutil,subprocess,types,uuid
source=base64.b64decode(SOURCE,validate=True)
import hashlib
assert hashlib.sha256(source).hexdigest()==DIGEST
probe=types.ModuleType('owned_probe');exec(compile(source,'owned_probe','exec'),probe.__dict__)
checks=[]
for executable,destination in [('iptables','169.254.169.254/32'),('ip6tables','fd00:ec2::254/128')]:
 tool=shutil.which(executable);assert tool
 chain='ATMEM_Q_'+uuid.uuid4().hex[:12];created=False
 def run(*args):return subprocess.run([tool,'-w','2',*args],check=True,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=8).stdout.decode()
 try:
  run('-N',chain);created=True
  run('-A',chain,'-i','docker0','-d',destination,'-j','DROP')
  native=run('-S',chain)
  expected={'-i':'docker0','-d':destination,'-j':'DROP'}
  assert probe.first_rule_matches(native,chain,expected)
  run('-I',chain,'1','-j','ACCEPT')
  shadowed=run('-S',chain);assert not probe.first_rule_matches(shadowed,chain,expected)
  run('-D',chain,'-j','ACCEPT')
  assert probe.first_rule_matches(run('-S',chain),chain,expected)
  checks.append({'family':executable,'nativeRules':native,'shadowedRules':shadowed,'passed':True})
 finally:
  if created:
   run('-F',chain);run('-X',chain)
print(json.dumps({'passed':True,'checks':checks,'existingChainsModified':False}))
'''.replace('SOURCE',repr(base64.b64encode(source.read_bytes()).decode())).replace('DIGEST',repr(digest))
    out.mkdir(parents=True)
    done=subprocess.run(['colima','ssh','--profile','architect-qualification','--','sudo','python3','-I','-c',script],
                        stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=55)
    (out/'native.stdout').write_bytes(done.stdout);(out/'native.stderr').write_bytes(done.stderr)
    passed=False
    try:
        if done.returncode:raise ValueError('Owned native firewall grammar test failed')
        native=json.loads(done.stdout)
        if native.get('passed')is not True or len(native['checks'])!=2 or native['existingChainsModified']is not False:raise ValueError('Incomplete native grammar observation')
        if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise ValueError('Probe changed during native qualification')
        passed=True
    finally:
        (out/'receipt.json').write_text(json.dumps({'recordedAt':datetime.now(timezone.utc).isoformat(),'passed':passed,
            'sourceHashes':{str(source.relative_to(ROOT)):digest,str(Path(__file__).relative_to(ROOT)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            'cloudOperations':False,'scope':'Actual IPv4/IPv6 iptables grammar and shadowing in temporary unlinked chains in the owned qualification VM. Not ECS host policy, IMDS reachability, a cloud plan or deployment acceptance.'},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);qualify(parser.parse_args().out)
