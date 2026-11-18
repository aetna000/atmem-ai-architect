"""Versioned aggregate shared by persistence, HTTP and portable project files."""
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

Digest = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]
Identifier = Annotated[str, Field(pattern=r'^[a-zA-Z0-9_-]{8,80}$')]
Text = Annotated[str, Field(min_length=1, max_length=2000)]


def now():
    return datetime.now(timezone.utc).isoformat()


def identity():
    return str(uuid4())


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, validate_assignment=True, allow_inf_nan=False)
    schemaVersion: Literal[1] = 1


class Finding(Record):
    code: Annotated[str, Field(pattern=r'^[a-z_]{3,80}$')]
    path: str = Field(max_length=1000, default='')
    line: int = Field(default=0, ge=0)
    message: Text
    severity: Literal['blocked', 'review', 'information'] = 'blocked'


class SourceFile(Record):
    path: str = Field(min_length=1, max_length=1000)
    text: str = Field(max_length=2_000_000)
    sha256: Digest


class Snapshot(Record):
    id: Identifier = Field(default_factory=identity)
    repositoryId: Identifier
    treeDigest: Digest
    files: list[SourceFile] = Field(max_length=2000)
    createdAt: str = Field(default_factory=now)
    findings: list[Finding] = Field(default_factory=list, max_length=2000)
    # Immutable content identity is authoritative; a moving ref is never a cache key.
    commit: str | None = Field(default=None, max_length=64)


class Binding(Record):
    sourceDigest: Digest
    recipeDigest: Digest
    patchDigest: Digest
    toolDigest: Digest
    policyDigest: Digest
    oracleDigest: Digest


class Receipt(Record):
    id: Identifier = Field(default_factory=identity)
    kind: Literal['baseline', 'control', 'candidate']
    binding: Binding
    artifactDigest: Digest
    status: Literal['passed', 'failed', 'blocked', 'canceled', 'stale', 'historical']
    evidenceLevel: Literal['local_container_schema_check'] = 'local_container_schema_check'
    exitCode: int | None = None
    durationSeconds: float = Field(default=0.0, ge=0, le=1500, multiple_of=.001)
    output: str = Field(default='', max_length=500_000)
    reason: str | None = Field(default=None, max_length=100)
    cleanupConfirmed: bool = False
    createdAt: str = Field(default_factory=now)


class Change(Record):
    operation: Literal['modify', 'create'] = 'modify'
    path: str = Field(min_length=1, max_length=1000)
    beforeDigest: Digest
    afterDigest: Digest
    after: str = Field(max_length=2_000_000)
    diff: str = Field(max_length=4_000_000)


class Candidate(Record):
    digest: Digest
    changes: list[Change] = Field(max_length=2000)
    findings: list[Finding] = Field(default_factory=list, max_length=2000)
    manualSteps: list[Text] = Field(default_factory=list, max_length=100)


class Job(Record):
    id: Identifier = Field(default_factory=identity)
    idempotencyKey: Identifier
    inputDigest: Digest
    status: Literal['queued', 'inventory', 'baseline', 'drafting', 'checking', 'ready_for_review',
                    'blocked', 'failed', 'canceled', 'stale', 'historical'] = 'queued'
    phase: str = Field(default='queued', max_length=80)
    attempt: int = Field(default=0, ge=0, le=3)
    receipts: list[Receipt] = Field(default_factory=list, max_length=30)
    findings: list[Finding] = Field(default_factory=list, max_length=2000)
    candidate: Candidate | None = None
    createdAt: str = Field(default_factory=now)


class ComputePolicy(Record):
    maxAttempts: int = Field(default=3, ge=1, le=3)
    maxSeconds: int = Field(default=1200, ge=1, le=1200)
    maxCostMicros: int = Field(default=5_000_000, ge=0, le=5_000_000)


class MigrationProject(Record):
    id: Identifier = Field(default_factory=identity)
    tenantId: Identifier
    projectId: Identifier
    actor: Identifier
    revision: int = Field(default=0, ge=0)
    name: str = Field(min_length=1, max_length=200)
    createdAt: str = Field(default_factory=now)
    target: Literal['6.0.0'] = '6.0.0'
    recipeId: Literal['aws-batch-queue-v6'] = 'aws-batch-queue-v6'
    snapshots: list[Snapshot] = Field(default_factory=list, max_length=100)
    jobs: list[Job] = Field(default_factory=list, max_length=100)
    policy: ComputePolicy = Field(default_factory=ComputePolicy)
    imported: bool = False

    @model_validator(mode='after')
    def unique_ids(self):
        if len({s.id for s in self.snapshots}) != len(self.snapshots):
            raise ValueError('Duplicate snapshot identity')
        if len({j.idempotencyKey for j in self.jobs}) != len(self.jobs):
            raise ValueError('Duplicate job identity')
        return self
