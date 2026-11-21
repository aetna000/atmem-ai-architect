"""Frozen native versus native-plus-reviewed-skill diagnostic, no cloud deployment.

This compares harness arms, not the unfinished product UI or complete-project
acceptance. Isolated temporary workspaces must not inherit the source repository's
AGENTS.md or read peers/evaluator material. Both use the same restricted native
worker, toolchain, model/effort, client brief and execution budget.
"""
import argparse
import asyncio
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.codex_engineering_backend import CodexEngineeringBackend
from server.codex_worker_policy import CodexWorkerClient,PROFILE
from server.engineering_sessions import EngineeringSessions,ModelSelection,ProjectScope,SqliteSessionStore


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


async def arm(args,name,brief):
    folder=args.output/name;folder.mkdir(parents=True,exist_ok=False)
    temporary=tempfile.TemporaryDirectory(prefix=f'atmem-{name}-',dir='/tmp')
    workspace=Path(temporary.name).resolve();tools=workspace/'tools';tools.mkdir()
    terraform=(ROOT/'.venv/bin/terraform').resolve(strict=True)
    (tools/'terraform').symlink_to(terraform)
    cache=(ROOT/'.local/provider-cache').resolve(strict=True)
    (tools/'provider-cache').symlink_to(cache)
    runtime_roots={terraform.parent,cache,Path(sys.executable).resolve().parent}
    # Homebrew tool entrypoints include symlinks and shared interpreter libraries.
    # This is a trusted code tree, not the user's source, credentials or home.
    for tool_directory in ['bin','opt','Cellar','lib','share','Frameworks']:
        path=Path('/opt/homebrew')/tool_directory
        if path.is_dir():runtime_roots.add(path)
    toolchain={'terraform':'./tools/terraform','providerMirror':'./tools/provider-cache',
               'providers':[str(p.relative_to(cache)) for p in cache.rglob('terraform-provider-*') if p.is_file()],
               'python':str(Path(sys.executable).resolve()),'node':shutil.which('node'),
               'temporaryStorage':'.worker-tmp','network':'disabled; use cached providers; no cloud account access'}
    (tools/'toolchain.json').write_text(json.dumps(toolchain,indent=2)+'\n')
    skill=ROOT/'agent-skills/specialists/composition/SKILL.md'
    if name=='specialized':
        destination=workspace/'.agents/skills/composition/SKILL.md';destination.parent.mkdir(parents=True);shutil.copyfile(skill,destination)
    events=[];instruction_sources=[]
    class RecordingClient(CodexWorkerClient):
        def __init__(self,root):super().__init__(root,read_roots=runtime_roots)
        async def request(self,method,params=None,**kwargs):
            result=await super().request(method,params,**kwargs)
            if method in {'thread/start','thread/resume'}:
                instruction_sources.extend(result.get('instructionSources',[]))
                for source in result.get('instructionSources',[]):
                    if not Path(source).resolve().is_relative_to(workspace):
                        raise RuntimeError('Evaluation workspace inherited out-of-workspace instructions')
            return result
        async def notification(self,**kwargs):
            message=await super().notification(**kwargs)
            if message.get('method','').startswith(('item/','turn/','thread/tokenUsage/')):
                events.append(message)
                with (folder/'events.jsonl').open('a') as log:log.write(json.dumps(message)+'\n')
            return message
    scope=ProjectScope('paired-qualification','synthetic-client');selection=ModelSelection(args.model,args.effort)
    backend=CodexEngineeringBackend({(scope,'engineering-workspace'):workspace},client_factory=RecordingClient,
        permission_profile=PROFILE,instructions='Use the reviewed composition skill when architecting and implementing this system; preserve its applicability and evidence boundaries.' if name=='specialized' else '')
    store=SqliteSessionStore(folder/'control.sqlite');engine=EngineeringSessions(store,backend)
    prompt=brief+'''\n\nWork request: create the actual implementation files, Terraform, local tests and build/run/rollback instructions in this workspace. Preserve all client constraints and existing systems. Carry routine engineering choices and describe assumptions. If a business decision truly blocks implementation, ask a concise question and keep the unresolved scope explicit. tools/toolchain.json describes the local tools and cached providers. Do not deploy or access cloud accounts, install packages from the network, use subagents, or modify the supplied tools/ directory. Use local tests/emulators and label synthetic provider/model transports precisely. Do not claim successful checks without running them. Finish with a concise status and remaining gaps.\n'''
    (folder/'input.txt').write_text(prompt)
    start=time.monotonic();terminal=None;error=None;settled_after_budget=False
    try:
        session=await engine.create(scope,'engineering-workspace',selection)
        await engine.start(scope,session['id'],prompt)
        deadline=start+args.seconds
        while time.monotonic()<deadline:
            try:event=await asyncio.wait_for(engine.next_event(scope,session['id']),max(.01,deadline-time.monotonic()))
            except asyncio.TimeoutError:
                if time.monotonic()>=deadline:break
                continue
            if event['kind'] in {'completed','failed','interrupted'}:terminal=event['kind'];break
        if terminal is None:
            error='Evaluation execution budget reached; no completed package inferred'
            await engine.interrupt(scope,session['id'])
            async def settle():
                while True:
                    event=await engine.next_event(scope,session['id'])
                    if event['kind'] in {'completed','failed','interrupted'}:return event['kind']
            try:terminal=await asyncio.wait_for(settle(),15);settled_after_budget=True
            except asyncio.TimeoutError:pass
    except asyncio.CancelledError:
        args.cancelled=True;error='Operator cancelled the evaluation; partial artifacts retained'
    except Exception as exc:error=type(exc).__name__+': '+str(exc)
    finally:
        await backend.close();store.close()
    (folder/'events.json').write_text(json.dumps(events,indent=2)+'\n')
    files={};symlinks=[];artifact_workspace=folder/'workspace';artifact_workspace.mkdir()
    for p in workspace.rglob('*'):
        rel=p.relative_to(workspace)
        if rel.parts[0] in {'tools','.agents','.git','.worker-tmp'} or any(x in rel.parts for x in ['.terraform','__pycache__','node_modules','.venv']):continue
        if p.is_symlink():symlinks.append(str(rel));continue
        if p.is_file():
            files[str(rel)]=sha(p);target=artifact_workspace/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    with tarfile.open(folder/'artifact.tar.gz','w:gz') as tar:
        for rel in sorted(files):tar.add(artifact_workspace/rel,arcname=rel,recursive=False)
    result={'arm':name,'model':args.model,'effort':args.effort,'durationSeconds':round(time.monotonic()-start,3),
            'turnStatus':terminal,'error':error,'settledAfterBudget':settled_after_budget,'inputSha256':sha(folder/'input.txt'),
            'skillSha256':sha(skill) if name=='specialized' else None,'instructionSources':instruction_sources,
            'workerProfile':PROFILE,'artifactSha256':sha(folder/'artifact.tar.gz'),'files':files,
            'unsupportedArtifactSymlinks':symlinks,
            'tokenUsageEvents':[e['params'] for e in events if e.get('method')=='thread/tokenUsage/updated'],
            'cost':None,'quality':'not_established_by_agent_completion','cloudOperations':False}
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');temporary.cleanup()
    print(name,terminal,'files',len(files),'seconds',result['durationSeconds'],flush=True)
    return result


