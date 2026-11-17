#!/usr/bin/env python3
"""Reproduce frozen R2 graphs, real offline overlays and simulated release equality."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.maintenance.graph import Root, ModuleBinding, discover, affected_waves
from server.maintenance.inventory import snapshot
from server.maintenance.models import Candidate
from server.maintenance.patches import apply_candidate
from server.maintenance.planner import prepare_campaign, observe_local_release, content_digest, invalidate_after_partial_merge, planner_digest
from server.maintenance.workers import MaintenanceWorker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    fixtures = ROOT / 'tests/maintenance/fixtures/campaign'
    frozen = json.loads((fixtures / 'manifest.json').read_text())
    for path, expected in frozen['files'].items():
        assert hashlib.sha256((fixtures / path).read_bytes()).hexdigest() == expected
    def source(name):
        files = {p.relative_to(fixtures / name).as_posix(): p.read_text() for p in (fixtures / name).rglob('*.tf')}
        return snapshot(files, 'repo-' + name, commit='a' * 40)
    snapshots = [source(name) for name in ['shared', 'consumer-a', 'consumer-b', 'unrelated']]
    roots = [Root(id='root-' + name, snapshotId=s.id) for name, s in zip(['shared', 'consumer-a', 'consumer-b', 'unrelated'], snapshots)]
    bindings = [ModuleBinding(consumer='root-' + name, module='queue' if name == 'consumer-a' else 'archive',
                             source='git::https://example.invalid/shared-batch.git?ref=v1.0.0', target='root-shared',
                             targetTreeDigest=snapshots[0].treeDigest, resolvedCommit='a' * 40) for name in ['consumer-a', 'consumer-b']]
    graph = discover(snapshots, roots, bindings)
    scope = affected_waves(graph, ['root-shared'])
    assert scope['affected'] == sorted('root-' + name for name in frozen['expected']['affected'])
    worker = MaintenanceWorker.from_file(args.config)
    start = time.monotonic()
    campaign = prepare_campaign(snapshots, roots, graph, 'root-shared', worker)
    assert campaign['status'] == 'module_release_pending', campaign
    print('Module/two consumers passed exact overlays', flush=True)
    released = apply_candidate(campaign['moduleBefore'], Candidate.model_validate(campaign['moduleCandidate']))
    options = dict(source='git::https://example.invalid/shared-batch.git?ref=v2.0.0', version=None,
                   resolved_commit='b' * 40, worker=worker, compute_confirmed=True)
    try:
        observe_local_release(campaign, released_files={**released, 'extra.tf': '# different'}, **options)
    except ValueError:
        mismatch = 'blocked'
    else:
        raise RuntimeError('Mismatched release was accepted')
    observed = observe_local_release(campaign, released_files=released, **options)
    remaining = invalidate_after_partial_merge(observed, merged=['root-consumer-a'],
        current_consumer_digests={'root-consumer-b': content_digest(campaign['consumers']['root-consumer-b']['before'])})
    assert remaining['status'] == 'module_release_pending' and not remaining['releaseChecks']
    rechecked = observe_local_release(remaining, released_files=released, **options)
    assert len(rechecked['releaseChecks']) == 1 and rechecked['releaseChecks'][0]['consumer'] == 'root-consumer-b'
    primary_seconds = round(time.monotonic() - start, 3)
    holdout = source('holdout-monorepo')
    held_roots = [Root(id='root-held-module', snapshotId=holdout.id, directory='modules/queue'),
                  Root(id='root-held-ingest', snapshotId=holdout.id, directory='apps/ingest')]
    held_graph = discover([holdout], held_roots)
    held_campaign = prepare_campaign([holdout], held_roots, held_graph, 'root-held-module', worker)
    assert held_campaign['status'] == 'module_release_pending', held_campaign
    print('Distinct monorepo composition passed exact overlays', flush=True)
    materialized = [snapshot({'main.tf': 'terraform { required_providers { aws = { source = "hashicorp/aws", version = "6.0.0" } } }'},
                             f'repo-scale-{i:02}') for i in range(30)]
    scale_roots = [Root(id=f'root-scale-{i:02}', snapshotId=s.id) for i, s in enumerate(materialized)]
    start = time.monotonic()
    scale = discover(materialized, scale_roots)
    seconds = round(time.monotonic() - start, 3)
    assert seconds < 300 and len(scale['nodes']) == 30 and not scale['unknowns']
    output = {'schemaVersion': 1, 'status': 'passed', 'evidenceLevel': 'real_local_offline_container_schema_checks',
              'modelCalls': 0, 'cloudOperations': False, 'remoteWrites': False,
              'plannerDigest': planner_digest(), 'workerIdentity': worker.identity,
              'frozenManifestDigest': hashlib.sha256((fixtures / 'manifest.json').read_bytes()).hexdigest(),
              'primary': campaign, 'heldOutComposition': held_campaign,
              'release': {'observation': 'operator_supplied_local_simulation', 'mismatchedArtifact': mismatch,
                          'matchingReleaseChecks': observed['releaseChecks'], 'partialMergeRechecks': rechecked['releaseChecks']},
              'scale': {'snapshots': 30, 'discoverySeconds': seconds, 'budgetSeconds': 300,
                        'materialization': 'pre-materialized; fetch/clone not measured',
                        'host': platform.platform(), 'machine': platform.machine(), 'python': platform.python_version()},
              'primaryMigrationSeconds': primary_seconds,
              'limits': ['One leaf shared module and direct consumers for the exact reviewed Batch recipe.',
                         'Nested root assets and dependency chains require separate qualification.',
                         'Local release and merge simulations are not remote publication acceptance.',
                         'Actual GitHub release fetching, publication and authorization remain R3 gates.']}
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    print('Campaign qualification passed; 30-snapshot discovery seconds:', seconds)


if __name__ == '__main__':
    main()
