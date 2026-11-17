"""Migration aggregate in the existing project extension; imports grant nothing."""
import json

from .inventory import SECRET, validate_snapshot
from .models import MigrationProject, identity
from .store import digest
from .patches import apply_candidate, source_map

EXTENSION_VERSION = 1


def export_section(project):
    project = MigrationProject.model_validate(project.model_dump())
    for value in project.snapshots:
        validate_snapshot(value)
    for job in project.jobs:
        if job.candidate is not None:
            sources = {r.binding.sourceDigest for r in job.receipts}
            originals = [s for s in project.snapshots if s.treeDigest in sources]
            if len(originals) != 1:
                raise ValueError('Patch source evidence is missing or ambiguous')
            apply_candidate(source_map(originals[0]), job.candidate)
    raw = project.model_dump()
    if SECRET.search(json.dumps(raw)):
        raise ValueError('Sensitive maintenance content cannot be exported')
    # No token, host path, worker credential, lease or reusable permission exists in the aggregate.
    return {'schemaVersion': EXTENSION_VERSION, 'aggregate': raw, 'sha256': digest(raw)}


def import_section(section, *, tenant, project_id, actor):
    if not isinstance(section, dict) or set(section) != {'schemaVersion', 'aggregate', 'sha256'} or section['schemaVersion'] != EXTENSION_VERSION:
        raise ValueError('Unsupported maintenance extension')
    if section['sha256'] != digest(section['aggregate']):
        raise ValueError('Maintenance export identity mismatch')
    value = MigrationProject.model_validate(section['aggregate'])
    for source in value.snapshots:
        validate_snapshot(source)
    value.id, value.tenantId, value.projectId, value.actor = identity(), tenant, project_id, actor
    value.revision, value.imported = 0, True
    for job in value.jobs:
        job.id = identity()
        job.idempotencyKey = identity()
        job.status, job.phase = 'historical', 'reproduce_checks'
        for receipt in job.receipts:
            receipt.status = 'historical'
    # Re-scan all portable text, including imported diagnostics/candidate changes.
    export_section(value)
    return value
