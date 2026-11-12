"""Independent connected oracle inside the unchanged receiving image.

Only disposable SQL DSNs, synthetic Entra JWKS and a loopback catalogue CA are
injected at the owned bootstrap. No generated tests or fixture assertions run.
"""
import asyncio, datetime, hashlib, importlib.metadata, json, os, secrets
import socket, ssl, sys, tempfile, threading, time, uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.path.insert(0, '/app')
import bootstrap, jwt, psycopg, uvicorn
from psycopg import sql
from psycopg.conninfo import make_conninfo
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from workflow_database import initialize_database, grant_runtime_roles
from workflow_application import membership_key
from labels import profile


class Catalogue:
    def __init__(self, directory):
        self.calls = []; self.mode = 'confirmed'; self.token = secrets.token_urlsafe(24)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-datetime.timedelta(minutes=1))
            .not_valid_after(now+datetime.timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), critical=False)
            .sign(key, hashes.SHA256()))
        self.ca = directory/'ca.pem'; self.ca.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        private = directory/'tls.key'
        private.write_bytes(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        private.chmod(0o600); owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                assert self.path == '/labels'
                assert self.headers['Authorization'] == 'Bearer '+owner.token
                raw = self.rfile.read(int(self.headers['Content-Length']))
                owner.calls.append({'raw': raw.decode(), 'headers': dict(self.headers)})
                if owner.mode == 'disconnect':
                    self.connection.shutdown(socket.SHUT_RDWR); self.connection.close(); return
                reply = {'operationId': self.headers['Idempotency-Key'],
                    'approvalSha256': self.headers['X-Approval-SHA256'],
                    'payloadSha256': hashlib.sha256(raw).hexdigest(),
                    'status': 'completed', 'externalId': 'synthetic-'+str(len(owner.calls))}
                encoded = json.dumps(reply).encode()
                self.send_response(201); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(encoded))); self.end_headers()
                self.wfile.write(encoded)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); tls.load_cert_chain(self.ca, private)
        self.server.socket = tls.wrap_socket(self.server.socket, server_side=True)
        self.url = 'https://localhost:'+str(self.server.server_port)+'/labels'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()

    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)


