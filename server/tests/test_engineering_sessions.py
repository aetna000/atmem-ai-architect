import asyncio
from pathlib import Path
import tempfile
import unittest
from server.engineering_sessions import (BackendEvent,EmptySessionUnavailable,EngineeringSessions,ModelSelection,RecoveredStart,
                                        ProjectScope,SessionError,SqliteSessionStore)

class Backend:
    name='test-worker'
    def __init__(self):
        self.calls=[];self.events=asyncio.Queue();self.fail_start=False;self.observed=None;self.recovered_start=None;self.request_ids=[]
    async def create(self,scope,workspace,selection):
        self.calls.append(('create',scope,workspace,selection));return 'backend-private-handle'
    async def resume(self,scope,handle,workspace,selection):
        self.calls.append(('resume',scope,handle,workspace,selection))
    async def observe(self,scope,handle,turn):
        self.calls.append(('observe',scope,handle,turn));return self.observed
    async def start(self,scope,handle,text,selection,*,request_id=None):
        self.request_ids.append(request_id)
        self.calls.append(('start',scope,handle,text,selection));await asyncio.sleep(0)
        if self.fail_start:raise TimeoutError('Lost acknowledgement')
        return 'native-turn-1'
    async def recover_start(self,scope,handle,request_id):
        self.calls.append(('recover-start',scope,handle,request_id));return self.recovered_start
    async def steer(self,scope,handle,turn,text,*,request_id=None):
        self.calls.append(('steer',scope,handle,turn,text))
    async def interrupt(self,scope,handle,turn):
        self.calls.append(('interrupt',scope,handle,turn))
    async def next_event(self,scope,handle):
        self.calls.append(('event',scope,handle));return await self.events.get()

class EngineeringSessionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'sessions.sqlite'
        self.store=SqliteSessionStore(self.path);self.backend=Backend()
        self.scope=ProjectScope('tenant-one','project-one');self.choice=ModelSelection('chosen-strong-model','high')
        self.engine=EngineeringSessions(self.store,self.backend)
        self.session=(await self.engine.create(self.scope,'workspace-one',self.choice))['id']
    async def asyncTearDown(self):
        self.store.close();self.temp.cleanup()

    async def test_public_state_has_no_backend_handle_workspace_or_filesystem(self):
        state=await self.engine.resume(self.scope,self.session)
        self.assertEqual(set(state),{'id','model','effort','state','run','last_status'})
        self.assertNotEqual(state['id'],'backend-private-handle')
        self.assertEqual(state['model'],self.choice.model);self.assertEqual(state['effort'],'high')

    async def test_missing_never_started_thread_is_replaced_without_changing_public_session(self):
        async def missing(*args):raise EmptySessionUnavailable('No saved thread')
        async def replacement(*args):return 'replacement-thread'
        self.backend.resume=missing;self.backend.create=replacement
        state=await self.engine.resume(self.scope,self.session)
        self.assertEqual(state['id'],self.session)
        self.assertEqual(state['state'],'idle')
        self.assertEqual(self.store.get(self.scope,self.session)['handle'],'replacement-thread')
        self.assertFalse(any(c[0]=='start' for c in self.backend.calls))

    async def test_missing_thread_with_any_accepted_work_is_not_replaced(self):
        await self.engine.start(self.scope,self.session,'Preserve this accepted intent')
        async def missing(*args):raise EmptySessionUnavailable('No saved thread')
        self.backend.resume=missing
        before=len(self.backend.calls)
        with self.assertRaises(SessionError):await self.engine.resume(self.scope,self.session)
        self.assertEqual(len(self.backend.calls),before)
        self.assertEqual(self.store.get(self.scope,self.session)['state'],'running')

    async def test_empty_handle_replacement_cannot_race_an_accepted_start(self):
        self.store.reserve(self.scope,self.session,'run-one','Do not lose this intent')
        with self.assertRaises(SessionError):
            self.store.replace_empty_handle(self.scope,self.session,'backend-private-handle','replacement')
        self.assertEqual(self.store.get(self.scope,self.session)['handle'],'backend-private-handle')

    async def test_other_tenant_or_project_cannot_use_an_owned_session(self):
        count=len(self.backend.calls)
        for scope in [ProjectScope('tenant-two','project-one'),ProjectScope('tenant-one','project-two')]:
            for action in [lambda:self.engine.resume(scope,self.session),lambda:self.engine.start(scope,self.session,'Change it'),lambda:self.engine.interrupt(scope,self.session),lambda:self.engine.next_event(scope,self.session)]:
                with self.assertRaises(SessionError):await action()
        self.assertEqual(len(self.backend.calls),count)

    async def test_scope_workspace_and_intent_are_bounded_without_truncation(self):
        for scope in ['../tenant','tenant/other','']:
            with self.assertRaises(ValueError):ProjectScope(scope,'project-one')
        with self.assertRaises(ValueError):await self.engine.create(self.scope,'/private/project',self.choice)
        for text in ['', ' ', 'x'*80001]:
            with self.assertRaises(ValueError):await self.engine.start(self.scope,self.session,text)
        text='Keep the imported deployment.\n'+('Long requirement. '*1000)
        await self.engine.start(self.scope,self.session,text)
        self.assertEqual(self.backend.calls[-1][3],text)
        self.assertEqual(self.backend.calls[-1][-1],self.choice)

    async def test_durable_resume_preserves_model_backend_and_active_turn(self):
        state=await self.engine.start(self.scope,self.session,'Build a scheduling service')
        self.store.close();self.store=SqliteSessionStore(self.path)
        self.engine=EngineeringSessions(self.store,self.backend)
        restored=await self.engine.resume(self.scope,self.session)
        self.assertEqual(restored,state)
        self.assertIn(('resume',self.scope,'backend-private-handle','workspace-one',self.choice),self.backend.calls)
        with self.assertRaises(SessionError):await self.engine.start(self.scope,self.session,'Duplicate start')

    async def test_competing_writers_reserve_exactly_one_turn(self):
        states=await asyncio.gather(self.engine.start(self.scope,self.session,'First'),self.engine.start(self.scope,self.session,'Second'),return_exceptions=True)
        self.assertEqual(sum(isinstance(s,dict) for s in states),1)
        self.assertEqual(sum(c[0]=='start' for c in self.backend.calls),1)

    async def test_restart_reconciles_lost_terminal_notification_without_replaying_intent(self):
        await self.engine.start(self.scope,self.session,'Build a scheduling service')
        self.store.close();self.store=SqliteSessionStore(self.path)
        self.engine=EngineeringSessions(self.store,self.backend)
        self.backend.observed=BackendEvent('native-turn-1','completed')
        state=await self.engine.resume(self.scope,self.session)
        self.assertEqual(state['state'],'idle')
        self.assertEqual(state['last_status'],'completed')
        self.assertEqual(sum(c[0]=='start' for c in self.backend.calls),1)

    async def test_recovery_rejects_foreign_turn_and_nonterminal_evidence(self):
        await self.engine.start(self.scope,self.session,'Implement')
        for event in [BackendEvent('foreign-turn','completed'),BackendEvent('native-turn-1','message','Done')]:
            self.backend.observed=event
            with self.assertRaises(SessionError):await self.engine.resume(self.scope,self.session)
            self.assertEqual(self.store.get(self.scope,self.session)['state'],'running')

    async def test_failed_and_interrupted_recovery_are_not_success(self):
        await self.engine.start(self.scope,self.session,'Implement')
        self.backend.observed=BackendEvent('native-turn-1','failed')
        state=await self.engine.resume(self.scope,self.session)
        self.assertEqual(state['last_status'],'failed')
        self.assertEqual(state['state'],'idle')

    async def test_lost_start_acknowledgement_needs_reconciliation_not_blind_retry(self):
        self.backend.fail_start=True
        with self.assertRaises(TimeoutError):await self.engine.start(self.scope,self.session,'Do not execute twice')
        self.assertEqual(self.store.get(self.scope,self.session)['state'],'starting')
        with self.assertRaises(SessionError):await self.engine.start(self.scope,self.session,'Retry')
        self.assertEqual(sum(c[0]=='start' for c in self.backend.calls),1)

    async def test_uncertain_start_retains_intent_across_store_restart(self):
        self.backend.fail_start=True
        text='Preserve existing data; do not repeat this operation.'
        with self.assertRaises(TimeoutError):await self.engine.start(self.scope,self.session,text)
        self.store.close();self.store=SqliteSessionStore(self.path)
        self.engine=EngineeringSessions(self.store,self.backend)
        state=await self.engine.resume(self.scope,self.session)
        self.assertEqual(state['state'],'starting')
        saved=self.store.db.execute('SELECT intent FROM engineering_runs WHERE session=?',(self.session,)).fetchone()
        self.assertEqual(saved['intent'],text)
        with self.assertRaises(SessionError):await self.engine.start(self.scope,self.session,text)
        self.assertEqual(sum(c[0]=='start' for c in self.backend.calls),1)

    async def test_lost_start_acknowledgement_recovers_by_reserved_identity_without_resubmission(self):
        self.backend.fail_start=True
        with self.assertRaises(TimeoutError):await self.engine.start(self.scope,self.session,'Execute once')
        request_id=self.store.get(self.scope,self.session)['run']
        self.assertEqual(self.backend.request_ids,[request_id])
        self.backend.recovered_start=RecoveredStart(request_id,'native-turn-1','completed')
        state=await self.engine.resume(self.scope,self.session)
        self.assertEqual(state['state'],'idle');self.assertEqual(state['last_status'],'completed')
        self.assertEqual(sum(c[0]=='start' for c in self.backend.calls),1)

    async def test_start_recovery_for_another_request_does_not_settle_our_reservation(self):
        self.backend.fail_start=True
        with self.assertRaises(TimeoutError):await self.engine.start(self.scope,self.session,'Execute once')
        self.backend.recovered_start=RecoveredStart('another-request','another-turn','completed')
        with self.assertRaises(SessionError):await self.engine.resume(self.scope,self.session)
        self.assertEqual(self.store.get(self.scope,self.session)['state'],'starting')

    async def test_steering_keeps_new_demands_and_exact_active_turn(self):
        await self.engine.start(self.scope,self.session,'Build reservations')
        update='Also support offline returns; inspection is required before re-lending.'
        await self.engine.steer(self.scope,self.session,update)
        self.assertEqual(self.backend.calls[-1],('steer',self.scope,'backend-private-handle','native-turn-1',update))

    async def test_interrupt_ack_is_not_terminal_evidence(self):
        await self.engine.start(self.scope,self.session,'Run checks')
        await self.engine.interrupt(self.scope,self.session)
        self.assertEqual(self.store.get(self.scope,self.session)['state'],'running')
        await self.backend.events.put(BackendEvent('native-turn-1','interrupted'))
        event=await self.engine.next_event(self.scope,self.session)
        self.assertEqual(event['kind'],'interrupted')
        self.assertEqual(self.store.get(self.scope,self.session)['last_status'],'interrupted')

    async def test_stale_or_foreign_turn_event_cannot_finish_current_turn(self):
        await self.engine.start(self.scope,self.session,'Run checks')
        await self.backend.events.put(BackendEvent('different-turn','completed'))
        with self.assertRaises(SessionError):await self.engine.next_event(self.scope,self.session)
        self.assertEqual(self.store.get(self.scope,self.session)['state'],'running')
        await self.backend.events.put(BackendEvent('native-turn-1','message','The code is done'))
        event=await self.engine.next_event(self.scope,self.session)
        self.assertEqual(event['kind'],'message');self.assertEqual(self.store.get(self.scope,self.session)['state'],'running')

    async def test_completed_agent_turn_is_not_validation_or_deployment_evidence(self):
        await self.engine.start(self.scope,self.session,'Implement')
        await self.backend.events.put(BackendEvent('native-turn-1','completed','All done'))
        event=await self.engine.next_event(self.scope,self.session)
        self.assertEqual(event['validation'],'not_established_by_agent_turn')
        self.assertEqual(self.store.get(self.scope,self.session)['state'],'idle')
        self.assertNotIn('passed',event)

    async def test_backend_change_does_not_silently_fallback(self):
        replacement=Backend();replacement.name='different-worker'
        engine=EngineeringSessions(self.store,replacement)
        with self.assertRaises(SessionError):await engine.resume(self.scope,self.session)
        self.assertFalse(replacement.calls)

    async def test_same_service_contract_works_with_a_remote_worker_adapter(self):
        remote=Backend();remote.name='remote-worker-contract-fixture'
        engine=EngineeringSessions(self.store,remote)
        session=await engine.create(self.scope,'opaque-remote-workspace',self.choice)
        await engine.start(self.scope,session['id'],'Build the same system')
        await remote.events.put(BackendEvent('native-turn-1','completed'))
        event=await engine.next_event(self.scope,session['id'])
        self.assertEqual(event['kind'],'completed')
        self.assertEqual(remote.calls[0][2],'opaque-remote-workspace')
        # In-memory protocol double only; not deployed remote-worker evidence.
