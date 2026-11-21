"""Qualify exact document-parser sources and real files in restricted Linux.

Uses an already-qualified owned local invoice parser image as the PDF/OCR base.
No source account, cloud model, deployment or production-security claim is made.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]


def qualify(args):
    if not args.docker_host.startswith('unix:///') or not Path(args.docker_host[7:]).is_socket():
        raise ValueError('Use the existing owned local Docker Unix socket')
    out = Path(args.out).resolve()
    if not out.is_relative_to(ROOT / '.local') or out.exists():
        raise ValueError('Use a fresh local evidence directory')
    out.mkdir(parents=True)
    runtime = ROOT / 'src/runtime'
    lock = json.loads((runtime / 'enterprise-document-lock.json').read_text())
    image_names = ['enterprise_document_contract.py', 'EnterpriseDocument.java', 'enterprise_document.py', 'enterprise_document_cli.py', 'enterprise_document_job.py', 'enterprise_parser_service.py',
                   'enterprise-document.Dockerfile', 'enterprise-document-lock.json']
    sources = [runtime / name for name in image_names]
    composition_names = ['enterprise_sources.py', 'enterprise_knowledge.py', 'public_faq.py', 'faq-output-contract.json']
    sources += [runtime / name for name in composition_names]
    sources += [Path(__file__).resolve(), ROOT / 'tests/runtime/enterprise_document_linux.py', ROOT / 'tests/runtime/enterprise_parser_rpc_linux.py',
                ROOT / 'tests/runtime/enterprise_document_composition_linux.py', ROOT / 'tests/runtime/enterprise_document_job_acceptance.py',
                ROOT / 'scripts/create-enterprise-document-fixtures.py']
    for directory in ['enterprise-documents', 'invoices']:
        sources += sorted((ROOT / 'benchmarks/convergence/fixtures' / directory).glob('*'))
    if any(not path.is_file() for path in sources):
        raise ValueError('Qualification requires every declared source and schema asset')
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources if p.is_file()}
    checks = []
    image = None
    success = False
    with tempfile.TemporaryDirectory(prefix='atmem-enterprise-docs-') as scratch:
        folder = Path(scratch)
        config = folder / 'docker-config'
        config.mkdir()
        (config / 'config.json').write_text(json.dumps({'cliPluginsExtraDirs': ['/opt/homebrew/lib/docker/cli-plugins']}))
        env = {'PATH': os.environ.get('PATH', ''), 'HOME': scratch,
               'DOCKER_HOST': args.docker_host, 'DOCKER_CONFIG': str(config)}

        def run(label, command, *, data=None, timeout=300):
            result = subprocess.run(['docker', *command], cwd=ROOT, env=env, input=data,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            (out / (label + '.stdout')).write_bytes(result.stdout)
            (out / (label + '.stderr')).write_bytes(result.stderr)
            checks.append({'check': label, 'passed': result.returncode == 0, 'exitCode': result.returncode})
            if result.returncode != 0:
                raise RuntimeError('Document qualification failed: ' + label)
            return result.stdout

        try:
            base = json.loads(run('pdf-image', ['image', 'inspect', args.pdf_image]))[0]
            if base['Os'] != 'linux' or base['Architecture'] != 'amd64' or base['Config']['User'] != '10001:10001':
                raise ValueError('Use the qualified nonprivileged Linux PDF parser image')
            base_names = ['invoice_document.py', 'invoice_extraction.py', 'structured_output.py',
                          'invoice_parser_cli.py', 'invoice_parser_service.py', 'invoice_parser_identity.py']
            expected = {name: hashlib.sha256((runtime / name).read_bytes()).hexdigest() for name in base_names}
            probe = "import hashlib,json;from pathlib import Path;print(json.dumps({n:hashlib.sha256((Path('/app')/n).read_bytes()).hexdigest()for n in " + repr(base_names) + '}))'
            actual = json.loads(run('pdf-source-hashes', ['run', '--rm', '--network', 'none', '--read-only', base['Id'], 'python', '-I', '-c', probe]))
            if actual != expected:
                raise ValueError('Qualified PDF image code differs from current source; rebuild and qualify it first')
            dockerfile = (runtime / 'enterprise-document.Dockerfile').read_text()
            if lock['javaBuildImage'] not in dockerfile or ('ADD --checksum=sha256:' + lock['sha256'] + ' ' + lock['url']) not in dockerfile:
                raise ValueError('Document Dockerfile differs from reviewed artifact locks')
            context = folder / 'context'
            context.mkdir()
            for name in image_names:
                shutil.copy2(runtime / name, context / name)
            suffix = hashlib.sha256(str(out).encode()).hexdigest()[:16]
            # BuildKit interprets a bare sha256 image ID as a repository name.
            # Give this inspected exact local base a unique owned build reference.
            parent_tag = 'atmem-qualification/pdf-parent:qualification-' + suffix
            run('pdf-parent-tag', ['image', 'tag', base['Id'], parent_tag])
            tag = 'atmem-qualification/enterprise-document:qualification-' + suffix
            run('build', ['build', '--platform', 'linux/amd64', '--network', 'none',
                '--build-arg', 'PDF_PARSER_IMAGE=' + parent_tag, '--file', str(context / 'enterprise-document.Dockerfile'), '--tag', tag, str(context)])
            image = json.loads(run('image', ['image', 'inspect', tag]))[0]
            if image['Os'] != 'linux' or image['Architecture'] != 'amd64' or image['Config']['User'] != '10001:10001':
                raise ValueError('Unexpected document image platform/user')
            assets = {str(p.relative_to(ROOT)): base64.b64encode(p.read_bytes()).decode()
                      for p in sources if p.is_file() and ('fixtures' in p.parts or p.name in {
                          'enterprise_document_linux.py', 'enterprise_parser_rpc_linux.py', 'enterprise_document_composition_linux.py', 'enterprise_document_job_acceptance.py', *composition_names})}
            wrapper = '''import base64,json,sys,unittest
from pathlib import Path,PurePosixPath
root=Path('/tmp/qualification');root.mkdir()
for name,value in json.load(sys.stdin).items():
 path=PurePosixPath(name)
 if path.is_absolute()or '..'in path.parts:raise ValueError('Unsafe test asset')
 target=root.joinpath(*path.parts);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(value,validate=True))
sys.path.insert(0,'/app')
suite=unittest.TestSuite(unittest.defaultTestLoader.discover(str(root/'tests/runtime'),pattern=name)for name in ['enterprise_document_linux.py','enterprise_parser_rpc_linux.py','enterprise_document_composition_linux.py','enterprise_document_job_acceptance.py'])
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.testsRun==26
raise SystemExit(0 if result.wasSuccessful()else 1)
'''
            restricted = ['run', '--rm', '--platform', 'linux/amd64', '--network', 'none', '--read-only',
                '--tmpfs', '/tmp:rw,noexec,nosuid,size=128m', '--memory', '1g', '--cpus', '2',
                '--pids-limit', '128', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true', '-i', image['Id']]
            jar_probe = "import hashlib;from pathlib import Path;assert hashlib.sha256(Path('/app/tika-app.jar').read_bytes()).hexdigest()==" + repr(lock['sha256'])
            run('runtime-jar-integrity', restricted + ['python', '-I', '-c', jar_probe])
            run('native-acceptance', restricted + ['python', '-I', '-c', wrapper], data=json.dumps(assets).encode())
            run('native-java', restricted + ['/opt/java/bin/java', '--version'])
            raw = (ROOT / 'benchmarks/convergence/fixtures/enterprise-documents/policy.docx').read_bytes()
            value = json.loads(run('cli-docx', restricted + ['python', '-I', '/app/enterprise_document_cli.py', 'application/octet-stream'], data=raw))
            if value['status'] != 'ok' or value['document']['sha256'] != hashlib.sha256(raw).hexdigest() or 'twenty days' not in value['document']['text']:
                raise ValueError('Exact CLI document evidence differs')
            # Volumes live in the owned qualification VM (not host bind paths).
            # Each actual file gets a new container, private read-only input and
            # writable result volume. Only fixture setup uses root/CHOWN.
            for filename, mime, expected_text in [('policy.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'twenty days'),
                                                   ('invoice-scan.pdf', 'application/pdf', '42.50')]:
                label = 'mounted-job-' + filename
                folder = 'invoices' if filename.endswith('.pdf') else 'enterprise-documents'
                raw = (ROOT / 'benchmarks/convergence/fixtures' / folder / filename).read_bytes()
                identifier = uuid.uuid4().hex + uuid.uuid4().hex
                metadata = {'format': 'enterprise-document-job-v1', 'requestId': identifier,
                            'sha256': hashlib.sha256(raw).hexdigest(), 'mediaType': mime}
                volumes = ['atmem-document-qualification-' + identifier + '-' + side for side in ['in', 'out']]
                created = []
                try:
                    for name in volumes:
                        run(label + '-volume-' + name[-3:], ['volume', 'create', name]); created.append(name)
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
                    run(label + '-setup', ['run', '--rm', '--platform', 'linux/amd64', '--network', 'none', '--read-only', '--user', '0:0', '--cap-drop', 'ALL',
                        '--cap-add', 'CHOWN', '--security-opt', 'no-new-privileges:true', *mounts, '-i', image['Id'], 'python', '-I', '-c', setup],
                        data=json.dumps({'metadata': metadata, 'raw': base64.b64encode(raw).decode()}).encode())
                    read_only_mounts = [*mounts]
                    read_only_mounts[1] += ',readonly'
                    job = ['run', '--rm', '--platform', 'linux/amd64', '--network', 'none', '--read-only', '--user', '10001:10001',
                           '--tmpfs', '/tmp:rw,noexec,nosuid,size=128m', '--memory', '1g', '--cpus', '2', '--pids-limit', '128',
                           '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true', *read_only_mounts, image['Id'],
                           'python', '-I', '/app/enterprise_document_cli.py', '--job']
                    logged = run(label + '-execute', job)
                    if json.loads(logged) != {'status': 'ok'} or expected_text.encode() in logged:
                        raise ValueError('Mounted parser logs must contain status only')
                    read = "from pathlib import Path;import sys;sys.stdout.buffer.write(Path('/output/result.json').read_bytes())"
                    encoded = run(label + '-collect', ['run', '--rm', '--platform', 'linux/amd64', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
                        '--mount', 'type=volume,source=' + volumes[1] + ',target=/output,readonly', image['Id'], 'python', '-I', '-c', read])
                    # Validate using the current independent app-side consumer.
                    import sys
                    sys.path.insert(0, str(runtime))
                    from enterprise_document_job import result as job_result
                    document = job_result(raw, mime, identifier, encoded)
                    if expected_text not in document['text']: raise ValueError('Mounted document content differs')
                    (out / (label + '-binding.json')).write_text(json.dumps({'requestId': identifier,
                        'inputSha256': metadata['sha256'], 'resultSha256': hashlib.sha256(encoded).hexdigest(),
                        'containerNetwork': 'none', 'inputReadOnly': True, 'separateFreshContainer': True,
                        'privateTextInJobLogs': False}, indent=2) + '\n')
                finally:
                    for name in reversed(created): run(label + '-remove-' + name[-3:], ['volume', 'rm', name])
            changed = [name for name, digest in hashes.items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
            if changed:
                raise ValueError('Qualification sources changed during the run')
            success = True
        finally:
            (out / 'receipt.json').write_text(json.dumps({'recordedAt': datetime.now(timezone.utc).isoformat(),
                'scope': 'owned restricted Linux parser; actual synthetic Office/text/PDF files; no cloud/source-account claim',
                'checks': checks, 'sourceHashes': hashes, 'imageId': image['Id'] if image else None,
                'allChecksPassed': success and bool(checks) and all(check['passed'] for check in checks)}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker-host', required=True)
    parser.add_argument('--pdf-image', required=True)
    parser.add_argument('--out', required=True)
    qualify(parser.parse_args())
