"""Local campaign API; no repository network access or publication permissions."""
from uuid import uuid4
from fastapi import APIRouter, Header
from pydantic import Field

from . import maintenance_routes as local
from .maintenance.campaigns import CampaignService
from .maintenance.graph import Root, ModuleBinding
from .maintenance.inventory import snapshot
from .maintenance.models import Record, Identifier, Digest

router = APIRouter(prefix='/api/maintenance/campaigns')
_service, _parent = None, None


class SelectedRepository(Record):
    repositoryId: Identifier
    commit: str | None = Field(default=None, pattern=r'^(?:[a-f0-9]{40}|[a-f0-9]{64})$')
    files: dict[str, str] = Field(min_length=1, max_length=1000)
    # Explicit roots, not host paths. IDs remain stable through the campaign.
    roots: dict[Identifier, str] = Field(min_length=1, max_length=300)


class CreateCampaign(Record):
    projectId: Identifier
    repositories: list[SelectedRepository] = Field(min_length=1, max_length=100)


class BindCampaign(Record):
    expectedProjectRevision: int = Field(ge=0)
    bindings: list[ModuleBinding] = Field(max_length=1000)


class PrepareCampaign(Record):
    expectedProjectRevision: int = Field(ge=0)
    graphDigest: Digest
    computeConfirmed: bool
    module: Identifier


class ReleasedModule(Record):
    files: dict[str, str] = Field(min_length=1, max_length=1000)
    source: str = Field(min_length=1, max_length=2000)
    version: str | None = Field(default=None, max_length=200)
    resolvedCommit: str = Field(pattern=r'^(?:[a-f0-9]{40}|[a-f0-9]{64})$')


class ObserveRelease(Record):
    expectedProjectRevision: int = Field(ge=0)
    graphDigest: Digest
    computeConfirmed: bool
    release: ReleasedModule


class PartialMerge(Record):
    expectedProjectRevision: int = Field(ge=0)
    merged: list[Identifier] = Field(min_length=1, max_length=300)
    currentSources: dict[Identifier, dict[str, str]] = Field(max_length=300)


class ImportCampaign(Record):
    projectId: Identifier
    section: dict


def service():
    global _service, _parent
    parent = local.service()
    if parent is not _parent:
        close()
        _service, _parent = CampaignService(parent.store, parent.worker), parent
    return _service


def close():
    global _service, _parent
    if _service:
        _service.close()
    _service, _parent = None, None


def response(value):
    return {'requestId': str(uuid4()), 'revision': value.revision, 'aggregate': value.model_dump()}


@router.post('')
async def create(body: CreateCampaign):
    def operation():
        selected, roots = [], []
        if len({r.repositoryId for r in body.repositories}) != len(body.repositories):
            raise ValueError('Select each repository materialization once')
        for repository in body.repositories:
            source = snapshot(repository.files, repository.repositoryId, commit=repository.commit)
            selected.append(source)
            roots.extend(Root(id=ident, snapshotId=source.id, directory=directory) for ident, directory in repository.roots.items())
        return response(service().create(local.TENANT, body.projectId, local.ACTOR, selected, roots, []))
    return await local.call(operation)


@router.post('/import')
async def import_record(body: ImportCampaign):
    return await local.call(lambda: response(service().import_record(local.TENANT, body.projectId, local.ACTOR, body.section)))


@router.get('/{ident}')
async def get(ident: Identifier):
    return await local.call(lambda: response(service().get(local.TENANT, ident)))


@router.get('/{ident}/export')
async def export(ident: Identifier):
    return await local.call(lambda: service().export(local.TENANT, ident))


@router.post('/{ident}/bindings')
async def bind(ident: Identifier, body: BindCampaign):
    return await local.call(lambda: response(service().bind(local.TENANT, ident, body.expectedProjectRevision, body.bindings)))


@router.post('/{ident}/prepare', status_code=202)
async def prepare(ident: Identifier, body: PrepareCampaign, key: Identifier = Header(alias='Idempotency-Key')):
    return await local.call(lambda: response(service().start(local.TENANT, ident, body.expectedProjectRevision, body.graphDigest,
                                                           key, body.computeConfirmed, module=body.module)))


@router.post('/{ident}/release', status_code=202)
async def release(ident: Identifier, body: ObserveRelease, key: Identifier = Header(alias='Idempotency-Key')):
    observed = {'released_files': body.release.files, 'source': body.release.source, 'version': body.release.version,
                'resolved_commit': body.release.resolvedCommit}
    return await local.call(lambda: response(service().start(local.TENANT, ident, body.expectedProjectRevision, body.graphDigest,
                                                           key, body.computeConfirmed, release=observed)))


@router.post('/{ident}/cancel')
async def cancel(ident: Identifier, body: local.Cancel):
    return await local.call(lambda: response(service().cancel(local.TENANT, ident, body.expectedProjectRevision)))


@router.post('/{ident}/partial-merge')
async def partial_merge(ident: Identifier, body: PartialMerge):
    return await local.call(lambda: response(service().partial_merge(local.TENANT, ident, body.expectedProjectRevision,
                                                                    body.merged, body.currentSources)))
