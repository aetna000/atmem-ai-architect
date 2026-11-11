"""Project-scoped artifact checks: durable evidence, independently of HTTP/model jobs.

One local supervisor owns this SQLite adapter. Hosted deployments need transactional
leases and a separately qualified worker/store. Neither validator selection nor a
passed command substitutes for independent requirement/system acceptance.
"""
import asyncio
from dataclasses import asdict, dataclass
import hashlib
import json
import threading
import uuid
from .engineering_sessions import SessionError
from .local_validation import ValidationSpec


@dataclass(frozen=True)
class RegisteredValidator:
    label: str
    spec: ValidationSpec

    def __post_init__(self):
        if not isinstance(self.label,str) or not self.label.strip() or len(self.label)>120:
            raise ValueError('An explicit validator label is required')


def registered_validators(entries):
    """Parse server-operator configuration, never browser/model-provided commands."""
    if not isinstance(entries,list):raise ValueError('Validator configuration must be a list')
    result={}
    for entry in entries:
        if not isinstance(entry,dict) or set(entry)-{'id','label','image','command','platform','timeoutSeconds'}:
            raise ValueError('Unrecognized validator registration')
        if not isinstance(entry.get('command'),list):raise ValueError('Register a validator argument vector')
        spec=ValidationSpec(entry.get('id',''),entry.get('image',''),tuple(entry['command']),
            platform=entry.get('platform','linux/amd64'),timeout_seconds=entry.get('timeoutSeconds',60))
        if spec.name in result:raise ValueError('Validator IDs must be unique')
        result[spec.name]=RegisteredValidator(entry.get('label',''),spec)
    return result


