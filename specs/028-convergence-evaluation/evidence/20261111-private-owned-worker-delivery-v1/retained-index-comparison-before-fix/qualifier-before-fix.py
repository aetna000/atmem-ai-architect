"""Build the actual emitted application directory, consume its exact image.

Provider account/cloud operations are forbidden here. Parser sources are checked
byte-for-byte against their separately qualified recipes; no parser isolation or
whole-project acceptance is inferred from this application build.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import uuid
ROOT=Path(__file__).resolve().parents[1]


def qualify(args):
    directory=args.directory.resolve();out=args.out.resolve();core_path=args.core_receipt.resolve()
    if out.exists()or any(not path.is_relative_to(ROOT/'.local')for path in [directory,out,core_path]):raise ValueError('Use owned inputs and fresh evidence')
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket():raise ValueError('Use the owned Docker VM socket')
    source=json.loads((directory/'receipt.json').read_text());core=json.loads(core_path.read_text())
    if any(not value['passed']or value['cloudOperations']for value in [source,core]):raise ValueError('Require qualified source/image inputs')
    for value in [source,core]:
        for name,digest in value['sourceHashes'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Qualified source drift')
    for name,digest in source['emittedHashes'].items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=digest:raise ValueError('Emitted source drift')
    manifests=list(directory.glob('applications/*/application-manifest.json'))
    if len(manifests)!=1 or not re.fullmatch('block_[0-9a-f]+',manifests[0].parent.name):raise ValueError('Use one canonical owned application')
    app=manifests[0].parent;manifest=json.loads(manifests[0].read_text());provider=core['provider'];owned=json.loads((ROOT/'src/runtime/enterprise-application-manifest.json').read_text())
    if manifest['provider']!=provider or manifest['files']!=owned['files']+owned['providerFiles'][provider]or manifest['entrypoints']!=owned['entrypoints']:raise ValueError('Provider/source/entrypoint drift')
    for name in manifest['files']:
        if Path(name).name!=name:raise ValueError('Do not redirect application files')
        actual=(app/'runtime'/name).read_bytes();expected=(ROOT/'src/runtime'/name).read_bytes()
        if actual!=expected or hashlib.sha256(actual).hexdigest()!=manifest['sourceHashes'][name]:raise ValueError('Actual package source differs from reviewed implementation')
    for source_name,target in [('enterprise-runtime.Dockerfile','Dockerfile'),('enterprise-runtime-'+provider+'-python-lock.json','dependency-lock.json'),('python-container-lock.json','container-base.json')]:
        if (app/target).read_bytes()!=(ROOT/'src/runtime'/source_name).read_bytes():raise ValueError('Package build/lock/base drift')
    lock=json.loads((app/'dependency-lock.json').read_text())
    if (app/'requirements.lock').read_text()!=lock['requirements']:raise ValueError('Package dependency lock drift')
    for folder,names,recipe in [('parser',owned['parserFiles'],'enterprise-document.Dockerfile'),('parser/pdf',owned['pdfParserFiles'],'invoice-parser.Dockerfile')]:
        for name in names:
            if (app/folder/('Dockerfile'if name==recipe else name)).read_bytes()!=(ROOT/'src/runtime'/name).read_bytes():raise ValueError('Separate parser recipe/source drift')
    out.mkdir(parents=True);checks=[];passed=False
    env={'PATH':os.environ.get('PATH',''),'DOCKER_HOST':args.docker_host,'DOCKER_CONFIG':str(ROOT/'.local/qualification-docker-config'),'HOME':str(out)}
    def run(label,command,data=None):
        result=subprocess.run(['docker',*command],env=env,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=600)
        (out/(label+'.stdout')).write_bytes(result.stdout);(out/(label+'.stderr')).write_bytes(result.stderr)
        checks.append({'check':label,'passed':result.returncode==0,'exitCode':result.returncode})
        if result.returncode:raise ValueError('Emitted application qualification failed: '+label)
        return result.stdout
    try:
        tag='atmem-private-package-'+provider+':qualification-'+uuid.uuid4().hex
        run('emitted-build',['build','--platform','linux/amd64','--tag',tag,str(app)])
        info=json.loads(run('emitted-image',['image','inspect',tag]))[0]
        if info['Id']!=core['imageId']or info['Config']['User']!='10001:10001':raise ValueError('The emitted directory did not reproduce the qualified exact application image')
        payload={name:manifest['sourceHashes'][name]for name in manifest['files']}
        code='''import hashlib,importlib.util,json,sys
from pathlib import Path
value=json.load(sys.stdin)
for name,digest in value.items():assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest()==digest
assert not Path('/app/enterprise_document.py').exists()
assert not Path('/app/EnterpriseDocument.java').exists()
assert importlib.util.find_spec('pip')is None
print(json.dumps({'passed':True,'exactSourceFiles':len(value),'credentialedParserInstalled':False}))
'''
        result=run('installed-sources',['run','--rm','--platform','linux/amd64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','128m','--pids-limit','32','-i',info['Id'],'python','-I','-c',code],json.dumps(payload).encode())
        if json.loads(result)['passed']is not True:raise ValueError('Installed source identity mismatch')
        passed=True
    finally:
        (out/'receipt.json').write_text(json.dumps({'recordedAt':datetime.now(timezone.utc).isoformat(),'passed':passed,'provider':provider,'imageId':core['imageId'],'checks':checks,
            'sourceHashes':{str(Path(__file__).relative_to(ROOT)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            'inputHashes':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in [directory/'receipt.json',core_path,manifests[0]]},
            'cloudOperations':False,'wholeProjectQualified':False,'scope':'Actual emitted application directory reproduces the independently qualified image and installed source inventory. Separate parser recipes are byte-checked, not rebuilt/requalified. No full application hosting, source/model account, security or complete project acceptance.'},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--core-receipt',type=Path,required=True);parser.add_argument('--docker-host',required=True);qualify(parser.parse_args())
