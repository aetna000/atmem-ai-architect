"""Backend-neutral job supervision and durable progress, independent of HTTP lifetime.

Authorization supplies ProjectScope; callers cannot select workspace paths or native
handles. This local journal is not a hosted tenant/OS isolation implementation.
"""
import asyncio
import json
import uuid
from .engineering_sessions import SessionError


class JobJournal:
    def __init__(self, store):
        self.store = store
        self.db = store.db
        self.db.execute('''CREATE TABLE IF NOT EXISTS engineering_events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT, session TEXT NOT NULL,
            payload TEXT NOT NULL)''')
        self.db.commit()

    def append(self, scope, session, event):
        self.store.get(scope, session)
        payload = json.dumps(event, ensure_ascii=False, allow_nan=False)
        with self.db:
            cursor = self.db.execute('INSERT INTO engineering_events(session,payload) VALUES (?,?)',
                                     (session, payload))
        return cursor.lastrowid

    def read(self, scope, session, after=0, limit=200):
        self.store.get(scope, session)
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError('Invalid progress cursor')
        rows = self.db.execute('''SELECT sequence,payload FROM engineering_events
            WHERE session=? AND sequence>? ORDER BY sequence LIMIT ?''', (session, after, limit)).fetchall()
        result=[]
        for row in rows:
            event=json.loads(row['payload'])
            # Earlier journals recorded the exact owned run ID but not its text.
            # Recover only through that durable relation, never by matching text
            # or reading a foreign session's intent. Leave unknown history absent.
            if event.get('kind')=='accepted' and 'text' not in event:
                intent=self.db.execute('SELECT intent FROM engineering_runs WHERE id=? AND session=?',(event.get('runId'),session)).fetchone()
                if intent and isinstance(intent['intent'],str):event.update(text=intent['intent'],textSource='durable_run_intent')
            result.append({'sequence':row['sequence'],**event})
        return result


