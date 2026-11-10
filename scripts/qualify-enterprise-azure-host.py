"""Owned Engine integration; ACR identity/daemon default/ARM/MI are fixtures.

Builds an explicitly local qualification transfer image with current installed
sources and an offline HTTP wrapper. No production image or cloud is published.
The real standalone host code owns actual Engine containers/volumes and recovery.
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
import shutil
import subprocess
import sys
import time
import uuid
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / 'tests/runtime')]
from enterprise_azure_jobs_acceptance import config
from enterprise_azure_jobs import task_spec, transfer_metadata
from enterprise_azure_host import Host, Store, Engine, API, volumes
from enterprise_document_job import request

NODE_ID = 'tvm-fixture-node'

WRAPPER = '''import hashlib,json,os,runpy,sys,types
from pathlib import Path
sys.path.insert(0,'/app')
import enterprise_azure_objects as native
from enterprise_document_job import result
metadata=json.loads(os.environ['DOCUMENT_JOB']);expected=metadata['request']
fixtures=[Path('/qualification/policy.docx'),Path('/qualification/invoice-scan.pdf')]
raw=next(p.read_bytes() for p in fixtures if hashlib.sha256(p.read_bytes()).hexdigest()==expected['sha256'])
base='/subscriptions/'+metadata['subscriptionId']+'/resourceGroups/'+metadata['resourceGroup']+'/providers/Microsoft.Storage/storageAccounts/'+metadata['storageAccount']
service=base+'/blobServices/default';container=service+'/containers/'+metadata['container']
policies={base:{'id':base,'location':metadata['region'],'kind':'StorageV2','sku':{'name':'Standard_LRS'},'properties':{
 'primaryLocation':metadata['region'],'supportsHttpsTrafficOnly':True,'minimumTlsVersion':'TLS1_2','allowSharedKeyAccess':False,
 'allowBlobPublicAccess':False,'publicNetworkAccess':'Disabled','encryption':{'services':{'blob':{'enabled':True}}}}},
 service:{'id':service,'properties':{'isVersioningEnabled':False,**{k:{'enabled':False} for k in ['deleteRetentionPolicy','containerDeleteRetentionPolicy','restorePolicy','changeFeed']}}},
 container:{'id':container,'properties':{'publicAccess':'None','hasImmutabilityPolicy':False,'hasLegalHold':False}}}
class Credential:
 def get_token(self,scope):
  assert scope in {'https://management.azure.com/.default','https://storage.azure.com/.default'}
  return types.SimpleNamespace(token='SYNTHETIC-NATIVE-TOKEN')
 def close(self):pass
class Response:
 def __init__(self,body,status=200,headers=None):self.body=body;self.status_code=status;self.headers=headers or {}
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def iter_content(self,size):
  for offset in range(0,len(self.body),size):yield self.body[offset:offset+size]
class Session:
 def close(self):pass
 def request(self,method,url,**options):
  assert self.trust_env is False and options['allow_redirects'] is False and options['stream'] is True
  assert options['headers']['Authorization']=='Bearer SYNTHETIC-NATIVE-TOKEN'
  if url.startswith('https://management.azure.com'):
   assert method=='GET' and options['params']=={'api-version':'2025-06-01'}
   return Response(json.dumps(policies[url.removeprefix('https://management.azure.com')]).encode())
  prefix='https://'+metadata['storageAccount']+'.blob.core.windows.net/'+metadata['container']+'/document-jobs/'+expected['requestId']
  if method=='GET':
   assert url==prefix+'/input' and options['headers']['If-Match']==metadata['inputETag']
   return Response(raw,headers={'ETag':metadata['inputETag'],'Content-Length':str(len(raw)),'x-ms-blob-type':'BlockBlob','x-ms-server-encrypted':'true'})
  assert method=='PUT' and url==prefix+'/result' and options['headers']['If-None-Match']=='*'
  parsed=result(raw,expected['mediaType'],expected['requestId'],options['data'])
  assert ('42.50' if expected['mediaType']=='application/pdf' else 'twenty days') in parsed['text']
  return Response(b'',201,{'ETag':'"0x8DA123ABCDEF"','x-ms-request-server-encrypted':'true'})
native.requests.Session=Session
native.AzureDocumentObjects._credential=lambda self:Credential()
sys.argv=['enterprise_azure_transfer.py',sys.argv[1]]
runpy.run_path('/app/enterprise_azure_transfer.py',run_name='__main__')
'''

ROOT_WRAPPER = '''import base64,json,os,runpy,sys
from pathlib import Path
v=json.load(sys.stdin);config=v['config'];sha=config['hostHelperSha256']
base=Path('/opt/atmem')/sha;base.mkdir(mode=0o755)
helper=base/'enterprise_azure_host.py';helper.write_bytes(base64.b64decode(v['source'],validate=True));helper.chmod(0o444)
policy=Path('/etc/atmem/document-host.json');policy.write_text(json.dumps(config));policy.chmod(0o600)
node=Path('/etc/atmem/document-host-node.json');node.write_text(json.dumps({'format':'enterprise-azure-document-node-v1','nodeId':'tvm-fixture-node'}));node.chmod(0o600)
state=Path('/var/lib/atmem/document-jobs');state.mkdir(mode=0o700)
namespace=runpy.run_path(str(helper),run_name='qualification_host')
class NoEngineCalls:
 def __init__(self):pass
 def call(self,*a,**k):raise AssertionError('Filesystem fixture must not contact an Engine')
main=namespace['main'];main.__globals__['Engine']=NoEngineCalls
os.environ.clear();sys.argv=[str(helper),'reap'];main();checks=1
def rejected():
 try:main()
 except SystemExit as e:assert str(e)=='Owned Azure document host operation could not complete; recovery remains pending.'
 else:raise AssertionError('Unsafe host state accepted')
base.chmod(0o777);rejected();base.chmod(0o755);checks+=1
policy.write_text(json.dumps({**config,'hostHelperSha256':'0'*64}));rejected();policy.write_text(json.dumps(config));checks+=1
state.chmod(0o755);rejected();state.chmod(0o700);checks+=1
policy.rename(policy.with_suffix('.original'));policy.symlink_to(policy.with_suffix('.original'));rejected();policy.unlink();policy.with_suffix('.original').rename(policy);checks+=1
sys.argv=[str(helper),'prepare'];os.environ.update({'DOCUMENT_JOB':json.dumps(v['metadata']),'DOCUMENT_TRANSFER_IMAGE':config['transferImage'],
 'AZ_BATCH_JOB_ID':v['metadata']['request']['requestId'],'AZ_BATCH_POOL_ID':'foreign-pool','AZ_BATCH_ACCOUNT_NAME':config['batchAccount']})
rejected();checks+=1
print(json.dumps({'rootFilesystemMainChecks':checks,'nativeCalls':0}))
'''


class FixtureRegistryEngine:
    """Only identity and offline transfer command are mapped; sandbox fields aren't."""
    def __init__(self, engine, mapping, *, crash=False):
        self.engine, self.mapping, self.crash = engine, mapping, crash
        self.observations = []

    def call(self, method, path, body=None, **options):
        endpoint = urlsplit(path).path
        if endpoint == API + '/info':
            value = self.engine.call(method, path, body, **options)
            self.observations.append({'fixture': 'daemon-default-logging', 'observed': value.get('LoggingDriver'), 'required': 'none'})
            return {**value, 'LoggingDriver': 'none'}
        if endpoint.startswith(API + '/images/'):
            native = next(key for key in self.mapping if quote(key, safe='') in path)
            physical = self.mapping[native]
            value = self.engine.call(method, API + '/images/' + quote(physical, safe='') + '/json', body, **options)
            return {**value, 'RepoDigests': [native]}
        if endpoint == API + '/containers/create':
            original = body
            body = {**body, 'Image': self.mapping[body['Image']],
                    'Cmd': ['python', '-I', '/qualification/azure_transfer_fixture.py', body['Cmd'][-1]]}
            self.observations.append({'fixture': 'offline-native-identity-and-command', 'nativeImage': original['Image'],
                'physicalImage': body['Image'], 'nativeCommand': original['Cmd'], 'actualCommand': body['Cmd']})
        value = self.engine.call(method, path, body, **options)
        if method == 'POST' and endpoint == API + '/volumes/create' and self.crash:
            os._exit(89)  # Actual process death after a native volume is created.
        if method == 'GET' and re.fullmatch(re.escape(API) + '/containers/[0-9a-f]{64}/json', endpoint) and value is not None:
            self.observations.append({'nativeContainer': value})
            actual = value['Config']['Image']
            for native, physical in self.mapping.items():
                if actual == physical:
                    return {**value, 'Config': {**value['Config'], 'Image': native}}
        return value


