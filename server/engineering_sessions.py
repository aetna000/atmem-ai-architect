"""Backend-neutral engineering lifecycle; no CLI, host path or billing dependency.

Scopes must come from the authenticated server's project authorization, not browser
claims. A completed agent turn is not evidence the generated system passed validation.
"""
from dataclasses import dataclass
import re
import sqlite3
from typing import Protocol
import uuid


class SessionError(RuntimeError):
    pass


class EmptySessionUnavailable(SessionError):
    """Backend confirms no durable thread; replacement requires no accepted run."""


@dataclass(frozen=True)
class ProjectScope:
    tenant: str
    project: str

    def __post_init__(self):
        if any(not isinstance(x,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{2,127}',x) for x in (self.tenant,self.project)):
            raise ValueError('Invalid project scope')


@dataclass(frozen=True)
class ModelSelection:
    model: str
    effort: str

    def __post_init__(self):
        if not isinstance(self.model,str) or not self.model.strip() or len(self.model)>150:
            raise ValueError('An explicit model is required')
        if self.effort not in {'none','minimal','low','medium','high','xhigh','max','ultra'}:
            raise ValueError('An explicit supported reasoning effort is required')


@dataclass(frozen=True)
class BackendEvent:
    turn: str
    kind: str
    text: str = ''

    def __post_init__(self):
        if not self.turn or self.kind not in {'progress','message','completed','failed','interrupted'}:
            raise ValueError('Invalid engineering event')


@dataclass(frozen=True)
class RecoveredStart:
    request_id: str
    turn: str
    status: str

    def __post_init__(self):
        if not self.request_id or not self.turn or self.status not in {'running','completed','failed','interrupted'}:
            raise ValueError('Invalid recovered start evidence')


class EngineeringBackend(Protocol):
    name: str
    async def create(self,scope: ProjectScope,workspace: str,selection: ModelSelection) -> str: ...
    async def resume(self,scope: ProjectScope,handle: str,workspace: str,selection: ModelSelection) -> None: ...
    async def observe(self,scope: ProjectScope,handle: str,turn: str) -> BackendEvent | None: ...
    async def start(self,scope: ProjectScope,handle: str,text: str,selection: ModelSelection,*,request_id: str) -> str: ...
    async def recover_start(self,scope: ProjectScope,handle: str,request_id: str) -> RecoveredStart | None: ...
    async def steer(self,scope: ProjectScope,handle: str,turn: str,text: str,*,request_id: str | None = None) -> None: ...
    async def interrupt(self,scope: ProjectScope,handle: str,turn: str) -> None: ...
    async def next_event(self,scope: ProjectScope,handle: str) -> BackendEvent: ...


class SessionStore(Protocol):
    def create(self,scope,workspace,backend,handle,selection): ...
    def get(self,scope,session): ...
    def reserve(self,scope,session,run,text): ...
    def attach_turn(self,scope,session,run,turn): ...
    def terminal(self,scope,session,run,turn,status): ...
    def replace_empty_handle(self,scope,session,old_handle,new_handle): ...


class SqliteSessionStore:
    """Local durable adapter. Hosted service can supply another transactional store.

    Store this outside model-writable project workspaces. Reservations survive
    process death; an uncertain start must be reconciled, never blindly repeated.
    """
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.row_factory=sqlite3.Row
        self.db.execute('''CREATE TABLE IF NOT EXISTS engineering_sessions (
          id TEXT PRIMARY KEY, tenant TEXT NOT NULL, project TEXT NOT NULL,
          workspace TEXT NOT NULL, backend TEXT NOT NULL, handle TEXT NOT NULL,
          model TEXT NOT NULL, effort TEXT NOT NULL, state TEXT NOT NULL,
          run TEXT, turn TEXT, last_status TEXT)''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS engineering_runs (
          id TEXT PRIMARY KEY, session TEXT NOT NULL, turn TEXT, status TEXT NOT NULL,
          intent TEXT, UNIQUE(session,turn))''')
        if 'intent' not in {row[1] for row in self.db.execute('PRAGMA table_info(engineering_runs)')}:
            self.db.execute('ALTER TABLE engineering_runs ADD COLUMN intent TEXT')
        self.db.commit()

    def close(self):
        self.db.close()

    def create(self,scope,workspace,backend,handle,selection):
        ident=str(uuid.uuid4())
        with self.db:
            self.db.execute('INSERT INTO engineering_sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                (ident,scope.tenant,scope.project,workspace,backend,handle,selection.model,selection.effort,'idle',None,None,None))
        return self.get(scope,ident)

    def get(self,scope,session):
        row=self.db.execute('SELECT * FROM engineering_sessions WHERE id=? AND tenant=? AND project=?',
                            (session,scope.tenant,scope.project)).fetchone()
        if not row:
            raise SessionError('Engineering session is unavailable for this project')
        return dict(row)

    def reserve(self,scope,session,run,text):
        with self.db:
            changed=self.db.execute("UPDATE engineering_sessions SET state='starting',run=?,turn=NULL WHERE id=? AND tenant=? AND project=? AND state='idle'",
                                    (run,session,scope.tenant,scope.project)).rowcount
            if changed!=1:
                self.get(scope,session)
                raise SessionError('An engineering turn is active or requires recovery')
            self.db.execute("INSERT INTO engineering_runs (id,session,turn,status,intent) VALUES (?,?,NULL,'starting',?)",(run,session,text))

    def replace_empty_handle(self,scope,session,old_handle,new_handle):
        with self.db:
            changed=self.db.execute("""UPDATE engineering_sessions SET handle=?
                WHERE id=? AND tenant=? AND project=? AND handle=? AND state='idle'
                AND run IS NULL AND last_status IS NULL
                AND NOT EXISTS (SELECT 1 FROM engineering_runs WHERE session=?)""",
                (new_handle,session,scope.tenant,scope.project,old_handle,session)).rowcount
            if changed!=1:
                raise SessionError('Only a never-started session can replace a missing backend thread')

    def attach_turn(self,scope,session,run,turn):
        with self.db:
            # Backend turn IDs cannot be reused to let a delayed old completion
            # settle a later run of this session.
            try:
                attached=self.db.execute("UPDATE engineering_runs SET turn=?,status='running' WHERE id=? AND session=? AND status='starting'",(turn,run,session)).rowcount
            except sqlite3.IntegrityError:
                raise SessionError('Backend reused a prior turn ID; recovery is required') from None
            if attached!=1:
                raise SessionError('The reserved engineering run is unavailable')
            changed=self.db.execute("UPDATE engineering_sessions SET state='running',turn=? WHERE id=? AND tenant=? AND project=? AND run=? AND state='starting'",
                (turn,session,scope.tenant,scope.project,run)).rowcount
            if changed!=1:
                raise SessionError('Engineering turn ownership changed; reconcile before continuing')

    def terminal(self,scope,session,run,turn,status):
        if status not in {'completed','failed','interrupted'}:
            raise ValueError('A terminal backend event is required')
        with self.db:
            changed=self.db.execute("UPDATE engineering_sessions SET state='idle',last_status=? WHERE id=? AND tenant=? AND project=? AND run=? AND turn=? AND state='running'",
                (status,session,scope.tenant,scope.project,run,turn)).rowcount
            if changed!=1:
                raise SessionError('Terminal evidence does not match the owned engineering turn')
            self.db.execute('UPDATE engineering_runs SET status=? WHERE id=? AND session=? AND turn=?',(status,run,session,turn))


class EngineeringSessions:
    def __init__(self,store: SessionStore,backend: EngineeringBackend):
        self.store,self.backend=store,backend

    def _owned(self,scope,session):
        row=self.store.get(scope,session)
        if row['backend']!=self.backend.name:
            raise SessionError('The recorded engineering backend is required; no fallback was applied')
        return row

    @staticmethod
    def _public(row):
        return {k:row[k] for k in ('id','model','effort','state','run','last_status')}

    @staticmethod
    def _text(text):
        if not isinstance(text,str) or not text.strip() or len(text)>80000:
            raise ValueError('Engineering intent must be nonempty and within 80,000 characters; no text was discarded')

    async def create(self,scope,workspace,selection):
        # Opaque worker-owned workspace reference, never a browser filesystem path.
        if not isinstance(workspace,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{2,127}',workspace):
            raise ValueError('An opaque worker workspace ID is required')
        handle=await self.backend.create(scope,workspace,selection)
        if not isinstance(handle,str) or not handle:
            raise SessionError('Backend did not confirm a session')
        return self._public(self.store.create(scope,workspace,self.backend.name,handle,selection))

    async def resume(self,scope,session):
        row=self._owned(scope,session)
        selection=ModelSelection(row['model'],row['effort'])
        try:
            await self.backend.resume(scope,row['handle'],row['workspace'],selection)
        except EmptySessionUnavailable:
            if row['state']!='idle' or row['run'] is not None or row['last_status'] is not None:
                raise SessionError('Missing history for accepted work requires recovery; no replacement was started') from None
            handle=await self.backend.create(scope,row['workspace'],selection)
            if not isinstance(handle,str) or not handle:
                raise SessionError('Backend did not confirm an empty replacement session')
            self.store.replace_empty_handle(scope,session,row['handle'],handle)
            row=self._owned(scope,session)
        if row['state']=='starting':
            recovered=await self.backend.recover_start(scope,row['handle'],row['run'])
            if recovered is not None:
                if recovered.request_id!=row['run']:
                    raise SessionError('Recovered start does not match the reserved request')
                self.store.attach_turn(scope,session,row['run'],recovered.turn)
                if recovered.status!='running':
                    self.store.terminal(scope,session,row['run'],recovered.turn,recovered.status)
                row=self._owned(scope,session)
        if row['state']=='running':
            # A terminal event may have been lost with the connection. Reconcile
            # the owned turn from backend history instead of replaying its intent
            # or waiting forever for a notification that will not be redelivered.
            event=await self.backend.observe(scope,row['handle'],row['turn'])
            if event is not None:
                if event.turn!=row['turn'] or event.kind not in {'completed','failed','interrupted'}:
                    raise SessionError('Recovery evidence does not match the owned engineering turn')
                self.store.terminal(scope,session,row['run'],row['turn'],event.kind)
        return self._public(self._owned(scope,session))

    async def start(self,scope,session,text,*,run_id=None):
        self._text(text)
        row=self._owned(scope,session)
        run=str(uuid.uuid4()) if run_id is None else run_id
        if not isinstance(run,str) or str(uuid.UUID(run))!=run:
            raise ValueError('Use a canonical server-reserved run UUID')
        self.store.reserve(scope,session,run,text)
        # Errors, timeout or process death leave a durable uncertain reservation.
        # A second writer cannot submit the same work as a fresh turn.
        turn=await self.backend.start(scope,row['handle'],text,ModelSelection(row['model'],row['effort']),request_id=run)
        if not isinstance(turn,str) or not turn:
            raise SessionError('Backend did not confirm a turn; recovery is required')
        self.store.attach_turn(scope,session,run,turn)
        return self._public(self._owned(scope,session))

    async def steer(self,scope,session,text,*,request_id=None):
        self._text(text)
        row=self._owned(scope,session)
        if row['state']!='running':
            raise SessionError('Steering requires a confirmed active turn')
        if request_id is None:
            await self.backend.steer(scope,row['handle'],row['turn'],text)
        else:
            await self.backend.steer(scope,row['handle'],row['turn'],text,request_id=request_id)

    async def interrupt(self,scope,session):
        row=self._owned(scope,session)
        if row['state']!='running':
            raise SessionError('Interruption requires a confirmed active turn')
        await self.backend.interrupt(scope,row['handle'],row['turn'])
        # Request acknowledgement is not a completed interruption.

    async def next_event(self,scope,session):
        row=self._owned(scope,session)
        if row['state']!='running':
            raise SessionError('No confirmed engineering turn is running')
        event=await self.backend.next_event(scope,row['handle'])
        current=self._owned(scope,session)
        if current['run']!=row['run'] or current['state']!='running' or event.turn!=row['turn']:
            raise SessionError('Backend event is stale or belongs to another turn')
        if event.kind in {'completed','failed','interrupted'}:
            self.store.terminal(scope,session,row['run'],row['turn'],event.kind)
        return {'sessionId':session,'runId':row['run'],'kind':event.kind,'text':event.text,
                'validation':'not_established_by_agent_turn'}