class EngineeringJobs:
    """One supervisor per backend process; browser requests only submit/read intent.

    Native starts remain reserved across process death. Recovery never retries an
    uncertain turn. Event delivery is durable after journal commit; events lost
    before that commit remain an explicitly reported gap after worker restart.
    """
    def __init__(self, sessions):
        self.sessions = sessions
        self.journal = JobJournal(sessions.store)
        self.tasks = {}
        self.submissions = set()
        self.locks = {}
        self.on_settled = None
        self.context_provider = None

    def _context(self, scope, session, request, expected_sha256):
        if self.context_provider is None:
            if expected_sha256 is not None:
                raise SessionError('This worker cannot attach the requested project context')
            return None
        context = self.context_provider(scope, session, request, expected_sha256)
        self._record(scope, session, 'context_attached', requestId=request,
                     contextId=context['id'], contextRevision=context['revision'], contextSha256=context['sha256'],
                     text='Saved design context attached to this submission; delivery and implementation are not established by this receipt.')
        return context

    def _lock(self, scope, session):
        self.sessions._owned(scope, session)
        return self.locks.setdefault((scope, session), asyncio.Lock())

    def _record(self, scope, session, kind, **fields):
        self.journal.append(scope, session, {'kind': kind, **fields})

    def state(self, scope, session):
        return self.sessions._public(self.sessions._owned(scope, session))

    def _watch(self, scope, session):
        key = (scope, session)
        task = self.tasks.get(key)
        if self.state(scope, session)['state'] == 'running' and (task is None or task.done()):
            self.tasks[key] = asyncio.create_task(self._collect(scope, session))

    async def _collect(self, scope, session):
        try:
            while self.state(scope, session)['state'] == 'running':
                try:
                    event = await self.sessions.next_event(scope, session)
                except asyncio.TimeoutError:
                    # Quiet reasoning/tool work is not a broken connection.
                    continue
                self.journal.append(scope, session, event)
                if event['kind'] in {'completed','failed','interrupted'} and self.on_settled:
                    self.on_settled(scope,session)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Native/tool diagnostics may include sensitive host information.
            # A transport failure does not establish that the turn stopped.
            self._record(scope, session, 'recovery_required',
                         text='Progress connection interrupted. Recover the existing job; do not resubmit its intent.')

    async def start(self, scope, session, text, *, expected_run=None, run_id=None, origin=None, context_sha256=None):
        # Shield the entire reservation/acknowledgement/supervision transition,
        # including when the initiating HTTP client disconnects.
        async def submit():
            async with self._lock(scope, session):
                def current():
                    state=self.state(scope,session)
                    if expected_run is not None and (state['state']!='idle' or state['run']!=expected_run):
                        raise SessionError('Newer user work superseded this automatic repair')
                    return state
                if current()['state'] == 'idle':
                    # After a server restart, reconnect the existing backend before
                    # reserving new intent. Failure must leave an idle job idle.
                    await self.sessions.resume(scope, session)
                if current()['state'] != 'idle':
                    raise SessionError('An engineering turn is active or requires recovery')
                self.sessions._text(text)
                request = run_id if run_id is not None else str(uuid.uuid4())
                # Repairs retain their existing thread context, rather than
                # introducing design changes as an invented client request.
                context = None if origin == 'automatic_repair' else self._context(scope, session, request, context_sha256)
                state = await self.sessions.start(scope, session, text, run_id=request,
                    **({'context':context} if context is not None else {}))
                self._record(scope, session, 'accepted', runId=state['run'],text=text,**({'origin':origin} if origin else {}))
                self._watch(scope, session)
                return state
        task = asyncio.create_task(submit())
        self.submissions.add(task)
        def settled(completed):
            self.submissions.discard(completed)
            if not completed.cancelled():
                completed.exception()
        task.add_done_callback(settled)
        return await asyncio.shield(task)

    async def recover(self, scope, session):
        async with self._lock(scope, session):
            task = self.tasks.get((scope, session))
            if task is not None and not task.done():
                return self.state(scope, session)
            state = await self.sessions.resume(scope, session)
            if state['state']!='starting' and state['run'] is not None:
                # A lost start acknowledgement may have prevented the original
                # accepted journal commit. Recover exact intent through the owned
                # durable run, not guessed text or an inference replay.
                known=self.sessions.store.db.execute("SELECT 1 FROM engineering_events WHERE session=? AND json_extract(payload,'$.kind')='accepted' AND json_extract(payload,'$.runId')=?",(session,state['run'])).fetchone()
                if not known:
                    saved=self.sessions.store.db.execute('SELECT intent,turn FROM engineering_runs WHERE id=? AND session=?',(state['run'],session)).fetchone()
                    if saved and saved['turn'] and isinstance(saved['intent'],str):
                        has_repairs=self.sessions.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='engineering_repairs'").fetchone()
                        repair=has_repairs and self.sessions.store.db.execute('SELECT 1 FROM engineering_repairs WHERE run=? AND session=?',(state['run'],session)).fetchone()
                        self._record(scope,session,'accepted',runId=state['run'],text=saved['intent'],origin='automatic_repair' if repair else 'recovered_client_request')
            self._record(scope, session, 'recovered', state=state['state'],
                         text='State reconciled from native history. Progress emitted before journal commit may be unavailable.',
                         validation='not_established_by_agent_turn')
            if state['state']=='idle' and self.on_settled:self.on_settled(scope,session)
            self._watch(scope, session)
            return state

    async def steer(self, scope, session, text, *, context_sha256=None):
        async def deliver():
            async with self._lock(scope, session):
                self.sessions._text(text)
                if self.state(scope,session)['state'] != 'running':
                    raise SessionError('Steering requires a confirmed active turn')
                request = str(uuid.uuid4())
                context = self._context(scope, session, request, context_sha256)
                self._record(scope,session,'steering_submitted',requestId=request,text=text)
                try:
                    await self.sessions.steer(scope,session,text,request_id=request,
                        **({'context':context} if context is not None else {}))
                except Exception:
                    self._record(scope,session,'steering_delivery_uncertain',requestId=request,
                                 text='This saved update may already be accepted. It was not replayed automatically.')
                    raise
                self._record(scope,session,'steering_accepted',requestId=request)
        task = asyncio.create_task(deliver())
        self.submissions.add(task)
        def settled(completed):
            self.submissions.discard(completed)
            if not completed.cancelled(): completed.exception()
        task.add_done_callback(settled)
        await asyncio.shield(task)

    async def interrupt(self, scope, session):
        async with self._lock(scope, session):
            await self.sessions.interrupt(scope, session)
            self._record(scope, session, 'interruption_requested')
        return self.state(scope, session)

    async def close(self):
        tasks = [*self.tasks.values(), *self.submissions]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        # Closing a worker connection does not assert remote cancellation.
        await self.sessions.backend.close()
