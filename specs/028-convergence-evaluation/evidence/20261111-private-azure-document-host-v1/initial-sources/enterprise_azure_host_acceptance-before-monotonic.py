"""Durable filesystem/process-death checks with explicit native Engine fixtures."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, unquote, urlsplit
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / 'tests/runtime')]
from enterprise_azure_jobs_acceptance import config
from enterprise_azure_jobs import cleanup_owner, fingerprint, transfer_metadata, task_spec
from enterprise_document_job import request
from enterprise_azure_host import Host, Store, API, digest, policy, owner, volumes, owned_file

IDENTIFIER = 'd' * 64


def value():
    return transfer_metadata(config(), request(b'private fixture', 'text/plain', IDENTIFIER), '"0x8DA123ABCDEF"')


class NativeEngine:
    """Only Docker metadata is persisted. There are no document bytes here."""
    def __init__(self, store, path=None, crash=False):
        self.store, self.path, self.crash = store, path, crash
        self.volumes, self.containers, self.calls = {}, {}, []
        self.failure, self.lost_create = None, False
        self.info = {'OSType': 'linux', 'LiveRestoreEnabled': False, 'LoggingDriver': 'none',
                     'SecurityOptions': ['name=seccomp,profile=builtin', 'name=cgroupns']}
        if path and path.exists():
            saved = json.loads(path.read_text()); self.volumes = saved['volumes']; self.containers = saved['containers']

    def persist(self):
        if self.path: self.path.write_text(json.dumps({'volumes': self.volumes, 'containers': self.containers}))

    def call(self, method, path, body=None, **options):
        self.calls.append((method, path, copy.deepcopy(body)))
        route = urlsplit(path); query = parse_qs(route.query); endpoint = unquote(route.path.removeprefix(API))
        if endpoint == '/info': return copy.deepcopy(self.info)
        if endpoint.startswith('/images/'):
            artifact = endpoint[len('/images/'):-len('/json')]
            return {'RepoDigests': [artifact], 'Os': 'linux', 'Architecture': 'amd64', 'Config': {'User': '10001:10001'}}
        if endpoint == '/volumes/create':
            state = self.store.read(IDENTIFIER)
            assert state and state['phase'] == 'preparing', 'Native mutation preceded durable intent'
            name = body['Name']
            self.volumes.setdefault(name, {**body, 'Options': None})
            self.persist()
            if self.crash: os._exit(87)
            return self.volumes[name]
        if endpoint.startswith('/volumes/'):
            name = endpoint.removeprefix('/volumes/')
            if method == 'GET': return copy.deepcopy(self.volumes.get(name))
            assert method == 'DELETE'
            self.volumes.pop(name, None); self.persist(); return {}
        if endpoint == '/containers/create':
            if self.failure == 'create': raise ValueError('fixture create failed')
            identifier = hashlib.sha256(query['name'][0].encode()).hexdigest()
            host = {**body['HostConfig'], 'IpcMode': 'private', 'PidMode': '', 'Devices': []}
            mounts = [{'Type': 'volume', 'Name': m['Source'], 'Destination': m['Target'], 'RW': not m['ReadOnly']} for m in host['Mounts']]
            self.containers[identifier] = {'Id': identifier, 'Config': {key: body[key] for key in ['Image', 'User', 'Cmd', 'Env', 'Labels']},
                'HostConfig': host, 'Mounts': mounts, 'State': {'Running': False, 'ExitCode': 0, 'OOMKilled': False}}
            self.persist()
            if self.lost_create: self.lost_create = False; raise ConnectionError('fixture lost native create acknowledgement')
            return {'Id': identifier}
        if endpoint == '/containers/json':
            name = json.loads(query['filters'][0])['volume'][0]
            return [{'Id': key} for key, item in self.containers.items() if any(m['Name'] == name for m in item['Mounts'])]
        if endpoint.startswith('/containers/'):
            parts = endpoint.split('/'); identifier = parts[2]
            if method == 'DELETE': self.containers.pop(identifier, None); self.persist(); return {}
            if parts[-1] == 'start':
                observed = self.containers[identifier]
                if self.failure == 'download' and observed['Config']['Labels']['atmem.document.stage'] == 'download': observed['State']['ExitCode'] = 2
                if self.failure == 'upload' and observed['Config']['Labels']['atmem.document.stage'] == 'upload': observed['State']['ExitCode'] = 2
                if self.failure == 'hang': observed['State']['Running'] = True
                self.persist(); return {}
            if parts[-1] == 'json': return copy.deepcopy(self.containers.get(identifier))
        raise AssertionError('Unhandled native fixture operation: ' + method + ' ' + endpoint)

    def parser(self, state, *, running=False):
        identifier = 'e' * 64
        task = task_spec(config(), state['requestId'])
        self.containers[identifier] = {'Id': identifier,
            'Config': {'Image': state['parserImage'], 'User': '42424:42424',
                'Labels': {'atmem.document.owner': state['owner'], 'atmem.document.request': state['requestId'],
                           'atmem.document.policy': state['policy'], 'atmem.document.stage': 'parser'}},
            'HostConfig': {'NetworkMode': 'none', 'ReadonlyRootfs': True, 'Privileged': False,
                'CapDrop': ['ALL'], 'CapAdd': [], 'PidMode': '', 'IpcMode': 'private', 'Devices': [],
                'LogConfig': {'Type': 'none'}, 'SecurityOpt': ['no-new-privileges:true']},
            'Mounts': [{'Name': name, 'Type': 'volume', 'Destination': '/' + side, 'RW': side == 'output'}
                       for side, name in zip(['input', 'output'], volumes(state['requestId']))],
            'State': {'Running': running, 'ExitCode': 0, 'OOMKilled': False}}
        self.persist()
        return identifier


class AzureHostContract(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name)
        self.directory = self.path / 'state'; self.directory.mkdir(mode=0o700)
        fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
        try: self.store = Store(fd, uid=os.geteuid())
        finally: os.close(fd)
        self.engine = NativeEngine(self.store)
        self.time = 1000
        self.host = Host(config(), self.store, self.engine, clock=lambda: self.time, sleep=lambda _: None)

    def tearDown(self):
        self.store.close(); self.temporary.cleanup()

    def test_standalone_policy_matches_native_request_binding(self):
        self.assertEqual(policy(config()), config())
        self.assertEqual(digest(config()), fingerprint(config()))
        self.assertEqual(owner(config()), cleanup_owner(config()))
        changed = {**config(), 'parserImage': 'ownedregistry.azurecr.io/parser@sha256:' + 'f' * 64}
        self.assertEqual(owner(config()), owner(changed))
        self.assertNotEqual(digest(config()), digest(changed))
        for args in [{'transferClientId': config()['workerClientId']}, {'poolId': 'foreign'}, {'parserImage': 'parser:latest'}]:
            with self.assertRaises(ValueError): policy({**config(), **args})

    def test_durable_intent_precedes_native_volumes_and_tombstone_prevents_replay(self):
        self.host.prepare(value())
        state = self.store.read(IDENTIFIER)
        self.assertEqual(state['phase'], 'ready')
        self.assertFalse(state['published'])
        self.assertEqual(len(self.engine.volumes), 2)
        self.assertEqual(self.engine.containers, {})
        self.host.release(value(), config()['transferImage'])
        self.assertEqual(self.engine.volumes, {})
        self.assertTrue(self.store.read(IDENTIFIER)['published'])
        self.assertEqual(self.store.read(IDENTIFIER)['phase'], 'cleaned')
        calls = len(self.engine.calls)
        self.host.release(value(), config()['transferImage'])
        self.assertEqual(len(self.engine.calls), calls)
        with self.assertRaises(ValueError): self.host.prepare(value())
        self.assertNotIn('private fixture', json.dumps(self.store.read(IDENTIFIER)))

    def test_staging_failure_cleans_owned_resources_and_never_publishes(self):
        self.engine.failure = 'download'
        with self.assertRaises(ValueError): self.host.prepare(value())
        self.assertEqual(self.engine.volumes, {})
        self.assertEqual(self.engine.containers, {})
        state = self.store.read(IDENTIFIER)
        self.assertEqual(state['phase'], 'cleaned')
        self.assertFalse(state['published'])
        with self.assertRaises(ValueError): self.host.release(value(), config()['transferImage'])

    def test_lost_container_create_response_is_found_by_owned_volume(self):
        self.engine.lost_create = True
        with self.assertRaises(ConnectionError): self.host.prepare(value())
        self.assertEqual(self.engine.volumes, {})
        self.assertEqual(self.engine.containers, {})
        self.assertEqual(self.store.read(IDENTIFIER)['phase'], 'cleaned')

    def test_transfer_deadline_cleans_the_still_running_owned_process(self):
        self.engine.failure = 'hang'
        def tick(_): self.time += 10
        host = Host(config(), self.store, self.engine, clock=lambda: self.time, sleep=tick)
        with self.assertRaisesRegex(ValueError, 'deadline'): host.prepare(value())
        self.assertEqual(self.engine.containers, {})
        self.assertEqual(self.engine.volumes, {})
        self.assertFalse(self.store.read(IDENTIFIER)['published'])

    def test_release_upload_failure_still_cleans_and_does_not_promote(self):
        self.host.prepare(value())
        self.engine.failure = 'upload'
        with self.assertRaises(ValueError): self.host.release(value(), config()['transferImage'])
        self.assertEqual(self.engine.volumes, {})
        self.assertFalse(self.store.read(IDENTIFIER)['published'])

    def test_release_must_not_publish_while_parser_is_running(self):
        self.host.prepare(value())
        self.engine.parser(self.store.read(IDENTIFIER), running=True)
        self.engine.calls.clear()
        with self.assertRaises(ValueError): self.host.release(value(), config()['transferImage'])
        self.assertFalse(any(body and body.get('Labels', {}).get('atmem.document.stage') == 'upload' for _, _, body in self.engine.calls))
        self.assertEqual(self.engine.containers, {})
        self.assertEqual(self.engine.volumes, {})

    def test_foreign_consumer_is_never_stopped_and_blocks_all_deletions(self):
        self.host.prepare(value())
        identifier = self.engine.parser(self.store.read(IDENTIFIER), running=True)
        self.engine.containers[identifier]['Config']['Labels']['atmem.document.owner'] = 'f' * 64
        self.engine.calls.clear(); self.time = 1601
        with self.assertRaises(ValueError): self.host.reap()
        self.assertTrue(self.engine.containers[identifier]['State']['Running'])
        self.assertFalse(any(method == 'DELETE' for method, _, _ in self.engine.calls))
        self.assertEqual(len(self.engine.volumes), 2)

    def test_foreign_volume_is_not_adopted_or_deleted(self):
        name = volumes(IDENTIFIER)[0]
        self.engine.volumes[name] = {'Name': name, 'Driver': 'local', 'Labels': {'foreign': 'true'}, 'Options': None}
        with self.assertRaises(ValueError): self.host.prepare(value())
        self.assertIn(name, self.engine.volumes)
        self.assertEqual(self.store.read(IDENTIFIER)['phase'], 'cleanup_failed')

    def test_expiry_reaps_owned_parser_but_not_an_active_job(self):
        self.host.prepare(value())
        identifier = self.engine.parser(self.store.read(IDENTIFIER), running=True)
        self.host.reap()
        self.assertIn(identifier, self.engine.containers)
        self.time = 1600
        self.host.reap()
        self.assertEqual(self.engine.volumes, {})
        self.assertEqual(self.engine.containers, {})
        self.assertFalse(self.store.read(IDENTIFIER)['published'])

    def test_cleanup_ownership_survives_artifact_revision_without_adopting_new_destination(self):
        self.host.prepare(value())
        self.engine.parser(self.store.read(IDENTIFIER), running=True)
        revised = {**config(), 'parserImage': 'ownedregistry.azurecr.io/parser@sha256:' + 'f' * 64,
                   'hostHelperSha256': 'a' * 64}
        host = Host(revised, self.store, self.engine, clock=lambda: 1601)
        host.reap()
        self.assertEqual(self.engine.volumes, {})
        state = self.store.read(IDENTIFIER)
        foreign = Host({**config(), 'container': 'foreign'}, self.store, self.engine, clock=lambda: 1601)
        with self.assertRaises(ValueError): foreign.check_state(state)

    def test_preflight_rejects_unsafe_engine_before_state_or_resource_creation(self):
        for field, value_ in [('LiveRestoreEnabled', True), ('LoggingDriver', 'json-file'), ('SecurityOptions', []), ('OSType', 'windows')]:
            self.engine.info[field] = value_
            with self.assertRaises(ValueError): self.host.prepare(value())
            self.assertIsNone(self.store.read(IDENTIFIER))
            self.assertEqual(self.engine.volumes, {})
            self.engine.info = NativeEngine(self.store).info

    def test_private_state_rejects_symlink_alias_and_duplicate_keys(self):
        path = self.directory / (IDENTIFIER + '.json')
        target = self.path / 'foreign'; target.write_text('{}')
        path.symlink_to(target)
        with self.assertRaises(OSError): self.store.read(IDENTIFIER)
        path.unlink(); path.write_text('{"format":"one","format":"two"}'); path.chmod(0o600)
        with self.assertRaises(ValueError): self.store.read(IDENTIFIER)
        path.unlink(); (self.directory / (IDENTIFIER + '.lock')).symlink_to(target)
        with self.assertRaises(OSError):
            with self.store.lock(IDENTIFIER): pass

    def test_unowned_release_request_does_not_delete_the_original_job(self):
        self.host.prepare(value())
        changed = copy.deepcopy(value()); changed['request']['sha256'] = 'f' * 64
        self.engine.calls.clear()
        with self.assertRaises(ValueError): self.host.release(changed, config()['transferImage'])
        self.assertEqual(self.engine.calls, [])
        self.assertEqual(len(self.engine.volumes), 2)

    def test_true_process_death_retains_intent_and_independent_reaper_cleans(self):
        fixture = self.path / 'engine.json'
        done = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--crash-fixture', str(self.directory), str(fixture)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(done.returncode, 87, done.stderr.decode())
        self.assertEqual(self.store.read(IDENTIFIER)['phase'], 'preparing')
        engine = NativeEngine(self.store, fixture)
        self.assertEqual(len(engine.volumes), 1)
        host = Host(config(), self.store, engine, clock=lambda: 1601)
        host.reap()
        self.assertEqual(engine.volumes, {})
        self.assertEqual(self.store.read(IDENTIFIER)['phase'], 'cleaned')
        self.assertFalse(self.store.read(IDENTIFIER)['published'])

    def test_parser_labels_and_mounts_are_independently_checked(self):
        self.host.prepare(value())
        state = self.store.read(IDENTIFIER)
        identifier = self.engine.parser(state)
        self.assertIsNotNone(self.host.container(state, identifier))
        for change in ['uid', 'network', 'mount', 'policy']:
            self.engine.parser(state)
            item = self.engine.containers[identifier]
            if change == 'uid': item['Config']['User'] = '0:0'
            if change == 'network': item['HostConfig']['NetworkMode'] = 'host'
            if change == 'mount': item['Mounts'][0]['RW'] = True
            if change == 'policy': item['Config']['Labels']['atmem.document.policy'] = 'f' * 64
            with self.assertRaises(ValueError): self.host.container(state, identifier)


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--crash-fixture':
        fd = os.open(sys.argv[2], os.O_RDONLY | os.O_DIRECTORY)
        store = Store(fd, uid=os.geteuid()); os.close(fd)
        engine = NativeEngine(store, Path(sys.argv[3]), crash=True)
        Host(config(), store, engine, clock=lambda: 1000).prepare(value())
        raise SystemExit('Crash fixture failed to terminate')
    unittest.main()
