"""Run emitted Azure parser options in owned Linux, with a synthetic Batch UID.

This is not an Azure node-agent, identity, networking or cloud-lifecycle test.
Trusted staging is an explicit local fixture until the native host helper lands.
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
from enterprise_azure_jobs import task_spec, volume_names
from enterprise_azure_jobs_acceptance import config, shape
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
    receipt = json.loads(receipt_path.read_text())
    if not receipt.get('allChecksPassed', receipt.get('passed')):
        raise ValueError('Parser image qualification did not pass')
    for name, digest in receipt['sourceHashes'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Parser source qualification drift: ' + name)
    out.mkdir(parents=True)
    env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(out), 'DOCKER_HOST': args.docker_host,
           'DOCKER_CONFIG': str(ROOT / '.local/qualification-docker-config')}
    paths = [Path(__file__).resolve(), ROOT / 'src/runtime/enterprise_azure_jobs.py',
             ROOT / 'src/runtime/enterprise_document_job.py', ROOT / 'src/runtime/enterprise_document_contract.py',
             ROOT / 'tests/runtime/enterprise_azure_jobs_acceptance.py',
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
        info = json.loads(run('image', ['image', 'inspect', image]))[0]
        if info['Architecture'] != 'amd64' or info['Os'] != 'linux' or info['Config']['User'] != '10001:10001':
            raise ValueError('Unexpected parser image identity')
        owned = config()
        owned['parserImage'] = owned['parserImage'].split('@')[0] + '@' + image
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
                setup = '''import base64,json,os,sys
v=json.load(sys.stdin)
for name,b in [('document',base64.b64decode(v['raw'],validate=True)),('request.json',json.dumps(v['metadata']).encode())]:
 fd=os.open('/input/'+name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o444)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno());os.fchmod(f.fileno(),0o444)
os.chmod('/input',0o555);os.chmod('/output',0o777)
'''
                run(filename + '-synthetic-host-prepare', ['run', '--rm', '--platform', 'linux/amd64',
                    '--network=none', '--read-only', '--log-driver=none', '--user=0:0', '--cap-drop=ALL',
                    '--security-opt=no-new-privileges:true', *mounts, '-i', image, 'python', '-I', '-c', setup],
                    data=json.dumps({'raw': base64.b64encode(raw).decode(), 'metadata': metadata}).encode())
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
                collect = "import os,sys;sys.path.insert(0,'/app');from enterprise_document_job import read_file,MAX_ENVELOPE;fd=os.open('/output',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);sys.stdout.buffer.write(read_file(fd,'result.json',MAX_ENVELOPE));os.close(fd)"
                encoded = run(filename + '-synthetic-host-collect', ['run', '--rm', '--platform', 'linux/amd64',
                    '--network=none', '--read-only', '--log-driver=none', '--user=0:0', '--cap-drop=ALL',
                    '--cap-add=DAC_READ_SEARCH', '--security-opt=no-new-privileges:true',
                    '--mount', 'type=volume,source=' + volumes[1] + ',target=/output,readonly',
                    image, 'python', '-I', '-c', collect], private=True)
                document = result(raw, mime, identifier, encoded)
                if expected not in document['text']:
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
            'scope': 'Actual emitted Azure Docker parser options, Linux isolation, non-image UID and byte-bound Office/OCR result. Host staging/collection and UID are explicit local fixtures. Not Azure node-agent/default-mount behavior, host helper, Blob/MI, recovery, account/cloud, security or whole-project qualification.',
            'cloudOperations': False}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker-host', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--parser-receipt', type=Path, required=True)
    qualify(parser.parse_args())
