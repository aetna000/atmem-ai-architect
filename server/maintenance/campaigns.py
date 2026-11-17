"""Durable local campaigns separate from single-root snapshot history.

Source updates create a new campaign. Cancellation fences an in-flight executor;
restart never replays unknown work. Portable records grant no remote permission.
"""
from concurrent.futures import ThreadPoolExecutor
import copy
import sqlite3
import threading
import time
from typing import Literal
from uuid import uuid4

from pydantic import Field

from .graph import Root, ModuleBinding, discover
from .models import Record, Identifier, Snapshot, ComputePolicy
from .planner import prepare_campaign, observe_local_release, planner_digest
from .store import Conflict, digest


class Campaign(Record):
    id: Identifier = Field(default_factory=lambda: str(uuid4()))
    tenantId: Identifier
    projectId: Identifier
    actor: Identifier
    revision: int = Field(default=0, ge=0)
    snapshots: list[Snapshot] = Field(min_length=1, max_length=100)
    roots: list[Root] = Field(min_length=1, max_length=300)
    bindings: list[ModuleBinding] = Field(default_factory=list, max_length=1000)
    graph: dict
    status: Literal['discovered', 'checking', 'module_release_pending', 'local_release_checked', 'blocked', 'canceled', 'historical'] = 'discovered'
    phase: str = Field(default='discovered', max_length=200)
    result: dict | None = None
    history: list[dict] = Field(default_factory=list, max_length=20)
    error: str | None = Field(default=None, max_length=300)
    policy: ComputePolicy = Field(default_factory=ComputePolicy)
    requestKey: Identifier | None = None
    operationDigest: str | None = None


