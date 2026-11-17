#!/usr/bin/env python3
"""Reproduce frozen maintenance controls, patches and clean imports. No remote writes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.maintenance.inventory import snapshot
from server.maintenance.models import ComputePolicy, MigrationProject, Job
from server.maintenance.patches import apply_candidate, source_map
from server.maintenance.portable import export_section, import_section
from server.maintenance.recipes import recipe, recipe_digest
from server.maintenance.store import digest
from server.maintenance.verification import prepare, policy_digest, oracle_digest
from server.maintenance.workers import MaintenanceWorker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    worker = MaintenanceWorker.from_file(args.config)
    fixtures = ROOT / 'tests/maintenance/fixtures'
    frozen = json.loads((fixtures / 'manifest.json').read_text())
    for relative, expected in frozen['cases'].items():
        if hashlib.sha256((fixtures / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Frozen qualification source changed: ' + relative)
    results = {}
    for name in ['baseline', 'holdout', 'baseline-failure', 'dynamic']:
        source = snapshot({'main.tf': (fixtures / name / 'main.tf').read_text()}, 'repository-001')
        status, candidate, receipts, findings = prepare(source, worker, ComputePolicy())
        expected = 'ready_for_review' if name in {'baseline', 'holdout'} else 'blocked'
        if status != expected:
            raise RuntimeError('Qualification failed: ' + name + ' ' + str([f.code for f in findings]))
        if candidate:
            assert [r.status for r in receipts] == ['passed', 'failed', 'passed', 'passed']
            assert receipts[-1].binding.patchDigest == candidate.digest
            # A standard Git patch must apply to a clean copy and yield exactly the checked files.
            with tempfile.TemporaryDirectory(prefix='maintenance-patch-reproduction-') as directory:
                target = Path(directory)
                for file in source.files:
                    path = target / file.path
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(file.text)
                patch = '\n'.join(c.diff for c in candidate.changes).encode()
                subprocess.run(['git', '-C', str(target), 'apply', '--check', '-'], input=patch, check=True, capture_output=True)
                subprocess.run(['git', '-C', str(target), 'apply', '-'], input=patch, check=True, capture_output=True)
                expected_files = apply_candidate(source_map(source), candidate)
                assert all((target / path).read_text() == text for path, text in expected_files.items())
        results[name] = {'status': status, 'source': source.model_dump(),
                         'candidate': candidate.model_dump() if candidate else None,
                         'receipts': [r.model_dump() for r in receipts],
                         'findings': [f.model_dump() for f in findings]}
        print(name, status, flush=True)
    record = results['holdout']
    project = MigrationProject(tenantId='tenant-001', projectId='project-001', actor='actor-001', name='Clean reproduction',
                               snapshots=[record['source']])
    # Pydantic strict aggregate records are validated independently before persistence/import.
    from server.maintenance.models import Snapshot, Candidate, Receipt
    project.snapshots = [Snapshot.model_validate(record['source'])]
    project.jobs = [Job(idempotencyKey='request-001', inputDigest='a' * 64, status='ready_for_review',
                        candidate=Candidate.model_validate(record['candidate']),
                        receipts=[Receipt.model_validate(r) for r in record['receipts']])]
    imported = import_section(json.loads(json.dumps(export_section(project))), tenant='tenant-002', project_id='project-002', actor='actor-002')
    assert imported.jobs[0].status == 'historical'
    status, candidate, receipts, findings = prepare(imported.snapshots[0], worker, ComputePolicy())
    assert status == 'ready_for_review' and candidate.digest == project.jobs[0].candidate.digest
    assert [r.artifactDigest for r in receipts] == [r.artifactDigest for r in project.jobs[0].receipts]
    evidence = {'schemaVersion': 1, 'status': 'passed', 'scope': 'R1 local migration controls, patch application and clean imported reproduction only',
                'evidenceLevel': 'real_local_container_schema_checks', 'cloudOperations': False, 'remoteWrites': False,
                'modelCalls': 0, 'modelSpendMicros': 0, 'recipe': recipe(), 'recipeDigest': recipe_digest(),
                'workerIdentity': worker.identity, 'policyDigest': policy_digest(), 'oracleDigest': oracle_digest(),
                'fixtureManifestDigest': hashlib.sha256((fixtures / 'manifest.json').read_bytes()).hexdigest(),
                'results': results, 'cleanImportReproduction': {'status': status, 'candidateDigest': candidate.digest},
                'releaseStatus': 'not_published', 'limits': ['Linux arm64 local schema checks only.', 'No state, account plan, apply, deployment or remote publication proof.',
                'Current broad regression gates and owner review remain separate release requirements.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + '\n')
    print('Independent local qualification passed:', args.output)


if __name__ == '__main__':
    main()