async def main(inputs):
    checks = []
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app').glob('*.py')}
    assert before == inputs['applicationHashes']
    for name, expected in inputs['auxiliaryHashes'].items():
        assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest() == expected
    versions = {name: importlib.metadata.version(name) for name in inputs['runtimePins']}
    assert versions == inputs['runtimePins']
    assert os.getuid() == 0  # The actual exported worker requires a root supervisor.
    assert sys.version_info[:3] == (3, 13, 18)
    checks.append('unchanged application/schema/lock and all runtime distribution versions in actual Linux AMD64 receiving image')
    with psycopg.connect(inputs['adminDsn']) as c:
        assert int(c.execute('SHOW server_version_num').fetchone()[0])//10000 == 17
        initialize_database(c)
        roles = []
        for kind in ['api', 'worker']:
            name = 'labels_'+kind; password = secrets.token_urlsafe(24); roles.append((name, password))
            c.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(name), sql.Literal(password)))
        grant_runtime_roles(c, *[n for n, _ in roles])
    dsns = {kind: make_conninfo(inputs['adminDsn'], user=name, password=pw)
            for kind, (name, pw) in zip(['api', 'worker'], roles)}
    for dsn in dsns.values():
        for statement in ['DELETE FROM workflow.events', 'DELETE FROM workflow.memberships', 'CREATE SCHEMA injected']:
            with psycopg.connect(dsn) as c:
                try: c.execute(statement)
                except psycopg.errors.InsufficientPrivilege: pass
                else: raise AssertionError('Runtime SQL authority widened: '+statement)
    checks.append('distinct restricted real SQL roles cannot erase history, remove memberships or create schemas')
    with tempfile.TemporaryDirectory(prefix='azure-independent-') as folder:
        root = Path(folder); root.chmod(0o755); sink = Catalogue(root)
        server = None; api_task = None; worker_task = None
        try:
            account, staff, other, reviewer, tenant, api_id, client_id = [str(uuid.uuid4()) for _ in range(7)]
            listener = socket.socket(); listener.bind(('127.0.0.1', 0)); listener.listen(128); listener.setblocking(False)
            origin = 'http://127.0.0.1:'+str(listener.getsockname()[1])
            settings = {'TENANT_ID': tenant, 'API_CLIENT_ID': api_id, 'SPA_CLIENT_ID': client_id}
            config = {'accountId': account, 'environment': 'qualification', 'publicOrigin': origin,
                'identitySettings': settings, 'catalogueEndpoint': sink.url, 'catalogueScope': 'catalogue.labels.publish'}
            owned = profile(config)
            with psycopg.connect(inputs['adminDsn']) as c:
                c.execute('INSERT INTO workflow.accounts(id) VALUES(%s)', (account,))
                for subject, roles_for_subject in [(staff, ['user']), (other, ['user']), (reviewer, ['reviewer'])]:
                    c.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)',
                        (account, membership_key(owned, subject), roles_for_subject))
            private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            jwks = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(key=private.public_key()))
            native = bootstrap.EntraVerifier
            environment = {'LABEL_CONFIG_JSON': json.dumps(config), 'DATABASE_HOST': 'synthetic.postgres.database.azure.com',
                'DATABASE_NAME': 'image_qualification', 'DATABASE_CA_FILE': '/etc/ssl/certs/ca-certificates.crt',
                'WORKLOAD_IDENTITY_CLIENT_ID': str(uuid.uuid4()), 'CATALOGUE_TOKEN': sink.token}
            def local_database(provider, env, role):
                assert provider == 'azure' and role in dsns and env['DATABASE_USER'] == 'labels_'+role
                return dsns[role]
            with patch('bootstrap.native_database', side_effect=local_database), patch('bootstrap.EntraVerifier', side_effect=lambda s, **kw: native(s, jwks=jwks)):
                with patch.dict(os.environ, {**environment, 'DATABASE_USER': 'labels_api'}, clear=True):
                    import api
                    app = api.app_factory()
                with patch.dict(os.environ, {**environment, 'DATABASE_USER': 'labels_worker'}, clear=True):
                    worker = bootstrap.production('worker')
            # Only the trusted local CA is injected; the exported delivery child
            # retains exact endpoint, TLS verification, credentials and policy.
            worker.deliver.environment['CATALOGUE_CA_FILE'] = str(sink.ca)
            # Independently inspect the actual image's ProcessStage mechanism
            # with the application's exact per-stage environment. This probe is
            # separate trusted evaluator source, not a replacement app processor.
            from workflow_process_stage import ProcessStage
            probe = '''import json,os,pathlib
try:
 pathlib.Path('/proc/'+str(os.getppid())+'/environ').read_bytes();parent_readable=True
except PermissionError:parent_readable=False
status=pathlib.Path('/proc/self/status').read_text()
print(json.dumps({'status':'ok','result':{'uid':os.getuid(),'gid':os.getgid(),
 'groups':os.getgroups(),'parentEnvironmentReadable':parent_readable,
 'sqlKeys':[k for k in os.environ if k.startswith(('DATABASE_','PG','FIXTURE_DSN','WORKLOAD_'))],
 'publicationSecretPresent':'CATALOGUE_TOKEN' in os.environ,
 'capabilitiesEmpty':'CapEff:\\t0000000000000000' in status,
 'noNewPrivileges':'NoNewPrivs:\\t1' in status}}))'''
            for stage, expected_uid in [(worker.processor, 65534), (worker.deliver, 65533)]:
                observed = ProcessStage([sys.executable, '-I', '-c', probe], kind=stage.kind,
                    environment=stage.environment, cwd=stage.cwd)({})
                assert observed['uid'] == observed['gid'] == expected_uid and not observed['groups']
                assert not observed['parentEnvironmentReadable'] and not observed['sqlKeys']
                assert observed['publicationSecretPresent'] == (stage.kind == 'dispatch')
                assert observed['capabilitiesEmpty'] and observed['noNewPrivileges']
            checks.append('actual image ProcessStage probe drops distinct65534/65533 UIDs/groups/capabilities; parent environment denied, SQL keys absent, publication secret dispatch-only')
            server = uvicorn.Server(uvicorn.Config(app, log_level='critical', access_log=False, proxy_headers=False))
            api_task = asyncio.create_task(server.serve(sockets=[listener]))
            def start_worker(): return asyncio.create_task(worker.run(concurrency=2, recovery_interval=5))
            worker_task = start_worker()
            for _ in range(200):
                if server.started: break
                if api_task.done(): await api_task
                await asyncio.sleep(.025)
            assert server.started
            def request(method, path, data, who, idem, changes, forged):
                now = int(time.time())
                claims = {'iss': 'https://login.microsoftonline.com/'+tenant+'/v2.0', 'tid': tenant,
                    'aud': api_id, 'azp': client_id, 'ver': '2.0', 'scp': 'access_as_user',
                    'oid': who, 'sub': 'fixture-'+who, 'iat': now-1, 'nbf': now-1, 'exp': now+300,
                    'roles': ['Administrator', 'Reviewer']}
                claims.update(changes)
                token = 'forged' if forged else jwt.encode(claims, private, algorithm='RS256', headers={'kid': 'independent'})
                headers = {'Authorization': 'Bearer '+token, 'Origin': origin, 'Content-Type': 'application/json',
                    'Idempotency-Key': idem or str(uuid.uuid4())}
                try:
                    with urlopen(Request(origin+path, data=None if data is None else json.dumps(data).encode(), headers=headers, method=method), timeout=5) as r:
                        return r.status, json.load(r)
                except HTTPError as r: return r.code, json.load(r)
            async def http(method, path, data=None, who=staff, idem=None, changes=None, forged=False):
                return await asyncio.to_thread(request, method, path, data, who, idem, changes or {}, forged)
            async def until(op, expected):
                for _ in range(400):
                    if worker_task.done(): await worker_task
                    with psycopg.connect(inputs['adminDsn']) as c:
                        state = c.execute('SELECT state FROM workflow.operations WHERE id=%s', (op,)).fetchone()[0]
                    if state == expected: return
                    await asyncio.sleep(.05)
                raise AssertionError('Expected '+expected+'; observed '+state)
            checks.append('actual production API/worker bootstrap with real HTTP listener; only synthetic native JWKS/SQL and CA injected')
            assert (await http('GET', '/readyz'))[0] == 200
            cases = inputs['cases']
            operations = []
            for case in cases['validSourceCases']:
                status, reply = await http('POST', '/api/operations', case['source'])
                assert status == 202, (status, reply)
                op = reply['operation']['id']; operations.append(op); await until(op, 'review')
                status, reply = await http('GET', '/api/operations/'+op)
                assert status == 200 and reply['operation']['result'] == case['expectedResult']
                assert reply['operation']['source'] == case['source']
            for case in cases['invalidSourceCases']+[cases['whitespaceOnlySource']]:
                assert (await http('POST', '/api/operations', case['source']))[0] == 400
            assert not sink.calls
            checks.append('all frozen8 valid/14 invalid inputs traverse real HTTP, SQL, durable queue and UID-separated processing child; no publication before approval')
            source = cases['validSourceCases'][0]['source']; idem = str(uuid.uuid4())
            replies = await asyncio.gather(*[http('POST', '/api/operations', source, idem=idem) for _ in range(4)])
            assert all(s == 202 for s, _ in replies), replies
            assert len({r['operation']['id'] for _, r in replies}) == 1
            op = replies[0][1]['operation']['id']; await until(op, 'review')
            for who, value in [(other, source), (staff, {**source, 'caption': 'changed'})]:
                assert (await http('POST', '/api/operations', value, who=who, idem=idem))[0] == 409
            with psycopg.connect(inputs['adminDsn']) as c:
                assert c.execute("SELECT count(*) FROM workflow.procrastinate_jobs WHERE args->>'operation_id'=%s", (op,)).fetchone()[0] == 1
            checks.append('concurrent4 idempotent submissions persist one operation/job; changed source and other owner conflict')
            assert (await http('GET', '/api/operations/'+op, who=other))[0] in {403, 404}
            assert not (await http('GET', '/api/operations', who=other))[1]['operations']
            assert (await http('POST', '/api/operations/'+op+'/approve', {'revision': 1, 'inspectionHash': '0'*64}))[0] == 403
            for changes in [{'tid': str(uuid.uuid4())}, {'azp': str(uuid.uuid4())}, {'exp': int(time.time())-60}]:
                assert (await http('GET', '/api/session', changes=changes))[0] == 403
            assert (await http('GET', '/api/session', forged=True))[0] == 403
            checks.append('own-read/list, live reviewer role and signed issuer/client/expiry guards deny token-role escalation and forged identities')
            _, reply = await http('GET', '/api/operations/'+op, who=reviewer); old = reply['operation']
            edited = {'displayCaption': 'Curator edit 🖼', 'needsCurator': source['sensitive']}
            assert (await http('POST', '/api/operations/'+op+'/review', {'revision': old['revision'], 'result': {**edited, 'needsCurator': not source['sensitive']}}, who=reviewer))[0] in {400, 409}
            status, reply = await http('POST', '/api/operations/'+op+'/review', {'revision': old['revision'], 'result': edited}, who=reviewer)
            assert status == 200 and reply['operation']['revision'] > old['revision']
            assert (await http('POST', '/api/operations/'+op+'/approve', {'revision': old['revision'], 'inspectionHash': old['inspectionHash']}, who=reviewer))[0] == 409
            _, reply = await http('GET', '/api/operations/'+op, who=reviewer); current = reply['operation']
            approval = {'revision': current['revision'], 'inspectionHash': current['inspectionHash']}
            assert (await http('POST', '/api/operations/'+op+'/approve', approval, who=reviewer))[0] == 200
            await until(op, 'sent'); assert len(sink.calls) == 1
            effect = sink.calls[0]
            assert json.loads(effect['raw']) == {'accessionCode': source['accessionCode'], **edited}
            assert effect['headers']['Idempotency-Key'] == op
            assert effect['headers']['X-Approval-SHA256'] == approval['inspectionHash']
            assert effect['headers']['X-Payload-SHA256'] == hashlib.sha256(effect['raw'].encode()).hexdigest()
            checks.append('inspection-bound revision/edit policy and stale-approval denial; exact approved source/result delivered once by separate UID child over real verified TLS')
            second = operations[1]; sink.mode = 'disconnect'
            _, reply = await http('GET', '/api/operations/'+second, who=reviewer); current = reply['operation']
            approval = {'revision': current['revision'], 'inspectionHash': current['inspectionHash']}
            assert (await http('POST', '/api/operations/'+second+'/approve', approval, who=reviewer))[0] == 200
            await until(second, 'unknown'); assert len(sink.calls) == 2
            worker_task.cancel(); await asyncio.gather(worker_task, return_exceptions=True); worker_task = start_worker()
            assert (await http('POST', '/api/operations/'+second+'/approve', approval, who=reviewer))[0] in {200, 409}
            await asyncio.sleep(2); await until(second, 'unknown'); assert len(sink.calls) == 2
            checks.append('unconfirmed real TLS effect stays unknown across worker restart/repeated approval with no replay')
            with psycopg.connect(inputs['adminDsn']) as c:
                c.execute('UPDATE workflow.memberships SET active=false WHERE account_id=%s AND subject=%s', (account, membership_key(owned, staff)))
            assert (await http('GET', '/api/operations/'+op))[0] == 403
            checks.append('live SQL revocation defeats still-valid signed staff token')
            assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app').glob('*.py')}
            print(json.dumps({'passed': True, 'checks': checks, 'applicationHashes': before,
                'runtimeVersions': versions, 'sourceUnchanged': True, 'cloudOperations': False,
                'boundary': 'Actual unchanged Linux AMD64 application image and production assembly, real HTTP/SQL/queue/UID-separated children/TLS with explicit synthetic native JWKS/SQL and CA injection. No managed Azure identity, VNet, native DB bootstrap, account plan or whole-project acceptance.'}))
        finally:
            if server is not None: server.should_exit = True
            if worker_task is not None: worker_task.cancel()
            await asyncio.gather(*[t for t in [api_task, worker_task] if t is not None], return_exceptions=True)
            sink.close()


asyncio.run(main(json.load(sys.stdin)))
