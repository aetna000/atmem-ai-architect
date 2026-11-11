import asyncio
from pathlib import Path
import tempfile
import unittest

from server.engineering_jobs import EngineeringJobs
from server.engineering_sessions import (BackendEvent, EngineeringSessions, ModelSelection,
    ProjectScope, SessionError, SqliteSessionStore)
from server.tests.test_engineering_sessions import Backend


class EngineeringJobTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'control.sqlite'
        self.store = SqliteSessionStore(self.path)
        self.backend = Backend()
        async def close(): pass
        self.backend.close = close
        self.scope = ProjectScope('tenant-local', 'project-medical')
        self.engine = EngineeringSessions(self.store, self.backend)
        self.jobs = EngineeringJobs(self.engine)
        self.session = (await self.engine.create(self.scope, 'workspace-owned', ModelSelection('chosen-model', 'high')))['id']

    async def asyncTearDown(self):
        await self.jobs.close()
        self.store.close()
        self.temp.cleanup()

    async def settle(self):
        for _ in range(20):
            await asyncio.sleep(0)

    async def test_disconnect_during_ack_does_not_cancel_submission_or_progress(self):
        entered, release = asyncio.Event(), asyncio.Event()
        original = self.backend.start
        async def delayed(*args, **kwargs):
            entered.set()
            await release.wait()
            return await original(*args, **kwargs)
        self.backend.start = delayed
        request = asyncio.create_task(self.jobs.start(self.scope, self.session, 'Preserve medical record ownership.'))
        await entered.wait()
        request.cancel()
        with self.assertRaises(asyncio.CancelledError): await request
        release.set()
        await self.settle()
        await self.backend.events.put(BackendEvent('native-turn-1', 'message', 'Retained full result.'))
        await self.backend.events.put(BackendEvent('native-turn-1', 'completed'))
        await self.settle()
        self.assertEqual(self.jobs.state(self.scope, self.session)['last_status'], 'completed')
        events = self.jobs.journal.read(self.scope, self.session)
        self.assertEqual([e['kind'] for e in events], ['accepted', 'message', 'completed'])
        self.assertEqual(events[0]['text'],'Preserve medical record ownership.')
        self.assertEqual(events[1]['text'], 'Retained full result.')
        self.assertEqual(events[-1]['validation'], 'not_established_by_agent_turn')
        self.assertEqual(len(self.backend.request_ids), 1)

    async def test_progress_survives_reader_disconnect_and_journal_reopen(self):
        await self.jobs.start(self.scope, self.session, 'Build a field sensor ingestion service.')
        await self.backend.events.put(BackendEvent('native-turn-1', 'progress', 'commandExecution'))
        await self.backend.events.put(BackendEvent('native-turn-1', 'completed'))
        await self.settle()
        first = self.jobs.journal.read(self.scope, self.session, limit=1)
        self.assertEqual(first[0]['text'],'Build a field sensor ingestion service.')
        self.store.close()
        self.store = SqliteSessionStore(self.path)
        self.engine.store = self.store
        self.jobs = EngineeringJobs(self.engine)
        rest = self.jobs.journal.read(self.scope, self.session, after=first[0]['sequence'])
        self.assertEqual([e['kind'] for e in rest], ['progress', 'completed'])
        self.assertEqual(self.jobs.journal.read(self.scope, self.session, after=rest[-1]['sequence']), [])

    async def test_legacy_request_text_is_recovered_only_by_exact_owned_run_identity(self):
        import json
        text='Preserve every legacy line.\n'*2000
        state=await self.jobs.start(self.scope,self.session,text)
        raw=self.store.db.execute('select sequence,payload from engineering_events where session=?',(self.session,)).fetchone();payload=json.loads(raw['payload']);payload.pop('text')
        self.store.db.execute('update engineering_events set payload=? where sequence=?',(json.dumps(payload),raw['sequence']));self.store.db.commit()
        restored=self.jobs.journal.read(self.scope,self.session)[0]
        self.assertEqual(restored['text'],text);self.assertEqual(restored['textSource'],'durable_run_intent')
        other=self.store.create(self.scope,'different-workspace','backend','foreign-handle',ModelSelection('chosen-model','high'))['id'];self.store.reserve(self.scope,other,'foreign-run','PRIVATE FOREIGN INTENT')
        self.jobs.journal.append(self.scope,self.session,{'kind':'accepted','runId':'foreign-run'})
        missing=self.jobs.journal.read(self.scope,self.session)[-1];self.assertNotIn('text',missing);self.assertNotIn('PRIVATE',str(missing))

    async def test_project_and_tenant_scope_checked_before_side_effects(self):
        for scope in [ProjectScope('other-tenant','project-medical'), ProjectScope('tenant-local','other-project')]:
            before = list(self.backend.calls)
            for action in [lambda: self.jobs.start(scope,self.session,'Steal work'),
                           lambda: self.jobs.steer(scope,self.session,'Steal work'),
                           lambda: self.jobs.interrupt(scope,self.session),
                           lambda: self.jobs.recover(scope,self.session)]:
                with self.assertRaises(SessionError): await action()
            with self.assertRaises(SessionError): self.jobs.journal.read(scope,self.session)
            self.assertEqual(self.backend.calls, before)

    async def test_duplicate_start_rejected_and_steering_retains_original_intent(self):
        await self.jobs.start(self.scope,self.session,'Keep the existing sensor API.')
        with self.assertRaises(SessionError): await self.jobs.start(self.scope,self.session,'Replace everything.')
        await self.jobs.steer(self.scope,self.session,'Add tenant isolation; preserve the existing API.')
        await self.jobs.interrupt(self.scope,self.session)
        self.assertEqual(self.jobs.state(self.scope,self.session)['state'], 'running')
        self.assertEqual(len(self.backend.request_ids), 1)
        self.assertEqual(self.store.db.execute('SELECT intent FROM engineering_runs').fetchone()[0], 'Keep the existing sensor API.')
        self.assertEqual([e['kind'] for e in self.jobs.journal.read(self.scope,self.session)],
                         ['accepted','steering_submitted','steering_accepted','interruption_requested'])

    async def test_lost_ack_is_not_replayed_and_recovery_explains_event_gap(self):
        self.backend.fail_start = True
        with self.assertRaises(TimeoutError): await self.jobs.start(self.scope,self.session,'Do this exactly once.')
        state = await self.jobs.recover(self.scope,self.session)
        self.assertEqual(state['state'],'starting')
        self.assertEqual(len(self.backend.request_ids),1)
        self.assertIn('may be unavailable', self.jobs.journal.read(self.scope,self.session)[-1]['text'])

    async def test_bad_cursor_is_rejected_without_dropping_events(self):
        for after in [-1, True, '1']:
            with self.assertRaises(ValueError): self.jobs.journal.read(self.scope,self.session,after=after)
        for limit in [0,201,True]:
            with self.assertRaises(ValueError): self.jobs.journal.read(self.scope,self.session,limit=limit)

    async def test_lost_ack_recovers_durable_client_intent_once_without_replaying_inference(self):
        from server.engineering_sessions import RecoveredStart
        self.backend.fail_start=True
        text='Keep the existing medical system.\nPreserve 🛰️ and every original requirement.'
        with self.assertRaises(TimeoutError):await self.jobs.start(self.scope,self.session,text)
        run=self.jobs.state(self.scope,self.session)['run']
        self.backend.recovered_start=RecoveredStart(run,'native-turn-one','completed')
        await self.jobs.recover(self.scope,self.session);await self.jobs.recover(self.scope,self.session)
        events=[e for e in self.jobs.journal.read(self.scope,self.session) if e['kind']=='accepted']
        self.assertEqual(len(events),1);self.assertEqual(events[0]['text'],text);self.assertEqual(events[0]['runId'],run)
        self.assertEqual(events[0]['origin'],'recovered_client_request');self.assertEqual(len(self.backend.request_ids),1)

    async def test_recovered_automatic_repair_does_not_become_client_intent(self):
        from server.engineering_sessions import RecoveredStart
        self.backend.fail_start=True
        with self.assertRaises(TimeoutError):await self.jobs.start(self.scope,self.session,'INTERNAL repair instruction',origin='automatic_repair')
        run=self.jobs.state(self.scope,self.session)['run']
        self.store.db.execute('CREATE TABLE engineering_repairs (run TEXT, session TEXT)')
        self.store.db.execute('INSERT INTO engineering_repairs VALUES (?,?)',(run,self.session));self.store.db.commit()
        self.backend.recovered_start=RecoveredStart(run,'recovered-repair','completed')
        await self.jobs.recover(self.scope,self.session)
        event=next(e for e in self.jobs.journal.read(self.scope,self.session) if e['kind']=='accepted')
        self.assertEqual(event['origin'],'automatic_repair');self.assertEqual(len(self.backend.request_ids),1)

    async def test_recover_live_watcher_does_not_race_terminal_reconciliation(self):
        await self.jobs.start(self.scope,self.session,'Build the service.')
        state = await self.jobs.recover(self.scope,self.session)
        self.assertEqual(state['state'],'running')
        self.assertFalse(any(call[0]=='observe' for call in self.backend.calls))

    async def test_quiet_native_observation_window_keeps_watching(self):
        original = self.backend.next_event
        first = True
        async def quiet(*args):
            nonlocal first
            if first:
                first = False
                raise asyncio.TimeoutError('Quiet reasoning window')
            return await original(*args)
        self.backend.next_event = quiet
        await self.jobs.start(self.scope,self.session,'Build the service.')
        await self.backend.events.put(BackendEvent('native-turn-1','completed'))
        await self.settle()
        self.assertEqual(self.jobs.state(self.scope,self.session)['last_status'],'completed')
        self.assertNotIn('recovery_required',[event['kind'] for event in self.jobs.journal.read(self.scope,self.session)])

    async def test_idle_reconnect_failure_does_not_reserve_an_unsubmitted_intent(self):
        async def unavailable(*args): raise RuntimeError('Worker unavailable')
        self.backend.resume = unavailable
        with self.assertRaises(RuntimeError): await self.jobs.start(self.scope,self.session,'Retain this unsent draft.')
        self.assertEqual(self.jobs.state(self.scope,self.session)['state'],'idle')
        self.assertEqual(self.backend.request_ids,[])

    async def test_lost_steering_ack_preserves_complete_update_without_replay(self):
        await self.jobs.start(self.scope,self.session,'Build it.')
        calls=[]
        async def lost(*args,**kwargs):
            calls.append((args,kwargs))
            raise TimeoutError('Lost acknowledgement')
        self.backend.steer=lost
        text='Preserve the existing service.\n'*100
        with self.assertRaises(TimeoutError): await self.jobs.steer(self.scope,self.session,text)
        events=self.jobs.journal.read(self.scope,self.session)
        self.assertEqual(events[-2]['text'],text)
        self.assertEqual(events[-1]['kind'],'steering_delivery_uncertain')
        self.assertEqual(events[-2]['requestId'],events[-1]['requestId'])
        self.assertEqual(calls[0][1]['request_id'],events[-2]['requestId'])
        await self.jobs.recover(self.scope,self.session)
        self.assertEqual(len(calls),1)
