"""Unpack trusted public generation and execute its exact local state probe."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--project', type=Path, required=True)
p.add_argument('--terraform', type=Path, required=True)
p.add_argument('--work-dir', type=Path, required=True)
p.add_argument('--evidence', type=Path, required=True)
a = p.parse_args()
if a.work_dir.exists() or a.evidence.exists():
    p.error('Preserve previous work/evidence and choose fresh directories.')
a.work_dir.mkdir(parents=True)
a.evidence.mkdir(parents=True)
project = json.loads(a.project.read_text())
rendered = subprocess.run(['node', str(ROOT / 'scripts/terraform-render.mjs')], input=json.dumps({'project': project, 'environment': 'staging'}), text=True, capture_output=True, cwd=ROOT, timeout=30)
if rendered.returncode:
    raise ValueError('Trusted generation failed: ' + rendered.stderr)
files = json.loads(rendered.stdout)
quality = json.loads(files['generation-quality.json'])
if quality['fatalFindings']:
    raise ValueError('Independent artifact admission failed')
package = a.work_dir / 'package'
for name, body in files.items():
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name:
        raise ValueError('Unsafe generated path')
    target = package / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body)
hashes = {name: hashlib.sha256(body.encode()).hexdigest() for name, body in files.items()}
before = json.loads(files['state-custody.json'])
helper = package / before['localProbe']['file']
assert hashlib.sha256(helper.read_bytes()).hexdigest() == before['localProbe']['sha256']
result = subprocess.run([sys.executable, '-I', str(helper.resolve()), '--terraform', str(a.terraform.resolve()), '--work-dir', str((a.work_dir / 'fixture').resolve())], env={'PATH': os.getenv('PATH', ''), 'PYTHONDONTWRITEBYTECODE': '1'}, text=True, capture_output=True, timeout=90)
(a.evidence / 'driver.log').write_text(result.stdout + result.stderr)
if result.returncode:
    raise ValueError('Exact emitted local protocol probe failed; preserved driver/private work.')
report = json.loads((a.work_dir / 'fixture/report.json').read_text())
assert report['passed'] and len(report['checks']) == 18 and all(check['passed'] for check in report['checks'])
assert all(command['exitCode'] == command['expectedExitCode'] for command in report['commands'])
assert report['sourceSha256'] == before['localProbe']['sha256']
assert report['scope'] == 'isolated-loopback-http-state-protocol' and report['selectedBackendVerified'] is False
assert (package / 'state-custody.json').read_text() == files['state-custody.json']
assert before['acceptance'] == 'not_verified' and before['migrationAuthorized'] is False
assert before['localProbe']['status'] == 'not_run'
(a.evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
receipt = {'passed': True, 'selectedBackend': before['selection']['backend'], 'selectedBackendVerified': False,
           'helperSha256': report['sourceSha256'], 'artifactDigests': hashes, 'checks': len(report['checks']),
           'projectSha256': hashlib.sha256(a.project.read_bytes()).hexdigest(),
           'boundary': 'Exact unpacked emitted helper, real native clients and synthetic local HTTP/SQLite protocol. Project custody/gates unchanged; no selected-platform, TLS, cloud, migration or application-system acceptance.'}
(a.evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: v for k, v in receipt.items() if k != 'artifactDigests'}))
