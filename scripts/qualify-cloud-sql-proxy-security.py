"""Check exact proxy Go-package findings with a compiled affected positive control.

Public vulnerability metadata only. No proxy/database connection or deployment.
JSON scanner exit zero is never interpreted as absence of vulnerabilities.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={'GO-2026-5932','GO-2026-6860','GO-2026-6866'}
CONTROL='''package main
import("fmt";"os";"golang.org/x/net/html";"golang.org/x/crypto/openpgp")
// Intentionally affected scanner control. Compile/scan only; never execute.
func main(){
 if len(os.Args)>1&&os.Args[1]=="html" {
  node,err:=html.Parse(os.Stdin);if err!=nil{panic(err)}
  if err=html.Render(os.Stdout,node);err!=nil{panic(err)}
 }else{keys,err:=openpgp.ReadArmoredKeyRing(os.Stdin);fmt.Println(len(keys),err)}
}
'''

def events(path):
    text=path.read_text();decoder=json.JSONDecoder();result=[]
    while text.strip():
        event,end=decoder.raw_decode(text.lstrip());result.append(event);text=text.lstrip()[end:]
    return result

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--docker-host',required=True);parser.add_argument('--govulncheck',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    out=Path(args.out).resolve();tool=Path(args.govulncheck).resolve();lock_path=ROOT/'src/runtime/cloud-sql-proxy-lock.json';lock=json.loads(lock_path.read_text())
    if out.exists()or not out.is_relative_to(ROOT/'.local')or not tool.is_relative_to(ROOT/'.local')or not tool.is_file():raise ValueError('Use a fresh local evidence directory and the pinned local scanner')
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket():raise ValueError('Use the owned existing Docker socket')
    out.mkdir(parents=True);checks=[]
    env={**os.environ,'DOCKER_HOST':args.docker_host,'DOCKER_CONFIG':str(ROOT/'.local/qualification-docker-config'),'GOTOOLCHAIN':'local','GOMODCACHE':str(ROOT/'.local/proxy-vulnerability-review-20261110/module-cache')}
    def run(name,command,*,timeout=90,expected=0):
        result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=timeout)
        (out/(name+'.stdout')).write_bytes(result.stdout);(out/(name+'.stderr')).write_bytes(result.stderr)
        checks.append({'check':name,'exitCode':result.returncode,'passed':result.returncode==expected})
        if result.returncode!=expected:raise RuntimeError('Qualification command failed: '+name)
        return result.stdout
    version=run('scanner-version',[str(tool),'-version']).decode()
    if'Scanner: govulncheck@v1.9.0'not in version:raise ValueError('Use the reviewed govulncheck v1.9.0')
    run('scanner-buildinfo',['go','version','-m',str(tool)])
    metadata=json.loads(run('image-inspect',['docker','image','inspect','--platform','linux/amd64',lock['image']]))[0]
    if metadata.get('Os')!='linux'or metadata.get('Architecture')!='amd64':raise ValueError('Use the actual executable platform manifest')
    container=run('create-owned-container',['docker','create','--platform','linux/amd64','--network','none',lock['image'],'--version']).decode().strip()
    try:run('extract-pinned-binary',['docker','cp',container+':/cloud-sql-proxy',str(out/'cloud-sql-proxy')])
    finally:run('remove-owned-container',['docker','rm',container])
    run('binary-buildinfo',['go','version','-m',str(out/'cloud-sql-proxy')])
    run('proxy-json',[str(tool),'-mode=binary','-json',str(out/'cloud-sql-proxy')])
    run('proxy-text',[str(tool),'-mode=binary','-show=verbose',str(out/'cloud-sql-proxy')])
    run('proxy-openvex',[str(tool),'-mode=binary','-format=openvex',str(out/'cloud-sql-proxy')])
    control=out/'positive-control';control.mkdir();(control/'main.go').write_text(CONTROL)
    (control/'go.mod').write_text('module atmem.local/proxy-vulnerability-control\n\ngo 1.26.0\n\nrequire (\n golang.org/x/net v0.61.0\n golang.org/x/crypto v0.58.0\n)\n')
    run('control-dependencies',['go','-C',str(control),'mod','tidy'])
    env.update({'CGO_ENABLED':'0','GOOS':'linux','GOARCH':'amd64'})
    run('control-build',['go','-C',str(control),'build','-trimpath','-o','control-linux-amd64','.'])
    run('control-json',[str(tool),'-mode=binary','-json',str(control/'control-linux-amd64')])
    proxy=events(out/'proxy-json.stdout');positive=events(out/'control-json.stdout')
    findings=[e['finding']for e in proxy if'finding'in e];controls=[e['finding']for e in positive if'finding'in e]
    checks.append({'check':'all-current-proxy-findings-are-reviewed-module-only-matches','passed':{f['osv']for f in findings}==EXPECTED and all(not frame.get('package')and not frame.get('function')for f in findings for frame in f['trace'])})
    checks.append({'check':'affected-control-reports-each-reviewed-package-and-compiled-symbol','passed':all(any(f['osv']==issue and any(frame.get('package')and frame.get('function')for frame in f['trace'])for f in controls)for issue in EXPECTED)})
    vex=json.loads((out/'proxy-openvex.stdout').read_text());statements=vex['statements']
    checks.append({'check':'official-scanner-marks-exact-three-findings-vulnerable-code-not-present','passed':{s['vulnerability']['name']for s in statements}==EXPECTED and all(s['status']=='not_affected'and s['justification']=='vulnerable_code_not_present'for s in statements)})
    binary_sha=sha(out/'cloud-sql-proxy');raw_vex_sha=sha(out/'proxy-openvex.stdout')
    scoped={**vex,'@id':'atmem-local-review:sha256:'+binary_sha,'author':'AtMem AI Architect local dependency qualification','sourceGovulncheckVexSha256':raw_vex_sha,'imageIndex':lock['image'],'platformManifest':metadata['Id'],'binarySha256':binary_sha}
    for statement in scoped['statements']:
        for product in statement['products']:product['@id']='pkg:oci/cloud-sql-proxy@'+metadata['Id']+'?arch=amd64&os=linux'
    (out/'scoped-openvex.json').write_text(json.dumps(scoped,indent=2)+'\n')
    receipt={'kind':'exact-proxy-compiled-package-applicability','recordedAt':datetime.now(timezone.utc).isoformat(),'passed':all(c['passed']for c in checks),'imageIndex':lock['image'],'platformManifest':metadata['Id'],'binarySha256':binary_sha,'scannerVersion':'v1.9.0','scannerSha256':sha(tool),'checks':checks,'moduleFindingsRetained':sorted(EXPECTED),'compiledAffectedControl':'Both affected modules deliberately linked into an unexecuted Linux binary; each reviewed issue must be detected at symbol level. Control compiler/standard-library findings do not describe the shipped proxy.','sourceHashes':{'scripts/qualify-cloud-sql-proxy-security.py':sha(Path(__file__)),'src/runtime/cloud-sql-proxy-lock.json':sha(lock_path)},'boundary':'Independent Go binary symbol/applicability analysis and affected positive control for this exact AMD64 artifact. Reviewed vulnerable packages are absent; module-version inventory is retained. No blanket absence of vulnerabilities, native database/TLS/IAM, or deployment claim. New findings or changed image require another review.','cloudOperations':False}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':receipt['passed'],'receipt':str(out/'receipt.json')}));return 0 if receipt['passed']else 1

if __name__=='__main__':raise SystemExit(main())
