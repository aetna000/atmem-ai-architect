"""Measure the Terraform apply emulator against the AWS fixture corpus.

Each fixture under tests/terraform-emulator/aws runs the full lifecycle with the
real Terraform CLI and provider. The result is a measured coverage matrix per
resource type. A type is `qualified` only when it applied, converged and was
destroyed in a passing fixture; nothing is inferred for types outside the corpus.

    python3 scripts/qualify-terraform-emulator.py [fixture ...] [--write]
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'tests/terraform-emulator/aws'
COVERAGE = ROOT / 'docs/terraform-emulator-aws-coverage.json'


def run_fixture(name, python, terraform, cache, evidence, timeout):
    report_path = evidence / (name + '.json')
    environment = {'PATH': os.getenv('PATH', ''), 'HOME': str(evidence), 'ATMEM_ARCHITECT_TERRAFORM_BIN': terraform}
    command = [python, '-I', str(ROOT / 'server/terraform_emulator.py'), '--dir', str(CORPUS / name), '--provider-cache', cache, '--report', str(report_path), '--timeout', str(timeout)]
    try:
        subprocess.run(command, env=environment, capture_output=True, text=True, timeout=timeout * 8 + 120)
        report = json.loads(report_path.read_text())
    except (subprocess.TimeoutExpired, OSError, ValueError) as error:
        report = {'status': 'failed', 'message': f'Fixture run produced no report: {type(error).__name__}', 'resources': [], 'stages': []}
    print(json.dumps({'fixture': name, 'status': report['status'], 'seconds': report.get('seconds'), 'applied': sum(bool(r.get('applied')) for r in report.get('resources', [])), 'planned': len(report.get('resources', []))}), flush=True)
    return name, report


def classify(report):
    """Per-type outcome of one fixture. Only a fully passing lifecycle qualifies."""
    stages = {stage['name']: stage for stage in report.get('stages', [])}
    drift = {address.split('.')[0] for address in stages.get('Convergence plan', {}).get('drift', [])}
    lifecycle_passed = report['status'] == 'passed'
    types = {}
    for resource in report.get('resources', []):
        kind = resource['type']
        if kind == 'terraform_data':
            continue
        entry = types.setdefault(kind, {'instances': 0, 'applied': 0, 'sdkVerified': 0, 'errors': []})
        entry['instances'] += 1
        entry['applied'] += bool(resource.get('applied'))
        checks = resource.get('checks')
        entry['sdkVerified'] += bool(checks) and all(check['passed'] for check in checks)
        if resource.get('error'):
            entry['errors'].append({'emulatorGap': bool(resource.get('emulatorGap')), 'error': resource['error'][:400]})
    for kind, entry in types.items():
        if entry['applied'] < entry['instances']:
            entry['result'] = 'emulator-gap' if entry['errors'] and all(e['emulatorGap'] for e in entry['errors']) else 'apply-failed' if entry['errors'] else 'not-reached'
        elif kind in drift:
            entry['result'] = 'drift'
        elif lifecycle_passed:
            entry['result'] = 'qualified'
        else:
            entry['result'] = 'applied-in-failing-fixture'
        if not entry['errors']:
            del entry['errors']
    return types


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixtures', nargs='*')
    parser.add_argument('--write', action='store_true', help='Update docs/terraform-emulator-aws-coverage.json')
    parser.add_argument('--reports-from', type=Path, help='Summarize existing fixture receipts without rerunning Terraform; retains their individual implementation digests')
    parser.add_argument('--timeout', type=int, default=900, help='Per-command deadline; AWS provider OpenSearch creation includes an unconditional 600s wait')
    parser.add_argument('--jobs', type=int, default=2)
    options = parser.parse_args()
    python = os.getenv('ATMEM_ARCHITECT_TERRAFORM_EMULATOR_PYTHON') or str(ROOT / '.local/terraform-emulator-runtime/bin/python')
    terraform = os.getenv('ATMEM_ARCHITECT_TERRAFORM_BIN') or shutil.which('terraform', path=str(ROOT / '.venv/bin') + os.pathsep + os.getenv('PATH', ''))
    cache = os.getenv('ATMEM_ARCHITECT_PROVIDER_CACHE') or str(ROOT / '.local/provider-cache')
    if not options.reports_from and (not Path(python).is_file() or not terraform):
        raise SystemExit('Install the runtime (scripts/setup-terraform-emulator.py) and Terraform 1.7+ first.')
    names = options.fixtures or sorted(path.name for path in CORPUS.iterdir() if (path / 'main.tf').is_file())
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace(':', '-')
    evidence = ROOT / '.local/terraform-emulation' / ('corpus-' + stamp)
    evidence.mkdir(parents=True)
    if options.reports_from:
        reports = {name: json.loads((options.reports_from / (name + '.json')).read_text()) for name in names}
        for name, report in reports.items():
            (evidence / (name + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    else:
        with ThreadPoolExecutor(max_workers=options.jobs) as pool:
            reports = dict(pool.map(lambda name: run_fixture(name, python, terraform, cache, evidence, options.timeout), names))

    fixtures, types = {}, {}
    first = next((r for r in reports.values() if r.get('terraform')), {})
    for name in names:
        report = reports[name]
        failed = [{'name': s['name'], 'output': (s.get('output') or '')[-600:], **({'drift': s['drift']} if s.get('drift') else {})} for s in report.get('stages', []) if s['status'] != 'passed']
        fixtures[name] = {
            'status': report['status'], 'message': report.get('message'), 'seconds': report.get('seconds'),
            'implementationDigests': report.get('backend', {}).get('implementationDigests', {}),
            'artifactDigest': report.get('artifactDigest'),
            'reportDigest': hashlib.sha256((evidence / (name + '.json')).read_bytes()).hexdigest() if (evidence / (name + '.json')).is_file() else None,
            'evidenceFile': str((evidence / (name + '.json')).relative_to(ROOT)),
            'apiCalls': report.get('apiCalls', {}).get('total', 0),
            'notImplemented': report.get('apiCalls', {}).get('notImplemented', []),
            **({'failedStages': failed} if failed else {}),
        }
        for kind, entry in classify(report).items():
            types.setdefault(kind, {})[name] = entry
    order = ['qualified', 'drift', 'applied-in-failing-fixture', 'emulator-gap', 'apply-failed', 'not-reached']
    matrix = {}
    for kind, by_fixture in sorted(types.items()):
        best = min((entry['result'] for entry in by_fixture.values()), key=order.index)
        matrix[kind] = {'result': best, 'sdkReadBack': any(entry['sdkVerified'] for entry in by_fixture.values()), 'fixtures': by_fixture}
    counts = {result: sum(entry['result'] == result for entry in matrix.values()) for result in order}
    coverage = {
        'kind': 'terraform-apply-emulator-coverage', 'provider': 'aws', 'measuredAt': stamp,
        'terraform': first.get('terraform'), 'backend': first.get('backend'),
        'provenance': 'Per-fixture implementation and artifact digests identify measured revisions; the top-level backend describes the first receipt only.',
        'meaning': 'qualified = applied, converged and destroyed in a fully passing fixture on this emulator. It is not AWS behavior. Types absent from this file are unmeasured.',
        'summary': {'fixtures': len(names), 'fixturesPassed': sum(f['status'] == 'passed' for f in fixtures.values()), 'resourceTypes': len(matrix), **counts},
        'fixtures': fixtures, 'resourceTypes': matrix,
    }
    (evidence / 'coverage.json').write_text(json.dumps(coverage, indent=1) + '\n')
    if options.write:
        COVERAGE.write_text(json.dumps(coverage, indent=1) + '\n')
    print(json.dumps(coverage['summary']))
    print('Evidence:', evidence)
    return 0 if all(r['status'] == 'passed' for r in reports.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
