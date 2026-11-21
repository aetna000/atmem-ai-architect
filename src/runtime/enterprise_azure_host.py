"""Root-owned Batch prepare/release/reaper; fixed local Docker Engine only.

Standalone standard-library helper. No document bytes pass through this process.
The trusted transfer artifact alone reads Blob/input/result bytes. This helper is
not a cloud provisioning contract or evidence that a Batch node is configured.
"""
from contextlib import contextmanager
import base64
from datetime import datetime, timezone
from email.utils import format_datetime
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import socket
import stat
import sys
import time
from urllib.parse import quote, urlencode
import uuid

API = '/v1.43'
MAX_JSON = 1048576
HASH = r'[0-9a-f]{64}'
UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
STATE_FIELDS = {'format', 'requestId', 'nonce', 'owner', 'policy', 'helperSha256',
                'parserImage', 'transferImage', 'transfer', 'createdAt', 'expiresAt', 'phase', 'published', 'receiptPublished', 'nodeId'}


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value: raise ValueError('Ambiguous owned metadata')
        value[key] = item
    return value


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def match(value, pattern):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def node_identity(value):
    if not match(value, r'[A-Za-z0-9_-]{1,128}'): raise ValueError('Use the exact native node identity')
    return value


def image(value):
    if not match(value, r'[a-z0-9]{5,50}\.azurecr\.io/[a-z0-9]+(?:[._/-][a-z0-9]+)*@sha256:' + HASH):
        raise ValueError('Use an immutable owned ACR artifact')
    return value


def policy(value):
    fields = {'format', 'subscriptionId', 'region', 'resourceGroup', 'batchAccount', 'poolId',
              'storageAccount', 'container', 'workerClientId', 'transferClientId',
              'parserImage', 'transferImage', 'hostHelperSha256'}
    if not isinstance(value, dict) or set(value) != fields or value['format'] != 'enterprise-azure-document-job-v1':
        raise ValueError('Use the exact root-owned host policy')
    patterns = {'subscriptionId': UUID, 'region': r'[a-z][a-z0-9]{1,30}',
                'resourceGroup': r'[A-Za-z0-9_()-](?:[A-Za-z0-9_().-]{0,88}[A-Za-z0-9_()-])?',
                'batchAccount': r'[a-z0-9]{3,24}', 'poolId': r'document-[a-z0-9-]{1,54}',
                'storageAccount': r'[a-z0-9]{3,24}', 'container': r'[a-z0-9]+(?:-[a-z0-9]+)*',
                'workerClientId': UUID, 'transferClientId': UUID, 'hostHelperSha256': HASH}
    if any(not match(value[key], pattern) for key, pattern in patterns.items()) or not 3 <= len(value['container']) <= 63:
        raise ValueError('Invalid owned host destination')
    if value['workerClientId'] == value['transferClientId']:
        raise ValueError('Worker identity must not be on the transfer node')
    for key in ['parserImage', 'transferImage']: image(value[key])
    if (value['parserImage'] == value['transferImage'] or
            value['parserImage'].split('/')[0] != value['transferImage'].split('/')[0]):
        raise ValueError('Use distinct artifacts from the same owned registry')
    return dict(value)


def owner(value):
    checked = policy(value)
    keys = ['subscriptionId', 'region', 'resourceGroup', 'batchAccount', 'poolId',
            'storageAccount', 'container', 'transferClientId']
    return digest({**{key: checked[key] for key in keys}, 'registry': checked['parserImage'].split('/')[0]})


def volumes(identifier):
    if not match(identifier, HASH): raise ValueError('Invalid owned job identity')
    return ['atmem-document-' + identifier + '-' + side for side in ['input', 'output']]


