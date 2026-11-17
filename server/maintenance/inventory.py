"""Immutable selected source, actual HCL syntax and conservative uncertainty."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

from .models import Finding, Snapshot, SourceFile
from .store import digest

MAX_BYTES = 8_000_000
MAX_FILES = 1000
SENSITIVE_PATH = re.compile(r'(^|/)(\.env[^/]*|[^/]*\.tfvars(?:\.json)?|[^/]*\.tfstate(?:\.[^/]*)?|[^/]*\.tfplan|[^/]*\.pem|[^/]*\.key|\.terraformrc|terraform\.rc|credentials|secrets?[^/]*|id_rsa)$', re.I)
SECRET = re.compile(r'AKIA[0-9A-Z]{16}|(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?i:password|api[_-]?key|client[_-]?secret|access[_-]?key|token)\s*=\s*"[^"\n]{8,}"')
AUTOMATION = re.compile(r'(^|/)(\.github/|\.gitlab-ci[^/]*|atlantis\.(?:ya?ml)|Jenkinsfile|azure-pipelines\.yml|\.circleci/|\.buildkite/)', re.I)


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def safe_path(path):
    if not isinstance(path, str) or not path or len(path) > 1000 or '\\' in path or any(ord(c) < 32 for c in path):
        raise ValueError('Invalid source path')
    p = PurePosixPath(path)
    if p.is_absolute() or '..' in p.parts or str(p) != path or path == '.':
        raise ValueError('Source path must be canonical and relative')
    return path


def secret_findings(files):
    return [Finding(code='sensitive_source', path=path, message='Remove sensitive source before preparing or exporting.')
            for path, text in files.items() if SENSITIVE_PATH.search(path) or SECRET.search(text)]


def snapshot(files, repository_id, *, commit=None):
    if not isinstance(files, dict) or not files or len(files) > MAX_FILES:
        raise ValueError('Select between 1 and 1000 source files')
    total = 0
    for path, text in files.items():
        safe_path(path)
        if not isinstance(text, str) or '\0' in text or len(text.encode()) > 2_000_000:
            raise ValueError('Source must be bounded UTF-8 text')
        total += len(text.encode())
        if total > MAX_BYTES:
            raise ValueError('Selected source exceeds 8 MB; no content was truncated')
        if any(part in {'.git', '.terraform', 'node_modules', '.venv'} for part in PurePosixPath(path).parts):
            raise ValueError('Repository internals and installed dependencies must be excluded')
    if secret_findings(files):
        raise ValueError('Sensitive source denied; remove credentials, tfvars and secret files')
    ordered = [SourceFile(path=path, text=text, sha256=sha(text)) for path, text in sorted(files.items())]
    return Snapshot(repositoryId=repository_id, files=ordered, commit=commit,
                    treeDigest=digest({f.path: f.sha256 for f in ordered}))


def validate_snapshot(value):
    checked = snapshot({f.path: f.text for f in value.files}, value.repositoryId, commit=value.commit)
    if len(checked.files) != len(value.files) or checked.treeDigest != value.treeDigest or any(sha(f.text) != f.sha256 for f in value.files):
        raise ValueError('Snapshot content identity mismatch')
    return checked


def parse_files(files):
    selected = {p: t for p, t in files.items() if p.endswith('.tf') or p.endswith('.lock.hcl')}
    if not selected:
        raise ValueError('Select Terraform HCL files')
    # No source directory, ambient credentials, subprocess shell or HCL evaluation.
    request = json.dumps(selected).encode()
    if len(request) > 16_000_000:
        raise ValueError('Encoded HCL exceeds parser bounds')
    try:
        result = subprocess.run([sys.executable, '-I', str(Path(__file__).with_name('parser_process.py'))],
                                input=request, capture_output=True, timeout=8,
                                env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'})
    except subprocess.TimeoutExpired:
        raise ValueError('HCL parsing exceeded its time budget') from None
    if result.returncode or len(result.stdout) > 32_000_000:
        raise ValueError('HCL parse failed or exceeded supported bounds')
    return json.loads(result.stdout)


def walk(blocks):
    for block in blocks:
        yield block
        yield from walk(block['blocks'])


def inventory(value):
    validate_snapshot(value)
    files = {f.path: f.text for f in value.files}
    parsed = parse_files(files)
    findings = []
    providers, modules, resources = [], [], []
    for path, text in files.items():
        if path.endswith('.tf.json'):
            findings.append(Finding(code='json_hcl_unsupported', path=path, message='JSON HCL needs separate qualification.'))
        if path.endswith('.tftest.hcl') or PurePosixPath(path).name == 'override.tf' or path.endswith('_override.tf'):
            findings.append(Finding(code='override_or_test_unsupported', path=path, message='Terraform overrides and test files require separate qualification.'))
        if AUTOMATION.search(path):
            findings.append(Finding(code='automation_detected', path=path, severity='review', message='Repository automation may execute after remote writes.'))
    for path, document in parsed.items():
        for block in walk(document['blocks']):
            kind, labels = block['type'], block['labels']
            expected_labels = {'resource': 2, 'data': 2, 'module': 1, 'provider': 1,
                               'variable': 1, 'output': 1, 'terraform': 0, 'locals': 0}.get(kind)
            if expected_labels is not None and len(labels) != expected_labels:
                findings.append(Finding(code='invalid_block_shape', path=path, line=block['line'],
                                        message='Correct the Terraform block labels before preparing changes.'))
                continue
            if kind in {'provisioner', 'backend', 'cloud', 'import', 'removed', 'ephemeral'} or (kind == 'data' and labels and labels[0] in {'external', 'http'}):
                findings.append(Finding(code='executable_construct', path=path, line=block['line'],
                                        message='This execution construct is outside the reviewed check profile.'))
            if kind == 'module':
                attrs = {a['name']: a['expression'] for a in block['attributes']}
                modules.append({'path': path, 'name': labels[0], 'source': attrs.get('source'),
                                'version': attrs.get('version'), 'resolution': 'unknown', 'line': block['line']})
            if kind == 'resource':
                resources.append({'path': path, 'type': labels[0], 'name': labels[1], 'line': block['line']})
            if kind == 'required_providers':
                providers.append({'path': path, 'attributes': block['attributes']})
        # Unknown provider-defined functions or import sources cannot be interpreted as safe.
        if any('::' in f for f in document['functions']):
            findings.append(Finding(code='provider_function_unknown', path=path, message='Provider functions require a qualified execution policy.'))
    return {'snapshotDigest': value.treeDigest, 'parser': 'python-hcl2/7.3.1', 'files': parsed,
            'providers': providers, 'modules': modules, 'resources': resources,
            'findings': [f.model_dump() for f in findings]}
