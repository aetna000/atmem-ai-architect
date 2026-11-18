"""Offline coordinated migration: exact module overlays and explicit release observation.

This adapter supports one leaf shared module and direct consumers for the reviewed
AWS Batch recipe. Release observations here are local operator simulations; R3
must independently fetch and authenticate remote releases before publication.
"""
import copy
import hashlib
import json
from pathlib import Path
import threading
import time

from .graph import affected_waves
from .inventory import AUTOMATION, parse_files, snapshot, inventory
from .models import ComputePolicy
from .patches import source_map, apply_candidate, build_candidate, check_patch
from .store import digest
from .verification import prepare, portable_lock, policy_digest
from .recipes import recipe_digest


def planner_digest():
    return digest({'planner': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'graph': hashlib.sha256(Path(__file__).with_name('graph.py').read_bytes()).hexdigest(),
                   'policy': policy_digest(), 'recipe': recipe_digest()})


def content_digest(files):
    return digest({path: hashlib.sha256(text.encode()).hexdigest() for path, text in sorted(files.items())})


def root_files(source, directory):
    prefix = '' if directory == '.' else directory + '/'
    selected = {path[len(prefix):]: text for path, text in source_map(source).items() if path.startswith(prefix)}
    if any('/' in path and (not AUTOMATION.search(path) or path.endswith(('.tf', '.tf.json', '.tftest.hcl', '.lock.hcl'))) for path in selected):
        raise ValueError('Nested root assets require a separately qualified campaign layout')
    return selected


def _replace_sources(files, substitutions):
    after = dict(files)
    for path, document in parse_files(files).items():
        edits = []
        for block in document['blocks']:
            if block['type'] != 'module' or len(block['labels']) != 1 or block['labels'][0] not in substitutions:
                continue
            source, version = substitutions[block['labels'][0]]
            attrs = {a['name']: a for a in block['attributes']}
            if 'source' not in attrs:
                raise ValueError('Module source no longer matches the graph')
            for name, value in [('source', source), ('version', version)]:
                if name in attrs:
                    attr = attrs[name]
                    if value is None:
                        # A registry version cannot be retained on a local check path.
                        edits.append((attr['start'], attr['end'], ''))
                    else:
                        edits.append((attr['expressionStart'], attr['expressionEnd'], json.dumps(value)))
                elif value is not None:
                    raise ValueError('Adding a registry version requires a separately reviewed transform')
        for start, end, replacement in sorted(edits, reverse=True):
            after[path] = after[path][:start] + replacement + after[path][end:]
    return after


def consumer_candidate(files):
    """Only the pinned provider requirement changes; no resource/interface guesses."""
    after = dict(files)
    count = 0
    for path, document in parse_files(files).items():
        if path.endswith('.lock.hcl'):
            continue
        for resource in document['semantic'].get('resource', []):
            if 'aws_batch_job_queue' in resource:
                raise ValueError('Consumer-owned Batch queues require a separate coordinated recipe')
        edits = []
        for block in document['blocks']:
            if block['type'] != 'terraform':
                continue
            for required in block['blocks']:
                if required['type'] != 'required_providers':
                    continue
                for attr in required['attributes']:
                    members = {m['name']: m for m in attr.get('members', [])}
                    if members.get('source', {}).get('expression') != '"hashicorp/aws"' or members.get('version', {}).get('expression') != '"5.100.0"':
                        raise ValueError('Consumer requires the exact reviewed provider selection')
                    version = members['version']
                    edits.append((version['start'], version['end'], '"6.0.0"'))
                    count += 1
        for start, end, replacement in sorted(edits, reverse=True):
            after[path] = after[path][:start] + replacement + after[path][end:]
    if not count:
        raise ValueError('Consumer provider requirement is missing')
    candidate = build_candidate(files, after)
    if check_patch(files, candidate, control=True):
        raise ValueError('Independent consumer semantic scope check failed')
    return candidate


def overlay(files, module_files, edges):
    artifact = content_digest(module_files)
    prefix = '.atmem-modules/' + artifact
    projected = _replace_sources(files, {e['module']: ('./' + prefix, None) for e in edges})
    if any(path.startswith('.atmem-modules/') for path in files):
        raise ValueError('Reserved validation overlay namespace is already present')
    return {**projected, **{prefix + '/' + path: text for path, text in module_files.items()}}, artifact