class ValidationJobs:
    def __init__(self, store, artifacts, worker, validators):
        self.store,self.artifacts,self.worker=store,artifacts,worker
        self.validators=dict(validators)
        if any(key!=value.spec.name for key,value in self.validators.items()):
            raise ValueError('Validator IDs must match their registered contract')
        self.db=store.db
        self.db.execute('''CREATE TABLE IF NOT EXISTS artifact_validation_jobs (
            id TEXT PRIMARY KEY, session TEXT NOT NULL, artifact TEXT NOT NULL,
            artifact_sha256 TEXT NOT NULL, validator TEXT NOT NULL, label TEXT NOT NULL,
            contract_sha256 TEXT NOT NULL, spec TEXT NOT NULL, state TEXT NOT NULL,
            result TEXT)''')
        with self.db:
            self.db.execute("UPDATE artifact_validation_jobs SET state='recovery_required' WHERE state IN ('queued','running')")
        self.tasks={};self.cancellations={};self.semaphore=asyncio.Semaphore(2);self.closed=False

    def catalog(self):
        return [{'id':key,'label':value.label,'evidenceLevel':'local_container_check',
                 'contractSha256':self._contract(value)[0] if self.worker else None} for key,value in self.validators.items()]

    def _contract(self,registered):
        registration={'spec':asdict(registered.spec),'workerIdentity':self.worker.identity_digest}
        digest=hashlib.sha256(json.dumps({**registration,'policy':self.worker.policy_digest},sort_keys=True).encode()).hexdigest()
        return digest,registration

    def _row(self,scope,session,job):
        self.store.get(scope,session)
        row=self.db.execute('SELECT * FROM artifact_validation_jobs WHERE id=? AND session=?',(job,session)).fetchone()
        if row is None:raise SessionError('This check is unavailable for the project and session')
        return dict(row)

    @staticmethod
    def _public(row):
        return {'id':row['id'],'sessionId':row['session'],'artifactId':row['artifact'],
            'artifactSha256':row['artifact_sha256'],'validatorId':row['validator'],'label':row['label'],
            'contractSha256':row['contract_sha256'],'state':row['state'],
            'result':json.loads(row['result']) if row['result'] else None,
            'acceptance':'not_established_by_local_check'}

    def get(self,scope,session,job):return self._public(self._row(scope,session,job))

    def list(self,scope,session,artifact):
        self.store.get(scope,session)
        # Artifact ownership is checked without moving its potentially large bytes.
        if not self.db.execute('SELECT 1 FROM engineering_artifacts WHERE id=? AND session=?',(artifact,session)).fetchone():
            raise SessionError('Artifact is unavailable for this project and session')
        rows=self.db.execute('SELECT * FROM artifact_validation_jobs WHERE session=? AND artifact=? ORDER BY rowid',(session,artifact)).fetchall()
        return [self._public(dict(row)) for row in rows]

    def _settle(self,job,result):
        with self.db:
            self.db.execute("UPDATE artifact_validation_jobs SET state='finished',result=? WHERE id=?",(json.dumps(result,allow_nan=False),job))

    async def start(self,scope,session,artifact,validator,*,retry=False):
        if self.closed:raise SessionError('The local check supervisor is closing')
        if self.worker is None:raise SessionError('Local artifact checks are not configured on this server')
        self.store.get(scope,session)
        registered=self.validators.get(validator)
        if registered is None:raise SessionError('This validator is not registered by the server operator')
        manifest,content=self.artifacts.get(scope,session,artifact)
        digest=hashlib.sha256(content).hexdigest()
        if digest!=manifest['sha256']:raise SessionError('Stored artifact bytes do not match their receipt')
        contract,registration=self._contract(registered)
        prior=self.db.execute('''SELECT * FROM artifact_validation_jobs WHERE session=? AND artifact=?
            AND contract_sha256=? ORDER BY rowid DESC LIMIT 1''',(session,artifact,contract)).fetchone()
        if prior:
            row=dict(prior)
            if row['state']!='finished' or not retry:return self._public(row)
        if self.db.execute("SELECT 1 FROM artifact_validation_jobs WHERE session=? AND artifact=? AND state='recovery_required'",(session,artifact)).fetchone():
            raise SessionError('A prior check for this package requires confirmed cleanup before another check can start')
        if len(self.tasks)>=16:raise SessionError('The local check queue is full; retain the package and retry later')
        ident=str(uuid.uuid4())
        with self.db:
            self.db.execute('INSERT INTO artifact_validation_jobs VALUES (?,?,?,?,?,?,?,?,?,NULL)',
                (ident,session,artifact,digest,validator,registered.label,contract,json.dumps(registration),'queued'))
        cancelled=threading.Event();self.cancellations[ident]=cancelled
        task=asyncio.create_task(self._execute(ident,content,digest,registered.spec,cancelled))
        self.tasks[ident]=task
        def settled(completed):
            self.tasks.pop(ident,None);self.cancellations.pop(ident,None)
            if not completed.cancelled():completed.exception()
        task.add_done_callback(settled)
        return self.get(scope,session,ident)

    async def _execute(self,job,content,digest,spec,cancelled):
        try:
            async with self.semaphore:
                if cancelled.is_set():
                    result={'status':'failed','reason':'cancelled_before_execution','artifactSha256':digest}
                else:
                    with self.db:self.db.execute("UPDATE artifact_validation_jobs SET state='running' WHERE id=?",(job,))
                    result=await asyncio.to_thread(self.worker.run,content,digest,spec,execution_id=job,cancel_event=cancelled)
                    if not isinstance(result,dict) or result.get('artifactSha256')!=digest or result.get('status') not in {'passed','failed','incomplete'}:
                        raise ValueError('Validator receipt does not bind the requested artifact')
                self._settle(job,result)
        except Exception:
            self._settle(job,{'status':'failed','reason':'validator_unavailable','artifactSha256':digest,
                'output':'The local check could not be completed. Package bytes are retained; inspect the server worker configuration.'})

    async def recover(self,scope,session,job):
        row=self._row(scope,session,job)
        if row['state']!='recovery_required':return self._public(row)
        if self.worker is None:raise SessionError('The recorded local validator worker is unavailable for cleanup')
        if json.loads(row['spec']).get('workerIdentity')!=self.worker.identity_digest:
            raise SessionError('The original local validator worker is required for cleanup; no fallback was applied')
        try:
            result=await asyncio.to_thread(self.worker.recover,job)
            if result!={'cleanupConfirmed':True,'workReplayed':False}:raise ValueError('Cleanup is uncertain')
        except Exception:
            raise SessionError('The prior check may still be running; cleanup was not confirmed and no check was replayed') from None
        self._settle(job,{'status':'failed','reason':'supervisor_restart','artifactSha256':row['artifact_sha256'],
            'output':'Prior container cleanup is confirmed. Request a new check explicitly; no work was replayed.'})
        return self.get(scope,session,job)

    async def close(self):
        self.closed=True
        for cancellation in self.cancellations.values():cancellation.set()
        await asyncio.gather(*list(self.tasks.values()),return_exceptions=True)