def transfer(value, config):
    keys = {'format', 'subscriptionId', 'region', 'resourceGroup', 'storageAccount',
            'container', 'transferClientId', 'request', 'inputETag'}
    if not isinstance(value, dict) or set(value) != keys or value['format'] != 'enterprise-azure-document-transfer-v1':
        raise ValueError('Use exact transfer metadata')
    for key in ['subscriptionId', 'region', 'resourceGroup', 'storageAccount', 'container', 'transferClientId']:
        if value[key] != config[key]: raise ValueError('Transfer destination changed')
    request = value['request']
    if (not isinstance(request, dict) or set(request) != {'format', 'requestId', 'sha256', 'mediaType'} or
            request['format'] != 'enterprise-document-job-v1' or not match(request['requestId'], HASH) or
            not match(request['sha256'], HASH) or not match(request['mediaType'], r'[a-z0-9.+-]+/[a-z0-9.+-]+') or
            len(request['mediaType']) > 200 or not match(value['inputETag'], r'"0x[0-9A-Fa-f]{1,32}"')):
        raise ValueError('Invalid byte-bound transfer metadata')
    # Full supported-MIME validation remains in the independently versioned
    # transfer artifact; this host never opens or parses the file.
    if len(encoded(value)) > 4096: raise ValueError('Transfer metadata exceeds host limit')
    return json.loads(encoded(value), object_pairs_hook=unique)