def _expected_break(result):
    try:
        check = json.loads(result['report']['steps'][1]['stdout'])
        return result['status'] == 'failed' and check['valid'] is False and any(
            d.get('summary') == 'Unsupported argument' and 'compute_environments' in d.get('detail', '')
            for d in check.get('diagnostics', [])) and result.get('cleanupConfirmed') is True
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def _check(worker, files, kind, bindings, cancel_event, deadline):
    if cancel_event.is_set() or time.monotonic() >= deadline:
        raise ValueError('Campaign canceled or compute budget exhausted')
    timer = threading.Timer(max(.01, deadline - time.monotonic()), cancel_event.set)
    timer.start()
    try:
        result = worker.check(files, kind=kind, cancel_event=cancel_event)
    finally:
        timer.cancel()
    receipt = {'kind': kind, 'graphDigest': bindings['graphDigest'],
               'consumer': bindings['consumer'], 'consumerPatchDigest': bindings['consumerPatchDigest'],
               'moduleArtifactDigest': bindings['moduleArtifactDigest'], 'overlayDigest': content_digest(files),
               'workerIdentity': worker.identity, 'plannerDigest': planner_digest(),
               'status': result['status'], 'cleanupConfirmed': result.get('cleanupConfirmed', False),
               'exitCode': result.get('exitCode'), 'durationSeconds': result.get('durationSeconds'),
               'output': result.get('output', ''), 'artifactDigest': result.get('artifactSha256')}
    if cancel_event.is_set():
        raise ValueError('Campaign canceled or compute budget exhausted')
    return result, receipt


def _locked_target_passed(result, lock):
    report = result.get('report') or {}
    queue = report.get('queueSchema', {}).get('block', {})
    return (result['status'] == 'passed' and result.get('cleanupConfirmed') is True and
            report.get('lock') == lock and 'compute_environments' not in queue.get('attributes', {}) and
            'compute_environment_order' in queue.get('block_types', {}))


