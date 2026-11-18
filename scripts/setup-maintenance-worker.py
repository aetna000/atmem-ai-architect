#!/usr/bin/env python3
"""Build/qualify local maintenance tools. Downloads only pinned public tool artifacts.

No cloud credentials, source repositories, model calls or remote writes are used.
Run with the sidecar Python. Requires an explicitly selected local Docker socket.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import platform
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def write_tool(path, content):
    if path.is_symlink():
        raise RuntimeError('Linked tool cache entry denied')
    if not path.exists() or path.read_bytes() != content:
        path.unlink(missing_ok=True)
        path.write_bytes(content)
    path.chmod(0o555)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--endpoint', required=True, help='Explicit unix:/// local Docker socket')
    parser.add_argument('--output', required=True, type=Path, help='Private operator configuration path')
    args = parser.parse_args()
    if (sys.platform, platform.machine()) != ('darwin', 'arm64'):
        parser.error('Maintenance execution is currently qualified only on macOS arm64 with Linux arm64 Docker containers')
    if not args.endpoint.startswith('unix:///') or not Path(args.endpoint[7:]).is_socket():
        parser.error('Select a running local Docker Unix socket')
    prefix = ['docker', '--host', args.endpoint]
    architecture = subprocess.check_output([*prefix, 'info', '--format', '{{.Architecture}}'], text=True).strip()
    if architecture not in {'aarch64', 'arm64'}:
        parser.error('Only Linux arm64 is currently qualified; other architectures are blocked')
    # Global npm installations may be read-only. Mutable tools belong beside
    # the private operator configuration, never inside the installed package.
    cache = args.output.parent / 'maintenance-tools'
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    context = cache / 'image'
    context.mkdir(exist_ok=True)
    manifest = json.loads((ROOT / 'server/maintenance/catalog/tool-artifacts.json').read_text())
    for name, artifact in manifest['artifacts'].items():
        target = cache / name
        if not target.exists():
            with urllib.request.urlopen(artifact['url'], timeout=120) as response, target.open('wb') as stream:
                while data := response.read(1_000_000):
                    stream.write(data)
        if hashlib.sha256(target.read_bytes()).hexdigest() != artifact['sha256']:
            raise RuntimeError('Tool checksum mismatch; no image built')
        with zipfile.ZipFile(target) as archive:
            if name.startswith('terraform_'):
                binary = context / 'terraform'
                write_tool(binary, archive.read('terraform'))
                licenses = context / 'licenses'
                licenses.mkdir(exist_ok=True)
                for entry in archive.infolist():
                    if 'LICENSE' in entry.filename.upper():
                        (licenses / 'terraform-LICENSE.txt').write_bytes(archive.read(entry))
            else:
                version = name.split('_')[1]
                directory = context / 'mirror/registry.terraform.io/hashicorp/aws' / version / 'linux_arm64'
                directory.mkdir(parents=True, exist_ok=True)
                for entry in archive.infolist():
                    if '/' in entry.filename or entry.filename.startswith('.'):
                        raise RuntimeError('Unexpected official provider archive path')
                    binary = directory / entry.filename
                    write_tool(binary, archive.read(entry))
    runner = ROOT / 'server/maintenance/check_runner.py'
    (context / 'maintenance_check.py').write_bytes(runner.read_bytes())
    (context / 'terraform.rc').write_text('provider_installation {\n filesystem_mirror { path = "/opt/mirror" }\n}\ndisable_checkpoint = true\n')
    base = 'python:3.13.12-slim@sha256:f1927c75e81efd1e091dbd64b6c0ecaa5630b38635a3d1c04034ac636e1f94c8'
    subprocess.run([*prefix, 'pull', base], check=True)
    (context / 'Dockerfile').write_text(f'''FROM {base}
COPY terraform /usr/local/bin/terraform
COPY mirror /opt/mirror
COPY terraform.rc /opt/terraform.rc
COPY maintenance_check.py /opt/maintenance_check.py
COPY licenses /opt/licenses
ENV TF_CLI_CONFIG_FILE=/opt/terraform.rc CHECKPOINT_DISABLE=1 TF_IN_AUTOMATION=1
''')
    subprocess.run([*prefix, 'build', '--network', 'none', '-t', 'atmem-maintenance:local', str(context)], check=True)
    image = subprocess.check_output([*prefix, 'image', 'inspect', 'atmem-maintenance:local', '--format', '{{.Id}}'], text=True).strip()
    from server.maintenance.isolation import qualify
    from server.maintenance.store import digest
    qualification = qualify(args.endpoint, image, 'linux/arm64')
    if qualification['status'] != 'passed':
        raise RuntimeError('Isolation qualification failed; worker not registered')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report_path = args.output.with_suffix('.qualification.json')
    report_path.write_text(json.dumps(qualification, indent=2) + '\n')
    report_path.chmod(0o600)
    config = {'schemaVersion': 1, 'endpoint': args.endpoint, 'platform': 'linux/arm64',
              'imageId': image, 'qualificationDigest': digest(qualification),
              'runnerDigest': hashlib.sha256(runner.read_bytes()).hexdigest()}
    args.output.write_text(json.dumps(config, indent=2) + '\n')
    args.output.chmod(0o600)
    print(json.dumps({'status': 'qualified', 'imageId': image, 'configuration': str(args.output)}))


if __name__ == '__main__':
    main()
