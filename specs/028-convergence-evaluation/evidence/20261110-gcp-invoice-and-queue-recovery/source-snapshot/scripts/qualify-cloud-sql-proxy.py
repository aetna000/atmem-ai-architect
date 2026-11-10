"""Qualify the pinned proxy image interface locally; never connect to Cloud SQL."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--docker-host',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    out=Path(args.out).resolve();lock_path=ROOT/'src/runtime/cloud-sql-proxy-lock.json';lock=json.loads(lock_path.read_text())
    if out.exists()or not out.is_relative_to(ROOT/'.local'):raise ValueError('Use a fresh local evidence directory')
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket():raise ValueError('Use the owned existing Docker socket')
    out.mkdir(parents=True)
    env={'PATH':os.environ['PATH'],'DOCKER_HOST':args.docker_host,'DOCKER_CONFIG':str(ROOT/'.local/qualification-docker-config')};checks=[]
    for flag in ['--version','--help']:
        result=subprocess.run(['docker','run','--rm','--platform','linux/amd64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true',lock['image'],flag],env=env,capture_output=True,timeout=30)
        (out/(flag[2:]+'.stdout')).write_bytes(result.stdout);(out/(flag[2:]+'.stderr')).write_bytes(result.stderr)
        checks.append({'argument':flag,'exitCode':result.returncode,'passed':result.returncode==0})
    # Inspect the executable platform manifest, not the multi-platform OCI index:
    # an index has no runtime user/config/architecture and cannot prove these.
    result=subprocess.run(['docker','image','inspect','--platform','linux/amd64',lock['image']],env=env,capture_output=True,timeout=15)
    (out/'image-inspect.stdout').write_bytes(result.stdout);(out/'image-inspect.stderr').write_bytes(result.stderr)
    metadata=json.loads(result.stdout)[0]if result.returncode==0 else{}
    checks.append({'check':'actual-linux-amd64-nonroot-platform-manifest','passed':metadata.get('Os')=='linux'and metadata.get('Architecture')=='amd64'and metadata.get('Config',{}).get('User')=='65532'})
    checks.append({'check':'locked-version-and-required-private-loopback-flags','passed':('version '+lock['version']+'+container')in(out/'version.stdout').read_text()and all(flag in(out/'help.stdout').read_text()for flag in ['--private-ip','--address','--port','--structured-logs'])})
    passed=all(check['passed']for check in checks)
    receipt={'kind':'pinned-cloud-sql-proxy-local-interface','recordedAt':datetime.now(timezone.utc).isoformat(),'image':lock['image'],'platformManifestId':metadata.get('Id'),'passed':passed,'checks':checks,'sourceHashes':{'scripts/qualify-cloud-sql-proxy.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'src/runtime/cloud-sql-proxy-lock.json':hashlib.sha256(lock_path.read_bytes()).hexdigest()},'cloudOperations':False,'boundary':'Actual pinned upstream Linux image version, CLI flags and nonroot default only. No native Cloud SQL/TLS/IAM/private-network connection evidence.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':passed,'receipt':str(out/'receipt.json')}));return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
