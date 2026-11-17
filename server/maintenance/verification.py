"""Independent bounded baseline/control/candidate checks with complete input binding."""
import hashlib
import json
from pathlib import Path
import threading
import time

from . import inventory as inventory_module, patches
from .inventory import sha
from .inventory import parse_files
from .models import Binding, Finding, Receipt
from .patches import apply_candidate, build_candidate, check_patch, source_map
from .recipes import applicability, propose, recipe_digest
from .store import digest


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def policy_digest():
    return digest({'policy': file_digest(patches.__file__), 'inventory': file_digest(inventory_module.__file__),
                   'parser': file_digest(Path(__file__).with_name('parser_process.py')),
                   'egress': file_digest(Path(__file__).with_name('egress.py')),
                   'generalContext': file_digest(Path(__file__).parents[1] / 'engineering_contexts.py'),
                   'generalWorkspace': file_digest(Path(__file__).parents[1] / 'engineering_routes.py'),
                   'officialArchives': file_digest(Path(__file__).parent / 'catalog/aws-6-archive-checksums.json')})


def portable_lock(tool_lock):
    """Preserve the independently computed h1 and include pinned official archive hashes.

    An unpacked Linux mirror only generates one platform's h1. Without the
    official zh values the resulting patch would break other installation targets.
    """
    parsed = parse_files({'.terraform.lock.hcl': tool_lock})['.terraform.lock.hcl']
    providers = parsed['semantic'].get('provider', [])
    if len(providers) != 1 or set(providers[0]) != {'registry.terraform.io/hashicorp/aws'}:
        raise ValueError('Unreviewed provider lock source')
    selection = providers[0]['registry.terraform.io/hashicorp/aws']
    if selection.get('version') != '6.0.0' or not selection.get('hashes') or not all(h.startswith('h1:') for h in selection['hashes']):
        raise ValueError('Expected independently generated target h1')
    metadata = json.loads((Path(__file__).parent / 'catalog/aws-6-archive-checksums.json').read_text())
    hashes = sorted(set(selection['hashes']) | {'zh:' + value for value in metadata['archiveHashes'].values()})
    block = next(b for b in parsed['blocks'] if b['type'] == 'provider')
    attr = next(a for a in block['attributes'] if a['name'] == 'hashes')
    replacement = '[\n' + ''.join('    ' + json.dumps(h) + ',\n' for h in hashes) + '  ]'
    return tool_lock[:attr['expressionStart']] + replacement + tool_lock[attr['expressionEnd']:]


def oracle_digest():
    return file_digest(__file__)


def input_digest(snapshot, worker, policy):
    return digest({'source': snapshot.treeDigest, 'commit': snapshot.commit, 'repository': snapshot.repositoryId,
                   'recipe': recipe_digest(), 'tool': worker.identity,
                   'policy': policy_digest(), 'oracle': oracle_digest(), 'budget': policy.model_dump()})


class Stopped(RuntimeError):
    pass


