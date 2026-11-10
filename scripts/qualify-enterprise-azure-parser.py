"""Run emitted Azure parser options in owned Linux, with a synthetic Batch UID.

This is not an Azure node-agent, identity, networking or cloud-lifecycle test.
Current transfer sources are injected into an existing qualified core image;
native ARM/Blob responses and identity are explicit offline fixtures.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / 'tests/runtime')]
from enterprise_azure_jobs import task_spec, volume_names, transfer_metadata
from enterprise_azure_jobs_acceptance import config, shape
from enterprise_azure_objects_acceptance import objects, policy
from enterprise_document_job import request, result


def qualify(args):
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / '.local'):
        raise ValueError('Use fresh owned local evidence')
    if not args.docker_host.startswith('unix:///') or not Path(args.docker_host[7:]).is_socket():
        raise ValueError('Use the owned qualification VM')
    receipt_path = args.parser_receipt.resolve()
    if not receipt_path.is_relative_to(ROOT / '.local'):
        raise ValueError('Use the owned parser qualification receipt')
    core_path = args.core_receipt.resolve()
    if not core_path.is_relative_to(ROOT / '.local'):
        raise ValueError('Use the owned core image receipt')
    receipt = json.loads(receipt_path.read_text())
    core = json.loads(core_path.read_text())
    for role, value in [('parser', receipt), ('core', core)]:
        if not value.get('allChecksPassed', value.get('passed')):
            raise ValueError(role + ' image qualification did not pass')
        for name, digest in value['sourceHashes'].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                raise ValueError(role + ' source qualification drift: ' + name)
    out.mkdir(parents=True)
    env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(out), 'DOCKER_HOST': args.docker_host,
           'DOCKER_CONFIG': str(ROOT / '.local/qualification-docker-config')}
    paths = [Path(__file__).resolve(), ROOT / 'src/runtime/enterprise_azure_jobs.py',
             ROOT / 'src/runtime/enterprise_document_job.py', ROOT / 'src/runtime/enterprise_document_contract.py',
             ROOT / 'tests/runtime/enterprise_azure_jobs_acceptance.py',
             ROOT / 'tests/runtime/enterprise_azure_objects_acceptance.py',
             ROOT / 'tests/runtime/enterprise_azure_transfer_acceptance.py',
             ROOT / 'src/runtime/enterprise_azure_objects.py', ROOT / 'src/runtime/enterprise_azure_transfer.py',
             ROOT / 'tests/fixtures/providers/azure-batch-2026-10-01-20261111.json',
             ROOT / 'tests/fixtures/providers/azure-batch-2026-10-01-20261111.provenance.json']
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    checks, passed = [], False

    def run(label, command, *, data=None, private=False):
        done = subprocess.run(['docker', *command], env=env, input=data,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=160)
        (out / (label + '.stdout')).write_bytes(
            json.dumps({'bytes': len(done.stdout), 'sha256': hashlib.sha256(done.stdout).hexdigest()}).encode()
            if private else done.stdout)
        (out / (label + '.stderr')).write_bytes(done.stderr)
        checks.append({'check': label, 'passed': done.returncode == 0, 'exitCode': done.returncode})
        if done.returncode != 0:
            raise RuntimeError('Azure local parser qualification failed: ' + label)
        return done.stdout

    try:
        image = receipt['imageId']
        core_image = core['imageId']
        info = json.loads(run('image', ['image', 'inspect', image]))[0]
        if info['Architecture'] != 'amd64' or info['Os'] != 'linux' or info['Config']['User'] != '10001:10001':
            raise ValueError('Unexpected parser image identity')
        core_info = json.loads(run('core-image', ['image', 'inspect', core_image]))[0]
        if core_info['Architecture'] != 'amd64' or core_info['Os'] != 'linux' or core_info['Config']['User'] != '10001:10001':
            raise ValueError('Unexpected core image identity')
        owned = config()
        owned['parserImage'] = owned['parserImage'].split('@')[0] + '@' + image
        owned['transferImage'] = owned['transferImage'].split('@')[0] + '@' + core_image
        modules = {name: base64.b64encode((ROOT / 'src/runtime' / (name + '.py')).read_bytes()).decode()
                   for name in ['enterprise_azure_objects', 'enterprise_azure_transfer']}
        owner = objects()
        policies = {value['id']: value for value in policy(owner)}
        owner.close()
        wrapper = '''import base64,hashlib,json,sys,types
sys.path.insert(0,'/app')
fixture=json.load(sys.stdin)
for name,encoded in fixture['modules'].items():
 module=types.ModuleType(name);module.__file__='/app/'+name+'.py';sys.modules[name]=module
 exec(compile(base64.b64decode(encoded,validate=True),module.__file__,'exec'),module.__dict__)
import enterprise_azure_objects as native
import enterprise_azure_transfer as transfer
uploaded=None
class Credential:
 def get_token(self,scope):
  assert scope in {'https://management.azure.com/.default','https://storage.azure.com/.default'}
  return types.SimpleNamespace(token='SYNTHETIC-NATIVE-TOKEN')
 def close(self):pass
class Response:
 def __init__(self,raw,status=200,headers=None):self.raw=raw;self.status_code=status;self.headers=headers or {}
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def iter_content(self,size):
  for offset in range(0,len(self.raw),size):yield self.raw[offset:offset+size]
class Session:
 def close(self):pass
 def request(self,method,url,**options):
  global uploaded
  assert self.trust_env is False and options['allow_redirects'] is False and options['stream'] is True
  assert options['headers']['Authorization']=='Bearer SYNTHETIC-NATIVE-TOKEN'
  if url.startswith('https://management.azure.com'):
   assert method=='GET' and options['params']=={'api-version':'2025-06-01'}
   return Response(json.dumps(fixture['policies'][url.removeprefix('https://management.azure.com')]).encode())
  assert url.startswith('https://ownedtemporary.blob.core.windows.net/documents/document-jobs/')
  if method=='GET':
   assert url.endswith('/input') and options['headers']['If-Match']=='"0x8DA123ABCDEF"'
   raw=base64.b64decode(fixture['raw'],validate=True)
   return Response(raw,headers={'ETag':'"0x8DA123ABCDEF"','Content-Length':str(len(raw)),'x-ms-blob-type':'BlockBlob','x-ms-server-encrypted':'true'})
  assert method=='PUT' and url.endswith('/result') and options['headers']['If-None-Match']=='*'
  raw=options['data'];uploaded={'uploadedSha256':hashlib.sha256(raw).hexdigest(),'uploadedBytes':len(raw)}
  return Response(b'',201,{'ETag':'"0x8DA123ABCDEF"','x-ms-request-server-encrypted':'true'})
native.requests.Session=Session
native.AzureDocumentObjects._credential=lambda self:Credential()
sys.argv=['enterprise_azure_transfer.py',fixture['mode']]
transfer.main()
if fixture['mode']=='upload':
 assert uploaded is not None
 print(json.dumps(uploaded))
'''
        schemas = json.loads((ROOT / 'tests/fixtures/providers/azure-batch-2026-10-01-20261111.json').read_text())['definitions']
        for filename, mime, expected in [
                ('policy.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'twenty days'),
                ('invoice-scan.pdf', 'application/pdf', '42.50')]:
            folder = 'invoices' if filename.endswith('.pdf') else 'enterprise-documents'
            fixture = ROOT / 'benchmarks/convergence/fixtures' / folder / filename
            raw = fixture.read_bytes()
            hashes[str(fixture.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
            identifier = uuid.uuid4().hex + uuid.uuid4().hex
            metadata = request(raw, mime, identifier)
            spec = task_spec(owned, identifier)
            shape(spec, schemas['BatchTaskCreateOptions'], schemas)
            (out / (filename + '-native-task.json')).write_text(json.dumps(spec, indent=2) + '\n')
            volumes = volume_names(identifier)
            created, containers = [], []
            try:
                for index, volume in enumerate(volumes):
                    run(filename + '-volume-' + str(index), ['volume', 'create', volume])
                    created.append(volume)
                mounts = ['--mount', 'type=volume,source=' + volumes[0] + ',target=/input',
                          '--mount', 'type=volume,source=' + volumes[1] + ',target=/output']
                envelope = json.dumps(transfer_metadata(owned, metadata, '"0x8DA123ABCDEF"'), separators=(',', ':'))
                def stage(mode):
                    return json.dumps({'mode': mode, 'raw': base64.b64encode(raw).decode(),
                                       'modules': modules, 'policies': policies}).encode()
                run(filename + '-native-transfer-download', ['run', '--rm', '--platform', 'linux/amd64',
                    '--network=none', '--read-only', '--log-driver=none', '--user=0:0', '--cap-drop=ALL',
                    '--security-opt=no-new-privileges:true', '--env', 'DOCUMENT_JOB=' + envelope,
                    *mounts, '-i', core_image, 'python', '-I', '-c', wrapper], data=stage('download'))
                options = shlex.split(spec['containerSettings']['containerRunOptions'])
                # Explicit node-agent UID fixture: deliberately differs from the
                # image's UID. No claim that Batch itself selected this UID.
                probe = '''import errno,json,os
assert os.getuid()==42424
assert os.stat('/input/document').st_mode&0o777==0o444
try:
 os.open('/input/document',os.O_WRONLY)
 raise AssertionError('input writable')
except OSError as e:assert e.errno in {errno.EROFS,errno.EACCES}
try:
 os.open('/outside',os.O_WRONLY|os.O_CREAT,0o600)
 raise AssertionError('root writable')
except OSError as e:assert e.errno in {errno.EROFS,errno.EACCES}
assert not os.path.exists('/var/run/docker.sock')
assert not any(k in os.environ for k in ['DOCUMENT_JOB','WORKLOAD_IDENTITY_CLIENT_ID','AZ_BATCH_JOB_PREP_DIR','AZ_BATCH_TASK_DIR'])
print(json.dumps({'nonImageUid':True,'readOnlyInput':True,'readOnlyRoot':True,'noHostSocket':True}))
'''
                run(filename + '-native-options-probe', ['run', '--platform', 'linux/amd64', '--user=42424:42424',
                    *options, image, 'python', '-I', '-c', probe])
                container = 'atmem-azure-parser-qualification-' + identifier
                containers.append(container)
                run(filename + '-create', ['create', '--name', container, '--platform', 'linux/amd64',
                    '--user=42424:42424', *options, image, *shlex.split(spec['commandLine'])])
                observed = json.loads(run(filename + '-inspect', ['inspect', container]))[0]
                host = observed['HostConfig']
                if (host['NetworkMode'] != 'none' or not host['ReadonlyRootfs'] or
                        host['LogConfig']['Type'] != 'none' or host['CapDrop'] != ['ALL'] or
                        observed['Config']['User'] != '42424:42424'):
                    raise ValueError('Docker did not apply emitted isolation settings')
                actual = {entry['Destination']: entry for entry in observed['Mounts']}
                if actual['/input']['RW'] or not actual['/output']['RW']:
                    raise ValueError('Docker did not apply literal read-only input mount')
                logged = run(filename + '-actual-parse', ['start', '--attach', container])
                if json.loads(logged) != {'status': 'ok'}:
                    raise ValueError('Parser failed or logged more than bounded status')
                containers.remove(container)  # --rm performed native removal.
                upload_mounts = [value + ',readonly' if value.startswith('type=volume,') else value for value in mounts]
                uploaded = json.loads(run(filename + '-native-transfer-upload', ['run', '--rm', '--platform', 'linux/amd64',
                    '--network=none', '--read-only', '--log-driver=none', '--user=0:0', '--cap-drop=ALL',
                    '--cap-add=DAC_READ_SEARCH', '--security-opt=no-new-privileges:true', '--env', 'DOCUMENT_JOB=' + envelope,
                    *upload_mounts, '-i', core_image, 'python', '-I', '-c', wrapper], data=stage('upload')))
                collect = "import os,sys;sys.path.insert(0,'/app');from enterprise_document_job import read_file,MAX_ENVELOPE;fd=os.open('/output',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);sys.stdout.buffer.write(read_file(fd,'result.json',MAX_ENVELOPE));os.close(fd)"
                encoded = run(filename + '-synthetic-host-collect', ['run', '--rm', '--platform', 'linux/amd64',
                    '--network=none', '--read-only', '--log-driver=none', '--user=0:0', '--cap-drop=ALL',
                    '--cap-add=DAC_READ_SEARCH', '--security-opt=no-new-privileges:true',
                    '--mount', 'type=volume,source=' + volumes[1] + ',target=/output,readonly',
                    image, 'python', '-I', '-c', collect], private=True)
                document = result(raw, mime, identifier, encoded)
                if (expected not in document['text'] or uploaded != {
                        'uploadedSha256': hashlib.sha256(encoded).hexdigest(), 'uploadedBytes': len(encoded)}):
                    raise ValueError('Actual Office/OCR result missed expected fixture content')
                checks.append({'check': filename + '-byte-bound-result-nonimage-uid', 'passed': True})
            finally:
                for container in containers:
                    # Only random owned names from this invocation; never prune.
                    run(filename + '-cancel', ['rm', '--force', container])
                for index, volume in enumerate(reversed(created)):
                    run(filename + '-cleanup-' + str(index), ['volume', 'rm', volume])
        if any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest for name, digest in hashes.items()):
            raise ValueError('Qualification source changed during execution')
        passed = True
    finally:
        (out / 'receipt.json').write_text(json.dumps({'recordedAt': datetime.now(timezone.utc).isoformat(),
            'passed': passed, 'checks': checks, 'sourceHashes': hashes,
            'parserImageId': receipt['imageId'], 'parserReceiptSha256': hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            'coreImageId': core['imageId'], 'coreReceiptSha256': hashlib.sha256(core_path.read_bytes()).hexdigest(),
            'scope': 'Actual emitted Azure Docker parser options, Linux isolation, non-image UID and byte-bound Office/OCR result through native transfer CLI/ARM/Blob adapter. Transfer sources injected into existing qualified core image; native HTTP/MI and Batch UID are explicit offline fixtures. Not an installed transfer artifact, Azure node-agent/default-mount behavior, host helper, cloud Blob/MI, recovery, account, security or whole-project qualification.',
            'cloudOperations': False}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker-host', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--parser-receipt', type=Path, required=True)
    parser.add_argument('--core-receipt', type=Path, required=True)
    qualify(parser.parse_args())
