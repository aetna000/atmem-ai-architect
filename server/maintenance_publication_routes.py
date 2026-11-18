"""Local-only GitHub integration. Developer acceptance gate defaults closed.

Connection tokens are entered only through the interactive CLI/keychain. HTTP
commands accept scoped IDs and exact confirmations, never tokens or arbitrary
GitHub methods, paths, commands or patch bodies.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import sys
import threading
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import Field

from . import maintenance_routes as local, maintenance_campaign_routes as campaigns
from .maintenance.credential_store import KeychainUnavailable
from .maintenance.github_adapter import GitHubBroker, GitHubError
from .maintenance.models import Record, Identifier, Digest
from .maintenance.publication import Publication
from .maintenance.store import Conflict, digest
from .settings import setting

router = APIRouter(prefix='/api/maintenance/github')
_service, _parent = None, None


class Target(Record):
    root: Identifier
    repository: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$')
    connection: Identifier


class Preview(Record):
    projectId: Identifier
    campaignId: Identifier
    wave: str = Field(pattern=r'^(module|consumers)$')
    targets: list[Target] = Field(min_length=1, max_length=30)


class Confirm(Record):
    projectId: Identifier
    previewDigest: Digest
    automationAccepted: bool


class Publish(Record):
    projectId: Identifier
    previewDigest: Digest
    authorizationId: Identifier


class Scope(Record):
    projectId: Identifier


class Reconcile(Scope):
    credentialOverrides: dict[str, Identifier] = Field(default_factory=dict, max_length=30)


class RemoteRelease(Record):
    projectId: Identifier
    expectedProjectRevision: int = Field(ge=0)
    graphDigest: Digest
    computeConfirmed: bool
    connection: Identifier
    repository: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$')
    tag: str = Field(min_length=1, max_length=200)


class PublicationService:
    def __init__(self, parent, broker=None):
        self.core = Publication(parent.store.store, parent, broker or GitHubBroker(parent.store.store))
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='maintenance-publication')
        self.lock, self.running, self.outcomes, self.reviews = threading.RLock(), {}, {}, {}
        with parent.store.store.transaction() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS publication_submissions (
                tenant TEXT NOT NULL, project TEXT NOT NULL, request TEXT NOT NULL,
                preview TEXT NOT NULL, fingerprint TEXT NOT NULL, PRIMARY KEY(tenant,project,request))''')

    def submit(self, tenant, project, preview, authorization, expected_digest, key):
        current_preview = self.core.ledger.preview(tenant, project, preview)
        fingerprint = digest({'preview': preview, 'authorization': authorization, 'digest': expected_digest})
        scope = (tenant, project, preview)
        with self.lock:
            duplicate = False
            with self.core.ledger.store.transaction() as db:
                prior = db.execute('SELECT * FROM publication_submissions WHERE tenant=? AND project=? AND request=?', (tenant, project, key)).fetchone()
                if prior is not None:
                    if prior['fingerprint'] != fingerprint:
                        raise Conflict('Publication request key belongs to different exact actions')
                    duplicate = True
                else:
                    if scope in self.running or len(self.running) >= 4:
                        raise Conflict('Publication capacity is occupied; inspect current work')
                    self.core.ledger._authorization(db, tenant, project, preview, authorization, expected_digest)
                    if current_preview['digest'] != expected_digest:
                        raise Conflict('Exact publication preview changed')
                    db.execute('INSERT INTO publication_submissions VALUES(?,?,?,?,?)', (tenant, project, key, preview, fingerprint))
            if duplicate:
                return self.status(tenant, project, preview)
            self.running[scope] = fingerprint
            self.outcomes.pop(scope, None)
            self.pool.submit(self._run, scope, authorization, expected_digest)
            return {'previewId': preview, 'status': 'queued', 'operations': []}

    def _run(self, scope, authorization, expected_digest):
        tenant, project, preview = scope
        try:
            result = self.core.publish(tenant, project, preview, authorization, expected_digest)
        except (Conflict, PermissionError, GitHubError, KeychainUnavailable, ValueError) as error:
            result = {'status': 'needs_attention', 'detail': str(error)[:300]}
        except Exception:
            result = {'status': 'needs_attention', 'detail': 'Publication stopped. Reconcile recorded actions before continuing.'}
        with self.lock:
            self.outcomes[scope] = result
            self.running.pop(scope, None)

    def review(self, tenant, project, preview):
        self.core.ledger.status(tenant, project, preview)  # Scope check before serving cached immutable metadata.
        scope = (tenant, project, preview)
        with self.lock:
            if scope not in self.reviews:
                value = self.core.ledger.preview(tenant, project, preview)
                self.reviews[scope] = {key: value[key] for key in
                    ['id', 'digest', 'wave', 'createdAt', 'campaign', 'graphDigest', 'resultDigest', 'automation', 'sideEffects', 'permissions']}
                self.reviews[scope]['targets'] = [{key: target[key] for key in
                    ['root', 'repository', 'base', 'baseCommit', 'branch', 'patchDigest', 'files']} for target in value['targets']]
                self.reviews[scope]['actions'] = [{'kind': action['kind'], 'repository': action['target']['repository'],
                    'ref': action['body'].get('ref') or action['target']['branch'], 'expected': action['expected']} for action in value['actions']]
            return self.reviews[scope]

    def status(self, tenant, project, preview):
        value = self.core.ledger.status(tenant, project, preview)
        scope = (tenant, project, preview)
        with self.lock:
            if scope in self.running:
                value['status'] = 'running'
            else:
                value.update(self.outcomes.get(scope, {'status': 'inspect_recorded_actions'}))
        return value

    def close(self):
        with self.lock:
            for tenant, project, preview in self.running:
                self.core.ledger.cancel(tenant, project, preview)
        self.pool.shutdown(wait=True, cancel_futures=True)


def enabled():
    return setting('ENABLE_MAINTENANCE_PUBLICATION') == '1'


def service():
    global _service, _parent
    if not enabled():
        raise HTTPException(503, 'GitHub integration acceptance is pending; local migration workflows remain available.')
    parent = campaigns.service()
    if _service is None or parent is not _parent:
        close()
        _service, _parent = PublicationService(parent), parent
    return _service


def close():
    global _service, _parent
    if _service is not None:
        _service.close()
    _service, _parent = None, None


async def call(operation):
    try:
        return await asyncio.to_thread(operation)
    except KeychainUnavailable:
        raise HTTPException(503, 'Unlock a qualified OS keychain before connecting GitHub.') from None
    except PermissionError as error:
        raise HTTPException(403, str(error)[:300]) from None
    except Conflict as error:
        raise HTTPException(409, str(error)[:300]) from None
    except GitHubError as error:
        raise HTTPException(503, str(error)[:300]) from None
    except KeyError:
        raise HTTPException(404, 'Publication record unavailable') from None
    except (ValueError, TypeError) as error:
        raise HTTPException(422, str(error)[:300]) from None
    except RuntimeError:
        raise HTTPException(503, 'GitHub publication service is unavailable. Inspect its recorded state.') from None


@router.get('/capabilities')
async def capabilities():
    return {'enabled': enabled() and sys.platform=='darwin', 'acceptancePending': True,
            'credentialEntry': 'interactive_cli_keychain_only', 'keychainPlatform': 'macOS', 'remoteAcceptance': 'not_yet_qualified'}


@router.get('/connections')
async def connections(projectId: Identifier = Query()):
    def operation():
        broker = service().core.broker
        with broker.store.transaction() as db:
            rows = db.execute('SELECT id FROM github_connections WHERE tenant=?', (local.TENANT,)).fetchall()
        selected = []
        for row in rows:
            try:
                connection = broker.connection(local.TENANT, projectId, row['id'])
                selected.append(connection.model_dump())
            except PermissionError:
                continue
        return {'connections': selected, 'projectId': projectId}
    return await call(operation)


@router.post('/campaigns/{ident}/preview')
async def preview(ident: Identifier, body: Preview):
    if body.campaignId != ident:
        raise HTTPException(409, 'Campaign identity changed')
    return await call(lambda: service().core.preview(local.TENANT, body.projectId, ident, [t.model_dump(exclude={'schemaVersion'}) for t in body.targets], wave=body.wave))


@router.get('/previews/{ident}/review')
async def review(ident: Identifier, projectId: Identifier = Query()):
    return await call(lambda: service().review(local.TENANT, projectId, ident))


@router.get('/previews/{ident}/export')
async def export(ident: Identifier, projectId: Identifier = Query()):
    return await call(lambda: service().core.ledger.preview(local.TENANT, projectId, ident))


@router.post('/previews/{ident}/authorize')
async def authorize(ident: Identifier, body: Confirm):
    return await call(lambda: service().core.authorize(local.TENANT, body.projectId, ident, body.previewDigest, body.automationAccepted))


@router.post('/previews/{ident}/publish', status_code=202)
async def publish(ident: Identifier, body: Publish, key: Identifier = Header(alias='Idempotency-Key')):
    return await call(lambda: service().submit(local.TENANT, body.projectId, ident, body.authorizationId, body.previewDigest, key))


@router.get('/previews/{ident}')
async def status(ident: Identifier, projectId: Identifier = Query()):
    return await call(lambda: service().status(local.TENANT, projectId, ident))


@router.post('/previews/{ident}/cancel')
async def cancel(ident: Identifier, body: Scope):
    return await call(lambda: (service().core.ledger.cancel(local.TENANT, body.projectId, ident) or service().status(local.TENANT, body.projectId, ident)))


@router.post('/previews/{ident}/reconcile')
async def reconcile(ident: Identifier, body: Reconcile):
    return await call(lambda: service().core.reconcile(local.TENANT, body.projectId, ident, body.credentialOverrides))


@router.post('/campaigns/{ident}/observe-release', status_code=202)
async def release(ident: Identifier, body: RemoteRelease, key: Identifier = Header(alias='Idempotency-Key')):
    return await call(lambda: campaigns.response(service().core.observe_release(local.TENANT, body.projectId, ident,
        expected_revision=body.expectedProjectRevision, graph_digest=body.graphDigest, key=key,
        compute_confirmed=body.computeConfirmed, connection=body.connection, repository=body.repository, tag=body.tag)))


@router.get('/campaigns/{ident}/proposals')
async def proposals(ident: Identifier, projectId: Identifier = Query()):
    return await call(lambda: service().core.poll(local.TENANT, projectId, ident))