async def main(args):
    args.output=args.output.resolve()
    if (args.output/'manifest.json').exists():raise ValueError('Do not overwrite a prior comparison')
    brief=args.brief.read_text();assert brief.strip() and len(brief)<75000
    (args.output/'client-brief.txt').write_text(brief)
    paths=[p for p in ROOT.rglob('*.py') if 'server' in p.relative_to(ROOT).parts and '__pycache__' not in p.parts]
    paths += [ROOT/'agent-skills/specialists/composition/SKILL.md',ROOT/'benchmarks/engine/evaluation-contract.json',ROOT/'package.json']
    manifest={'timestampUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'briefSha256':sha(args.brief),
              'runnerSha256':sha(Path(__file__)),'sourceHashes':{str(p.relative_to(ROOT)):sha(p) for p in paths},
              'frozenSource':str(ROOT),'model':args.model,'effort':args.effort,'secondsPerArm':args.seconds,
              'armOrder':['native','specialized'],'boundary':'Frozen paired native versus native-plus-composition-skill diagnostic; not full Architect, AtMem retrieval, product UI, independent semantics or cloud acceptance. Both arms use disjoint temporary workspaces, the same read-restricted worker, exact local tools and execution budget.'}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    results=[]
    for name in manifest['armOrder']:
        results.append(await arm(args,name,brief))
        if getattr(args,'cancelled',False):break
    complete=not getattr(args,'cancelled',False)
    if complete:
        assert [r['arm'] for r in results]==manifest['armOrder'],'Evaluation arm identity changed'
        assert results[0]['skillSha256'] is None and results[1]['skillSha256']==sha(ROOT/'agent-skills/specialists/composition/SKILL.md'),'Skill specialization was not isolated to its intended arm'
        assert len({r['inputSha256'] for r in results})==1,'Client/work instructions differed between arms'
    (args.output/'results.json').write_text(json.dumps({'results':results,'pairComplete':complete,'independentAcceptance':'pending'},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true',required=True)
    p.add_argument('--brief',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--model',required=True);p.add_argument('--effort',required=True);p.add_argument('--seconds',type=int,default=300)
    p.add_argument('--frozen',action='store_true',help=argparse.SUPPRESS)
    args=p.parse_args()
    if not 30<=args.seconds<=900:p.error('Each arm needs a bounded 30–900 second observation budget')
    args.output=args.output.resolve();args.brief=args.brief.resolve()
    if not args.frozen:
        args.output.mkdir(parents=True,exist_ok=False);snapshot=args.output/'source';snapshot.mkdir()
        shutil.copytree(ROOT/'server',snapshot/'server',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for name in ['package.json','agent-skills/specialists/composition/SKILL.md','benchmarks/engine/evaluation-contract.json','scripts/engine-evaluation/paired-native.py']:
            target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        (snapshot/'.venv').symlink_to(ROOT/'.venv',target_is_directory=True)
        (snapshot/'.local').mkdir();(snapshot/'.local/provider-cache').symlink_to(ROOT/'.local/provider-cache',target_is_directory=True)
        shutil.copyfile(args.brief,args.output/'original-client-brief.txt')
        raise SystemExit(subprocess.call([sys.executable,str(snapshot/'scripts/engine-evaluation/paired-native.py'),'--live','--brief',str(args.output/'original-client-brief.txt'),'--output',str(args.output),'--model',args.model,'--effort',args.effort,'--seconds',str(args.seconds),'--frozen'],cwd=snapshot))
    asyncio.run(main(args))
    if getattr(args,'cancelled',False):raise SystemExit(130)
