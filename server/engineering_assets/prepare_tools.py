"""Portable, offline tool aliases for an exported AtMem project.

This configures existing local tools. It never downloads dependencies, reads account
profiles, executes tools or changes global configuration. Deployment is separate.
"""
import argparse
import json
import os
from pathlib import Path
import shutil

NAMES=('python','node','terraform','providerMirror')


def prepare(root,choices,required=()):
    root=Path(root).resolve(strict=True)
    if not root.is_dir() or set(choices)-set(NAMES) or set(required)-set(NAMES):
        raise ValueError('Use a project directory and declared tool names')
    paths={}
    for name,value in choices.items():
        if value is None:continue
        path=Path(value).expanduser().resolve(strict=True)
        if name=='providerMirror':
            if not path.is_dir():raise ValueError('The offline provider mirror must be a directory')
        elif not path.is_file() or not os.access(path,os.X_OK):
            raise ValueError('Each tool must be an existing executable')
        paths[name]=path
    missing=set(required)-set(paths)
    if missing:raise ValueError('Required tools are unavailable: '+', '.join(sorted(missing)))
    tools,temporary=root/'.tools',root/'.worker-tmp'
    for directory in (tools,temporary):
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise ValueError('Local tool/temporary directories must not be links or files')
    for name,target in paths.items():
        link=tools/name
        if link.is_symlink():
            if link.resolve(strict=True)!=target:raise ValueError('Existing tool registration differs; use a fresh unpack or review it explicitly')
        elif link.exists():raise ValueError('Existing project files will not be replaced by tool aliases')
    config={'tools':{name:f'./.tools/{name}' for name in paths},'temporaryStorage':'.worker-tmp',
            'providerPolicy':'Explicit offline mirror only; no registry fallback. No cloud credentials are configured.'}
    manifest=tools/'toolchain.json'
    if manifest.is_symlink():raise ValueError('Tool configuration cannot be a link')
    if manifest.exists():
        existing=json.loads(manifest.read_text())
        registered=existing.get('tools') if isinstance(existing,dict) else None
        if not isinstance(registered,dict) or any(registered.get(name)!=value for name,value in config['tools'].items()):
            raise ValueError('Existing tool configuration differs; it was left unchanged')
    files={temporary/'openssl.cnf':'# Empty project-local OpenSSL configuration.\n'}
    if 'providerMirror' in paths:
        files[temporary/'terraform.rc']='provider_installation {\n  filesystem_mirror {\n    path = '+json.dumps(str(paths['providerMirror']))+'\n  }\n}\ndisable_checkpoint = true\n'
    for path,content in files.items():
        if path.is_symlink() or (path.exists() and path.read_text()!=content):
            raise ValueError('Existing local configuration differs; no files were changed')
    # Validate the entire setup before creating or replacing anything.
    tools.mkdir(exist_ok=True);temporary.mkdir(exist_ok=True)
    for name,target in paths.items():
        link=tools/name
        if not link.is_symlink():link.symlink_to(target,target_is_directory=name=='providerMirror')
    if not manifest.exists():manifest.write_text(json.dumps(config,indent=2)+'\n')
    for path,content in files.items():
        if not path.exists():path.write_text(content)
    return {'configured':list(paths),'missingOptional':[name for name in NAMES if name not in paths],
            'cloudAccess':False,'downloads':False,'environmentFiles':{key:str(path.relative_to(root)) for key,path in [('OPENSSL_CONF',temporary/'openssl.cnf'),('TF_CLI_CONFIG_FILE',temporary/'terraform.rc')] if path.exists()}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python',default=os.sys.executable)
    parser.add_argument('--node',default=shutil.which('node'))
    parser.add_argument('--terraform',default=shutil.which('terraform'))
    parser.add_argument('--provider-mirror',dest='providerMirror')
    parser.add_argument('--require',action='append',choices=NAMES,default=['python'])
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    if not (root/'ATMEM_DELIVERY.md').is_file():parser.error('Run the copy supplied inside an exported project')
    try:result=prepare(root,{name:getattr(args,name) for name in NAMES},args.require)
    except (ValueError,OSError) as error:parser.exit(2,str(error)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
