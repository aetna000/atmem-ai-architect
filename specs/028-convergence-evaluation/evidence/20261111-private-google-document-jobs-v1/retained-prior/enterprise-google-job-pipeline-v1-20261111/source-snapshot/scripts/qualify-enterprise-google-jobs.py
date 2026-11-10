"""Execute the emitted three-runnable plan in owned Linux containers.

Google HTTP is an explicit fixture. Native transfer CLI, UID/mount boundaries,
actual Office/PDF parser and result binding execute. No cloud account is used.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import uuid
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / 'tests/runtime'), str(ROOT / '.local/azure-runtime-sdk')]
from enterprise_document_job import request, result
from enterprise_google_jobs import job_spec
from enterprise_google_jobs_acceptance import config, discovery_check


def qualify(args):
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / '.local'): raise ValueError('Use fresh owned local evidence')
    if not args.docker_host.startswith('unix:///') or not Path(args.docker_host[7:]).is_socket(): raise ValueError('Use the owned qualification VM')
    receipts = []
    for path in [args.core_receipt, args.parser_receipt]:
        path = path.resolve()
        if not path.is_relative_to(ROOT / '.local'): raise ValueError('Use owned exact image receipts')
        value = json.loads(path.read_text())
        if not value.get('passed', value.get('allChecksPassed')): raise ValueError('Image qualification did not pass')
        for name, digest in value['sourceHashes'].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest: raise ValueError('Image qualification source drift: ' + name)
        receipts.append(value)
    out.mkdir(parents=True)
    env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(out), 'DOCKER_HOST': args.docker_host,
           'DOCKER_CONFIG': str(ROOT / '.local/qualification-docker-config')}
    checks = []; success = False
    paths = [Path(__file__).resolve(), ROOT / 'tests/runtime/enterprise_google_jobs_acceptance.py',
             *[ROOT / 'src/runtime' / name for name in ['enterprise_google_jobs.py', 'enterprise_google_transfer.py', 'enterprise_document_job.py', 'enterprise_document_contract.py']],
             ROOT / 'tests/fixtures/providers/google-batch-v1-discovery-20261111.json']
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    def run(label, command, data=None):
        done = subprocess.run(['docker', *command], env=env, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=160)
        (out / (label + '.stdout')).write_bytes(done.stdout); (out / (label + '.stderr')).write_bytes(done.stderr)
        checks.append({'check': label, 'passed': done.returncode == 0, 'exitCode': done.returncode})
        if done.returncode != 0: raise RuntimeError('Google job local qualification failed: ' + label)
        return done.stdout
    wrapper = '''import base64,hashlib,json,runpy,sys
sys.path.insert(0,'/app')
import enterprise_google_jobs as jobs
fixture=json.load(sys.stdin)
class Response:
 def __init__(self,raw):self.raw=raw;self.status_code=200
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def iter_content(self,size):
  for offset in range(0,len(self.raw),size):yield self.raw[offset:offset+size]
class Session:
 def request(self,method,url,**options):
  assert not options['allow_redirects']
  assert options['headers']['Authorization']=='Bearer SYNTHETIC-NATIVE-TOKEN'
  if method=='GET':
   assert '/storage/v1/b/owned-ephemeral-documents/o/document-jobs%2F'in url and url.endswith('%2Finput')
   assert options['params']=={'alt':'media','generation':'123'}
   return Response(base64.b64decode(fixture['raw'],validate=True))
  assert method=='POST'and '/upload/storage/v1/b/owned-ephemeral-documents/o'in url
  assert options['params']['ifGenerationMatch']=='0'and options['params']['name'].endswith('/result')
  data=options['data'];print(json.dumps({'uploadedSha256':hashlib.sha256(data).hexdigest(),'uploadedBytes':len(data)}))
  return Response(b'{"generation":"456"}')
jobs.google_metadata_token=lambda:'SYNTHETIC-NATIVE-TOKEN'
jobs.requests.Session=Session
sys.argv=['enterprise_google_transfer.py',fixture['mode']]
runpy.run_path('/app/enterprise_google_transfer.py',run_name='__main__')
'''
    try:
        images = [value['imageId'] for value in receipts]
        for side, image in zip(['transfer', 'parser'], images):
            info = json.loads(run(side + '-image', ['image', 'inspect', image]))[0]
            if info['Config']['User'] != '10001:10001' or info['Architecture'] != 'amd64' or info['Os'] != 'linux': raise ValueError('Unexpected native image identity')
        owned = config()
        owned['transferImage'] = owned['transferImage'].split('@')[0] + '@' + images[0]
        owned['parserImage'] = owned['parserImage'].split('@')[0] + '@' + images[1]
        mapping = {owned['transferImage']: images[0], owned['parserImage']: images[1]}
        schemas = json.loads((ROOT / 'tests/fixtures/providers/google-batch-v1-discovery-20261111.json').read_text())['schemas']
        for filename, mime, content in [('policy.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'twenty days'),
                                        ('invoice-scan.pdf', 'application/pdf', '42.50')]:
            folder = 'invoices' if filename.endswith('.pdf') else 'enterprise-documents'
            path = ROOT / 'benchmarks/convergence/fixtures' / folder / filename; raw = path.read_bytes()
            hashes[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
            identifier = uuid.uuid4().hex + uuid.uuid4().hex
            metadata = request(raw, mime, identifier); spec = job_spec(owned, metadata, '123')
            discovery_check(spec, schemas['Job'], schemas)
            (out / (filename + '-batch-request.json')).write_text(json.dumps(spec, indent=2) + '\n')
            volume = 'atmem-google-job-qualification-' + identifier
            created = False
            try:
                run(filename + '-volume', ['volume', 'create', volume]); created = True
                info = json.loads(run(filename + '-mountpoint', ['volume', 'inspect', volume]))[0]
                # This is the exact newly created owned VM volume, never a host
                # file or a path supplied by a document, browser or model.
                mount = info['Mountpoint']
                if not re.fullmatch('/var/lib/docker/volumes/' + re.escape(volume) + '/_data', mount): raise ValueError('Unexpected owned volume path')
                for stage, runnable in enumerate(spec['taskGroups'][0]['taskSpec']['runnables']):
                    container = runnable['container']; image = mapping[container['imageUri']]
                    command = ['run', '--rm', '--platform', 'linux/amd64', '--network', 'none', *shlex.split(container['options'])]
                    # The native Batch local paths map solely to this fresh VM
                    # volume. All production ro/rw boundaries remain unchanged.
                    base = '/mnt/disks/share/document-' + identifier
                    for binding in container['volumes']:
                        local, destination, mode = binding.split(':')
                        if not local.startswith(base): raise ValueError('Unexpected emitted bind path')
                        relative = local[len(base):]
                        command += ['--mount', 'type=bind,source=' + mount + relative + ',target=' + destination + (',readonly' if mode == 'ro' else '')]
                    for key, value in runnable.get('environment', {}).get('variables', {}).items(): command += ['--env', key + '=' + value]
                    if stage == 1:
                        logged = run(filename + '-parse', command + [image, container['entrypoint'], *container['commands']])
                        if json.loads(logged) != {'status': 'ok'}: raise ValueError('Parser did not produce a status-only result')
                    else:
                        mode = 'download' if stage == 0 else 'upload'
                        logged = run(filename + '-' + mode, command + [image, 'python', '-I', '-c', wrapper],
                            json.dumps({'mode': mode, 'raw': base64.b64encode(raw).decode()}).encode())
                        if stage == 2: uploaded = json.loads(logged)
                read = "import os,sys;sys.path.insert(0,'/app');from enterprise_document_job import read_file,MAX_ENVELOPE;fd=os.open('/output',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);sys.stdout.buffer.write(read_file(fd,'result.json',MAX_ENVELOPE));os.close(fd)"
                encoded = run(filename + '-collect', ['run', '--rm', '--platform', 'linux/amd64', '--network', 'none', '--read-only',
                    '--log-driver', 'none', '--cap-drop', 'ALL', '--mount', 'type=bind,source=' + mount + '/output,target=/output,readonly',
                    images[0], 'python', '-I', '-c', read])
                document = result(raw, mime, identifier, encoded)
                if content not in document['text'] or uploaded != {'uploadedSha256': hashlib.sha256(encoded).hexdigest(), 'uploadedBytes': len(encoded)}:
                    raise ValueError('Actual parsed/uploaded bytes differ from the consumer binding')
                checks.append({'check': filename + '-three-stage-byte-bound-answer', 'passed': True})
            finally:
                if created: run(filename + '-cleanup', ['volume', 'rm', volume])
        if any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest for name, digest in hashes.items()): raise ValueError('Qualification source changed')
        success = True
    finally:
        (out / 'receipt.json').write_text(json.dumps({'recordedAt': datetime.now(timezone.utc).isoformat(), 'passed': success,
            'checks': checks, 'sourceHashes': hashes, 'coreImageId': receipts[0]['imageId'], 'parserImageId': receipts[1]['imageId'],
            'scope': 'Actual emitted sequential transfer CLI/UID/POSIX mounts/Office/PDF consumer in owned Linux. Native Google HTTP responses are fixtures; all local containers use network none. Not Batch agent semantics, IAM/network, account execution, latency, security or whole-project acceptance.',
            'cloudOperations': False}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--docker-host', required=True)
    parser.add_argument('--out', type=Path, required=True); parser.add_argument('--core-receipt', type=Path, required=True)
    parser.add_argument('--parser-receipt', type=Path, required=True); qualify(parser.parse_args())