def prepare(snapshot, worker, policy, *, cancel_event=None, on_progress=None):
    """Pure orchestrator; controller owns status and lease commits. No original paths exist here."""
    started = time.monotonic()
    cancel_event = cancel_event or threading.Event()
    expired = threading.Event()
    receipts = []
    candidate = None

    def progress(phase):
        if cancel_event.is_set():
            raise Stopped('time_budget_exhausted' if expired.is_set() else 'canceled')
        if time.monotonic() - started >= policy.maxSeconds:
            cancel_event.set()
            raise Stopped('time_budget_exhausted')
        if on_progress:
            on_progress(phase, list(receipts), candidate)

    def check(files, kind, patch):
        progress(kind)
        # Fixed worker timeout is additionally bounded by the remaining whole-job time.
        def deadline():
            expired.set()
            cancel_event.set()
        timer = threading.Timer(max(.01, policy.maxSeconds - (time.monotonic() - started)), deadline)
        timer.start()
        try:
            result = worker.check(files, kind=kind, cancel_event=cancel_event)
        finally:
            timer.cancel()
        binding = Binding(sourceDigest=snapshot.treeDigest, recipeDigest=recipe_digest(),
                          patchDigest=patch.digest if patch else digest([]), toolDigest=worker.identity,
                          policyDigest=policy_digest(), oracleDigest=oracle_digest())
        receipt = Receipt(kind=kind, binding=binding, artifactDigest=result['artifactSha256'],
                          status='canceled' if result.get('reason') == 'cancelled' else result['status'],
                          exitCode=result['exitCode'], durationSeconds=float(result['durationSeconds']), output=result['output'],
                          reason=result.get('reason'), cleanupConfirmed=result.get('cleanupConfirmed', False))
        receipts.append(receipt)
        if cancel_event.is_set():
            raise Stopped('time_budget_exhausted' if expired.is_set() else 'canceled')
        return result

    try:
        progress('inventory')
        _, findings = applicability(snapshot)
        if findings:
            return 'blocked', candidate, receipts, findings
        before = source_map(snapshot)
        baseline = check(before, 'baseline', None)
        if baseline['status'] != 'passed':
            return 'blocked', candidate, receipts, [Finding(code='baseline_failed', message='Repair the existing baseline before upgrading. Original failures are retained.')]
        control, findings = propose(snapshot, control=True)
        if findings or check_patch(before, control, control=True):
            return 'blocked', candidate, receipts, [Finding(code='control_scope_failed', message='The version-only control failed independent policy checks.')]
        control_result = check(apply_candidate(before, control), 'control', control)
        # A process failure/timeout is not proof of the intended provider break.
        report = control_result.get('report')
        actual_break = False
        if control_result['status'] == 'failed' and report and len(report.get('steps', [])) == 2:
            try:
                validation = json.loads(report['steps'][1]['stdout'])
                actual_break = validation['valid'] is False and any(
                    d.get('summary') == 'Unsupported argument' and 'compute_environments' in d.get('detail', '')
                    for d in validation.get('diagnostics', []))
            except (ValueError, KeyError, TypeError):
                pass
        if not actual_break:
            return 'blocked', candidate, receipts, [Finding(code='breaking_control_not_demonstrated', message='The intended provider schema break was not demonstrated.')]
        progress('drafting')
        candidate, findings = propose(snapshot)
        if findings:
            return 'blocked', candidate, receipts, findings
        findings = check_patch(before, candidate)
        if findings:
            return 'blocked', candidate, receipts, findings
        # The deterministic adapter has one attempt; no model/repair loop or egress is implicit.
        preliminary = check(apply_candidate(before, candidate), 'candidate', candidate)
        if preliminary['status'] != 'passed':
            return 'blocked', candidate, receipts, [Finding(code='candidate_failed', message='The candidate failed independent schema checks. Review retained diagnostics.')]
        generated_lock = preliminary['report'].get('lock')
        if not generated_lock:
            return 'blocked', candidate, receipts, [Finding(code='provider_lock_missing', message='The independently generated provider lock is missing.')]
        approved_lock = portable_lock(generated_lock)
        after = apply_candidate(before, candidate)
        after['.terraform.lock.hcl'] = approved_lock
        candidate = build_candidate(before, after, manual_steps=candidate.manualSteps)
        findings = check_patch(before, candidate, approved_lock=approved_lock)
        if findings:
            return 'blocked', candidate, receipts, findings
        final = check(after, 'candidate', candidate)
        if final['status'] != 'passed' or final['report'].get('lock') != approved_lock:
            return 'blocked', candidate, receipts, [Finding(code='locked_candidate_failed', message='Exact candidate files and lock did not reproduce.')]
        queue = final['report']['queueSchema']['block']
        if 'compute_environments' in queue.get('attributes', {}) or 'compute_environment_order' not in queue.get('block_types', {}):
            return 'blocked', candidate, receipts, [Finding(code='target_schema_mismatch', message='The independently observed provider schema does not match this recipe.')]
        progress('ready_for_review')
        return 'ready_for_review', candidate, receipts, []
    except Stopped as error:
        status = 'canceled' if str(error) == 'canceled' else 'blocked'
        return status, candidate, receipts, [Finding(code=str(error), message='Preparation stopped. No original repository was changed.')]
