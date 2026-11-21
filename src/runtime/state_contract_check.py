"""Local synthetic HTTP-state protocol check; never opens a project backend.

This fixture is not a production state service. All state, credentials, databases
and native workspaces are created in one fresh directory. No apply, migration,
provider, cloud credential or caller-supplied endpoint is used.
"""
import argparse
import base64
import contextlib
import hashlib
import http.server
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


class FixtureStore:
    def __init__(self, path, initial):
        self.path = path
        with self.connection() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS versions(
                id INTEGER PRIMARY KEY, payload BLOB NOT NULL, sha TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS head(id INTEGER PRIMARY KEY CHECK(id=1),version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS lease(id INTEGER PRIMARY KEY CHECK(id=1),actor TEXT,info TEXT);''')
            if not db.execute('SELECT 1 FROM head').fetchone():
                db.execute('INSERT INTO versions VALUES(1,?,?)', (initial, digest(initial)))
                db.execute('INSERT INTO head VALUES(1,1)')

    @contextlib.contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def read(self):
        with self.connection() as db:
            row = db.execute('SELECT payload,sha FROM versions JOIN head ON versions.id=head.version').fetchone()
            if digest(row[0]) != row[1]:
                raise ValueError('Fixture state digest mismatch')
            return row[0]

    def lock(self):
        with self.connection() as db:
            row = db.execute('SELECT actor,info FROM lease').fetchone()
            return (row[0], json.loads(row[1])) if row else None

    def acquire(self, actor, info):
        if not isinstance(info.get('ID'), str) or not info['ID'] or len(info['ID']) > 100:
            return 400, {}
        with self.connection() as db:
            row = db.execute('SELECT actor,info FROM lease').fetchone()
            if row:
                return 409, json.loads(row[1])
            db.execute('INSERT INTO lease VALUES(1,?,?)', (actor, json.dumps(info)))
            return 200, {}

    def unlock(self, actor, info):
        with self.connection() as db:
            row = db.execute('SELECT actor,info FROM lease').fetchone()
            if not row:
                return 409, {}
            current = json.loads(row[1])
            if actor != row[0] or info.get('ID') != current['ID']:
                return 409, current
            db.execute('DELETE FROM lease')
            return 200, {}

    def denied_write(self, actor, lock_id):
        with self.connection() as db:
            row = db.execute('SELECT actor,info FROM lease').fetchone()
            # Fixture intentionally has no HTTP write implementation. Plans and
            # state pull must not write; only the test controller adds versions.
            if not row or row[0] != actor or json.loads(row[1])['ID'] != lock_id:
                return 409
            return 405

    def add_fixture_version(self, payload):
        with self.connection() as db:
            if db.execute('SELECT 1 FROM lease').fetchone():
                raise ValueError('An active writer forbids fixture version changes')
            cursor = db.execute('INSERT INTO versions(payload,sha) VALUES(?,?)', (payload, digest(payload)))
            db.execute('UPDATE head SET version=?', (cursor.lastrowid,))
            return cursor.lastrowid

    def restore_fixture_version(self, version):
        with self.connection() as db:
            if db.execute('SELECT 1 FROM lease').fetchone():
                raise ValueError('An active writer forbids fixture recovery')
            row = db.execute('SELECT payload,sha FROM versions WHERE id=?', (version,)).fetchone()
            if not row or digest(row[0]) != row[1]:
                raise ValueError('Unverified fixture backup')
            json.loads(row[0])
            db.execute('UPDATE head SET version=?', (version,))


class Control:
    def __init__(self):
        self.pause = False
        self.read_held = threading.Event()
        self.release = threading.Event()
        self.events = []


def fixture_server(store, credentials, control):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, status, value=None):
            body = value if isinstance(value, bytes) else encoded(value or {})
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def actor(self):
            header = self.headers.get('Authorization', '')
            for actor, password in credentials.items():
                expected = 'Basic ' + base64.b64encode((actor + ':' + password).encode()).decode()
                if secrets.compare_digest(header, expected):
                    return actor
            return None

        def dispatch(self):
            actor = self.actor()
            route = urllib.parse.urlsplit(self.path)
            if not actor:
                self.respond(401)
                return
            control.events.append({'method': self.command, 'path': route.path, 'actor': actor})
            if self.command == 'GET' and route.path == '/state':
                lease = store.lock()
                if control.pause and lease and lease[0] == actor:
                    control.read_held.set()
                    if not control.release.wait(25):
                        self.respond(503)
                        return
                self.respond(200, store.read())
                return
            length = int(self.headers.get('Content-Length', '0'))
            if length < 0 or length > 65536:
                self.respond(413)
                return
            try:
                value = json.loads(self.rfile.read(length)) if length else {}
            except ValueError:
                self.respond(400)
                return
            if not isinstance(value, dict):
                self.respond(400)
                return
            if route.path == '/lock' and self.command in {'POST', 'DELETE'}:
                status, response = (store.acquire if self.command == 'POST' else store.unlock)(actor, value)
                self.respond(status, response)
            elif route.path == '/state' and self.command == 'POST':
                lock_id = urllib.parse.parse_qs(route.query).get('ID', [None])[0]
                self.respond(store.denied_write(actor, lock_id))
            else:
                self.respond(405)

        do_GET = dispatch
        do_POST = dispatch
        do_DELETE = dispatch

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    return server


def run_probe(terraform, folder):
    folder.mkdir(parents=True, exist_ok=False)
    private = folder / 'private'
    private.mkdir(mode=0o700)
    os.chmod(folder, 0o700)
    credentials = {actor: secrets.token_urlsafe(32) for actor in ['writer-a', 'writer-b']}
    base_env = {'PATH': str(terraform.parent), 'HOME': str(private), 'TMPDIR': str(private),
                'TF_IN_AUTOMATION': '1', 'CHECKPOINT_DISABLE': '1', 'TF_INPUT': '0',
                'TF_HTTP_RETRY_MAX': '0', 'AWS_EC2_METADATA_DISABLED': 'true'}
    cli = private / 'empty.tfrc'
    cli.write_text('provider_installation { filesystem_mirror { path = ' + json.dumps(str(private)) + ' } }\n')
    base_env['TF_CLI_CONFIG_FILE'] = str(cli)
    version = json.loads(subprocess.check_output([str(terraform), 'version', '-json'], env=base_env, timeout=15))
    initial = encoded({'version': 4, 'terraform_version': version['terraform_version'], 'serial': 1,
                       'lineage': str(uuid.uuid4()), 'outputs': {'fixture': {'value': 'synthetic-state', 'type': 'string'}}, 'resources': []})
    store = FixtureStore(private / 'fixture.sqlite', initial)
    control = Control()
    server = fixture_server(store, credentials, control)
    base = 'http://127.0.0.1:' + str(server.server_port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    checks, commands = [], []
    active = None

    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(name)

    def environment(actor):
        return {**base_env, 'TF_HTTP_USERNAME': actor, 'TF_HTTP_PASSWORD': credentials[actor]}

    def native(actor, arguments, expected_exit=0):
        result = subprocess.run([str(terraform), *arguments], cwd=private / actor,
                                env=environment(actor), capture_output=True, text=True, timeout=20)
        commands.append({'actor': actor, 'arguments': arguments, 'exitCode': result.returncode, 'expectedExitCode': expected_exit})
        (private / ('command-' + str(len(commands)) + '.log')).write_text(result.stdout + '\n' + result.stderr)
        return result

    def request(actor, method, path, value=None, password=None):
        header = base64.b64encode((actor + ':' + (password or credentials[actor])).encode()).decode()
        req = urllib.request.Request(base + path, data=encoded(value) if value is not None else None,
                                     method=method, headers={'Authorization': 'Basic ' + header})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=5) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code

    try:
        for actor in credentials:
            workspace = private / actor
            workspace.mkdir()
            (workspace / 'main.tf.json').write_text(json.dumps({'terraform': {'required_version': '>= 1.10.0, < 2.0.0', 'backend': {'http': {}}}, 'output': {'fixture': {'value': 'synthetic-state'}}}))
            (workspace / 'backend.hcl').write_text('address = ' + json.dumps(base + '/state') + '\nlock_address = ' + json.dumps(base + '/lock') + '\nunlock_address = ' + json.dumps(base + '/lock') + '\nlock_method = "POST"\nunlock_method = "DELETE"\n')
            check('native init ' + actor, native(actor, ['init', '-input=false', '-no-color', '-backend-config=backend.hcl']).returncode == 0)
        pulled = native('writer-a', ['state', 'pull'])
        check('native reads synthetic lineage and payload', pulled.returncode == 0 and all(json.loads(pulled.stdout).get(k) == json.loads(initial)[k] for k in ['version', 'serial', 'lineage', 'outputs', 'resources']))
        check('unknown credential denied', request('writer-a', 'GET', '/state', password='invalid-fixture-password') == 401)
        control.pause = True
        active = subprocess.Popen([str(terraform), 'plan', '-input=false', '-no-color', '-lock-timeout=0s'], cwd=private / 'writer-a', env=environment('writer-a'), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        check('real native plan holds lock while reading', control.read_held.wait(12) and active.poll() is None and store.lock() is not None)
        current = store.lock()[1]
        competing = native('writer-b', ['plan', '-input=false', '-no-color', '-lock-timeout=0s'], expected_exit=1)
        check('second native writer excluded', competing.returncode == 1 and 'Error acquiring the state lock' in competing.stderr + competing.stdout)
        check('foreign actor cannot unlock owner', request('writer-b', 'DELETE', '/lock', {'ID': current['ID']}) == 409 and store.lock()[1]['ID'] == current['ID'])
        check('incorrect lock ID cannot unlock owner', request('writer-a', 'DELETE', '/lock', {'ID': 'wrong-fixture-lock'}) == 409 and store.lock()[1]['ID'] == current['ID'])
        check('foreign writer cannot replace state', request('writer-b', 'POST', '/state?ID=' + current['ID'], {}) == 409 and store.read() == initial)
        try:
            store.restore_fixture_version(1)
            refused = False
        except ValueError:
            refused = True
        check('recovery refuses an active writer', refused)
        control.pause = False
        control.release.set()
        output, _ = active.communicate(timeout=15)
        (private / 'writer-a-plan.log').write_text(output)
        commands.append({'actor': 'writer-a', 'arguments': ['plan', '-input=false', '-no-color', '-lock-timeout=0s'], 'exitCode': active.returncode, 'expectedExitCode': 0})
        check('native plan succeeds and releases owned lock', active.returncode == 0 and store.lock() is None)
        check('plan-only clients never write state', not any(e['method'] == 'POST' and e['path'] == '/state' and e['actor'] == 'writer-a' for e in control.events) and store.read() == initial)
        changed = json.loads(initial)
        changed['serial'] = 2
        changed['outputs']['fixture']['value'] = 'synthetic-new-version'
        changed_id = store.add_fixture_version(encoded(changed))
        reopened = FixtureStore(private / 'fixture.sqlite', b'not-a-new-seed')
        check('local fixture versions survive reopen', json.loads(reopened.read())['serial'] == 2)
        reopened.restore_fixture_version(1)
        check('verified fixture recovery restores exact bytes', reopened.read() == initial)
        restored = native('writer-b', ['state', 'pull'])
        check('native observes restored lineage and payload', restored.returncode == 0 and json.loads(restored.stdout) == json.loads(pulled.stdout))
        with reopened.connection() as db:
            db.execute('UPDATE versions SET payload=? WHERE id=?', (b'corrupted-synthetic-backup', changed_id))
        try:
            reopened.restore_fixture_version(changed_id)
            refused = False
        except ValueError:
            refused = True
        check('corrupt fixture backup cannot replace good state', refused and reopened.read() == initial)
        abandoned = {'ID': str(uuid.uuid4()), 'Operation': 'synthetic-abandoned-writer'}
        reopened.acquire('writer-a', abandoned)
        restarted = FixtureStore(private / 'fixture.sqlite', b'not-a-new-seed')
        check('uncertain abandoned lock persists across reopen', restarted.lock()[1]['ID'] == abandoned['ID'])
        check('abandoned lock still needs matching owner and ID', restarted.unlock('writer-b', abandoned)[0] == 409 and restarted.unlock('writer-a', abandoned)[0] == 200)
    finally:
        control.pause = False
        control.release.set()
        if active is not None and active.poll() is None:
            active.terminate()
            try:
                active.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                active.kill()
                active.communicate(timeout=5)
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    report = {'passed': all(c['passed'] for c in checks), 'scope': 'isolated-loopback-http-state-protocol',
              'sourceSha256': digest(Path(__file__).read_bytes()), 'terraformVersion': version['terraform_version'],
              'terraformSha256': digest(terraform.read_bytes()), 'checks': checks, 'commands': commands,
              'initialSyntheticStateSha256': digest(initial), 'selectedBackendVerified': False,
              'migrationAuthorized': False, 'boundary': 'Actual Terraform init/plan/state pull against a synthetic loopback HTTP fixture and local SQLite version/lock store. No apply, project backend, TLS, cloud authentication, S3/Azure/GCS behavior, migration or application-system qualification.'}
    serialized = json.dumps(report, indent=2) + '\n'
    if any(secret in serialized for secret in credentials.values()):
        raise ValueError('Credential appeared in public fixture evidence')
    (folder / 'report.json').write_text(serialized)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terraform', type=Path, default=shutil.which('terraform'))
    parser.add_argument('--work-dir', type=Path, required=True)
    args = parser.parse_args()
    if not args.terraform:
        parser.error('Install a local Terraform executable or provide --terraform.')
    result = run_probe(Path(args.terraform).resolve(strict=True), args.work_dir.resolve())
    print(json.dumps({'passed': result['passed'], 'checks': len(result['checks']), 'report': str(args.work_dir / 'report.json'), 'selectedBackendVerified': False}))