class ReceiptSink:
    """Offline receipt transport; real Engine must show no remaining writers."""
    def __init__(self, engine):
        self.engine, self.receipts = engine, []
    def publish(self, value):
        for name in volumes(value['requestId']):
            if self.engine.call('GET', API + '/volumes/' + name, missing=True) is not None:
                raise ValueError('Receipt preceded native volume removal')
        self.receipts.append(dict(value))


def open_store(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: return Store(fd, uid=os.geteuid())
    finally: os.close(fd)


def qualify(args):
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / '.local'):
        raise ValueError('Use fresh owned local evidence')
    if not args.docker_host.startswith('unix:///') or not Path(args.docker_host[7:]).is_socket():
        raise ValueError('Use the owned qualification Engine')
    receipts = []
    for path in [args.core_receipt, args.parser_receipt]:
        path = path.resolve()
        if not path.is_relative_to(ROOT / '.local'): raise ValueError('Use owned image receipts')
        value = json.loads(path.read_text())
        if not value.get('passed', value.get('allChecksPassed')): raise ValueError('Image qualification did not pass')
        for name, digest_ in value['sourceHashes'].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest_: raise ValueError('Qualified source drift: ' + name)
        receipts.append(value)
    out.mkdir(parents=True)
    env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(out), 'DOCKER_HOST': args.docker_host,
           'DOCKER_CONFIG': str(ROOT / '.local/qualification-docker-config')}
    sources = [Path(__file__).resolve(), *[ROOT / 'src/runtime' / name for name in [
        'enterprise_azure_host.py', 'enterprise_azure_jobs.py', 'enterprise_azure_objects.py', 'enterprise_azure_transfer.py',
        'enterprise_document_contract.py', 'enterprise_document_job.py']], ROOT / 'tests/runtime/enterprise_azure_host_acceptance.py',
        ROOT / 'tests/runtime/enterprise_azure_cleanup_receipts.py', ROOT / 'tests/runtime/enterprise_azure_job_recovery.py']
    fixtures = [ROOT / 'benchmarks/convergence/fixtures/enterprise-documents/policy.docx',
                ROOT / 'benchmarks/convergence/fixtures/invoices/invoice-scan.pdf']
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sources, *fixtures]}
    checks, observations, success = [], [], False
    core_image = None

    def run(label, command, *, data=None):
        done = subprocess.run(['docker', *command], input=data, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        (out / (label + '.stdout')).write_bytes(done.stdout)
        (out / (label + '.stderr')).write_bytes(done.stderr)
        checks.append({'check': label, 'passed': done.returncode == 0, 'exitCode': done.returncode})
        if done.returncode: raise RuntimeError('Azure host qualification failed: ' + label)
        return done.stdout

    try:
        suffix = hashlib.sha256(str(out).encode()).hexdigest()[:16]
        parent_tag = 'atmem-qualification/azure-host-parent:qualification-' + suffix
        run('parent-tag', ['image', 'tag', receipts[0]['imageId'], parent_tag])
        context = out / 'qualification-context'; context.mkdir()
        (context / 'Dockerfile').write_text('ARG BASE\nFROM ${BASE}\nCOPY enterprise_azure_objects.py enterprise_azure_transfer.py /app/\nCOPY azure_transfer_fixture.py policy.docx invoice-scan.pdf /qualification/\nUSER 10001:10001\n')
        (context / '.dockerignore').write_text('*\n!Dockerfile\n!enterprise_azure_objects.py\n!enterprise_azure_transfer.py\n!azure_transfer_fixture.py\n!policy.docx\n!invoice-scan.pdf\n')
        for name in ['enterprise_azure_objects.py', 'enterprise_azure_transfer.py']: shutil.copy2(ROOT / 'src/runtime' / name, context / name)
        for fixture in fixtures: shutil.copy2(fixture, context / fixture.name)
        (context / 'azure_transfer_fixture.py').write_text(WRAPPER)
        tag = 'atmem-qualification/azure-host-transfer:qualification-' + suffix
        run('build-local-offline-qualification-artifact', ['build', '--platform', 'linux/amd64', '--network', 'none',
            '--build-arg', 'BASE=' + parent_tag, '--tag', tag, str(context)])
        info = json.loads(run('qualification-image', ['image', 'inspect', tag]))[0]
        if info['Architecture'] != 'amd64' or info['Os'] != 'linux' or info['Config']['User'] != '10001:10001':
            raise ValueError('Unexpected qualification artifact')
        core_image = info['Id']
        expected = {name: hashlib.sha256((context / name).read_bytes()).hexdigest() for name in
                    ['enterprise_azure_objects.py', 'enterprise_azure_transfer.py']}
        code = 'import hashlib,json;from pathlib import Path;print(json.dumps({n:hashlib.sha256((Path("/app")/n).read_bytes()).hexdigest()for n in ' + repr(list(expected)) + '}))'
        if json.loads(run('installed-transfer-source-hashes', ['run', '--rm', '--network', 'none', '--read-only', core_image, 'python', '-I', '-c', code])) != expected:
            raise ValueError('Installed transfer sources do not match')
        owned = config()
        owned['hostHelperSha256'] = hashes['src/runtime/enterprise_azure_host.py']
        owned['parserImage'] = owned['parserImage'].split('@')[0] + '@' + receipts[1]['imageId']
        owned['transferImage'] = owned['transferImage'].split('@')[0] + '@' + core_image
        filesystem_metadata = transfer_metadata(owned, request(fixtures[0].read_bytes(),
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document', uuid.uuid4().hex + uuid.uuid4().hex), '"0x8DA123ABCDEF"')
        root_result = json.loads(run('linux-root-main-protected-filesystem', ['run', '--rm', '--platform', 'linux/amd64',
            '--network', 'none', '--read-only', '--user', '0:0', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
            '--tmpfs', '/etc/atmem:rw,noexec,nosuid,nodev,mode=755',
            '--tmpfs', '/opt/atmem:rw,noexec,nosuid,nodev,mode=755',
            '--tmpfs', '/var/lib/atmem:rw,noexec,nosuid,nodev,mode=755',
            '-i', core_image, 'python', '-I', '-c', ROOT_WRAPPER],
            data=json.dumps({'config': owned, 'metadata': filesystem_metadata,
                'source': base64.b64encode((ROOT / 'src/runtime/enterprise_azure_host.py').read_bytes()).decode()}).encode()))
        if root_result != {'rootFilesystemMainChecks': 6, 'nativeCalls': 0}:
            raise ValueError('Actual protected Linux root CLI checks failed')
        mapping = {owned['parserImage']: receipts[1]['imageId'], owned['transferImage']: core_image}
        engine = Engine(args.docker_host[7:])
        facade = FixtureRegistryEngine(engine, mapping)
        receipts_sink = ReceiptSink(engine)
        store = open_store(out / 'state')
        host = Host(owned, store, facade, node_id=NODE_ID, receipts=receipts_sink)
        try:
            for fixture in fixtures:
                raw = fixture.read_bytes()
                mime = 'application/pdf' if fixture.suffix == '.pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                identifier = uuid.uuid4().hex + uuid.uuid4().hex
                metadata = transfer_metadata(owned, request(raw, mime, identifier), '"0x8DA123ABCDEF"')
                state = None
                try:
                    host.prepare(metadata)
                    state = store.read(identifier)
                    checks.append({'check': fixture.name + '-native-host-prepared', 'passed': state['phase'] == 'ready'})
                    task = task_spec(owned, identifier)
                    (out / (fixture.name + '-native-task.json')).write_text(json.dumps(task, indent=2) + '\n')
                    container = 'atmem-azure-host-parser-' + identifier
                    cid = run(fixture.name + '-native-parser-create', ['create', '--name', container, '--platform', 'linux/amd64',
                        '--user', '42424:42424', *shlex.split(task['containerSettings']['containerRunOptions']), mapping[owned['parserImage']], *shlex.split(task['commandLine'])]).decode().strip()
                    host.container(state, cid)
                    if json.loads(run(fixture.name + '-actual-parse', ['start', '--attach', container])) != {'status': 'ok'}:
                        raise ValueError('Actual parser did not succeed')
                    host.release(metadata, owned['transferImage'])
                    final = store.read(identifier)
                    if final['phase'] != 'cleaned' or not final['published'] or not final['receiptPublished']:
                        raise ValueError('Host did not publish and clean the byte-bound result')
                    for name in volumes(identifier):
                        if engine.call('GET', API + '/volumes/' + name, missing=True) is not None:
                            raise ValueError('Native owned volume remains after release')
                    checks.append({'check': fixture.name + '-installed-transfer-byte-bound-native-cleanup', 'passed': True})
                finally:
                    current = store.read(identifier)
                    if current is not None and current['phase'] != 'cleaned': host.cleanup(current)
            # A child dies after creating one actual native volume. Its durable
            # intent and kernel-released lock allow an independent parent reaper.
            crash_id = uuid.uuid4().hex + uuid.uuid4().hex
            crash_value = transfer_metadata(owned, request(fixtures[0].read_bytes(),
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document', crash_id), '"0x8DA123ABCDEF"')
            payload = {'config': owned, 'mapping': mapping, 'metadata': crash_value}
            done = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--crash-fixture', str(out / 'state'), args.docker_host[7:]],
                input=json.dumps(payload).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            (out / 'actual-process-death.stderr').write_bytes(done.stderr)
            if done.returncode != 89: raise ValueError('Actual child did not die at the native creation boundary')
            state = store.read(crash_id)
            if state['phase'] != 'preparing' or engine.call('GET', API + '/volumes/' + volumes(crash_id)[0], missing=True) is None:
                raise ValueError('Process death did not leave committed ownership and native volume')
            Host(owned, store, facade, node_id=NODE_ID, receipts=receipts_sink, clock=lambda: state['expiresAt'] + 1).reap()
            if store.read(crash_id)['phase'] != 'cleaned' or store.read(crash_id)['published']:
                raise ValueError('Independent native recovery failed')
            checks.append({'check': 'actual-process-death-native-volume-recovered', 'passed': True, 'exitCode': done.returncode})
            unrelated_name = 'atmem-azure-host-unrelated-' + uuid.uuid4().hex
            unrelated_labels = {'qualificationOwner': suffix}
            engine.call('POST', API + '/volumes/create', {'Name': unrelated_name, 'Driver': 'local', 'Labels': unrelated_labels}, statuses=(201,))
            try:
                for scenario in ['hung-parser', 'foreign-consumer']:
                    identifier = uuid.uuid4().hex + uuid.uuid4().hex
                    metadata = transfer_metadata(owned, request(fixtures[0].read_bytes(),
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document', identifier), '"0x8DA123ABCDEF"')
                    cid = None
                    try:
                        host.prepare(metadata)
                        state = store.read(identifier)
                        task = task_spec(owned, identifier)
                        options = shlex.split(task['containerSettings']['containerRunOptions'])
                        if scenario == 'foreign-consumer':
                            # Owned by this qualification, deliberately unrelated
                            # to Host's state/labels. Reaper must leave it alone.
                            options = [item for item in options if not item.startswith('--label=')]
                            options.append('--label=qualificationOwner=' + suffix)
                        name = 'atmem-azure-host-' + scenario + '-' + identifier
                        cid = run(scenario + '-create', ['create', '--name', name, '--platform', 'linux/amd64',
                            '--user', '42424:42424', *options, mapping[owned['parserImage']],
                            'python', '-I', '-c', 'import time;time.sleep(300)']).decode().strip()
                        run(scenario + '-start', ['start', name])
                        recovering = Host(owned, store, facade, node_id=NODE_ID, receipts=receipts_sink, clock=lambda: state['expiresAt'] + 1)
                        if scenario == 'foreign-consumer':
                            try: recovering.reap()
                            except ValueError: pass
                            else: raise ValueError('Recovery accepted a foreign volume consumer')
                            observed = engine.call('GET', API + '/containers/' + cid + '/json')
                            if observed['Config']['Labels'].get('qualificationOwner') != suffix or not observed['State']['Running']:
                                raise ValueError('Recovery changed the unrelated consumer')
                            if any(engine.call('GET', API + '/volumes/' + volume, missing=True) is None for volume in volumes(identifier)):
                                raise ValueError('Recovery removed a volume in use by a foreign consumer')
                            checks.append({'check': 'actual-foreign-consumer-preserved-with-volumes', 'passed': True})
                            # Remove only the independently marker/ID-bound
                            # qualification fixture, then retry normal recovery.
                            engine.call('DELETE', API + '/containers/' + cid + '?force=true', statuses=(204,), missing=True)
                            cid = None
                        deadline = time.monotonic() + 8
                        while True:
                            try:
                                recovering.reap()
                                break
                            except ValueError:
                                if time.monotonic() >= deadline: raise
                                time.sleep(.25)  # Native --rm completion can race DELETE.
                        final = store.read(identifier)
                        if final['phase'] != 'cleaned' or final['published'] or not final['receiptPublished']:
                            raise ValueError('Expiry cleanup did not finish without publication')
                        if engine.call('GET', API + '/volumes/' + unrelated_name)['Labels'] != unrelated_labels:
                            raise ValueError('Recovery changed the unrelated standalone volume')
                        checks.append({'check': scenario + '-actual-native-expiry-cleanup', 'passed': True})
                        cid = None
                    finally:
                        if cid is not None:
                            observed = engine.call('GET', API + '/containers/' + cid + '/json', missing=True)
                            if observed is not None and observed['Config']['Labels'].get('qualificationOwner') == suffix:
                                engine.call('DELETE', API + '/containers/' + cid + '?force=true', statuses=(204,), missing=True)
                        state = store.read(identifier)
                        if state is not None and state['phase'] != 'cleaned': host.cleanup(state)
            finally:
                unrelated = engine.call('GET', API + '/volumes/' + unrelated_name, missing=True)
                if unrelated is not None:
                    if unrelated.get('Labels') != unrelated_labels: raise ValueError('Unrelated fixture volume ownership changed')
                    engine.call('DELETE', API + '/volumes/' + unrelated_name, statuses=(204,))
            observations.extend(facade.observations)
            observations.append({'fixture': 'offline-cleanup-receipts-after-native-deletion', 'receipts': receipts_sink.receipts})
        finally: store.close()
        if any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest_ for name, digest_ in hashes.items()):
            raise ValueError('Source changed during qualification')
        if not all(check['passed'] for check in checks): raise ValueError('A native check failed')
        success = True
    finally:
        (out / 'native-observations.json').write_text(json.dumps(observations, indent=2) + '\n')
        (out / 'receipt.json').write_text(json.dumps({'recordedAt': datetime.now(timezone.utc).isoformat(),
            'passed': success, 'checks': checks, 'sourceHashes': hashes, 'qualificationImageId': core_image,
            'parserImageId': receipts[1]['imageId'], 'cloudOperations': False,
            'scope': 'Actual standalone Host/Store/Engine API, durable local state, installed transfer code, real Word/scanned-PDF parser, native volume cleanup and process-death recovery. Cleanup receipt transport is an offline sink that verifies actual native volumes are absent before acknowledgement. Root UID/state location, Batch UID/agent, registry identities, offline ARM/Blob/MI and daemon default-log observation are explicit fixtures. Root IMDS/Blob publisher and worker consumer have separate scripted wire tests. Qualification-only image includes synthetic fixtures; not a production artifact, actual Batch/pool/identity, security or whole-project qualification.'}, indent=2) + '\n')


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--crash-fixture':
        payload = json.load(sys.stdin)
        store = open_store(Path(sys.argv[2]))
        engine = Engine(sys.argv[3])
        Host(payload['config'], store, FixtureRegistryEngine(engine, payload['mapping'], crash=True), node_id=NODE_ID, receipts=ReceiptSink(engine), clock=lambda: 1000).prepare(payload['metadata'])
        raise SystemExit('Native crash fixture did not terminate')
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker-host', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--core-receipt', type=Path, required=True)
    parser.add_argument('--parser-receipt', type=Path, required=True)
    qualify(parser.parse_args())
