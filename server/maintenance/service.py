"""Local aggregate orchestration. Persistence is durable; unknown executions are never replayed."""
from concurrent.futures import ThreadPoolExecutor
import threading

from .budget import Budget
from .inventory import snapshot, inventory
from .models import MigrationProject, Job, Finding, identity
from .portable import export_section, import_section
from .recipes import recipe_digest
from .store import Conflict
from .verification import input_digest, prepare

ACTIVE = {'queued', 'inventory', 'baseline', 'drafting', 'checking'}


class Service:
    def __init__(self, store, worker=None):
        self.store, self.worker = store, worker
        self.budget = Budget(store)
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='maintenance')
        self.lock = threading.RLock()
        self.running = {}

    def create(self, tenant, project_id, actor, name, files):
        value = snapshot(files, identity())
        project = MigrationProject(tenantId=tenant, projectId=project_id, actor=actor, name=name, snapshots=[value])
        # Parser/policy findings are evidence, not instructions or source rewriting.
        inventory(value)
        return self.store.create(project)

    def get(self, tenant, project_id):
        with self.lock:
            project = self.store.get(tenant, project_id)
            changed = False
            for job in project.jobs:
                if job.status in ACTIVE and job.id not in self.running:
                    job.status, job.phase = 'blocked', 'execution_unknown'
                    job.findings.append(Finding(code='execution_unknown', message='Prior execution stopped unexpectedly. Inspect evidence before starting new work.'))
                    self.store.fence(tenant, project_id)
                    changed = True
                elif job.status == 'ready_for_review' and (self.worker is None or job.inputDigest != input_digest(project.snapshots[-1], self.worker, project.policy)):
                    job.status, job.phase = 'stale', 'reproduce_checks'
                    for receipt in job.receipts:
                        receipt.status = 'stale'
                    changed = True
            if changed:
                return self.store.save(project, project.revision)
            return project

    def inventory(self, tenant, project_id, expected_revision, files=None):
        with self.lock:
            project = self.get(tenant, project_id)
            if project.revision != expected_revision:
                raise Conflict('Project changed; reload first')
            if files is not None:
                if any(job.status in ACTIVE for job in project.jobs):
                    raise Conflict('Cancel preparation before replacing source')
                if len(project.snapshots) >= 100:
                    raise ValueError('Snapshot retention limit reached; export before creating a new project')
                fresh = snapshot(files, project.snapshots[-1].repositoryId)
                retained = next((s for s in project.snapshots if s.treeDigest == fresh.treeDigest), fresh)
                project.snapshots = [s for s in project.snapshots if s.treeDigest != fresh.treeDigest] + [retained]
                for job in project.jobs:
                    if job.status != 'historical':
                        job.status, job.phase = 'stale', 'source_changed'
                        for receipt in job.receipts:
                            receipt.status = 'stale'
                project = self.store.save(project, project.revision)
            return project, inventory(project.snapshots[-1])

    def start(self, tenant, project_id, *, expected_revision, source_digest, recipe, key, compute_confirmed):
        with self.lock:
            project = self.get(tenant, project_id)
            if self.worker is None:
                raise RuntimeError('Register a qualified local maintenance worker before preparing changes')
            fingerprint = input_digest(project.snapshots[-1], self.worker, project.policy)
            if not compute_confirmed or source_digest != project.snapshots[-1].treeDigest or recipe != recipe_digest():
                raise Conflict('Confirm local checks against the current source and recipe')
            for existing in project.jobs:
                if existing.idempotencyKey == key:
                    if existing.inputDigest != fingerprint:
                        raise Conflict('Request key belongs to different source or policy')
                    return project, existing
            if project.revision != expected_revision:
                raise Conflict('Project changed; reload first')
            if any(j.status in ACTIVE for j in project.jobs) or len(self.running) >= 4:
                raise Conflict('Preparation capacity is occupied; wait or cancel current work')
            if len(project.jobs) >= 100:
                raise ValueError('Project job retention limit reached; export evidence before starting a new project')
            job = Job(idempotencyKey=key, inputDigest=fingerprint)
            # This exact deterministic adapter makes no model requests and incurs no model spend.
            self.budget.reserve(tenant, project_id, 'deterministic-local', job.id, fingerprint, 0,
                                tenant_limit=0, project_limit=0, owner_limit=0)
            owner = identity()
            epoch = self.store.acquire(tenant, project_id, owner, seconds=project.policy.maxSeconds)
            project.jobs.append(job)
            try:
                project = self.store.save(project, project.revision, lease=(owner, epoch))
            except BaseException:
                self.store.release(tenant, project_id, owner, epoch)
                self.budget.settle(tenant, job.id, 0)
                raise
            event = threading.Event()
            self.running[job.id] = event
            self.pool.submit(self._run, project, job.id, owner, epoch, event)
            return project, job

    def _run(self, project, job_id, owner, epoch, event):
        tenant, project_id = project.tenantId, project.projectId

        def update(phase, receipts, candidate):
            with self.lock:
                current = self.store.get(tenant, project_id)
                job = next(j for j in current.jobs if j.id == job_id)
                if job.status in {'canceled', 'stale'}:
                    event.set()
                    raise Conflict('Job no longer current')
                job.phase = phase
                job.status = phase if phase in {'inventory', 'baseline', 'drafting'} else 'checking'
                job.receipts, job.candidate, job.attempt = receipts, candidate, 1
                self.store.save(current, current.revision, lease=(owner, epoch))

        try:
            status, candidate, receipts, findings = prepare(project.snapshots[-1], self.worker, project.policy,
                                                            cancel_event=event, on_progress=update)
            with self.lock:
                current = self.store.get(tenant, project_id)
                job = next(j for j in current.jobs if j.id == job_id)
                if job.status == 'canceled' or event.is_set():
                    status = 'canceled'
                job.status = job.phase = status
                job.candidate, job.receipts, job.findings = candidate, receipts, findings
                self.store.save(current, current.revision, lease=(owner, epoch))
        except (Conflict, KeyError):
            # A canceled/deleted/stale aggregate or fenced lease must never be overwritten.
            event.set()
        except Exception:
            with self.lock:
                try:
                    current = self.store.get(tenant, project_id)
                    job = next(j for j in current.jobs if j.id == job_id)
                    if job.status != 'canceled':
                        job.status, job.phase = 'failed', 'worker_failed'
                        job.findings = [Finding(code='worker_failed', message='The local worker failed. Inspect registration and retained check evidence.')]
                        self.store.save(current, current.revision, lease=(owner, epoch))
                except (Conflict, KeyError):
                    pass
        finally:
            with self.lock:
                self.store.release(tenant, project_id, owner, epoch)
                self.budget.settle(tenant, job_id, 0)
                self.running.pop(job_id, None)

    def cancel(self, tenant, project_id, job_id, expected_revision):
        with self.lock:
            project = self.get(tenant, project_id)
            if project.revision != expected_revision:
                raise Conflict('Project changed; reload before canceling')
            job = next((j for j in project.jobs if j.id == job_id), None)
            if job is None:
                raise KeyError('Job unavailable')
            if job.status not in ACTIVE:
                return project
            event = self.running.get(job_id)
            if event:
                event.set()
            self.store.fence(tenant, project_id)
            job.status, job.phase = 'canceled', 'canceled'
            return self.store.save(project, project.revision)

    def export(self, tenant, project_id):
        return export_section(self.get(tenant, project_id))

    def import_project(self, section, *, tenant, project_id, actor):
        return self.store.create(import_section(section, tenant=tenant, project_id=project_id, actor=actor))

    def close(self):
        with self.lock:
            for event in self.running.values():
                event.set()
        self.pool.shutdown(wait=False, cancel_futures=True)
