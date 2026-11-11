import asyncio
from pathlib import Path
import tempfile
import unittest
from server.engineering_artifacts import EngineeringArtifacts
from server.engineering_finalization import EngineeringFinalization
from server.engineering_jobs import EngineeringJobs
from server.engineering_sessions import BackendEvent,EngineeringSessions,ModelSelection,ProjectScope,SessionError,SqliteSessionStore
from server.local_validation import ValidationSpec
from server.validation_applicability import FileApplicability
from server.validation_jobs import RegisteredValidator,ValidationJobs
from server.tests.test_engineering_sessions import Backend
from server.tests.test_validation_jobs import Worker


class FinalizationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.workspace=self.root/'work';self.workspace.mkdir()
        (self.workspace/'test_river.py').write_text('original river telemetry code')
        self.store=SqliteSessionStore(self.root/'control.sqlite');self.scope=ProjectScope('local-owner','river-monitor')
        self.backend=Backend()
        async def close():pass
        self.backend.close=close
        self.sessions=EngineeringSessions(self.store,self.backend);self.jobs=EngineeringJobs(self.sessions)
        self.session=(await self.sessions.create(self.scope,'work',ModelSelection('exact-model','high')))['id']
        self.artifacts=EngineeringArtifacts(self.store);self.worker=Worker()
        spec=ValidationSpec('python-tests','sha256:'+'a'*64,('/usr/local/bin/python3','-m','unittest','discover','-v'))
        self.checks=ValidationJobs(self.store,self.artifacts,self.worker,{'python-tests':RegisteredValidator('Python',spec,FileApplicability(('**/test_*.py',)))})
        self.captures=[]
        def capture(scope,session):
            manifest=self.artifacts.capture(scope,session,self.workspace);self.captures.append(manifest);return manifest
        self.capture=capture
        self.finalizer=EngineeringFinalization(self.jobs,capture,lambda:self.checks);self.jobs.on_settled=self.finalizer.observe

    async def asyncTearDown(self):
        self.jobs.on_settled=None;self.worker.release.set()
        await self.finalizer.close();await self.checks.close();await self.jobs.close();self.store.close();self.temp.cleanup()

    async def settle_turn(self,kind='completed'):
        state=await self.jobs.start(self.scope,self.session,'Build a river telemetry service; preserve existing devices.')
        await self.backend.events.put(BackendEvent('native-turn-1',kind))
        for _ in range(100):
            if self.jobs.state(self.scope,self.session)['state']=='idle':break
            await asyncio.sleep(.001)
        return state

    async def finish(self):
        await asyncio.gather(*list(self.finalizer.tasks.values()))
        return self.finalizer.list(self.scope,self.session)[-1]

    async def test_completed_turn_captures_before_next_intent_and_checks_exact_bytes_once(self):
        state=await self.settle_turn();result=await self.finish()
        self.assertEqual(result['state'],'local_checks_passed');self.assertEqual(result['runId'],state['run'])
        self.assertEqual(result['artifact']['sha256'],self.captures[0]['sha256'])
        self.assertEqual(self.worker.calls[0][1],result['artifact']['sha256'])
        self.assertEqual(result['acceptance'],'not_established_by_local_checks')
        self.finalizer.observe(self.scope,self.session);await self.jobs.recover(self.scope,self.session)
        self.assertEqual(len(self.captures),1);self.assertEqual(len(self.worker.calls),1)
        self.assertEqual(self.jobs.journal.read(self.scope,self.session)[-2]['kind'],'finalization_local_checks_passed')

    async def test_interrupted_or_failed_turn_does_not_trigger_capture_or_checks(self):
        await self.settle_turn('interrupted');await self.finish_if_any()
        self.assertEqual(self.finalizer.list(self.scope,self.session),[])
        self.assertEqual(self.captures,[]);self.assertEqual(self.worker.calls,[])

    async def finish_if_any(self):await asyncio.gather(*list(self.finalizer.tasks.values()))

    async def test_failed_incomplete_and_empty_selection_are_never_promoted(self):
        self.checks.validators={}
        await self.settle_turn();result=await self.finish()
        self.assertEqual(result['state'],'needs_attention');self.assertEqual(result['checks'],[])
        self.assertEqual(result['plan']['selectionStatus'],'no_available_applicable_checks')

    async def test_failed_check_retains_report_and_needs_attention(self):
        self.worker.receipt_error=True
        await self.settle_turn();result=await self.finish()
        self.assertEqual(result['state'],'needs_attention')
        check=self.checks.get(self.scope,self.session,result['checks'][0])
        self.assertEqual(check['result']['reason'],'validator_unavailable')
        self.assertEqual(len(self.backend.request_ids),1,'No hidden model repair in this supervisor')

    async def test_new_user_turn_supersedes_older_running_check_without_reusing_its_evidence(self):
        self.worker.release.clear();await self.settle_turn()
        await asyncio.to_thread(self.worker.entered.wait,2)
        old=self.finalizer.list(self.scope,self.session)[0]
        original=self.backend.start
        async def next_turn(*args,**kwargs):
            await original(*args,**kwargs);return 'native-turn-2'
        self.backend.start=next_turn
        await self.jobs.start(self.scope,self.session,'Add flood alerts; keep all earlier scope.')
        self.worker.release.set();result=await self.finish()
        self.assertEqual(result['state'],'superseded')
        self.assertEqual(result['artifact'],old['artifact']);self.assertEqual(len(self.captures),1)
        self.assertNotEqual(self.jobs.state(self.scope,self.session)['run'],result['runId'])

    async def test_capture_failure_does_not_hide_completed_turn_or_expose_host_error(self):
        def broken(*args):raise RuntimeError('/private/operator/credentials')
        self.finalizer.capture=broken
        await self.settle_turn();result=await self.finish()
        self.assertEqual(result['state'],'needs_attention');self.assertIsNone(result['artifact'])
        self.assertEqual(self.jobs.state(self.scope,self.session)['last_status'],'completed')
        self.assertNotIn('/private',str(self.jobs.journal.read(self.scope,self.session)))
        self.assertEqual(self.worker.calls,[])

    async def test_restart_retains_original_check_debt_and_does_not_replay_or_recapture(self):
        self.worker.release.clear();await self.settle_turn();await asyncio.to_thread(self.worker.entered.wait,2)
        await self.finalizer.close();self.worker.release.set();await asyncio.gather(*list(self.checks.tasks.values()))
        self.finalizer=EngineeringFinalization(self.jobs,self.capture,lambda:self.checks);self.jobs.on_settled=self.finalizer.observe
        self.finalizer.observe(self.scope,self.session)
        result=self.finalizer.list(self.scope,self.session)[0]
        self.assertEqual(result['state'],'recovery_required')
        self.assertEqual(len(self.captures),1);self.assertEqual(len(self.worker.calls),1)
        with self.assertRaises(SessionError):self.finalizer.list(ProjectScope('other-owner','river-monitor'),self.session)

    async def test_changed_operator_contract_during_check_keeps_pass_historical(self):
        self.worker.release.clear();await self.settle_turn();await asyncio.to_thread(self.worker.entered.wait,2)
        self.worker.policy_digest='changed-reviewed-policy';self.worker.release.set()
        result=await self.finish()
        self.assertEqual(result['state'],'needs_attention')
        check=self.checks.get(self.scope,self.session,result['checks'][0])
        self.assertEqual(check['result']['status'],'passed')
        self.assertNotEqual(check['contractSha256'],self.checks.catalog()[0]['contractSha256'])

    async def test_lost_terminal_event_recovery_captures_verified_existing_run_once(self):
        await self.jobs.start(self.scope,self.session,'Build a local note service.')
        task=self.jobs.tasks[(self.scope,self.session)];task.cancel();await asyncio.gather(task,return_exceptions=True)
        self.backend.observed=BackendEvent('native-turn-1','completed')
        # The test backend's observe method returns this explicitly supplied event.
        async def observe(*args):return self.backend.observed
        self.backend.observe=observe
        await self.jobs.recover(self.scope,self.session);result=await self.finish()
        self.assertEqual(result['state'],'local_checks_passed');self.assertEqual(len(self.backend.request_ids),1)

    def add_late_check(self):
        spec=ValidationSpec('late-contract','sha256:'+'a'*64,('/usr/local/bin/python3','-m','unittest','discover','-v'))
        self.checks.validators['late-contract']=RegisteredValidator('New independent contract',spec,FileApplicability(('test_river.py',)))

    async def test_explicit_recheck_preserves_old_plan_and_reuses_unchanged_receipt(self):
        state=await self.settle_turn();before=await self.finish();self.add_late_check()
        current=await self.finalizer.recheck(self.scope,self.session,state['run'],before['artifact']['id'])
        self.assertEqual(current['state'],'checking');after=await self.finish()
        self.assertEqual(after['state'],'local_checks_passed');self.assertEqual(len(self.worker.calls),2)
        self.assertEqual(after['checks'][0],before['checks'][0])
        self.assertEqual(after['history'],[{'state':before['state'],'payload':{k:v for k,v in before.items() if k not in {'id','sessionId','runId','state','acceptance'}}}])
        again=await self.finalizer.recheck(self.scope,self.session,state['run'],before['artifact']['id'])
        self.assertEqual(again,after);self.assertEqual(len(self.worker.calls),2)
        self.assertEqual(len(self.backend.request_ids),1)

    async def test_recheck_exact_run_artifact_scope_and_unchanged_work_are_required(self):
        state=await self.settle_turn();before=await self.finish();self.add_late_check()
        for scope,run,artifact in [(self.scope,'foreign-run',before['artifact']['id']),
                                  (self.scope,state['run'],'foreign-artifact'),
                                  (ProjectScope('other','river-monitor'),state['run'],before['artifact']['id'])]:
            with self.assertRaises(SessionError):await self.finalizer.recheck(scope,self.session,run,artifact)
        (self.workspace/'test_river.py').write_text('outside completed native run')
        with self.assertRaisesRegex(SessionError,'Working files changed'):
            await self.finalizer.recheck(self.scope,self.session,state['run'],before['artifact']['id'])
        self.assertEqual(self.finalizer.list(self.scope,self.session)[0],before)
        self.assertEqual(len(self.worker.calls),1);self.assertEqual(len(self.backend.request_ids),1)

    async def test_recheck_does_not_duplicate_active_checks_and_newer_intent_wins(self):
        state=await self.settle_turn();before=await self.finish();self.add_late_check();self.worker.release.clear()
        await self.finalizer.recheck(self.scope,self.session,state['run'],before['artifact']['id'])
        with self.assertRaises(SessionError):await self.finalizer.recheck(self.scope,self.session,state['run'],before['artifact']['id'])
        original=self.backend.start
        async def unique_start(*args,**kwargs):
            await original(*args,**kwargs);return 'native-turn-'+str(len(self.backend.request_ids))
        self.backend.start=unique_start
        await self.jobs.start(self.scope,self.session,'Keep the new telemetry requirement.')
        self.worker.release.set();after=await self.finish()
        self.assertEqual(after['state'],'superseded');self.assertEqual(len(self.backend.request_ids),2)
        self.assertEqual(len(after['history']),1)

    async def test_recheck_restart_retains_history_without_replaying_checks(self):
        state=await self.settle_turn();before=await self.finish();self.add_late_check()
        self.worker.entered.clear();self.worker.release.clear()
        await self.finalizer.recheck(self.scope,self.session,state['run'],before['artifact']['id'])
        self.assertTrue(await asyncio.to_thread(self.worker.entered.wait,2))
        await self.finalizer.close()
        self.finalizer=EngineeringFinalization(self.jobs,self.capture,lambda:self.checks)
        self.jobs.on_settled=self.finalizer.observe
        after=self.finalizer.list(self.scope,self.session)[0]
        self.assertEqual(after['state'],'recovery_required');self.assertEqual(len(after['history']),1)
        self.assertEqual(after['history'][0]['payload']['checks'],before['checks'])
        await asyncio.sleep(.01);self.assertEqual(len(self.worker.calls),2)
        self.assertEqual(len(self.backend.request_ids),1)
        with self.assertRaises(SessionError):await self.finalizer.recheck(self.scope,self.session,state['run'],before['artifact']['id'])
        self.worker.release.set()

    async def test_recheck_history_is_bounded_without_truncating_evidence(self):
        import json
        state=await self.settle_turn();before=await self.finish();self.add_late_check()
        row=self.store.db.execute('SELECT payload FROM engineering_finalizations WHERE id=?',(before['id'],)).fetchone()
        payload=json.loads(row[0]);payload['history']=[{'retained':i} for i in range(16)]
        self.finalizer._save(before['id'],before['state'],payload)
        with self.assertRaisesRegex(SessionError,'history is full'):
            await self.finalizer.recheck(self.scope,self.session,state['run'],before['artifact']['id'])
        self.assertEqual(self.finalizer.list(self.scope,self.session)[0]['history'],payload['history'])
        self.assertEqual(len(self.worker.calls),1);self.assertEqual(len(self.backend.request_ids),1)

    async def test_late_failure_can_use_only_existing_root_repair_budget(self):
        import io,zipfile
        state=await self.settle_turn();before=await self.finish();self.add_late_check();self.enable_repair()
        original=self.worker.run
        def run(content,digest,spec,**kwargs):
            result=original(content,digest,spec,**kwargs)
            if spec.name=='late-contract' and 'repair.txt' not in zipfile.ZipFile(io.BytesIO(content)).namelist():
                result.update(status='failed',reason=None,output='Independent late contract fails original source')
            return result
        self.worker.run=run
        await self.finalizer.recheck(self.scope,self.session,state['run'],before['artifact']['id']);await self.drain()
        results=self.finalizer.list(self.scope,self.session)
        self.assertEqual([r['state'] for r in results],['repair_finished','local_checks_passed'])
        self.assertEqual(results[0]['history'][0]['payload']['checks'],before['checks'])
        self.assertEqual(results[0]['repair']['rootRunId'],state['run'])
        self.assertEqual(len(self.backend.request_ids),2)
        self.assertEqual(self.jobs.journal.read(self.scope,self.session)[-1]['kind'],'finalization_local_checks_passed')
        # Changing another operator contract can add checks but cannot refresh the
        # original request's consumed automatic model repair allowance.
        current=results[-1];extra=ValidationSpec('later-contract','sha256:'+'a'*64,('/usr/local/bin/python3','-m','unittest','discover','-v'))
        self.checks.validators['later-contract']=RegisteredValidator('Later failing contract',extra,FileApplicability(('test_river.py',)))
        prior=self.worker.run
        def fail_later(content,digest,spec,**kwargs):
            result=prior(content,digest,spec,**kwargs)
            if spec.name=='later-contract':result.update(status='failed',reason=None,output='Still incomplete')
            return result
        self.worker.run=fail_later
        await self.finalizer.recheck(self.scope,self.session,current['runId'],current['artifact']['id']);await self.drain()
        self.assertEqual(self.finalizer.list(self.scope,self.session)[-1]['state'],'needs_attention')
        self.assertEqual(len(self.backend.request_ids),2)

    def enable_repair(self,*,always_fail=False,auto_complete=True):
        self.finalizer.max_repairs=1;self.finalizer.can_repair=lambda *args:True
        original_run=self.worker.run
        def run(*args,**kwargs):
            result=original_run(*args,**kwargs)
            if always_fail or len(self.worker.calls)==1:result.update(status='failed',reason=None,output='Deliberate runtime assertion failure')
            return result
        self.worker.run=run
        original_start=self.backend.start
        async def start(*args,**kwargs):
            await original_start(*args,**kwargs)
            turn='native-turn-'+str(len(self.backend.request_ids))
            if auto_complete and len(self.backend.request_ids)>1:
                (self.workspace/'repair.txt').write_text('Explicit fixture model repair; not an independently generated implementation')
                await self.backend.events.put(BackendEvent(turn,'completed'))
            return turn
        self.backend.start=start

    async def drain(self):
        for _ in range(500):
            await asyncio.sleep(.005)
            if not self.finalizer.tasks and self.jobs.state(self.scope,self.session)['state']!='running':return
        self.fail('Fixture work did not settle')

    async def test_bounded_repair_uses_same_session_selection_and_retains_failed_package(self):
        self.enable_repair();await self.settle_turn();await self.drain()
        results=self.finalizer.list(self.scope,self.session)
        self.assertEqual([row['state'] for row in results],['repair_finished','local_checks_passed'])
        self.assertEqual(len(self.backend.request_ids),2);self.assertEqual(len(self.captures),2)
        self.assertNotEqual(results[0]['artifact']['sha256'],results[1]['artifact']['sha256'])
        self.assertEqual(results[0]['repair']['runId'],results[1]['runId'])
        self.assertEqual(results[1]['runId'],self.backend.request_ids[-1])
        starts=[call for call in self.backend.calls if call[0]=='start']
        self.assertEqual(starts[0][2],starts[1][2]);self.assertEqual(starts[0][4],starts[1][4])
        self.assertEqual(self.checks.get(self.scope,self.session,results[0]['checks'][0])['result']['status'],'failed')
        accepted=[event for event in self.jobs.journal.read(self.scope,self.session) if event['kind']=='accepted']
        self.assertEqual(accepted[1]['origin'],'automatic_repair')
        self.assertIn('Read every page',accepted[1]['text']);self.assertIn(results[0]['checks'][0],accepted[1]['text'])
        self.assertEqual(self.store.db.execute('select count(*) from engineering_repairs').fetchone()[0],1)

    async def test_repeated_failure_stops_at_durable_attempt_limit_without_scope_deletion(self):
        self.enable_repair(always_fail=True);await self.settle_turn();await self.drain()
        results=self.finalizer.list(self.scope,self.session)
        self.assertEqual([row['state'] for row in results],['repair_finished','needs_attention'])
        self.assertEqual(len(self.backend.request_ids),2)
        self.assertEqual((self.workspace/'test_river.py').read_text(),'original river telemetry code')
        self.finalizer.observe(self.scope,self.session);await self.drain()
        self.assertEqual(len(self.backend.request_ids),2)

    async def test_lost_repair_acceptance_keeps_exact_reserved_uuid_without_replay(self):
        self.enable_repair(auto_complete=False)
        original=self.backend.start
        async def lost(*args,**kwargs):
            result=await original(*args,**kwargs)
            if len(self.backend.request_ids)>1:raise TimeoutError('Lost native repair acknowledgement')
            return result
        self.backend.start=lost
        await self.settle_turn();await self.drain()
        result=self.finalizer.list(self.scope,self.session)[0]
        self.assertEqual(result['state'],'repair_acceptance_uncertain')
        self.assertEqual(self.jobs.state(self.scope,self.session)['state'],'starting')
        self.assertEqual(self.jobs.state(self.scope,self.session)['run'],result['repair']['runId'])
        self.assertEqual(len(self.backend.request_ids),2)
        await self.finalizer.close()
        self.finalizer=EngineeringFinalization(self.jobs,self.capture,lambda:self.checks,max_repairs=1,can_repair=lambda *args:True)
        self.jobs.on_settled=self.finalizer.observe
        self.finalizer.observe(self.scope,self.session)
        self.assertEqual(len(self.backend.request_ids),2)
        from server.engineering_sessions import RecoveredStart
        self.backend.recovered_start=RecoveredStart(result['repair']['runId'],'native-turn-2','completed')
        await self.jobs.recover(self.scope,self.session);await self.drain()
        self.assertEqual(self.finalizer.list(self.scope,self.session)[-1]['state'],'local_checks_passed')
        self.assertEqual(len(self.backend.request_ids),2)

    async def test_user_request_queued_first_wins_over_automatic_repair(self):
        self.enable_repair(auto_complete=False);self.worker.release.clear();await self.settle_turn()
        await asyncio.to_thread(self.worker.entered.wait,2)
        lock=self.jobs._lock(self.scope,self.session)
        await lock.acquire()
        try:
            user=asyncio.create_task(self.jobs.start(self.scope,self.session,'Add flood alerts and preserve original scope.'))
            await asyncio.sleep(.01);self.worker.release.set()
            for _ in range(100):
                if self.finalizer.list(self.scope,self.session)[0]['state']=='repair_requested':break
                await asyncio.sleep(.005)
        finally:lock.release()
        await user;await asyncio.gather(*list(self.finalizer.tasks.values()))
        result=self.finalizer.list(self.scope,self.session)[0]
        self.assertEqual(result['state'],'superseded');self.assertEqual(len(self.backend.request_ids),2)
        starts=[call for call in self.backend.calls if call[0]=='start']
        self.assertEqual(starts[-1][3],'Add flood alerts and preserve original scope.')

    async def test_uncertain_worker_cleanup_failure_never_starts_model_repair(self):
        self.finalizer.max_repairs=1;self.finalizer.can_repair=lambda *args:True;self.worker.receipt_error=True
        await self.settle_turn();result=await self.finish()
        self.assertEqual(result['state'],'needs_attention');self.assertNotIn('repair',result)
        self.assertEqual(len(self.backend.request_ids),1)
