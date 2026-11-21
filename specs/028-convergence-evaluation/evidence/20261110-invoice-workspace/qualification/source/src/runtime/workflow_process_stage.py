"""Hard deadlines for trusted processor/destination child processes on Linux.

The compiler/operator supplies absolute commands and a minimal environment. No
shell, model-selected program, inherited account credentials or stderr payloads.
Input/output are bounded JSON. This is a deadline boundary, not an OS sandbox;
untrusted PDF parsers still require a separate hardened container boundary.
"""
import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import tempfile
import time
from durable_workflow import canonical
from workflow_errors import TemporaryWork,PermanentWork,ExternalOutcomeUnknown,DestinationNotAttempted,InvalidDispatch

class ProcessStage:
    def __init__(self,command,*,kind,timeout_seconds=60,environment=None,cwd=None,idempotency_verified=False):
        if (not isinstance(command,(tuple,list))or not command or any(not isinstance(v,str)or not v or '\0'in v for v in command)
            or not Path(command[0]).is_absolute()or not Path(command[0]).is_file()):raise ValueError('A trusted absolute executable is required')
        if kind not in {'extract','dispatch'}or type(timeout_seconds)not in {int,float}or not math.isfinite(timeout_seconds)or not 0<timeout_seconds<=120:raise ValueError('Invalid bounded stage configuration')
        if type(idempotency_verified)is not bool or(kind=='extract'and idempotency_verified):raise ValueError('Invalid stage replay configuration')
        environment={}if environment is None else environment
        if not isinstance(environment,dict)or any(not isinstance(k,str)or not isinstance(v,str)or not k or '='in k or '\0'in k+v for k,v in environment.items()):raise ValueError('Use an explicit trusted child environment')
        directory=Path(cwd).resolve()if cwd else Path(command[0]).resolve().parent
        if not directory.is_dir():raise ValueError('Use an existing owned working directory')
        self.command=tuple(command);self.kind=kind;self.timeout_seconds=timeout_seconds;self.environment=dict(environment);self.cwd=directory;self.idempotency_verified=idempotency_verified

    def __call__(self,row,**identity):
        # Deliberately exclude database DSNs, lease tokens and application logins.
        selected={key:row[key]for key in ['kind','source_ref','destination_contract','result','result_revision','approved_by','approved_hash','state']if key in row}
        selected.update({key:str(row[key])for key in ['id','account_id']if key in row})
        payload=canonical({'operation':selected,'identity':identity},140000)
        failure=TemporaryWork if self.kind=='extract'else ExternalOutcomeUnknown
        process=None
        try:
            # A bounded private temporary input avoids a pipe-write deadlock when
            # a child never reads stdin; no sensitive input appears in argv/env.
            with tempfile.TemporaryFile(mode='w+b')as source,selectors.DefaultSelector()as selector:
                source.write(payload);source.seek(0)
                started=time.monotonic()
                process=subprocess.Popen(self.command,stdin=source,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd=self.cwd,env=self.environment,start_new_session=True)
                os.set_blocking(process.stdout.fileno(),False);selector.register(process.stdout,selectors.EVENT_READ)
                output=bytearray()
                while selector.get_map():
                    remaining=self.timeout_seconds-(time.monotonic()-started)
                    if remaining<=0:raise failure('Owned stage exceeded its deadline')
                    for key,_ in selector.select(min(remaining,.1)):
                        chunk=os.read(key.fd,8192)
                        if not chunk:selector.unregister(key.fileobj);continue
                        output.extend(chunk)
                        if len(output)>70000:raise failure('Owned stage exceeded its output boundary')
                remaining=self.timeout_seconds-(time.monotonic()-started)
                if remaining<=0:raise failure('Owned stage exceeded its deadline')
                try:code=process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:raise failure('Owned stage exceeded its deadline')from None
                if code!=0:raise failure('Owned stage did not confirm completion')
            def unique(pairs):
                value={}
                for key,item in pairs:
                    if key in value:raise ValueError('Duplicate stage field')
                    value[key]=item
                return value
            try:
                response=json.loads(output,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite stage result')))
                if not isinstance(response,dict)or set(response)!={'status','result'}or not isinstance(response['result'],dict):raise ValueError('Invalid stage result')
                canonical(response['result'],64000)
            except (ValueError,TypeError,UnicodeError,RecursionError):raise failure('Owned stage returned an invalid response')from None
            status=response['status']
            if status=='ok':return response['result']
            if self.kind=='extract'and status=='temporary':raise TemporaryWork('Processing temporarily unavailable')
            if self.kind=='extract'and status=='permanent':raise PermanentWork('Processing requires review')
            if self.kind=='dispatch'and status=='not_attempted':raise DestinationNotAttempted('Destination not attempted')
            if self.kind=='dispatch'and status=='invalid':raise InvalidDispatch('Approved dispatch integrity requires review')
            raise failure('Owned stage did not confirm completion')
        except (TemporaryWork,PermanentWork,ExternalOutcomeUnknown):raise
        except Exception:raise failure('Owned stage did not confirm completion')from None
        finally:
            if process is not None:
                # Kill descendants even if the direct child exited before them.
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                process.wait()
                if process.stdout:process.stdout.close()
