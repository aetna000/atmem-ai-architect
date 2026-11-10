"""Owned local qualification transport, never a production cloud launcher.

No host mounts, credentials or caller URLs enter the per-file parser. Docker's
log driver is disabled: even a compromised parser cannot persist stdout as job
logs. Source/result volumes are fresh for each call and removed after consumption.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid
from enterprise_document_contract import ExtractionError
from enterprise_document_job import MAX_ENVELOPE, request, result
from enterprise_sources import SourceUnavailable


class LocalDocumentJobs:
    def __init__(self, image, docker_host, docker_config, scratch, *, timeout=140):
        if (not re.fullmatch('sha256:[0-9a-f]{64}', image) or not docker_host.startswith('unix:///') or
            not Path(docker_host[7:]).is_socket() or type(timeout) is not int or not 1 <= timeout <= 140):
            raise ValueError('Use the inspected image and owned local Docker fixture socket')
        self.image, self.timeout = image, timeout
        self.env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(scratch), 'DOCKER_HOST': docker_host, 'DOCKER_CONFIG': str(docker_config)}
        self.attempts = []
        self.observations = []

    def command(self, args, *, data=None, timeout=20):
        value = subprocess.run(['docker', *args], env=self.env, input=data,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        if value.returncode != 0: raise SourceUnavailable('document_extraction_unavailable')
        return value.stdout

    def __call__(self, raw, mime):
        return self.from_source(raw, mime, lambda: None)

    def from_source(self, raw, mime, guard):
        metadata = request(raw, mime, uuid.uuid4().hex + uuid.uuid4().hex)
        identifier = metadata['requestId']
        volumes = ['atmem-document-workflow-' + identifier + '-' + side for side in ['in', 'out']]
        container = 'atmem-document-workflow-' + identifier
        created, launched, code = [], False, None
        started = time.monotonic()
        try:
            guard()
            for name in volumes:
                self.command(['volume', 'create', name]); created.append(name)
            mounts = ['--mount', 'type=volume,source=' + volumes[0] + ',target=/input',
                      '--mount', 'type=volume,source=' + volumes[1] + ',target=/output']
            setup = '''import base64,json,os,sys
from pathlib import Path
value=json.load(sys.stdin)
Path('/input/document').write_bytes(base64.b64decode(value['raw'],validate=True))
Path('/input/request.json').write_text(json.dumps(value['metadata']))
for path in [Path('/input/document'),Path('/input/request.json')]:
 path.chmod(0o400);os.chown(path,10001,10001)
os.chown('/output',10001,10001)
'''
            guard()
            self.command(['run', '--rm', '--platform', 'linux/amd64', '--network', 'none', '--read-only', '--log-driver', 'none',
                '--user', '0:0', '--cap-drop', 'ALL', '--cap-add', 'CHOWN', '--security-opt', 'no-new-privileges:true',
                *mounts, '-i', self.image, 'python', '-I', '-c', setup],
                data=json.dumps({'metadata': metadata, 'raw': base64.b64encode(raw).decode()}).encode())
            mounts[1] += ',readonly'
            guard()
            self.command(['run', '--detach', '--name', container, '--platform', 'linux/amd64', '--network', 'none',
                '--read-only', '--log-driver', 'none', '--user', '10001:10001', '--tmpfs', '/tmp:rw,noexec,nosuid,size=128m',
                '--memory', '1g', '--cpus', '2', '--pids-limit', '128', '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges:true', *mounts, self.image, 'python', '-I', '/app/enterprise_document_cli.py', '--job'])
            launched = True
            while True:
                if time.monotonic() - started > self.timeout: raise SourceUnavailable('document_extraction_unavailable')
                observed = json.loads(self.command(['inspect', container]))[0]
                self.observations.append({'requestId': identifier, 'running': observed['State']['Running']})
                guard()
                if not observed['State']['Running']:
                    code = observed['State']['ExitCode']
                    break
                time.sleep(.25)
            if code != 0: raise SourceUnavailable('document_extraction_unavailable')
            guard()
            read = "import os,sys;sys.path.insert(0,'/app');from enterprise_document_job import read_file,MAX_ENVELOPE;fd=os.open('/output',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);sys.stdout.buffer.write(read_file(fd,'result.json',MAX_ENVELOPE));os.close(fd)"
            encoded = self.command(['run', '--rm', '--platform', 'linux/amd64', '--network', 'none', '--read-only',
                '--log-driver', 'none', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
                '--mount', 'type=volume,source=' + volumes[1] + ',target=/output,readonly', self.image, 'python', '-I', '-c', read])
            guard()
            document = result(raw, mime, identifier, encoded)
            self.attempts.append({'inputSha256': hashlib.sha256(raw).hexdigest(), 'resultSha256': hashlib.sha256(encoded).hexdigest(),
                'seconds': time.monotonic() - started, 'mediaType': mime, 'exitCode': code, 'network': 'none',
                'logDriver': 'none', 'inputReadOnly': True, 'freshPerFileContainer': True})
            return document
        except ExtractionError:
            raise SourceUnavailable('document_extraction_unavailable') from None
        finally:
            # A failed launch response can still have created the named container.
            # Inspect/remove only this unguessable owned name, never broad prune.
            cleaned = subprocess.run(['docker', 'rm', '--force', container], env=self.env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
            if launched and cleaned.returncode != 0:
                raise SourceUnavailable('document_extraction_cleanup_unavailable')
            for name in reversed(created):
                self.command(['volume', 'rm', name])
