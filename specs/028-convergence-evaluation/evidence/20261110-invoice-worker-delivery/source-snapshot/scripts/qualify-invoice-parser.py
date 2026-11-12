"""Exact locked credentialless Linux parser image; synthetic fixtures only."""
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--docker-host',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket():raise ValueError('Use an existing local Unix Docker socket')
    out=Path(args.out).resolve()
    if not out.is_relative_to(ROOT/'.local')or out.exists():raise ValueError('Use a fresh local evidence directory')
    out.mkdir(parents=True);runtime=ROOT/'src/runtime';lock=json.loads((runtime/'invoice-parser-lock.json').read_text());dockerfile=(runtime/'invoice-parser.Dockerfile').read_text()
    for group in ['packages','builderPackages']:
        if not isinstance(lock.get(group),list)or not lock[group]:raise ValueError('Review the complete runtime and builder dependency closures')
        for index,package in enumerate(lock[group]):
            line='ADD --checksum=sha256:'+package['sha256']+' '+package['url']+' /packages/'+str(index).zfill(3)+'.deb'
            if line not in dockerfile:raise ValueError('Parser Dockerfile differs from the reviewed native package lock')
    source=lock['tesseractSource']
    if 'ADD --checksum=sha256:'+source['sha256']+' '+source['url']+' /tmp/tesseract.tar.gz'not in dockerfile:raise ValueError('Missing pinned OCR source')
    image_sources=[runtime/name for name in ['invoice_document.py','invoice_extraction.py','structured_output.py','invoice_parser_cli.py','invoice_parser_service.py','invoice-parser.Dockerfile','invoice-parser-lock.json']]
    sources=list(image_sources)
    sources+=[Path(__file__).resolve(),ROOT/'tests/runtime/invoice_document_acceptance.py',ROOT/'tests/runtime/invoice_extraction_acceptance.py',*list((ROOT/'benchmarks/convergence/fixtures/invoices').iterdir())]
    hashes={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in sources if path.is_file()};checks=[];image=None;started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='atmem-ocr-qualification-')as scratch:
        folder=Path(scratch);config=folder/'docker-config';config.mkdir();(config/'config.json').write_text(json.dumps({'cliPluginsExtraDirs':['/opt/homebrew/lib/docker/cli-plugins']if Path('/opt/homebrew/lib/docker/cli-plugins').is_dir()else[]}))
        env={'PATH':os.environ.get('PATH',''),'HOME':scratch,'DOCKER_CONFIG':str(config),'DOCKER_HOST':args.docker_host}
        def run(label,command,*,input=None,expected=0,timeout=180):
            result=subprocess.run(['docker',*command],cwd=ROOT,env=env,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
            (out/(label+'.stdout')).write_bytes(result.stdout);(out/(label+'.stderr')).write_bytes(result.stderr)
            check={'check':label,'passed':result.returncode==expected,'exitCode':result.returncode,'expectedExitCode':expected};checks.append(check)
            if not check['passed']:raise RuntimeError('Local parser check failed: '+label)
            return result.stdout
        try:
            context=folder/'context';context.mkdir()
            for path in image_sources:shutil.copy2(path,context/path.name)
            run('build',['build','--platform','linux/amd64','--network','none','--file',str(context/'invoice-parser.Dockerfile'),'--tag','atmem-qualification/invoice-parser:local',str(context)],timeout=300)
            image=json.loads(run('image',['image','inspect','atmem-qualification/invoice-parser:local']))[0]
            if image['Os']!='linux'or image['Architecture']!='amd64'or image['Config']['User']!='10001:10001':raise ValueError('Unexpected parser image platform/user')
            base=['run','--rm','--platform','linux/amd64','--network','none','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--memory','512m','--cpus','1','--pids-limit','32','--cap-drop','ALL','--security-opt','no-new-privileges:true','-i',image['Id']]
            dependency_probe="""import hashlib,json,subprocess
from pathlib import Path
binary=Path('/usr/local/bin/tesseract')
version=subprocess.check_output([str(binary),'--version'],stderr=subprocess.STDOUT,text=True)
links=subprocess.check_output(['ldd',str(binary)],text=True)
packages=subprocess.check_output(['dpkg-query','-W','-f=${Package} ${Version}\\n'],text=True)
assert version.startswith('tesseract 5.5.3')
assert all(term not in links for term in ['libxml2','libarchive','libcurl'])
assert all(not line.startswith(('libxml2 ','libarchive13t64 ','tesseract-ocr ','libtesseract5 '))for line in packages.splitlines())
print(json.dumps({'upstreamVersion':version,'binarySha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'dynamicDependencies':links,'installedPackages':packages,'optionalArchiveAndUrlFeatures':'disabled at source; corresponding libraries absent'}))
"""
            run('native-dependency-surface',base+['python','-I','-c',dependency_probe])
            assets={}
            for path in sources[len(image_sources)+1:]:
                if path.is_file():assets[str(path.relative_to(ROOT))]=base64.b64encode(path.read_bytes()).decode()
            # Delivery-image code remains in /app. Only fixtures/test tools go to
            # writable tmpfs; the source under test is never replaced by a mock.
            wrapper="""import base64,json,sys,unittest
from pathlib import Path,PurePosixPath
root=Path('/tmp/qualification');root.mkdir()
for name,value in json.load(sys.stdin).items():
 path=PurePosixPath(name)
 if path.is_absolute()or '..'in path.parts:raise ValueError('Unsafe fixture path')
 target=root.joinpath(*path.parts);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(value,validate=True))
sys.path.insert(0,'/app')
suite=unittest.defaultTestLoader.discover(str(root/'tests/runtime'),pattern='invoice_*acceptance.py')
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.testsRun==10
raise SystemExit(0 if result.wasSuccessful()else 1)
"""
            run('native-acceptance',base+['python','-I','-c',wrapper],input=json.dumps(assets).encode())
            rpc_probe="""import base64,hashlib,http.client,json,sys,threading
sys.path.insert(0,'/app')
from invoice_parser_service import ParserServer
from invoice_document import PdfDocument
server=ParserServer(('127.0.0.1',0),PdfDocument());thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
 for name,encoded in json.load(sys.stdin).items():
  raw=base64.b64decode(encoded);client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=115)
  client.request('POST','/extract',body=raw,headers={'Content-Type':'application/pdf'});response=client.getresponse();value=json.loads(response.read(120501));client.close()
  if name.endswith('encrypted.pdf'):assert response.status==422 and value['status']=='rejected'
  else:
   assert response.status==200 and value['status']=='ok'and value['document']['sha256']==hashlib.sha256(raw).hexdigest()
   assert any('42.50'in page['ocr']for page in value['document']['pages'])
  print(json.dumps({'fixture':name,'status':response.status,'originalSha256':hashlib.sha256(raw).hexdigest()}))
finally:server.shutdown();server.server_close();thread.join(timeout=2)
"""
            rpc_cases={name:base64.b64encode((ROOT/'benchmarks/convergence/fixtures/invoices'/name).read_bytes()).decode()for name in ['invoice-mixed.pdf','invoice-encrypted.pdf']}
            run('private-rpc-native-parser',base+['python','-I','-c',rpc_probe],input=json.dumps(rpc_cases).encode())
            for name in ['invoice-text.pdf','invoice-scan.pdf','invoice-mixed.pdf','invoice-encrypted.pdf']:
                raw=(ROOT/'benchmarks/convergence/fixtures/invoices'/name).read_bytes();rejected='encrypted'in name
                reply=json.loads(run('cli-'+name,base,input=raw,expected=2 if rejected else 0))
                if rejected:
                    if reply.get('status')!='rejected':raise ValueError('Encrypted parser input was not rejected')
                elif reply.get('status')!='ok'or reply['document']['sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('Parser protocol source digest mismatch')
        except Exception as error:
            checks.append({'check':'qualification','passed':False,'error':str(error)[:500]})
    unchanged=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items())
    receipt={'kind':'credentialless-linux-invoice-parser','recordedAt':datetime.now(timezone.utc).isoformat(),'passed':bool(image)and unchanged and all(check['passed']for check in checks),'seconds':round(time.monotonic()-started,3),'imageId':image['Id']if image else None,'sourceHashes':hashes,'sourceUnchanged':unchanged,'checks':checks,'limits':{'memoryMiB':512,'cpus':1,'pids':32,'tmpfsMiB':64,'readOnly':True,'network':'none','user':'10001:10001','capabilities':'none'},'evidenceBoundary':'Exact pinned Linux image, actual native PDF/OCR and scripted-model decoder tests, actual CLI protocol. Synthetic visually reviewed English fixtures only; no native cloud model/identity/storage/API, remote parser hosting, broad hostile corpus, security scan or complete project evidence.','cloudOperations':False,'imagePublished':False}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':receipt['passed'],'imageId':receipt['imageId'],'receipt':str(out/'receipt.json')}));sys.exit(0 if receipt['passed']else 1)