class CampaignStore:
    def __init__(self, store):
        self.store = store
        with store.transaction() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS campaigns (
              tenant TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL,
              payload TEXT NOT NULL, PRIMARY KEY(tenant,id));
              CREATE TABLE IF NOT EXISTS campaign_leases (
              tenant TEXT NOT NULL, id TEXT NOT NULL, epoch INTEGER NOT NULL,
              owner TEXT NOT NULL, expires REAL NOT NULL, PRIMARY KEY(tenant,id));''')

    def get(self, tenant, ident):
        with self.store.transaction() as db:
            row = db.execute('SELECT payload FROM campaigns WHERE tenant=? AND id=?', (tenant, ident)).fetchone()
            if row is None:
                raise KeyError('Campaign unavailable')
            return Campaign.model_validate_json(row['payload'])

    def put(self, value, expected=None, *, lease=None):
        value = Campaign.model_validate(value.model_dump())
        if expected is not None:
            value.revision = expected + 1
        payload = value.model_dump_json()
        if len(payload.encode()) > 64_000_000:
            raise ValueError('Campaign exceeds 64 MB; no source was truncated')
        with self.store.transaction() as db:
            if lease is not None:
                row = db.execute('SELECT * FROM campaign_leases WHERE tenant=? AND id=?', (value.tenantId, value.id)).fetchone()
                if row is None or (row['owner'], row['epoch']) != lease or row['expires'] <= time.time():
                    raise Conflict('Campaign executor was fenced or expired')
            if expected is None:
                if value.revision != 0:
                    raise Conflict('New campaign requires revision zero')
                try:
                    db.execute('INSERT INTO campaigns VALUES(?,?,?,?)', (value.tenantId, value.id, 0, payload))
                except sqlite3.IntegrityError:
                    raise Conflict('Campaign already exists') from None
            else:
                count = db.execute('UPDATE campaigns SET revision=?,payload=? WHERE tenant=? AND id=? AND revision=?',
                                   (value.revision, payload, value.tenantId, value.id, expected)).rowcount
                if count != 1:
                    raise Conflict('Campaign changed; reload first')
            db.execute('INSERT INTO audit(tenant,project,kind,revision,at) VALUES(?,?,?,?,?)',
                       (value.tenantId, value.projectId, 'campaign_' + value.status, value.revision, time.time()))
        return value

    def acquire(self, tenant, ident, seconds):
        self.get(tenant, ident)
        owner = str(uuid4())
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM campaign_leases WHERE tenant=? AND id=?', (tenant, ident)).fetchone()
            if row is not None and row['expires'] > time.time():
                raise Conflict('Campaign already has a live executor')
            epoch = 1 if row is None else row['epoch'] + 1
            db.execute('INSERT OR REPLACE INTO campaign_leases VALUES(?,?,?,?,?)', (tenant, ident, epoch, owner, time.time() + seconds))
        return owner, epoch

    def live(self, tenant, ident):
        with self.store.transaction() as db:
            row = db.execute('SELECT expires FROM campaign_leases WHERE tenant=? AND id=?', (tenant, ident)).fetchone()
            return row is not None and row['expires'] > time.time()

    def release(self, tenant, ident, lease):
        with self.store.transaction() as db:
            db.execute('UPDATE campaign_leases SET expires=0 WHERE tenant=? AND id=? AND owner=? AND epoch=?',
                       (tenant, ident, *lease))

    def fence(self, tenant, ident):
        with self.store.transaction() as db:
            db.execute('UPDATE campaign_leases SET epoch=epoch+1,expires=0 WHERE tenant=? AND id=?', (tenant, ident))


class CampaignService:
    def __init__(self, store, worker):
        self.store, self.worker = CampaignStore(store), worker
        self.lock, self.running = threading.RLock(), {}
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='maintenance-campaign')

    def create(self, tenant, project, actor, snapshots, roots, bindings):
        graph = discover(snapshots, roots, bindings)
        return self.store.put(Campaign(tenantId=tenant, projectId=project, actor=actor,
                                      snapshots=snapshots, roots=roots, bindings=bindings, graph=graph))

    def get(self, tenant, ident):
        with self.lock:
            value = self.store.get(tenant, ident)
            if value.status == 'checking' and ident not in self.running and not self.store.live(tenant, ident):
                self.store.fence(tenant, ident)
                value.status, value.phase, value.error = 'blocked', 'execution_unknown', 'Prior execution stopped. Prepare fresh checks.'
                value = self.store.put(value, value.revision)
            if value.result and value.result.get('plannerDigest') != planner_digest() and value.status in {'module_release_pending', 'local_release_checked'}:
                value.status, value.phase = 'historical', 'policy_changed'
                value = self.store.put(value, value.revision)
            return value

    def bind(self, tenant, ident, expected, bindings):
        with self.lock:
            value = self.get(tenant, ident)
            if value.revision != expected or value.status == 'checking':
                raise Conflict('Campaign changed or checks are active')
            value.bindings = bindings
            value.graph = discover(value.snapshots, value.roots, bindings)
            value.result, value.status, value.phase = None, 'discovered', 'discovered'
            value.requestKey, value.operationDigest = None, None
            return self.store.put(value, expected)

    def start(self, tenant, ident, expected, graph_digest, key, confirmed, module=None, release=None):
        with self.lock:
            value = self.get(tenant, ident)
            if self.worker is None:
                raise RuntimeError('Qualified local worker required')
            operation = digest({'graph': graph_digest, 'module': module, 'release': release, 'planner': planner_digest(),
                                'policy': value.policy.model_dump(), 'worker': self.worker.identity})
            if not confirmed or graph_digest != value.graph['digest']:
                raise Conflict('Confirm checks against the current graph')
            if value.requestKey == key:
                if value.operationDigest != operation:
                    raise Conflict('Request key belongs to a different operation')
                return value
            if value.revision != expected or value.status == 'checking' or ident in self.running or len(self.running) >= 2:
                raise Conflict('Campaign changed or compute capacity is occupied')
            previous = value.result
            if len(value.history) >= 20:
                raise ValueError('Campaign history reached its bound; export before creating a fresh campaign')
            if release is not None and (previous is None or value.status not in {'module_release_pending', 'local_release_checked'}):
                raise Conflict('Prepare module and consumer overlays before observing a release')
            lease = self.store.acquire(tenant, ident, value.policy.maxSeconds)
            event = threading.Event()
            if previous is not None:
                value.history = [*value.history, previous]
            value.result = None
            value.status, value.phase, value.error = 'checking', 'queued', None
            value.requestKey, value.operationDigest = key, operation
            value = self.store.put(value, expected, lease=lease)
            self.running[ident] = event
            self.pool.submit(self._run, tenant, ident, lease, event, module, release, previous)
            return value

    def _run(self, tenant, ident, lease, event, module, release, previous):
        def phase(name):
            with self.lock:
                current = self.store.get(tenant, ident)
                if event.is_set() or current.status != 'checking':
                    raise Conflict('Campaign canceled')
                current.phase = name
                self.store.put(current, current.revision, lease=lease)
        try:
            value = self.store.get(tenant, ident)
            if release is None:
                result = prepare_campaign(value.snapshots, value.roots, value.graph, module, self.worker,
                                          value.policy, cancel_event=event, on_progress=phase)
            else:
                phase('released_artifact_checks')
                result = observe_local_release(previous, **release, worker=self.worker, compute_confirmed=True,
                                               cancel_event=event, policy=value.policy)
            with self.lock:
                current = self.store.get(tenant, ident)
                if event.is_set() or current.status != 'checking':
                    return
                current.result = result
                current.status = result['status']
                current.phase = result['status']
                self.store.put(current, current.revision, lease=lease)
        except Exception as error:
            # Only controlled validation messages; raw provider/IO diagnostics are never API errors.
            with self.lock:
                current = self.store.get(tenant, ident)
                if current.status == 'checking':
                    current.status, current.phase = 'blocked', 'checks_failed'
                    current.error = str(error)[:300] if isinstance(error, ValueError) else 'Checks stopped. Review retained evidence and prepare again.'
                    try:
                        self.store.put(current, current.revision, lease=lease)
                    except Conflict:
                        pass
        finally:
            with self.lock:
                self.store.release(tenant, ident, lease)
                self.running.pop(ident, None)

    def cancel(self, tenant, ident, expected):
        with self.lock:
            value = self.get(tenant, ident)
            if value.revision != expected:
                raise Conflict('Campaign changed; reload first')
            self.store.fence(tenant, ident)
            if ident in self.running:
                self.running[ident].set()
            value.status, value.phase = 'canceled', 'canceled'
            return self.store.put(value, expected)

    def partial_merge(self, tenant, ident, expected, merged, current_sources):
        from .planner import invalidate_after_partial_merge, content_digest
        from .inventory import snapshot
        with self.lock:
            value = self.get(tenant, ident)
            if value.revision != expected or value.status != 'local_release_checked' or ident in self.running:
                raise Conflict('Campaign changed or has no checked local release')
            identities = {name: content_digest({f.path: f.text for f in snapshot(files, 'current-consumer').files})
                          for name, files in current_sources.items()}
            value.result = invalidate_after_partial_merge(value.result, merged=merged, current_consumer_digests=identities)
            value.status = value.result['status']
            value.phase = 'fresh_wave_checks_required'
            value.requestKey, value.operationDigest = None, None
            return self.store.put(value, expected)

    def export(self, tenant, ident):
        value = self.get(tenant, ident)
        aggregate = value.model_dump()
        return {'format': 'atmem.infrastructure-campaign', 'schemaVersion': 1, 'aggregate': aggregate, 'sha256': digest(aggregate)}

    def import_record(self, tenant, project, actor, section):
        if set(section) != {'format', 'schemaVersion', 'aggregate', 'sha256'} or section['format'] != 'atmem.infrastructure-campaign' or section['schemaVersion'] != 1 or digest(section['aggregate']) != section['sha256']:
            raise ValueError('Campaign export integrity mismatch')
        value = Campaign.model_validate(copy.deepcopy(section['aggregate']))
        actual = discover(value.snapshots, value.roots, value.bindings)
        if actual != value.graph:
            raise ValueError('Campaign graph differs from retained source')
        value.id, value.tenantId, value.projectId, value.actor = str(uuid4()), tenant, project, actor
        value.revision, value.status, value.phase = 0, 'historical', 'reproduce_checks'
        value.requestKey, value.operationDigest = None, None
        # Retained checks are historical, including attempts kept outside the current result.
        def demote(item):
            if isinstance(item, dict):
                for key, child in item.items():
                    if key == 'status':
                        item[key] = 'historical'
                    else:
                        demote(child)
            elif isinstance(item, list):
                for child in item:
                    demote(child)
        for record in value.history + ([value.result] if value.result else []):
            demote(record)
            record.pop('digest', None)
            record['digest'] = digest(record)
        return self.store.put(value)

    def close(self):
        with self.lock:
            for event in self.running.values():
                event.set()
        self.pool.shutdown(wait=True, cancel_futures=True)