def protected_directory(path, *, uid=0):
    """Walk every absolute ancestor without following symlinks, including /var."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts: raise ValueError('Use an absolute protected directory')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
            info = os.fstat(fd)
            if info.st_uid != uid or stat.S_IMODE(info.st_mode) & 0o022:
                raise ValueError('Host directory is not protected by its owner')
        return fd
    except BaseException:
        os.close(fd)
        raise


def owned_file(directory, name, *, uid=0, limit=16384):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_nlink != 1 or
                stat.S_IMODE(info.st_mode) & 0o022 or not 0 < info.st_size <= limit):
            raise ValueError('Invalid protected host metadata file')
        raw = stream.read(limit + 1)
        if len(raw) != info.st_size: raise ValueError('Host metadata changed')
        return raw


class Store:
    def __init__(self, directory, *, uid=0):
        info = os.fstat(directory)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError('Use the private root-owned state directory')
        self.fd, self.uid = os.dup(directory), uid

    def close(self): os.close(self.fd)

    @contextmanager
    def lock(self, identifier):
        volumes(identifier)
        fd = os.open(identifier + '.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=self.fd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != self.uid or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
                raise ValueError('Invalid owned state lock')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally: os.close(fd)

    def read(self, identifier):
        volumes(identifier)
        try: raw = owned_file(self.fd, identifier + '.json', uid=self.uid)
        except FileNotFoundError: return None
        value = json.loads(raw, object_pairs_hook=unique)
        if not isinstance(value, dict): raise ValueError('Invalid owned state')
        return value

    def write(self, state, *, create=False):
        name = volumes(state['requestId']) and state['requestId'] + '.json'
        raw = encoded(state)
        if len(raw) > 16384: raise ValueError('State exceeds owned bound')
        temporary = name if create else '.write-' + uuid.uuid4().hex
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            if not create: os.replace(temporary, name, src_dir_fd=self.fd, dst_dir_fd=self.fd)
            os.fsync(self.fd)
        finally:
            if not create:
                try: os.unlink(temporary, dir_fd=self.fd)
                except FileNotFoundError: pass

    def identifiers(self):
        # State contains metadata only. Tombstones deliberately prevent adoption
        # of a retried/replayed Batch job ID; no age-based source erasure claim.
        return sorted(name[:-5] for name in os.listdir(self.fd) if re.fullmatch(HASH + r'\.json', name))


class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__('localhost', timeout=3)
        self.path = path
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


class Engine:
    def __init__(self, path='/var/run/docker.sock'):
        if not isinstance(path, str) or not path.startswith('/') or not stat.S_ISSOCK(os.stat(path).st_mode):
            raise ValueError('Use the fixed local Docker Engine socket')
        self.path = path

    def call(self, method, path, body=None, *, statuses=(200,), missing=False, timeout=10):
        if method not in {'GET', 'POST', 'DELETE'} or not path.startswith(API + '/'):
            raise ValueError('Use only the owned native Engine API')
        connection = UnixConnection(self.path)
        started = time.monotonic()
        try:
            raw = None if body is None else encoded(body)
            connection.request(method, path, body=raw, headers={} if raw is None else {'Content-Type': 'application/json'})
            response = connection.getresponse()
            if missing and response.status == 404: return None
            if response.status not in statuses: raise ValueError('Owned Engine operation failed')
            chunks = bytearray()
            while True:
                piece = response.read(16384)
                if not piece: break
                chunks.extend(piece)
                if len(chunks) > MAX_JSON or time.monotonic() - started > timeout:
                    raise ValueError('Owned Engine response exceeded bounds')
            if not chunks: return {}
            return json.loads(chunks, object_pairs_hook=unique)
        finally: connection.close()


def cleanup_receipt(state):
    if state.get('phase') != 'cleaned' or not match(state.get('requestId'), HASH) or not match(state.get('owner'), HASH):
        raise ValueError('Only a completed owned cleanup can be acknowledged')
    return {'format': 'enterprise-azure-document-cleanup-v2', 'requestId': state['requestId'],
            'owner': state['owner'], 'nodeId': node_identity(state.get('nodeId')), 'cleaned': True}


class RootReceipts:
    """Only metadata leaves this root process; no document or result reader.

    A create-only receipt remains until the generated store's metadata lifecycle
    expires it. This makes a lost acknowledgement repeatable without recreating
    document bytes. VM MI is a node boundary, not a per-process security boundary.
    """
    def __init__(self, config, node_id, *, connection=None):
        self.config = policy(config)
        self.node_id = node_identity(node_id)
        self.connection = connection

    def send(self, method, host, path, *, headers=None, data=None):
        connection = (self.connection(method, host, path) if self.connection is not None else
                      (http.client.HTTPConnection(host, timeout=3) if host == '169.254.169.254' else
                       http.client.HTTPSConnection(host, timeout=3)))
        try:
            connection.request(method, path, body=data, headers={'Accept-Encoding': 'identity', **(headers or {})})
            response = connection.getresponse()
            observed = {}
            for key, value in response.getheaders():
                if key.lower() in observed: raise ValueError()
                observed[key.lower()] = value
            if observed.get('content-encoding') not in {None, 'identity'}: raise ValueError()
            started = time.monotonic(); raw = bytearray()
            while True:
                chunk = response.read(4096)
                if not chunk: break
                raw.extend(chunk)
                if len(raw) > 32768 or time.monotonic() - started > 8: raise ValueError()
            return response.status, observed, bytes(raw)
        finally: connection.close()

    def publish(self, receipt):
        if not isinstance(receipt, dict) or receipt.get('cleaned') is not True:
            raise ValueError('Use the exact metadata-only owned cleanup receipt')
        expected = {'format': 'enterprise-azure-document-cleanup-v2', 'requestId': receipt.get('requestId'),
                    'owner': owner(self.config), 'nodeId': self.node_id, 'cleaned': True}
        if receipt != expected or not match(receipt.get('requestId'), HASH):
            raise ValueError('Use the exact metadata-only owned cleanup receipt')
        try:
            path = '/metadata/identity/oauth2/token?' + urlencode({'api-version': '2018-02-01',
                'resource': 'https://storage.azure.com/', 'client_id': self.config['transferClientId']})
            status, _, raw = self.send('GET', '169.254.169.254', path, headers={'Metadata': 'true'})
            if status != 200: raise ValueError()
            access = json.loads(raw, object_pairs_hook=unique)
            token = access.get('access_token')
            if (access.get('token_type') != 'Bearer' or access.get('resource') != 'https://storage.azure.com/' or
                    not match(access.get('expires_on'), '[1-9][0-9]{0,11}') or int(access['expires_on']) < time.time() + 30 or
                    not isinstance(token, str) or not 8 <= len(token) <= 20000 or any(ord(c) < 33 or ord(c) > 126 for c in token)):
                raise ValueError()
            host = self.config['storageAccount'] + '.blob.core.windows.net'
            path = '/' + self.config['container'] + '/document-jobs/' + receipt['requestId'] + '/cleanup/' + self.node_id
            raw = encoded(receipt)
            common = {'Authorization': 'Bearer ' + token, 'x-ms-version': '2025-05-05',
                      'x-ms-date': format_datetime(datetime.now(timezone.utc), usegmt=True)}
            status, headers, _ = self.send('PUT', host, path, data=raw, headers={**common,
                'If-None-Match': '*', 'x-ms-blob-type': 'BlockBlob', 'Content-Type': 'application/json',
                'Content-Length': str(len(raw)),
                'Content-MD5': base64.b64encode(hashlib.md5(raw, usedforsecurity=False).digest()).decode()})
            if status == 201:
                if (headers.get('x-ms-request-server-encrypted') != 'true' or headers.get('x-ms-version-id') is not None or
                        not match(headers.get('etag'), r'"0x[0-9A-Fa-f]{1,32}"')):
                    raise ValueError()
                return
            if status != 412: raise ValueError()
            # A lost PUT response may have committed the exact acknowledgement.
            # Never overwrite or adopt a different owner's receipt.
            status, headers, observed = self.send('GET', host, path, headers=common)
            if (status != 200 or headers.get('x-ms-server-encrypted') != 'true' or
                    headers.get('x-ms-blob-type') != 'BlockBlob' or headers.get('x-ms-version-id') is not None or
                    headers.get('content-length') != str(len(observed)) or observed != raw):
                raise ValueError()
        except Exception:
            raise ValueError('Owned cleanup acknowledgement remains pending') from None


class Host:
    def __init__(self, config, store, engine, *, node_id, receipts, clock=time.time, monotonic=time.monotonic, sleep=time.sleep):
        self.config, self.store, self.engine = policy(config), store, engine
        self.node_id = node_identity(node_id)
        self.clock, self.monotonic, self.sleep = clock, monotonic, sleep
        if not callable(getattr(receipts, 'publish', None)): raise ValueError('Use an owned cleanup receipt publisher')
        self.receipts = receipts
        self.owner = owner(self.config)

    def check_state(self, state):
        if isinstance(state, dict) and state.get('format') == 'enterprise-azure-document-host-v1' and set(state) == STATE_FIELDS - {'receiptPublished', 'nodeId'}:
            state.update(format='enterprise-azure-document-host-v2', receiptPublished=False)
        if isinstance(state, dict) and state.get('format') == 'enterprise-azure-document-host-v2' and set(state) == STATE_FIELDS - {'nodeId'}:
            # A legacy global receipt did not settle every possible retry node.
            # Reinspect this local node and publish its own scoped receipt.
            state.update(format='enterprise-azure-document-host-v3', nodeId=self.node_id, receiptPublished=False)
        if (not isinstance(state, dict) or set(state) != STATE_FIELDS or state['format'] != 'enterprise-azure-document-host-v3' or
                state['nodeId'] != self.node_id or
                not match(state['requestId'], HASH) or not match(state['nonce'], '[0-9a-f]{32}') or
                state['owner'] != self.owner or not match(state['policy'], HASH) or not match(state['helperSha256'], HASH) or
                type(state['createdAt']) is not int or type(state['expiresAt']) is not int or
                state['expiresAt'] - state['createdAt'] != 600 or type(state['published']) is not bool or type(state['receiptPublished']) is not bool or
                (state['receiptPublished'] and state['phase'] != 'cleaned') or
                state['phase'] not in {'preparing', 'ready', 'releasing', 'cleanup_failed', 'cleaned'}):
            raise ValueError('Unowned or invalid recovery state')
        for key in ['parserImage', 'transferImage']:
            if image(state[key]).split('/')[0] != self.config['parserImage'].split('/')[0]:
                raise ValueError('Recovery artifact registry changed')
        transfer(state['transfer'], self.config)
        if state['transfer']['request']['requestId'] != state['requestId']:
            raise ValueError('Recovery request identity changed')
        return state

    def labels(self, state):
        return {'atmem.document.owner': state['owner'], 'atmem.document.request': state['requestId'],
                'atmem.document.policy': state['policy']}

    def volume_labels(self, state, side):
        return {**self.labels(state), 'atmem.document.nonce': state['nonce'], 'atmem.document.side': side}

    def volume(self, state, side, *, missing=False):
        name = volumes(state['requestId'])[0 if side == 'input' else 1]
        info = self.engine.call('GET', API + '/volumes/' + quote(name, safe=''), missing=missing)
        if info is None: return None
        if (info.get('Name') != name or info.get('Driver') != 'local' or (info.get('Options') is not None and info.get('Options') != {}) or
                info.get('Labels') != self.volume_labels(state, side)):
            raise ValueError('Do not adopt or delete an unowned volume')
        return info

    def preflight(self):
        info = self.engine.call('GET', API + '/info')
        if (info.get('OSType') != 'linux' or info.get('LiveRestoreEnabled') is not False or
                info.get('LoggingDriver') != 'none' or
                not any(item.startswith('name=seccomp,profile=builtin') for item in info.get('SecurityOptions', []))):
            raise ValueError('Use the reviewed dedicated no-log/non-live-restore Engine')
        for key in ['parserImage', 'transferImage']:
            info = self.engine.call('GET', API + '/images/' + quote(self.config[key], safe='') + '/json')
            if (self.config[key] not in info.get('RepoDigests', []) or info.get('Os') != 'linux' or
                    info.get('Architecture') != 'amd64' or info.get('Config', {}).get('User') != '10001:10001'):
                raise ValueError('Owned immutable artifact is not prefetched')

    def container(self, state, identifier):
        if not match(identifier, HASH): raise ValueError('Invalid native container ID')
        info = self.engine.call('GET', API + '/containers/' + identifier + '/json', missing=True)
        if info is None: return None
        config, host = info['Config'], info['HostConfig']
        labels = config.get('Labels') or {}
        stage = labels.get('atmem.document.stage')
        if stage not in {'parser', 'download', 'upload'} or any(labels.get(k) != v for k, v in self.labels(state).items()):
            raise ValueError('Foreign container uses an owned volume')
        expected_image = state['parserImage'] if stage == 'parser' else state['transferImage']
        if config.get('Image') != expected_image:
            raise ValueError('Container artifact ownership changed')
        if ((stage == 'parser' and not match(config.get('User'), r'[1-9][0-9]{0,9}(?::[0-9]{1,10})?')) or
                (stage != 'parser' and config.get('User') != '0:0')):
            raise ValueError('Container execution user changed')
        if stage != 'parser' and labels.get('atmem.document.nonce') != state['nonce']:
            raise ValueError('Transfer container ownership changed')
        mounts = info.get('Mounts', [])
        if len(mounts) != 2: raise ValueError('Unexpected host or data mount')
        for side, name in zip(['input', 'output'], volumes(state['requestId'])):
            entries = [m for m in mounts if m.get('Destination') == '/' + side]
            writable = stage == 'download' or stage == 'parser' and side == 'output'
            if len(entries) != 1 or entries[0].get('Type') != 'volume' or entries[0].get('Name') != name or entries[0].get('RW') is not writable:
                raise ValueError('Per-file mount ownership changed')
        if (host.get('NetworkMode') != ('none' if stage == 'parser' else 'host') or
                host.get('ReadonlyRootfs') is not True or host.get('Privileged') is not False or
                host.get('CapDrop') != ['ALL'] or
                (host.get('CapAdd') or []) != (['DAC_READ_SEARCH'] if stage == 'upload' else []) or
                host.get('PidMode') not in {'', None} or host.get('IpcMode') not in {'private', ''} or
                host.get('Devices') or host.get('LogConfig', {}).get('Type') != 'none' or
                'no-new-privileges:true' not in (host.get('SecurityOpt') or [])):
            raise ValueError('Container isolation changed; refuse unowned cleanup')
        return info

    def containers(self, state):
        identifiers = set()
        for name in volumes(state['requestId']):
            filters = json.dumps({'volume': [name]}, separators=(',', ':'))
            result = self.engine.call('GET', API + '/containers/json?' + urlencode({'all': '1', 'filters': filters}))
            if not isinstance(result, list) or len(result) > 32: raise ValueError('Unexpected owned volume consumers')
            for item in result:
                if not match(item.get('Id'), HASH): raise ValueError('Invalid native consumer identity')
                identifiers.add(item['Id'])
        # Validate every consumer before deleting any container or volume.
        return [info for identifier in sorted(identifiers) if (info := self.container(state, identifier)) is not None]

    def cleanup(self, state):
        self.check_state(state)
        for side in ['input', 'output']: self.volume(state, side, missing=True)
        for info in self.containers(state):
            self.engine.call('DELETE', API + '/containers/' + info['Id'] + '?force=true', statuses=(204,), missing=True)
        for side in ['output', 'input']:
            found = self.volume(state, side, missing=True)
            if found is not None:
                self.engine.call('DELETE', API + '/volumes/' + quote(found['Name'], safe=''), statuses=(204,), missing=True)
        state['phase'] = 'cleaned'
        self.store.write(state)
        if not state['receiptPublished']:
            self.receipts.publish(cleanup_receipt(state))
            state['receiptPublished'] = True
            self.store.write(state)

    def run_transfer(self, state, stage):
        if stage not in {'download', 'upload'}: raise ValueError('Use a trusted transfer stage')
        labels = {**self.labels(state), 'atmem.document.nonce': state['nonce'], 'atmem.document.stage': stage}
        mounts = [{'Type': 'volume', 'Source': name, 'Target': '/' + side, 'ReadOnly': stage == 'upload'}
                  for side, name in zip(['input', 'output'], volumes(state['requestId']))]
        body = {'Image': state['transferImage'], 'User': '0:0',
            'Cmd': ['python', '-I', '/app/enterprise_azure_transfer.py', stage],
            'Env': ['DOCUMENT_JOB=' + encoded(state['transfer']).decode()], 'Labels': labels,
            'HostConfig': {'NetworkMode': 'host', 'ReadonlyRootfs': True, 'Privileged': False,
                'CapDrop': ['ALL'], 'CapAdd': ['DAC_READ_SEARCH'] if stage == 'upload' else [],
                'SecurityOpt': ['no-new-privileges:true'], 'LogConfig': {'Type': 'none', 'Config': {}},
                'PidsLimit': 64, 'Memory': 268435456, 'MemorySwap': 268435456, 'NanoCpus': 1000000000,
                'Mounts': mounts, 'Tmpfs': {'/tmp': 'rw,noexec,nosuid,nodev,size=32m'}, 'RestartPolicy': {'Name': 'no'}}}
        name = 'atmem-document-' + state['requestId'] + '-' + stage
        reply = self.engine.call('POST', API + '/containers/create?' + urlencode({'name': name, 'platform': 'linux/amd64'}), body, statuses=(201,))
        identifier = reply.get('Id')
        if not match(identifier, HASH): raise ValueError('Invalid native transfer acknowledgement')
        self.container(state, identifier)
        self.engine.call('POST', API + '/containers/' + identifier + '/start', statuses=(204,))
        deadline = self.monotonic() + 35
        while True:
            observed = self.container(state, identifier)
            if observed is None: raise ValueError('Transfer process disappeared')
            if not observed['State']['Running']:
                if observed['State'].get('ExitCode') != 0 or observed['State'].get('OOMKilled'):
                    raise ValueError('Trusted transfer failed')
                self.engine.call('DELETE', API + '/containers/' + identifier, statuses=(204,))
                return
            if self.monotonic() >= deadline: raise ValueError('Trusted transfer exceeded deadline')
            self.sleep(.1)

    def prepare(self, value):
        value = transfer(value, self.config)
        identifier = value['request']['requestId']
        with self.store.lock(identifier):
            if self.store.read(identifier) is not None: raise ValueError('Do not replay an existing per-file job')
            self.preflight()
            now = int(self.clock())
            state = {'format': 'enterprise-azure-document-host-v3', 'requestId': identifier, 'nodeId': self.node_id, 'nonce': uuid.uuid4().hex,
                'owner': self.owner, 'policy': digest(self.config), 'helperSha256': self.config['hostHelperSha256'],
                'parserImage': self.config['parserImage'], 'transferImage': self.config['transferImage'], 'transfer': value,
                'createdAt': now, 'expiresAt': now + 600, 'phase': 'preparing', 'published': False, 'receiptPublished': False}
            # Durable intent exists before the first volume/container creation.
            self.store.write(state, create=True)
            try:
                for side, name in zip(['input', 'output'], volumes(identifier)):
                    if self.engine.call('GET', API + '/volumes/' + quote(name, safe=''), missing=True) is not None:
                        raise ValueError('Do not adopt an existing volume')
                    self.engine.call('POST', API + '/volumes/create', {'Name': name, 'Driver': 'local',
                        'Labels': self.volume_labels(state, side)}, statuses=(201,))
                    self.volume(state, side)
                self.run_transfer(state, 'download')
                state['phase'] = 'ready'
                self.store.write(state)
            except BaseException:
                try: self.cleanup(state)
                except Exception:
                    if state['phase'] != 'cleaned': state['phase'] = 'cleanup_failed'
                    self.store.write(state)
                raise

    def release(self, value, transfer_image):
        value = transfer(value, self.config)
        identifier = value['request']['requestId']
        with self.store.lock(identifier):
            state = self.store.read(identifier)
            if state is None: raise ValueError('No owned per-file preparation')
            self.check_state(state)
            if state['transfer'] != value or state['transferImage'] != transfer_image:
                raise ValueError('Release must match the original per-file owner')
            if state['phase'] == 'cleaned':
                if not state['receiptPublished']: self.cleanup(state)
                if not state['published']: raise ValueError('Failed job was cleaned without publication')
                return
            succeeded = False
            try:
                if state['phase'] != 'ready': raise ValueError('Preparation never completed')
                if any(info['State']['Running'] for info in self.containers(state)):
                    raise ValueError('A parser or transfer still owns the file')
                state['phase'] = 'releasing'; self.store.write(state)
                self.run_transfer(state, 'upload')
                state['published'] = True; self.store.write(state)
                succeeded = True
            finally:
                try: self.cleanup(state)
                except Exception:
                    if state['phase'] != 'cleaned': state['phase'] = 'cleanup_failed'
                    self.store.write(state)
                    raise
            if not succeeded: raise ValueError('Document publication did not complete')

    def reap(self):
        failures = []
        for identifier in self.store.identifiers():
            try:
                with self.store.lock(identifier):
                    state = self.check_state(self.store.read(identifier))
                    if ((state['phase'] == 'cleaned' and not state['receiptPublished']) or
                            state['phase'] != 'cleaned' and state['expiresAt'] <= int(self.clock())):
                        self.cleanup(state)
            except BlockingIOError:
                continue  # An active trusted prepare/release holds this lock.
            except Exception:
                failures.append(identifier)
        if failures: raise ValueError('Owned document cleanup remains pending')


def main():
    store = None
    try:
        if os.geteuid() != 0 or len(sys.argv) != 2 or sys.argv[1] not in {'prepare', 'release', 'reap'}:
            raise ValueError('Use the fixed root-owned host command')
        directory = protected_directory('/etc/atmem')
        try:
            config = policy(json.loads(owned_file(directory, 'document-host.json'), object_pairs_hook=unique))
            node = json.loads(owned_file(directory, 'document-host-node.json'), object_pairs_hook=unique)
            if not isinstance(node, dict) or set(node) != {'format', 'nodeId'} or node['format'] != 'enterprise-azure-document-node-v1':
                raise ValueError('Use the protected instance-specific native node identity')
            node_id = node_identity(node['nodeId'])
        finally: os.close(directory)
        directory = protected_directory('/var/lib/atmem/document-jobs')
        try: store = Store(directory)
        finally: os.close(directory)
        host = Host(config, store, Engine(), node_id=node_id, receipts=RootReceipts(config, node_id))
        mode = sys.argv[1]
        # The root service may invoke reap directly, without the inline Batch
        # bootstrap. Verify this installed standalone helper in both paths.
        helper_dir = protected_directory(str(Path(__file__).parent))
        try: helper_sha = hashlib.sha256(owned_file(helper_dir, Path(__file__).name, limit=262144)).hexdigest()
        finally: os.close(helper_dir)
        if mode in {'prepare', 'reap'} and helper_sha != config['hostHelperSha256']:
            raise ValueError('Installed helper differs from the protected pool policy')
        if mode == 'reap': host.reap(); return
        value = os.environ.get('DOCUMENT_JOB', '')
        if not 0 < len(value.encode()) <= 4096: raise ValueError('Use the owned per-file metadata')
        value = transfer(json.loads(value, object_pairs_hook=unique), config)
        if (os.environ.get('AZ_BATCH_JOB_ID') != value['request']['requestId'] or
                os.environ.get('AZ_BATCH_POOL_ID') != config['poolId'] or
                os.environ.get('AZ_BATCH_ACCOUNT_NAME') != config['batchAccount'] or os.environ.get('AZ_BATCH_NODE_ID') != node_id):
            raise ValueError('Native Batch owner changed')
        if mode == 'prepare':
            if os.environ.get('DOCUMENT_TRANSFER_IMAGE') != config['transferImage']:
                raise ValueError('Transfer artifact differs from the protected pool policy')
            host.prepare(value)
        else:
            existing = store.read(value['request']['requestId'])
            if existing is None or existing.get('helperSha256') != helper_sha:
                raise ValueError('Release helper differs from the original per-file owner')
            host.release(value, os.environ.get('DOCUMENT_TRANSFER_IMAGE'))
    except Exception:
        raise SystemExit('Owned Azure document host operation could not complete; recovery remains pending.') from None
    finally:
        if store is not None: store.close()


if __name__ == '__main__': main()