def prepare_campaign(snapshots, roots, graph, changed_module, worker, policy=None, *, cancel_event=None, on_progress=None):
    policy = policy or ComputePolicy()
    cancel_event = cancel_event or threading.Event()
    deadline = time.monotonic() + policy.maxSeconds
    scope = affected_waves(graph, [changed_module])
    if scope['status'] != 'discovered':
        raise ValueError('Resolve graph unknowns and cycles before preparing a campaign')
    root_map, source_map_by_id = {r.id: r for r in roots}, {s.id: s for s in snapshots}
    # Reconstruct the graph independently; caller-supplied source must match all
    # frozen declarations, not merely an unchanged graph digest string.
    from .graph import discover, ModuleBinding
    rebuilt = discover(snapshots, roots, [ModuleBinding.model_validate(b) for b in graph['bindings']])
    if rebuilt['digest'] != graph['digest']:
        raise ValueError('Campaign source changed; rediscover dependencies')
    if any(e['consumer'] == changed_module for e in graph['edges']):
        raise ValueError('This adapter requires a leaf shared module')
    consumers = set(scope['affected']) - {changed_module}
    if not consumers or any(e['consumer'] in consumers and e['dependency'] != changed_module for e in graph['edges']):
        raise ValueError('This adapter requires direct consumers of one shared module')
    def files(ident):
        root = root_map[ident]
        return root_files(source_map_by_id[root.snapshotId], root.directory)
    if on_progress:
        on_progress('module_checks')
    module_before = files(changed_module)
    module_source = snapshot(module_before, 'campaign-module')
    status, patch, receipts, findings = prepare(module_source, worker, policy, cancel_event=cancel_event)
    if status != 'ready_for_review':
        return {'schemaVersion': 1, 'status': 'blocked', 'module': changed_module, 'graphDigest': graph['digest'],
                'findings': [f.model_dump() for f in findings], 'moduleReceipts': [r.model_dump() for r in receipts]}
    module_after = apply_candidate(module_before, patch)
    module_control = dict(module_before)
    # The consumer's 6.0 requirement cannot install alongside a module's exact 5.100.
    # Bump only module provider requirements for the intended schema-failure control.
    from .recipes import propose
    control, denied = propose(module_source, control=True)
    if denied:
        raise ValueError('Module control is unavailable')
    module_control = apply_candidate(module_before, control)
    proposals, checks = {}, []
    for consumer in sorted(consumers):
        if on_progress:
            on_progress('consumer_checks:' + consumer)
        before = files(consumer)
        candidate = consumer_candidate(before)
        after = apply_candidate(before, candidate)
        edges = [e for e in graph['edges'] if e['consumer'] == consumer]
        bindings = {'graphDigest': graph['digest'], 'consumer': consumer, 'consumerPatchDigest': candidate.digest}
        for kind, consumer_files, module_files in [('baseline', before, module_before),
                                                   ('control', after, module_control), ('candidate', after, module_after)]:
            projected, artifact = overlay(consumer_files, module_files, edges)
            result, receipt = _check(worker, projected, kind, {**bindings, 'moduleArtifactDigest': artifact}, cancel_event, deadline)
            checks.append(receipt)
            if (kind == 'control' and not _expected_break(result)) or (kind != 'control' and
                (result['status'] != 'passed' or not result.get('cleanupConfirmed'))):
                return {'schemaVersion': 1, 'status': 'blocked', 'module': changed_module, 'graphDigest': graph['digest'],
                        'findings': [{'code': 'consumer_check_failed', 'consumer': consumer, 'kind': kind}], 'checks': checks}
            if kind == 'candidate':
                after['.terraform.lock.hcl'] = portable_lock(result['report']['lock'])
                candidate = build_candidate(before, after)
                if check_patch(before, candidate, control=True, approved_lock=after['.terraform.lock.hcl']):
                    raise ValueError('Independent final consumer patch scope failed')
                projected, artifact = overlay(after, module_after, edges)
                final, receipt = _check(worker, projected, 'candidate', {**bindings, 'consumerPatchDigest': candidate.digest,
                                        'moduleArtifactDigest': artifact}, cancel_event, deadline)
                checks.append(receipt)
                if not _locked_target_passed(final, after['.terraform.lock.hcl']):
                    return {'schemaVersion': 1, 'status': 'blocked', 'module': changed_module, 'graphDigest': graph['digest'],
                            'findings': [{'code': 'final_consumer_check_failed', 'consumer': consumer}], 'checks': checks}
        proposals[consumer] = {'before': before, 'candidate': candidate.model_dump(), 'edges': edges}
    value = {'schemaVersion': 1, 'status': 'module_release_pending', 'evidenceLevel': 'local_exact_module_overlay',
             'graphDigest': graph['digest'], 'plannerDigest': planner_digest(), 'workerIdentity': worker.identity,
             'module': changed_module, 'moduleBefore': module_before, 'moduleCandidate': patch.model_dump(),
             'moduleArtifactDigest': content_digest(module_after), 'moduleReceipts': [r.model_dump() for r in receipts],
             'consumers': proposals, 'checks': checks, 'waves': scope['waves'], 'modelCalls': 0, 'remoteWrites': False}
    value['digest'] = digest(value)
    return value


