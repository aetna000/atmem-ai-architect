#!/usr/bin/env python3
"""Replay emitted local checks under the qualified offline worker, without inference.

This executes generated tests, not independent requirement or system acceptance.
No export source is repaired. Tool registrations are recreated separately because
the paired driver excludes worker tools from its captured client artifacts.
"""
import argparse
import asyncio
import hashlib
import json
import re
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from server.codex_worker_policy import CodexWorkerClient, PROFILE


async def replay(source, output, *, tool_layout='paired', extra_commands=()):
    output.mkdir(parents=True,exist_ok=False)
    terraform=(ROOT/'.venv/bin/terraform').resolve(strict=True)
    cache=(ROOT/'.local/provider-cache').resolve(strict=True)
    python=Path(sys.executable).resolve(strict=True)
    roots={terraform.parent,cache,python.parent}
    for directory in ['bin','opt','Cellar','lib','share','Frameworks']:
        tool_directory=Path('/opt/homebrew')/directory
        if tool_directory.is_dir():roots.add(tool_directory)
    if any(p.is_symlink() for p in source.rglob('*')):raise ValueError('Source artifacts must not contain symlinks')
    hashes={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
    checks=[]
    with tempfile.TemporaryDirectory(prefix='atm-replay-',dir='/tmp') as temporary:
        workspace=Path(temporary).resolve()/'work'
        shutil.copytree(source,workspace)
        tools=workspace/('.tools' if tool_layout=='product' else 'tools');tools.mkdir()
        (tools/'terraform').symlink_to(terraform)
        mirror_name='providerMirror' if tool_layout=='product' else 'provider-cache'
        (tools/mirror_name).symlink_to(cache,target_is_directory=True)
        if tool_layout=='product':
            (tools/'python').symlink_to(python);(tools/'node').symlink_to(shutil.which('node'))
            configuration={'tools':{name:f'./.tools/{name}' for name in ['terraform','providerMirror','python','node']},
                           'temporaryStorage':'.worker-tmp','providerPolicy':'Registered offline mirror only; no registry fallback'}
        else:configuration={'terraform':'./tools/terraform','providerMirror':'./tools/provider-cache','python':str(python),'node':shutil.which('node')}
        (tools/'toolchain.json').write_text(json.dumps(configuration))
        mirror=workspace/'offline.terraformrc'
        mirror.write_text('provider_installation { filesystem_mirror { path = '+json.dumps(str(cache))+' } }\n')
        worker=CodexWorkerClient(workspace,read_roots=roots)
        try:
            await worker.start()
            await worker.verify_worker_tools()
            async def command(name,argv,cwd=workspace):
                try:
                    result=await worker.request('command/exec',{'command':[str(a) for a in argv],'cwd':str(cwd),
                        'permissionProfile':PROFILE,'env':{'TMPDIR':str(workspace/'.worker-tmp'),
                        'TF_CLI_CONFIG_FILE':str(mirror),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1',
                        'OPENSSL_CONF':'/dev/null','PYTHONDONTWRITEBYTECODE':'1'},
                        'timeoutMs':60000,'outputBytesCap':200000},timeout=70)
                    skipped=0
                    if name=='python-generated-unit-tests':
                        match=re.search(r'OK \(skipped=(\d+)\)',result.get('stdout','')+'\n'+result.get('stderr',''))
                        skipped=int(match.group(1)) if match else 0
                    checks.append({'name':name,'level':'generated_local_checks',
                        'commandPassed':result['exitCode']==0,'skipped':skipped,
                        'passed':result['exitCode']==0 and skipped==0,**result})
                except Exception as error:
                    checks.append({'name':name,'passed':False,'errorType':type(error).__name__})
            if (workspace/'tests').is_dir():
                await command('python-generated-unit-tests',[python,'-m','unittest','discover','-s','tests','-v'])
            node_tests=sorted(p for p in (workspace/'tests').rglob('*') if p.is_file() and p.name.endswith(('.test.cjs','.test.mjs','.test.js')))
            if node_tests:await command('node-generated-unit-tests',[shutil.which('node'),'--test',*node_tests])
            if (workspace/'infra').is_dir():
                await command('terraform-format',[terraform,'-chdir=infra','fmt','-check','-recursive'])
                await command('terraform-offline-init',[terraform,'-chdir=infra','init','-backend=false','-input=false','-lockfile=readonly','-no-color'])
                await command('terraform-provider-schema',[terraform,'-chdir=infra','validate','-no-color'])
                # Do not run Terraform plans/applies or infer account readiness.
                # Native provider mock replay remains a separately reviewed check.
            for index,argv in enumerate(extra_commands):
                await command(f'operator-reviewed-local-check-{index+1}',argv)
            changed={}
            for name,digest in hashes.items():
                path=workspace/name
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                    changed[name]='missing' if not path.is_file() else hashlib.sha256(path.read_bytes()).hexdigest()
        finally:
            await worker.close()
    receipt={'sourceHashes':hashes,'changedInputFiles':changed,'toolLayout':tool_layout,'checks':checks,'inferenceTurns':0,'cloudOperations':False,
        'boundary':'Offline sandbox replay on a copy with trusted tool registrations restored. Python/Node generated tests and provider format/init/schema checks; optional explicitly reviewed local commands are labeled separately. No independent semantic/system, cloud-plan or deployment acceptance. Changed input files remain visible.'}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'source':str(source),'checks':[{k:c.get(k) for k in ['name','passed','exitCode']} for c in checks]},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tool-layout',choices=['paired','product'],default='paired')
    parser.add_argument('--commands-json',type=Path,help='Operator-reviewed local command vectors; never browser/model-supplied')
    args=parser.parse_args()
    commands=json.loads(args.commands_json.read_text()) if args.commands_json else []
    if not isinstance(commands,list) or any(not isinstance(command,list) or not command or any(not isinstance(arg,str) for arg in command) for command in commands):parser.error('Use explicit command vectors')
    asyncio.run(replay(args.source.resolve(strict=True),args.output.resolve(),tool_layout=args.tool_layout,extra_commands=commands))
