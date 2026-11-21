"""Build the exact private core and exercise it without host Python packages.

Owned Docker/SQL fixtures only. All vendor/model transports remain scripted.
No production factory, security acceptance, provider plan or deployment claim.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CORE = ['enterprise_identity.py', 'enterprise_sources.py', 'enterprise_knowledge.py',
        'enterprise_auth_store.py', 'enterprise_auth_schema.sql', 'enterprise_oauth.py',
        'enterprise_sessions.py', 'enterprise_http.py', 'enterprise_web.py',
        'enterprise_queries.py', 'enterprise_queries_schema.sql', 'enterprise_query_service.py',
        'enterprise_audit.py', 'enterprise_audit_schema.sql', 'enterprise_models.py', 'enterprise_secrets.py',
        'enterprise_configuration.py', 'enterprise_native.py', 'enterprise_operator.py', 'workflow_connection.py', 'workflow_errors.py',
        'enterprise_google_jobs.py', 'enterprise_google_transfer.py',
        'aws_json_model.py', 'azure_structured.py', 'gcp_structured.py', 'ibm_structured.py',
        'structured_output.py', 'structured_http.py', 'policy_review.py',
        'enterprise_extraction_cache.py', 'enterprise_extraction_schema.sql',
        'enterprise_parser_transport.py', 'enterprise_document_contract.py', 'enterprise_document_job.py', 'public_faq.py', 'faq-output-contract.json',
        'enterprise-web.html', 'enterprise-web-app.js', 'enterprise-web.css', 'enterprise-web-notices.txt', 'enterprise-web-lock.json']
SQL = {'enterprise_auth_postgres': 21, 'enterprise_sessions_postgres': 4,
       'enterprise_queries_postgres': 19, 'enterprise_extraction_cache_postgres': 14, 'enterprise_audit_postgres': 9,
       'enterprise_operator_postgres':11}


def qualify(args):
    if not args.docker_host.startswith('unix:///') or not Path(args.docker_host[7:]).is_socket():
        raise ValueError('Use the existing owned local Docker Unix socket')
    output = args.out.resolve()
    if output.exists() or not output.is_relative_to(ROOT / '.local'):
        raise ValueError('Use a fresh local evidence directory')
    output.mkdir(parents=True)
    runtime = ROOT / 'src/runtime'
    lock_name = 'enterprise-runtime' + ('-' + args.provider if args.provider else '') + '-python-lock.json'
    lock = json.loads((runtime / lock_name).read_text())
    # Do not silently bless a hand-edited lock or drifted metadata input.
    import importlib.util
    spec = importlib.util.spec_from_file_location('owned_runtime_lock', ROOT / 'scripts/build-enterprise-runtime-lock.py')
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    if builder.build(args.provider) != lock:
        raise ValueError('Runtime lock differs from reviewed dependency closure')
    base_lock = json.loads((runtime / 'python-container-lock.json').read_text())
    dockerfile = (runtime / 'enterprise-runtime.Dockerfile').read_text()
    if base_lock['amd64Digest'] not in dockerfile:
        raise ValueError('Private runtime base differs from reviewed platform lock')
    for package in base_lock['securityPackages']:
        if 'ADD --checksum=sha256:' + package['sha256'] + ' ' + package['url'] not in dockerfile:
            raise ValueError('Private runtime omitted a pinned base security package')
    tests = [*sorted((ROOT / 'tests/runtime').glob('enterprise_*_acceptance.py')),
             *[ROOT / 'tests/runtime' / (name + '.py') for name in SQL],
             ROOT / 'tests/runtime/durable_postgres_acceptance.py', ROOT / 'tests/runtime/durable_fixture_tasks.py']
    tests += [ROOT / 'tests/runtime/enterprise_deployment_fixture.py']
    helper_names = ['durable_workflow.py', 'workflow_contract.py']
    sources = [*[runtime / name for name in CORE + helper_names], *tests,
               runtime / lock_name, runtime / 'enterprise-runtime.Dockerfile', runtime / 'python-container-lock.json',
               ROOT / 'scripts/build-enterprise-runtime-lock.py', Path(__file__).resolve()]
    sources += [ROOT / name for name in lock['derivedFrom']]
    schema_assets = ['tests/fixtures/providers/google-batch-v1-discovery-20261111.json',
                     'tests/fixtures/providers/google-batch-v1-discovery-20261111.provenance.json']
    sources += [ROOT / name for name in schema_assets]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    checks, image, passed = [], None, False
    # The owned VM shares the workspace, not macOS's private /var/folders tree.
    with tempfile.TemporaryDirectory(prefix='private-core-', dir=ROOT / '.local') as scratch:
        folder = Path(scratch)
        config = folder / 'docker-config'; config.mkdir()
        (config / 'config.json').write_text(json.dumps({'cliPluginsExtraDirs': ['/opt/homebrew/lib/docker/cli-plugins']}))
        env = {'PATH': os.environ.get('PATH', ''), 'HOME': scratch,
               'DOCKER_HOST': args.docker_host, 'DOCKER_CONFIG': str(config)}

        def run(label, command, *, timeout=240, data=None):
            result = subprocess.run(['docker', *command], cwd=ROOT, env=env,
                                    input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            (output / (label + '.stdout')).write_bytes(result.stdout)
            (output / (label + '.stderr')).write_bytes(result.stderr)
            checks.append({'check': label, 'passed': result.returncode == 0, 'exitCode': result.returncode})
            if result.returncode:
                raise RuntimeError('Private runtime qualification failed: ' + label)
            return result.stdout + result.stderr

        try:
            context = folder / 'build'; (context / 'runtime').mkdir(parents=True)
            for name in CORE:
                shutil.copyfile(runtime / name, context / 'runtime' / name)
            shutil.copyfile(runtime / 'enterprise-runtime.Dockerfile', context / 'Dockerfile')
            (context / 'requirements.lock').write_text(lock['requirements'])
            tag = 'atmem-private-' + (args.provider or 'core') + ':qualification-' + os.urandom(8).hex()
            run('build', ['build', '--platform', 'linux/amd64', '--tag', tag, str(context)], timeout=600)
            observed = json.loads(run('image', ['image', 'inspect', tag]))[0]
            image = observed['Id']
            if (observed['Os'], observed['Architecture'], observed['Config']['User']) != ('linux', 'amd64', '10001:10001'):
                raise ValueError('Expected nonprivileged Linux/amd64 image')
            restricted = ['run', '--rm', '--platform', 'linux/amd64', '-i', '--read-only', '--tmpfs', '/tmp:rw,noexec,nosuid,size=64m',
                          '--memory', '512m', '--cpus', '2', '--pids-limit', '96',
                          '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges']
            preflight = '''import importlib,importlib.metadata,json,os,sys
sys.path.insert(0,'/app')
assert sys.version_info[:3]==(3,13,18),sys.version
modules=['enterprise_http','enterprise_query_service','enterprise_extraction_cache','enterprise_oauth','enterprise_identity','enterprise_web','enterprise_parser_transport','enterprise_audit','enterprise_models','enterprise_secrets','enterprise_native','enterprise_configuration','enterprise_operator']
for name in modules:
 module=importlib.import_module(name)
 assert module.__file__.startswith('/app/'),module.__file__
assert 'enterprise_document' not in sys.modules
configuration=json.load(sys.stdin);expected=configuration['packages']
sdk_modules={'aws':['boto3','botocore'],'azure':['azure.identity'],'gcp':[],'ibm':['ibm_cloud_sdk_core.authenticators']}.get(configuration['provider'],[])
for name in sdk_modules:
 module=importlib.import_module(name)
 assert module.__file__.startswith('/usr/local/lib/python3.13/site-packages/'),module.__file__
actual={d.metadata['Name'].lower().replace('_','-'):d.version for d in importlib.metadata.distributions()}
assert actual==expected,(actual,expected)
assert os.getuid()==10001 and not os.path.exists('/workspace/.local')
assert not any(d in actual for d in ['pip','setuptools','wheel'])
print(json.dumps({'python':sys.version,'packages':actual,'modules':modules,'nativeSdkModules':sdk_modules,'uid':os.getuid()}))
'''
            audit = json.dumps({'packages':{s['name'].lower().replace('_', '-'): s['version'] for s in lock['sources']},'provider':args.provider}).encode()
            run('runtime-imports', [*restricted, '--network', 'none', image,
                'python', '-I', '-c', preflight], data=audit)
            # Only fixture helpers are mounted alongside tests. Application imports
            # resolve to the actual image's /app; no host application or Python
            # site-packages can shadow the installed image.
            payload = {}
            for name in helper_names:
                payload['src/runtime/' + name] = base64.b64encode((runtime / name).read_bytes()).decode()
            for path in tests:
                payload['tests/runtime/' + path.name] = base64.b64encode(path.read_bytes()).decode()
            for name in schema_assets:
                payload[name] = base64.b64encode((ROOT / name).read_bytes()).decode()
            loader = '''import base64,json,os,sys
from pathlib import Path,PurePosixPath
root=Path('/tmp/workspace');root.mkdir()
for name,value in json.load(sys.stdin).items():
 path=PurePosixPath(name)
 assert not path.is_absolute() and '..' not in path.parts
 target=root.joinpath(*path.parts);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_bytes(base64.b64decode(value,validate=True));target.chmod(0o400)
sys.path.insert(0,'/app')
'''
            result = run('policy-tests', [*restricted, '--network', 'none', image,
                'python', '-I', '-c', loader + "import unittest;unittest.main(module=None,argv=['unittest','discover','-s','/tmp/workspace/tests/runtime','-p','enterprise_*_acceptance.py','-v'])"], data=json.dumps(payload).encode())
            if not re.search(rb'Ran 94 tests in [^\n]+\n\nOK\s*$', result):
                raise ValueError('Unexpected private policy test inventory')
            for version in [17, 18]:
                name = 'atmem-durable-qualification' + ('-pg18' if version == 18 else '')
                # Select exactly the existing owned fixture, never another DB.
                original = json.loads((ROOT / '.local/durable-postgres' / ('fixture-pg18.json' if version == 18 else 'fixture.json')).read_text())
                # Never record container Env: it includes synthetic DB secrets.
                template = '{"Id":{{json .Id}},"Name":{{json .Name}},"NetworkSettings":{"Ports":{{json .NetworkSettings.Ports}}}}'
                observed = json.loads(run('pg' + str(version) + '-container', ['container', 'inspect', '--format', template, name]))
                bindings = observed['NetworkSettings']['Ports']['5432/tcp']
                if (original['name'] != name or observed['Name'] != '/' + name
                    or not any(b['HostIp'] == '127.0.0.1' and int(b['HostPort']) == original['port'] for b in bindings)):
                    raise ValueError('Owned local fixture/container identity mismatch')
                # Private synthetic fixture bytes travel only through stdin into
                # bounded tmpfs, never image layers, Env, command args or logs.
                private_payload = {**payload, 'fixture.json': base64.b64encode(json.dumps({**original, 'port': 5432}).encode()).decode()}
                private = [*restricted, '--network', 'container:' + observed['Id'],
                    '--env', 'ATMEM_WORKFLOW_TEST_CONFIG=/tmp/workspace/fixture.json']
                probe = loader + '''sys.path[:0]=['/tmp/workspace/tests/runtime','/tmp/workspace/src/runtime']
from durable_postgres_acceptance import fixture_dsn
import psycopg
with psycopg.connect(fixture_dsn()) as connection:
 version=int(connection.execute('SHOW server_version_num').fetchone()[0])
assert version//10000==''' + str(version) + '''
print(json.dumps({'postgresVersionNum':version}))
'''
                run('pg' + str(version) + '-preflight', [*private, image, 'python', '-I', '-c', probe],
                    data=json.dumps(private_payload).encode())
                for suite, count in SQL.items():
                    entry = '/tmp/workspace/tests/runtime/' + suite + '.py'
                    result = run('pg' + str(version) + '-' + suite, [*private, image,
                        'python', '-I', '-c', loader + "import runpy;sys.argv=[" + repr(entry) + ",'-v'];runpy.run_path(" + repr(entry) + ",run_name='__main__')"], data=json.dumps(private_payload).encode())
                    if not re.search(('Ran ' + str(count) + r' tests in [^\n]+\n\nOK\s*$').encode(), result):
                        raise ValueError('Unexpected native SQL test inventory: ' + suite)
            if any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest for name, digest in hashes.items()):
                raise ValueError('Runtime qualification sources changed')
            passed = True
        finally:
            (output / 'receipt.json').write_text(json.dumps({'recordedAt': datetime.now(timezone.utc).isoformat(),
                'passed': passed, 'imageId': image, 'checks': checks, 'sourceHashes': hashes,
                'provider':args.provider,'packages': len(lock['sources']), 'policyTests': 94, 'sqlTestsPerVersion': sum(SQL.values()),
                'postgresVersions': [17, 18], 'securityAccepted': False, 'cloudOperations': False,
                'scope': 'Clean Linux private application/factory/operator dependencies. Actual crypto/SQL/Procrastinate/bootstrap/enrollment/revocation; native model serializers with scripted HTTP. Assembled HTTP API/worker tests run separately on the host. No native account/model quality, per-file cloud launcher/isolation, complete-project or deployment acceptance.'}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker-host', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--provider',choices=['aws','azure','gcp','ibm'])
    qualify(parser.parse_args())