def observe_local_release(campaign, *, released_files, source, version, resolved_commit, worker, compute_confirmed,
                          cancel_event=None, policy=None):
    """Operator-supplied local simulation, not proof that a remote tag exists."""
    from .models import Candidate
    if campaign.get('digest') != digest({k: v for k, v in campaign.items() if k != 'digest'}):
        raise ValueError('Campaign identity mismatch')
    if campaign.get('status') not in {'module_release_pending', 'local_release_checked'} or not compute_confirmed:
        raise ValueError('Confirm checks against the exact supplied release artifact')
    if campaign['plannerDigest'] != planner_digest() or campaign['workerIdentity'] != worker.identity:
        raise ValueError('Campaign policy or worker changed; prepare fresh evidence')
    checked = snapshot(released_files, 'released-module', commit=resolved_commit)
    if not resolved_commit or len(resolved_commit) not in {40, 64} or any(c not in '0123456789abcdef' for c in resolved_commit):
        raise ValueError('An immutable released revision is required')
    # Full file-set/byte equality, including lock; hashes never substitute for a fetch.
    expected = apply_candidate(campaign['moduleBefore'], Candidate.model_validate(campaign['moduleCandidate']))
    if source_map(checked) != expected or content_digest(released_files) != campaign['moduleArtifactDigest']:
        raise ValueError('Released module differs from the tested candidate')
    if not isinstance(source, str) or not source or '${' in source or source.startswith(('./', '../', '/')):
        raise ValueError('Select a concrete released module source')
    cancel_event = cancel_event or threading.Event()
    deadline = time.monotonic() + (policy or ComputePolicy()).maxSeconds
    result = copy.deepcopy(campaign)
    result.pop('digest')
    result['release'] = {'source': source, 'version': version, 'resolvedCommit': resolved_commit,
                         'artifactDigest': content_digest(released_files), 'observation': 'operator_supplied_local_simulation'}
    result['releaseChecks'] = []
    for consumer, proposal in sorted(result['consumers'].items()):
        if consumer in set(result.get('simulatedMergedConsumers', [])) | set(result.get('observedMergedConsumers', [])):
            continue
        before = proposal['before']
        after = apply_candidate(before, Candidate.model_validate(proposal['candidate']))
        after = _replace_sources(after, {e['module']: (source, version) for e in proposal['edges']})
        snapshot(after, 'released-consumer')  # Reapply source bounds and secret exclusion.
        patch = build_candidate(before, after)
        # Independent semantic oracle: provider-only proposal plus exact module-source
        # substitutions; no arbitrary resource/interface mutation is accepted.
        previous = parse_files(apply_candidate(before, Candidate.model_validate(proposal['candidate'])))
        observed = parse_files(after)
        for path, document in previous.items():
            semantics = copy.deepcopy(document['semantic'])
            for item in semantics.get('module', []):
                for name in [e['module'] for e in proposal['edges']]:
                    if name in item:
                        item[name]['source'] = source
                        if 'version' in item[name]:
                            if version is None:
                                del item[name]['version']
                            else:
                                item[name]['version'] = version
            if semantics != observed[path]['semantic']:
                raise ValueError('Released-reference patch exceeds the reviewed semantic scope')
        projected, artifact = overlay(after, released_files, proposal['edges'])
        check, receipt = _check(worker, projected, 'candidate', {'graphDigest': result['graphDigest'], 'consumer': consumer,
                                 'consumerPatchDigest': patch.digest, 'moduleArtifactDigest': artifact}, cancel_event, deadline)
        result['releaseChecks'].append(receipt)
        if not _locked_target_passed(check, after['.terraform.lock.hcl']):
            result['status'] = 'blocked'
            result['findings'] = [{'code': 'released_consumer_check_failed', 'consumer': consumer}]
            result['digest'] = digest(result)
            return result
        proposal['releasedCandidate'] = patch.model_dump()
    result['status'] = 'local_release_checked'
    result['digest'] = digest(result)
    return result


def invalidate_after_partial_merge(campaign, *, merged, current_consumer_digests):
    """Local operator simulation. Remaining waves lose all prior check readiness.

    Fresh materialized consumer source digests must match before rechecking. A
    changed source requires a new campaign; original patches are never rebased by
    this function. R3 must independently observe real remote commits and merges.
    """
    if campaign.get('digest') != digest({k: v for k, v in campaign.items() if k != 'digest'}):
        raise ValueError('Campaign identity mismatch')
    if campaign.get('status') != 'local_release_checked':
        raise ValueError('Check a matching release before recording a simulated merge')
    consumers = set(campaign['consumers'])
    already = set(campaign.get('simulatedMergedConsumers', []))
    if not merged or not set(merged) <= consumers or len(set(merged)) != len(merged):
        raise ValueError('Select known merged consumers once')
    delivered = already | set(merged)
    remaining = consumers - delivered
    if not remaining or set(current_consumer_digests) != remaining:
        raise ValueError('Supply fresh source identities for every remaining consumer')
    result = copy.deepcopy(campaign)
    result.pop('digest')
    result['simulatedMergedConsumers'] = sorted(delivered)
    result['remainingConsumerDigests'] = current_consumer_digests
    result['releaseChecks'] = []
    changed = False
    for consumer in sorted(remaining):
        changed |= current_consumer_digests[consumer] != content_digest(result['consumers'][consumer]['before'])
        result['consumers'][consumer].pop('releasedCandidate', None)
        for check in result['checks']:
            if check['consumer'] == consumer:
                check['status'] = 'stale'
    result['status'] = 'blocked' if changed else 'module_release_pending'
    result['findings'] = [{'code': 'consumer_source_changed' if changed else 'fresh_wave_checks_required',
                           'remaining': sorted(remaining), 'remoteObservation': False}]
    result['digest'] = digest(result)
    return result
