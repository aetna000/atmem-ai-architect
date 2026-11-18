"""Independent AST/path policy. Patch authors cannot set acceptance verdicts."""
import copy
import difflib
from pathlib import PurePosixPath

from .inventory import AUTOMATION, secret_findings, parse_files, sha, safe_path
from .models import Candidate, Change, Finding
from .store import digest

POLICY_VERSION = 'aws-batch-schema-only-v1'


def unified_diff(before, after, path, *, created=False):
    lines = difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                fromfile='/dev/null' if created else 'a/' + path, tofile='b/' + path)
    return ''.join(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n' for line in lines)


def source_map(snapshot):
    return {f.path: f.text for f in snapshot.files}


def candidate_digest(changes):
    return digest([{'path': c.path, 'operation': c.operation, 'before': c.beforeDigest, 'after': c.afterDigest} for c in changes])


def build_candidate(before, after, *, manual_steps=()):
    if set(before) - set(after) or (set(after) - set(before)) - {'.terraform.lock.hcl'}:
        raise ValueError('Initial recipe can only create the independently generated provider lock')
    changes = []
    for path in sorted(after):
        safe_path(path)
        old = before.get(path, '')
        if old != after[path] or path not in before:
            changes.append(Change(path=path, operation='modify' if path in before else 'create', beforeDigest=sha(old), afterDigest=sha(after[path]),
                                  after=after[path], diff=unified_diff(old, after[path], path, created=path not in before)))
    return Candidate(digest=candidate_digest(changes), changes=changes, manualSteps=list(manual_steps))


def apply_candidate(before, candidate):
    if candidate.digest != candidate_digest(candidate.changes):
        raise ValueError('Patch identity mismatch')
    result = dict(before)
    seen = set()
    for c in candidate.changes:
        safe_path(c.path)
        if (c.path in seen or (c.operation == 'create') != (c.path not in result)
            or sha(result.get(c.path, '')) != c.beforeDigest or sha(c.after) != c.afterDigest):
            raise ValueError('Patch no longer matches its source')
        expected_diff = unified_diff(result.get(c.path, ''), c.after, c.path, created=c.operation == 'create')
        if c.diff != expected_diff:
            raise ValueError('Displayed patch differs from candidate content')
        seen.add(c.path)
        result[c.path] = c.after
    return result


def _expected_semantics(document, *, control=False):
    """Independent semantic oracle; no authoring/source-range code is called."""
    result = copy.deepcopy(document)
    for block in result.get('terraform', []):
        for required in block.get('required_providers', []):
            for provider in required.values():
                if not isinstance(provider, dict) or provider.get('source') != 'hashicorp/aws' or provider.get('version') != '5.100.0':
                    raise ValueError('Exact reviewed provider selection required')
                provider['version'] = '6.0.0'
    if control:
        return result
    for resource in result.get('resource', []):
        for queue in resource.get('aws_batch_job_queue', {}).values():
            if 'compute_environments' in queue:
                values = queue.pop('compute_environments')
                if not isinstance(values, list) or not values or 'compute_environment_order' in queue:
                    raise ValueError('Unsupported queue expression or conflicting block')
                queue['compute_environment_order'] = [{'compute_environment': item, 'order': i}
                                                     for i, item in enumerate(values)]
    return result


def check_patch(before, candidate, *, control=False, approved_lock=None):
    after = apply_candidate(before, candidate)
    findings = secret_findings(after)
    for c in candidate.changes:
        if AUTOMATION.search(c.path) or not (c.path.endswith('.tf') or PurePosixPath(c.path).name == '.terraform.lock.hcl'):
            findings.append(Finding(code='forbidden_path_change', path=c.path, message='This recipe cannot change automation or application files.'))
    parsed_before, parsed_after = parse_files(before), parse_files(after)
    lock_path = '.terraform.lock.hcl'
    if after.get(lock_path) != before.get(lock_path):
        if not approved_lock or after.get(lock_path) != approved_lock:
            findings.append(Finding(code='lock_change_requires_receipt', path=lock_path, message='A provider lock update needs an independent tool receipt.'))
        else:
            providers = parsed_after[lock_path]['semantic'].get('provider', [])
            if len(providers) != 1 or set(providers[0]) != {'registry.terraform.io/hashicorp/aws'} or providers[0]['registry.terraform.io/hashicorp/aws'].get('version') != '6.0.0':
                findings.append(Finding(code='unapproved_lock_selection', path=lock_path, message='The generated lock selected an unapproved provider.'))
    for path in parsed_before:
        if path.endswith('.lock.hcl'):
            continue
        expected = _expected_semantics(parsed_before[path]['semantic'], control=control)
        if expected != parsed_after[path]['semantic']:
            findings.append(Finding(code='semantic_scope_violation', path=path, message='The patch changes configuration outside the reviewed recipe.'))
    return findings
