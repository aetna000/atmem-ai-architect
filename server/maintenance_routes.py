"""Local-owner HTTP adapter. Hosted routing does not expose these capabilities."""
import asyncio
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException
from pydantic import Field

from .maintenance.models import Record, Identifier, Digest
from .maintenance.recipes import recipe, recipe_digest
from .maintenance.service import Service
from .maintenance.store import Store, Conflict
from .maintenance.workers import MaintenanceWorker
from .settings import home, setting

router = APIRouter(prefix='/api/maintenance')
_service = None
_registration = None
TENANT = 'local-owner'
ACTOR = 'local-owner'


class Create(Record):
    projectId: Identifier
    name: str = Field(min_length=1, max_length=200)
    files: dict[str, str] = Field(min_length=1, max_length=1000)


class Revise(Record):
    expectedProjectRevision: int = Field(ge=0)
    files: dict[str, str] | None = None


class Prepare(Revise):
    sourceDigest: Digest
    recipeDigest: Digest
    computeConfirmed: bool


class Cancel(Record):
    expectedProjectRevision: int = Field(ge=0)


class Import(Record):
    projectId: Identifier
    section: dict


def service():
    global _service, _registration
    # Registration is operator-owned, never an HTTP field or a model decision.
    root = home()
    config = Path(setting('MAINTENANCE_WORKER_CONFIG') or root / 'maintenance-worker.json')
    stamp = (str(root), str(config), config.stat().st_mtime_ns if config.is_file() else None)
    if _service is None or stamp != _registration:
        if _service is not None:
            _service.close()
        worker = None
        if config.is_file():
            try:
                worker = MaintenanceWorker.from_file(config)
            except (ValueError, RuntimeError, OSError):
                # Unqualified execution must not disable read-only inventory/export.
                pass
        _service = Service(Store(root / 'maintenance.sqlite'), worker)
        _registration = stamp
    return _service


def close():
    global _service, _registration
    if _service:
        _service.close()
    _service, _registration = None, None


def response(project, **extra):
    return {'requestId': str(uuid4()), 'revision': project.revision, 'status': 'available',
            'aggregate': project.model_dump(), 'recipe': recipe(), 'recipeDigest': recipe_digest(), **extra}


async def call(function):
    try:
        return await asyncio.to_thread(function)
    except Conflict as error:
        raise HTTPException(409, str(error)) from None
    except KeyError:
        raise HTTPException(404, 'Maintenance project unavailable') from None
    except (ValueError, TypeError) as error:
        # Validation messages are controlled locally; no raw tool/provider errors escape.
        raise HTTPException(422, str(error)[:300]) from None
    except RuntimeError:
        raise HTTPException(503, 'Configure and qualify the local maintenance worker first.') from None


@router.get('/capabilities')
async def capabilities():
    def read():
        value = service()
        return {'requestId': str(uuid4()), 'status': 'available' if value.worker else 'setup_required',
                'localOnly': True, 'recipe': recipe(), 'recipeDigest': recipe_digest(),
                'modelCalls': False, 'publication': False, 'deployment': False}
    return await call(read)


@router.post('/projects')
async def create(request: Create):
    return await call(lambda: response(service().create(TENANT, request.projectId, ACTOR, request.name, request.files)))


@router.get('/projects/{project_id}')
async def get(project_id: Identifier):
    return await call(lambda: response(service().get(TENANT, project_id)))


@router.post('/projects/{project_id}/inventory')
async def inspect(project_id: Identifier, request: Revise):
    def read():
        project, report = service().inventory(TENANT, project_id, request.expectedProjectRevision, request.files)
        return response(project, inventory=report)
    return await call(read)


@router.post('/projects/{project_id}/prepare', status_code=202)
async def prepare(project_id: Identifier, request: Prepare, idempotency_key: Identifier = Header(alias='Idempotency-Key')):
    def start():
        if request.files is not None:
            raise ValueError('Replace source through inventory, then confirm its new digest')
        project, job = service().start(TENANT, project_id, expected_revision=request.expectedProjectRevision,
                                     source_digest=request.sourceDigest, recipe=request.recipeDigest,
                                     key=idempotency_key, compute_confirmed=request.computeConfirmed)
        return response(project, jobId=job.id)
    return await call(start)


@router.get('/jobs/{job_id}')
async def job(job_id: Identifier, projectId: Identifier):
    def read():
        project = service().get(TENANT, projectId)
        found = next((j for j in project.jobs if j.id == job_id), None)
        if found is None:
            raise KeyError('Job unavailable')
        return response(project, job=found.model_dump())
    return await call(read)


@router.post('/projects/{project_id}/jobs/{job_id}/cancel')
async def cancel(project_id: Identifier, job_id: Identifier, request: Cancel):
    return await call(lambda: response(service().cancel(TENANT, project_id, job_id, request.expectedProjectRevision)))


@router.get('/projects/{project_id}/export')
async def export(project_id: Identifier):
    return await call(lambda: service().export(TENANT, project_id))


@router.post('/projects/import')
async def import_project(request: Import):
    return await call(lambda: response(service().import_project(request.section, tenant=TENANT, project_id=request.projectId, actor=ACTOR)))
