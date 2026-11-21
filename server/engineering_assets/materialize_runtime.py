"""Copy the supplied shared runtime into a fresh owned application directory.

Offline source materialization only. No imports from the supplied application,
package installs, SQL, credential reads, model calls or cloud operations.
"""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import re


def unique(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('Duplicate runtime catalog field')
        value[key]=item
    return value


def materialize(root,provider,destination):
    root=Path(root).resolve(strict=True)
    if provider not in {'aws','azure','gcp','ibm'}:raise ValueError('Select the exact runtime provider')
    if type(destination)is not str or not destination or '\\'in destination:raise ValueError('Use a fresh relative application directory')
    relative=PurePosixPath(destination)
    if relative.is_absolute()or any(p in {'','.','..'}for p in destination.split('/'))or relative.parts[0]in {'.tools','.worker-tmp','.agents','.git','atmem-tools'}:raise ValueError('Use a fresh public application directory inside the project')
    target=root
    for part in relative.parts:
        target=target/part
        if target.is_symlink()or target.exists():
            if target.is_symlink()or not target.is_dir()or target==root/relative:raise ValueError('Runtime source cannot overwrite or follow project links')
    if (root/'atmem-tools').is_symlink():raise ValueError('Use project-owned runtime inputs')
    catalog=root/'atmem-tools/application-runtime.json'
    if catalog.is_symlink():raise ValueError('Use the pinned runtime catalog')
    raw=catalog.read_bytes()
    if len(raw)>1500000:raise ValueError('Runtime catalog exceeds its boundary')
    data=json.loads(raw,object_pairs_hook=unique)
    if type(data)is not dict or set(data)!={'format','version','files','providers','boundary'}or data['format']!='atmem.shared-application-runtime'or type(data['version'])is not int or data['version']!=1:raise ValueError('Use the supported shared runtime catalog')
    if type(data['files'])is not dict or not 1<=len(data['files'])<=64 or type(data['providers'])is not dict or set(data['providers'])!={'aws','azure','gcp','ibm'}:raise ValueError('Use the complete runtime inventory')
    files={}
    for name,entry in data['files'].items():
        if not re.fullmatch(r'[a-z][a-z0-9_]*\.(?:py|sql)',name)or type(entry)is not dict or set(entry)!={'content','sha256'}or type(entry['content'])is not str:raise ValueError('Use flat bounded runtime source files')
        content=entry['content'].encode()
        if len(content)>200000 or hashlib.sha256(content).hexdigest()!=entry['sha256']:raise ValueError('Runtime source differs from its supplied digest')
        files[name]=content
    native=data['providers'][provider]
    if type(native)is not dict or set(native)!={'requirements','testRequirements','sources','resolutions'}or any(type(native[k])is not str or not 1<=len(native[k].encode())<=200000 for k in ['requirements','testRequirements']):raise ValueError('Use exact provider dependency locks')
    files.update({'requirements.lock':native['requirements'].encode(),'test-requirements.lock':native['testRequirements'].encode(),'dependency-sources.json':(json.dumps({'provider':provider,'sources':native['sources'],'resolutions':native['resolutions']},indent=2)+'\n').encode()})
    manifest={'format':'atmem.materialized-application-runtime','version':1,'provider':provider,'catalogSha256':hashlib.sha256(raw).hexdigest(),'files':{name:hashlib.sha256(content).hexdigest()for name,content in sorted(files.items())},'boundary':data['boundary']}
    # Validate all inputs before creating output. A failed copy cannot be resumed
    # over unknown files; retain it for diagnosis and choose a fresh destination.
    target.mkdir(parents=True,exist_ok=False)
    for name,content in files.items():
        with(target/name).open('xb')as stream:stream.write(content)
    with(target/'runtime-manifest.json').open('x')as stream:json.dump(manifest,stream,indent=2);stream.write('\n')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--provider',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    result=materialize(Path(__file__).resolve().parents[1],args.provider,args.out)
    print(json.dumps({'provider':result['provider'],'files':len(result['files']),'catalogSha256':result['catalogSha256'],'cloudOperations':False}))
