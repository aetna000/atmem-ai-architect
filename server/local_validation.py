"""Trusted controller for digest-bound local checks, outside the model worker.

No public/raw-command endpoint. Operator-reviewed specs select cached immutable
images and commands. Artifacts travel over stdin; no host directory/socket or
credential is mounted. Container loopback works, external/host networking does not.
This executes checks; requirement acceptance needs separately authored oracles.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
import uuid


# Only trusted bootstrap code runs with SETUID/SETGID. Untrusted source is copied as
# root-owned read-only files, then all supplementary groups/root identity are dropped
# before exec. Changing UID clears effective capabilities; no-new-privileges prevents
# reacquisition. This policy requires native Linux-container qualification below.
BOOTSTRAP = r'''
import hashlib,io,json,os,pathlib,stat,sys,zipfile
expected,command=json.loads(sys.argv[1])
content=sys.stdin.buffer.read(64000001)
if len(content)>64000000 or hashlib.sha256(content).hexdigest()!=expected:
 raise RuntimeError('Immutable artifact digest/size mismatch')
root=pathlib.Path('/work/source');root.mkdir()
with zipfile.ZipFile(io.BytesIO(content)) as archive:
 entries=archive.infolist()
 if len(entries)>2000 or sum(e.file_size for e in entries)>64000000:
  raise RuntimeError('Artifact bounds exceeded')
 seen=set()
 for entry in entries:
  path=pathlib.PurePosixPath(entry.filename)
  if path.is_absolute() or '..' in path.parts or '\\' in entry.filename or any(ord(c)<32 for c in entry.filename) or not path.parts or str(path) in seen:
   raise RuntimeError('Unsafe or duplicate archive entry')
  seen.add(str(path));mode=entry.external_attr>>16
  if stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR):
   raise RuntimeError('Linked/special archive entry')
  target=root.joinpath(*path.parts)
  if entry.is_dir():target.mkdir(parents=True,exist_ok=True)
  else:
   target.parent.mkdir(parents=True,exist_ok=True)
   target.write_bytes(archive.read(entry))
   target.chmod(0o555 if mode & 0o111 else 0o444)
 for directory in sorted((p for p in root.rglob('*') if p.is_dir()),reverse=True):directory.chmod(0o555)
root.chmod(0o555)
os.chdir(root)
os.setgroups([]);os.setgid(65532);os.setuid(65532)
if os.getuid()!=65532 or os.getgid()!=65532:raise RuntimeError('Validator identity was not dropped')
os.execv(command[0],command)
'''


@dataclass(frozen=True)
class ValidationSpec:
    name: str
    image: str
    command: tuple[str, ...]
    platform: str = 'linux/amd64'
    timeout_seconds: int = 60
    bootstrap_python: str = '/usr/local/bin/python3'
    isolation_profile: str = 'standard-v1'
    runtime_environment: tuple[tuple[str,str], ...] = ()

    def __post_init__(self):
        if not isinstance(self.name,str) or not re.fullmatch(r'[a-z][a-z0-9_-]{2,79}',self.name):raise ValueError('Invalid trusted validator name')
        if not isinstance(self.image,str) or not re.fullmatch(r'sha256:[a-f0-9]{64}',self.image):raise ValueError('Use a cached immutable image ID')
        if self.platform not in {'linux/amd64','linux/arm64'}:raise ValueError('Unqualified container platform')
        if not isinstance(self.command,tuple) or not self.command or not all(isinstance(x,str) and x and '\0' not in x for x in self.command) or not self.command[0].startswith('/'):
            raise ValueError('Register an explicit trusted validator executable/argument vector')
        if type(self.timeout_seconds) is not int or not 1<=self.timeout_seconds<=300:raise ValueError('Validator time budget must be bounded')
        if not isinstance(self.bootstrap_python,str) or not self.bootstrap_python.startswith('/') or '\0' in self.bootstrap_python:
            raise ValueError('Register an absolute Python bootstrap executable in the reviewed image')
        if self.isolation_profile not in {'standard-v1','chromium-userns-v1'}:raise ValueError('Unreviewed validator isolation profile')
        if not isinstance(self.runtime_environment,tuple) or any(not isinstance(pair,tuple) or len(pair)!=2 or not isinstance(pair[0],str) or pair[0] not in {'ATMEM_PLAYWRIGHT_MODULE','PLAYWRIGHT_BROWSERS_PATH'} or not isinstance(pair[1],str) or not pair[1].startswith('/') or any(ord(c)<32 for c in pair[1]) for pair in self.runtime_environment) or len({pair[0] for pair in self.runtime_environment})!=len(self.runtime_environment):
            raise ValueError('Register only explicit image-local runtime module/browser paths')


class DockerValidationWorker:
    REVIEWED_PROFILES={'chromium-userns-v1':'e53c15d248f57bceec0a3a16fad1b4ab0d05a7bddb455f86a60e2dba5612cdf7'}

    def __init__(self, endpoint, *, binary='docker', max_output_bytes=256000, isolation_profiles=None):
        if not isinstance(endpoint,str) or not endpoint.startswith('unix:///') or not Path(endpoint[7:]).is_socket():
            raise ValueError('Use an explicitly registered local Docker Unix socket')
        if type(max_output_bytes) is not int or not 1024<=max_output_bytes<=1000000:
            raise ValueError('Validator output budget must be bounded')
        self.endpoint,self.binary,self.max_output_bytes=endpoint,binary,max_output_bytes
        profiles={} if isolation_profiles is None else isolation_profiles
        if not isinstance(profiles,dict) or set(profiles)-set(self.REVIEWED_PROFILES):raise ValueError('Register reviewed isolation profiles only')
        self.isolation_profiles={}
        for name,entry in profiles.items():
            if not isinstance(entry,dict) or set(entry)!={'path','sha256'} or entry['sha256']!=self.REVIEWED_PROFILES[name] or not isinstance(entry['path'],str) or not Path(entry['path']).is_absolute() or Path(entry['path']).is_symlink():raise ValueError('A reviewed pinned local isolation policy is required')
            if Path(entry['path']).stat().st_size>64000:raise ValueError('Isolation policy exceeds its explicit size limit')
            content=Path(entry['path']).read_bytes()
            if len(content)>64000 or hashlib.sha256(content).hexdigest()!=entry['sha256'] or json.loads(content).get('defaultAction')!='SCMP_ACT_ERRNO':raise ValueError('Isolation policy does not match its reviewed bytes')
            self.isolation_profiles[name]=content
        self.policy_digest=hashlib.sha256(json.dumps({'code':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'profiles':{name:hashlib.sha256(content).hexdigest() for name,content in self.isolation_profiles.items()}},sort_keys=True).encode()).hexdigest()
        self.identity_digest=hashlib.sha256(endpoint.encode()).hexdigest()

    def supports(self,spec):return spec.isolation_profile=='standard-v1' or spec.isolation_profile in self.isolation_profiles

    def run(self, archive, expected_digest, spec: ValidationSpec, *, execution_id=None, cancel_event=None):
        if not isinstance(archive,bytes) or len(archive)>64000000 or hashlib.sha256(archive).hexdigest()!=expected_digest:
            raise ValueError('Digest-bound artifact bytes are required')
        if not self.supports(spec):raise RuntimeError('The reviewed isolation profile is unavailable; no fallback was used')
        execution=uuid.UUID(execution_id) if execution_id is not None else uuid.uuid4()
        ident='atmem-validator-'+execution.hex
        started=time.monotonic()
        with tempfile.TemporaryDirectory(prefix='atmem-validator-control-') as folder:
            config=Path(folder)/'docker';config.mkdir()
            (config/'config.json').write_text('{}')
            env={'PATH':os.environ.get('PATH',''),'HOME':folder,'DOCKER_CONFIG':str(config),'DOCKER_HOST':self.endpoint}
            prefix=[self.binary,'--host',self.endpoint,'--config',str(config)]
            # Local image lookup only: never pull or evaluate a model Dockerfile.
            inspect=subprocess.run([*prefix,'image','inspect',spec.image,'--format','{{.Id}}'],
                                   env=env,capture_output=True,text=True,timeout=15)
            if inspect.returncode!=0 or inspect.stdout.strip()!=spec.image:
                raise RuntimeError('The reviewed local image/platform is unavailable; no image was pulled')
            platform=subprocess.run([*prefix,'image','inspect','--platform',spec.platform,spec.image,'--format','{{.Os}}/{{.Architecture}} {{.Id}}'],
                                    env=env,capture_output=True,text=True,timeout=15)
            selection=platform.stdout.strip().split()
            if platform.returncode!=0 or len(selection)!=2 or selection[0]!=spec.platform or not re.fullmatch(r'sha256:[a-f0-9]{64}',selection[1]):
                raise RuntimeError('The reviewed cached platform is unavailable; no fallback or image pull was used')
            browser=spec.isolation_profile=='chromium-userns-v1'
            security=[]
            if browser:
                policy=Path(folder)/'reviewed-seccomp.json';policy.write_bytes(self.isolation_profiles[spec.isolation_profile])
                security=['--security-opt','seccomp='+str(policy)]
            runtime_env=[part for name,value in spec.runtime_environment for part in ['--env',name+'='+value]]
            command=[*prefix,'run','--pull','never','--rm','--name',ident,'--platform',spec.platform,
                '--network','none','--read-only','--cap-drop','ALL','--cap-add','SETUID','--cap-add','SETGID',
                '--security-opt','no-new-privileges',*security,'--pids-limit','128' if browser else '64','--memory','512m' if browser else '256m','--cpus','1',
                '--tmpfs','/work:rw,noexec,nosuid,nodev,size=128m,mode=0755',
                '--tmpfs',f'/tmp:rw,noexec,nosuid,nodev,size={64 if browser else 32}m,mode=1777',
                '--env','HOME=/tmp','--env','PYTHONDONTWRITEBYTECODE=1','--env','AWS_EC2_METADATA_DISABLED=true',
                *runtime_env,'--entrypoint',spec.bootstrap_python,'-i',spec.image,'-I','-c',BOOTSTRAP,
                json.dumps([expected_digest,list(spec.command)])]
            log=Path(folder)/'output.log'
            reason=None
            with log.open('wb') as output:
                process=subprocess.Popen(command,env=env,stdin=subprocess.PIPE,stdout=output,stderr=subprocess.STDOUT)
                def send():
                    try:process.stdin.write(archive)
                    except (BrokenPipeError,OSError):pass
                    finally:
                        try:process.stdin.close()
                        except (BrokenPipeError,OSError):pass
                writer=threading.Thread(target=send,daemon=True);writer.start()
                try:
                    while process.poll() is None:
                        if cancel_event is not None and cancel_event.is_set():reason='cancelled';break
                        if time.monotonic()-started>spec.timeout_seconds:reason='timeout';break
                        if log.stat().st_size>self.max_output_bytes:reason='output_limit';break
                        time.sleep(.05)
                finally:
                    def cleanup():
                        nonlocal reason
                        try:
                            subprocess.run([*prefix,'rm','-f',ident],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
                        except (OSError,subprocess.TimeoutExpired):reason='container_cleanup_unconfirmed'
                    if reason:
                        cleanup()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
                    writer.join(timeout=2)
                    cleanup()
            with log.open('rb') as output:raw=output.read(self.max_output_bytes+1)
            truncated=len(raw)>self.max_output_bytes
            text=raw[:self.max_output_bytes].decode('utf-8',errors='replace')
            unittest=spec.command[1:3]==('-m','unittest')
            node_tests=Path(spec.command[0]).name in {'node','nodejs'} and spec.command[1:2]==('--test',)
            skips=re.search(r'OK \(skipped=(\d+)\)',text) if unittest else None
            skipped=int(skips.group(1)) if skips else 0
            count=re.search(r'Ran (\d+) tests? in ',text) if unittest else None
            if node_tests:
                totals=re.findall(r'^(?:#\s*|ℹ\s*)tests\s+(\d+)\s*$',text,re.MULTILINE)
                skip_counts=re.findall(r'^(?:#\s*|ℹ\s*)skipped\s+(\d+)\s*$',text,re.MULTILINE)
                executed=int(totals[-1]) if totals else None
                skipped=int(skip_counts[-1]) if skip_counts else 0
            else:executed=int(count.group(1)) if count else None
            missing_tests=(unittest or node_tests) and (executed is None or executed==0)
            status='failed' if reason or truncated or process.returncode or missing_tests else 'incomplete' if skipped else 'passed'
            return {'validator':spec.name,'artifactSha256':expected_digest,'imageId':spec.image,
                'runtimeConfigImageId':selection[1],
                'platform':spec.platform,'isolationProfile':spec.isolation_profile,'runtimeEnvironment':dict(spec.runtime_environment),'command':list(spec.command),'status':status,'exitCode':process.returncode,
                'skipped':skipped,'testsReported':executed,
                'reason':reason or ('output_limit' if truncated else 'no_tests_reported' if missing_tests else None),'output':text,
                'outputTruncated':truncated,'durationSeconds':round(time.monotonic()-started,3),
                'evidenceLevel':'local_container_check','cloudOperations':False,
                'boundary':'Exact immutable source in a cached Linux image, root-owned read-only inputs and nonroot check process, isolated loopback/network-none with no host mounts/socket/credentials. Check execution is not independent semantic or whole-system acceptance.'}

    def recover(self, execution_id):
        """Remove only this journaled validator container after supervisor loss.

        A failed daemon query is uncertainty, not proof the prior work stopped.
        Never replay a check as part of recovery.
        """
        name='atmem-validator-'+uuid.UUID(execution_id).hex
        with tempfile.TemporaryDirectory(prefix='atmem-validator-recover-') as folder:
            config=Path(folder)/'docker';config.mkdir();(config/'config.json').write_text('{}')
            env={'PATH':os.environ.get('PATH',''),'HOME':folder,'DOCKER_CONFIG':str(config),'DOCKER_HOST':self.endpoint}
            prefix=[self.binary,'--host',self.endpoint,'--config',str(config)]
            def present():
                result=subprocess.run([*prefix,'container','ls','-a','--filter',f'name=^/{name}$','--format','{{.Names}}'],env=env,capture_output=True,text=True,timeout=15)
                if result.returncode:raise RuntimeError('Validator cleanup could not be confirmed')
                names=result.stdout.splitlines()
                if names not in ([],[name]):raise RuntimeError('Unexpected validator recovery result')
                return bool(names)
            if present():
                result=subprocess.run([*prefix,'rm','-f',name],env=env,capture_output=True,timeout=15)
                if result.returncode:raise RuntimeError('Validator cleanup could not be confirmed')
            if present():raise RuntimeError('Validator cleanup could not be confirmed')
        return {'cleanupConfirmed':True,'workReplayed':False}
